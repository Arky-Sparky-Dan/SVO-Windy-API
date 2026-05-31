#!/usr/bin/env python3
"""
allsky_windy.py — AllSky camera image server for Windy.com webcam integration

Windy.com uses a PULL model: you host your image at a public URL and Windy
fetches it on their schedule (~every 60 seconds). This script runs a small
HTTP server that serves the latest AllSky output image so Windy can pull it.

Quick start:
  1. cp config.ini.example config.ini  and edit the paths
  2. python3 allsky_windy.py
  3. Expose port 8080 publicly (router port-forward or cloudflared tunnel)
  4. Register your public image URL at windy.com/webcams/add
     e.g.  http://YOUR_PUBLIC_IP:8080/image.jpg

Endpoints:
  GET /image.jpg   — latest AllSky frame (what you give Windy)
  GET /status      — JSON health check (last update time, file size)
  GET /            — human-readable status page
"""

import argparse
import configparser
import json
import logging
import os
import signal
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    "allsky": {
        "image_path": "~/allsky/tmp/image.jpg",
        "stale_threshold_seconds": "120",
    },
    "server": {
        "host": "0.0.0.0",
        "port": "8080",
    },
    "logging": {
        "level": "INFO",
        "log_file": "",
    },
}


def load_config(config_path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    # Load defaults first
    for section, values in DEFAULT_CONFIG.items():
        cfg[section] = values
    if config_path and Path(config_path).exists():
        cfg.read(config_path)
        logging.info("Loaded config from %s", config_path)
    else:
        logging.warning("No config.ini found — using defaults. Copy config.ini.example to config.ini to customise.")
    return cfg


# ---------------------------------------------------------------------------
# Image watcher (background thread)
# ---------------------------------------------------------------------------

class ImageWatcher(threading.Thread):
    """Polls the AllSky image file and logs updates / staleness warnings."""

    def __init__(self, image_path: Path, stale_threshold: int):
        super().__init__(daemon=True, name="ImageWatcher")
        self.image_path = image_path
        self.stale_threshold = stale_threshold
        self._last_mtime: float = 0.0
        self._last_size: int = 0
        self.last_update: datetime | None = None
        self._lock = threading.Lock()

    def get_status(self) -> dict:
        with self._lock:
            if self.last_update is None:
                return {"status": "waiting", "message": "No image seen yet"}
            age = (datetime.now(timezone.utc) - self.last_update).total_seconds()
            stat = self.image_path.stat() if self.image_path.exists() else None
            return {
                "status": "stale" if age > self.stale_threshold else "ok",
                "image_path": str(self.image_path),
                "last_update_utc": self.last_update.isoformat(),
                "age_seconds": round(age, 1),
                "file_size_bytes": stat.st_size if stat else 0,
                "stale_threshold_seconds": self.stale_threshold,
            }

    def run(self):
        logging.info("ImageWatcher started — monitoring %s", self.image_path)
        warned_missing = False
        warned_stale = False

        while True:
            try:
                if not self.image_path.exists():
                    if not warned_missing:
                        logging.warning("Image file not found: %s — is AllSky running?", self.image_path)
                        warned_missing = True
                    time.sleep(5)
                    continue

                warned_missing = False
                stat = self.image_path.stat()

                if stat.st_mtime != self._last_mtime or stat.st_size != self._last_size:
                    self._last_mtime = stat.st_mtime
                    self._last_size = stat.st_size
                    with self._lock:
                        self.last_update = datetime.now(timezone.utc)
                    warned_stale = False
                    logging.info(
                        "Image updated — size: %d bytes  path: %s",
                        stat.st_size,
                        self.image_path,
                    )

                else:
                    age = time.time() - stat.st_mtime
                    if age > self.stale_threshold and not warned_stale:
                        logging.warning(
                            "Image has not updated in %.0f seconds (threshold: %d s) — "
                            "check AllSky is capturing",
                            age,
                            self.stale_threshold,
                        )
                        warned_stale = True

            except Exception as exc:
                logging.error("ImageWatcher error: %s", exc)

            time.sleep(3)


# ---------------------------------------------------------------------------
# HTTP request handler
# ---------------------------------------------------------------------------

class WindyHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests for the Windy webcam image server."""

    # Injected by the server setup below
    image_path: Path = None
    watcher: ImageWatcher = None

    def log_message(self, fmt, *args):
        # Route HTTP access log through Python logging
        logging.debug("HTTP %s - %s", self.address_string(), fmt % args)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/image.jpg", "/image.jpeg"):
            self._serve_image()
        elif path == "/status":
            self._serve_status()
        elif path in ("/", "/index.html"):
            self._serve_index()
        elif path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
        else:
            self.send_error(404, "Not found")

    def _serve_image(self):
        if not self.image_path.exists():
            self.send_error(503, "Image not available — AllSky may not be running")
            return
        try:
            data = self.image_path.read_bytes()
        except OSError as exc:
            self.send_error(500, f"Could not read image: {exc}")
            return

        self.send_response(200)
        self.send_header("Content-Type", "image/jpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)
        logging.info("Served image (%d bytes) to %s", len(data), self.address_string())

    def _serve_status(self):
        status = self.watcher.get_status() if self.watcher else {"status": "unknown"}
        body = json.dumps(status, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_index(self):
        status = self.watcher.get_status() if self.watcher else {}
        age = status.get("age_seconds", "?")
        state = status.get("status", "unknown")
        color = "#2ecc71" if state == "ok" else ("#e74c3c" if state == "stale" else "#f39c12")
        last_update = status.get("last_update_utc", "—")
        size = status.get("file_size_bytes", "?")

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="30">
  <title>AllSky → Windy Image Server</title>
  <style>
    body {{ font-family: monospace; background: #1a1a2e; color: #eee; padding: 2rem; }}
    h1 {{ color: #00d4ff; }}
    .status {{ display: inline-block; padding: .3rem .8rem; border-radius: 4px;
               background: {color}; color: #000; font-weight: bold; }}
    img {{ max-width: 640px; border: 2px solid #333; margin-top: 1rem; display: block; }}
    table {{ border-collapse: collapse; margin-top: 1rem; }}
    td {{ padding: .3rem 1rem .3rem 0; }}
  </style>
</head>
<body>
  <h1>AllSky → Windy Image Server</h1>
  <p>Status: <span class="status">{state.upper()}</span></p>
  <table>
    <tr><td>Last update</td><td>{last_update}</td></tr>
    <tr><td>Image age</td><td>{age} seconds</td></tr>
    <tr><td>File size</td><td>{size} bytes</td></tr>
    <tr><td>Image URL</td><td><a href="/image.jpg" style="color:#00d4ff">/image.jpg</a></td></tr>
    <tr><td>JSON status</td><td><a href="/status" style="color:#00d4ff">/status</a></td></tr>
  </table>
  <img src="/image.jpg?t={int(time.time())}" alt="Latest AllSky frame">
  <p style="color:#888;font-size:.8rem">Page auto-refreshes every 30 seconds.</p>
</body>
</html>"""
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def setup_logging(level_str: str, log_file: str):
    level = getattr(logging, level_str.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def make_handler_class(image_path: Path, watcher: ImageWatcher):
    """Return a handler class with image_path and watcher baked in."""
    class Handler(WindyHandler):
        pass
    Handler.image_path = image_path
    Handler.watcher = watcher
    return Handler


def main():
    parser = argparse.ArgumentParser(description="AllSky → Windy webcam image server")
    parser.add_argument("--config", default="config.ini", help="Path to config file (default: config.ini)")
    args = parser.parse_args()

    cfg = load_config(args.config)

    setup_logging(
        cfg.get("logging", "level", fallback="INFO"),
        cfg.get("logging", "log_file", fallback=""),
    )

    image_path = Path(cfg.get("allsky", "image_path")).expanduser().resolve()
    stale_threshold = cfg.getint("allsky", "stale_threshold_seconds", fallback=120)
    host = cfg.get("server", "host", fallback="0.0.0.0")
    port = cfg.getint("server", "port", fallback=8080)

    logging.info("=" * 60)
    logging.info("AllSky → Windy Image Server starting")
    logging.info("  AllSky image : %s", image_path)
    logging.info("  Listening on : http://%s:%d", host, port)
    logging.info("  Image URL    : http://<your-public-ip>:%d/image.jpg", port)
    logging.info("=" * 60)

    watcher = ImageWatcher(image_path, stale_threshold)
    watcher.start()

    handler_class = make_handler_class(image_path, watcher)
    server = HTTPServer((host, port), handler_class)

    def shutdown(sig, frame):
        logging.info("Shutting down...")
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        server.serve_forever()
    except Exception as exc:
        logging.error("Server error: %s", exc)
        sys.exit(1)

    logging.info("Server stopped.")


if __name__ == "__main__":
    main()
