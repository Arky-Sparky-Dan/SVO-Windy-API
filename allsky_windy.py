#!/usr/bin/env python3
"""
allsky_windy.py — AllSky → Hostinger → Windy.com uploader middleware

Every 60 seconds:
  1. Reads the latest AllSky image from disk
  2. FTPs it to Hostinger as Current.jpg (atomic upload via temp-then-rename)
  3. (Windy POST — ready to enable once the upload endpoint is confirmed)

Usage:
  cp config.ini.example config.ini
  # Edit config.ini with your FTP credentials and Windy API key
  python3 allsky_windy.py
"""

import configparser
import ftplib
import io
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read_dict({
        "allsky": {
            "image_path": "~/allsky/tmp/image.jpg",
        },
        "ftp": {
            "host": "",
            "username": "",
            "password": "",
            "remote_path": "public_html/allsky/Current.jpg",
            "upload_interval_seconds": "60",
            "timeout_seconds": "30",
        },
        "windy": {
            "api_key": "",
            "upload_endpoint": "",
            "enabled": "false",
        },
        "logging": {
            "level": "INFO",
            "log_file": "",
        },
    })
    if Path(path).exists():
        cfg.read(path)
        logging.info("Loaded config from %s", path)
    else:
        logging.warning("config.ini not found — copy config.ini.example and fill in your credentials")
        sys.exit(1)
    return cfg


# ---------------------------------------------------------------------------
# Uploader
# ---------------------------------------------------------------------------

class AllskyWindyUploader:
    def __init__(self, cfg: configparser.ConfigParser):
        self.image_path   = Path(cfg.get("allsky", "image_path")).expanduser().resolve()
        self.interval     = cfg.getint("ftp", "upload_interval_seconds", fallback=60)
        self.ftp_host     = cfg.get("ftp", "host")
        self.ftp_user     = cfg.get("ftp", "username")
        self.ftp_pass     = cfg.get("ftp", "password")
        self.ftp_remote   = cfg.get("ftp", "remote_path")
        self.ftp_timeout  = cfg.getint("ftp", "timeout_seconds", fallback=30)
        self.windy_key    = cfg.get("windy", "api_key", fallback="")
        self.windy_url    = cfg.get("windy", "upload_endpoint", fallback="")
        self.windy_on     = cfg.getboolean("windy", "enabled", fallback=False)

        self._running      = True
        self._upload_count = 0
        self._error_count  = 0

        if not self.ftp_host or not self.ftp_user or not self.ftp_pass:
            logging.error("FTP credentials missing in config.ini — set [ftp] host, username, password")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        logging.info("=" * 60)
        logging.info("AllSky → Windy uploader started")
        logging.info("  Image source : %s", self.image_path)
        logging.info("  FTP host     : %s", self.ftp_host)
        logging.info("  Remote path  : %s", self.ftp_remote)
        logging.info("  Interval     : %d seconds", self.interval)
        logging.info("  Windy POST   : %s", "enabled" if self.windy_on else "disabled (add endpoint to config to enable)")
        logging.info("=" * 60)

        while self._running:
            start = time.monotonic()
            self._tick()
            elapsed = time.monotonic() - start
            sleep_for = max(0, self.interval - elapsed)
            if self._running:
                time.sleep(sleep_for)

    def stop(self):
        logging.info("Shutting down...")
        self._running = False

    # ------------------------------------------------------------------
    # Single upload cycle
    # ------------------------------------------------------------------

    def _tick(self):
        if not self.image_path.exists():
            logging.warning("Image not found: %s — is AllSky running?", self.image_path)
            return

        try:
            image_data = self.image_path.read_bytes()
        except OSError as exc:
            logging.error("Could not read image: %s", exc)
            return

        stat = self.image_path.stat()
        age  = time.time() - stat.st_mtime
        logging.debug("Read %d bytes (file age: %.0f s)", len(image_data), age)

        self._ftp_upload(image_data)

        if self.windy_on and self.windy_url:
            self._windy_post(image_data)

    # ------------------------------------------------------------------
    # FTP upload (atomic: upload to .tmp then rename)
    # ------------------------------------------------------------------

    def _ftp_upload(self, data: bytes):
        remote_path = self.ftp_remote
        remote_dir  = "/".join(remote_path.split("/")[:-1]) or "."
        remote_file = remote_path.split("/")[-1]
        temp_file   = remote_file + ".tmp"

        try:
            with ftplib.FTP() as ftp:
                ftp.connect(self.ftp_host, timeout=self.ftp_timeout)
                ftp.login(self.ftp_user, self.ftp_pass)
                ftp.set_pasv(True)

                if remote_dir and remote_dir != ".":
                    ftp.cwd(remote_dir)

                # Upload to temp file so the live file is never partially written
                ftp.storbinary(f"STOR {temp_file}", io.BytesIO(data))

                # Rename temp → final (atomic on most servers)
                try:
                    ftp.rename(temp_file, remote_file)
                except ftplib.error_perm:
                    # Some servers refuse rename if destination exists — delete first
                    try:
                        ftp.delete(remote_file)
                    except ftplib.error_perm:
                        pass
                    ftp.rename(temp_file, remote_file)

            self._upload_count += 1
            self._error_count = 0  # reset consecutive error count on success
            logging.info(
                "FTP upload OK — %d bytes → %s/%s  (total uploads: %d)",
                len(data), self.ftp_host, remote_path, self._upload_count,
            )

        except ftplib.all_errors as exc:
            self._error_count += 1
            logging.error("FTP upload failed (error #%d): %s", self._error_count, exc)
            if self._error_count >= 5:
                logging.warning("5 consecutive FTP errors — check credentials and host")

    # ------------------------------------------------------------------
    # Windy API POST (enabled once endpoint is confirmed)
    # ------------------------------------------------------------------

    def _windy_post(self, data: bytes):
        """
        POST the image to Windy's webcam upload endpoint.
        Fill in self.windy_url and self.windy_key in config.ini once
        Windy confirms the upload URL and request format.
        """
        import urllib.request
        import urllib.error

        # Placeholder — update when Windy confirms the endpoint format.
        # Expected format (multipart/form-data):
        #   POST {windy_url}
        #   Header: x-windy-api-key: {api_key}
        #   Body:   image=<jpeg bytes>
        #
        # Uncomment and adapt once endpoint is confirmed:
        #
        # boundary = "----WindyUpload"
        # body = (
        #     f"--{boundary}\r\n"
        #     f'Content-Disposition: form-data; name="image"; filename="image.jpg"\r\n'
        #     f"Content-Type: image/jpeg\r\n\r\n"
        # ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
        # req = urllib.request.Request(
        #     self.windy_url,
        #     data=body,
        #     headers={
        #         "x-windy-api-key": self.windy_key,
        #         "Content-Type": f"multipart/form-data; boundary={boundary}",
        #     },
        #     method="POST",
        # )
        # try:
        #     with urllib.request.urlopen(req, timeout=15) as resp:
        #         logging.info("Windy POST OK — HTTP %d", resp.status)
        # except urllib.error.HTTPError as exc:
        #     logging.error("Windy POST failed: HTTP %d %s", exc.code, exc.reason)
        # except urllib.error.URLError as exc:
        #     logging.error("Windy POST error: %s", exc.reason)

        logging.debug("Windy POST placeholder — endpoint not yet configured")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def setup_logging(level_str: str, log_file: str):
    level    = getattr(logging, level_str.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AllSky → Windy.com uploader")
    parser.add_argument("--config", default="config.ini", help="Path to config file")
    args = parser.parse_args()

    # Bootstrap logging before config loads
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")

    cfg      = load_config(args.config)
    log_file = cfg.get("logging", "log_file", fallback="")
    setup_logging(cfg.get("logging", "level", fallback="INFO"), log_file)

    uploader = AllskyWindyUploader(cfg)

    signal.signal(signal.SIGINT,  lambda s, f: uploader.stop())
    signal.signal(signal.SIGTERM, lambda s, f: uploader.stop())

    uploader.run()
    logging.info("Stopped.")


if __name__ == "__main__":
    main()
