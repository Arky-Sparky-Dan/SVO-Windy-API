#!/usr/bin/env python3
"""
allsky_windy.py — AllSky → Hostinger → Windy.com uploader middleware

Every 60 seconds:
  1. Reads the latest AllSky image from disk
  2. FTPs it to Hostinger as Current.jpg (atomic upload via temp-then-rename)
  3. (Windy POST — ready to enable once the upload endpoint is confirmed)

Runs on Windows and Linux. No third-party packages required.

Usage (Windows):
  python allsky_windy.py
  python allsky_windy.py --config C:\\allsky-windy\\config.ini

Usage (Linux):
  python3 allsky_windy.py
"""

import configparser
import ftplib
import io
import logging
import platform
import signal
import sys
import time
from pathlib import Path
from typing import Optional


IS_WINDOWS = platform.system() == "Windows"


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str) -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read_dict({
        "allsky": {
            "image_path": _default_image_path(),
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
    if not Path(path).exists():
        logging.error("config.ini not found at: %s", path)
        logging.error("Copy config.ini.example to config.ini and fill in your credentials.")
        sys.exit(1)
    cfg.read(path)
    logging.info("Loaded config from %s", path)
    return cfg


def _default_image_path() -> str:
    if IS_WINDOWS:
        return r"C:\allsky\tmp\image.jpg"
    return "~/allsky/tmp/image.jpg"


# ---------------------------------------------------------------------------
# Uploader
# ---------------------------------------------------------------------------

class AllskyWindyUploader:
    def __init__(self, cfg: configparser.ConfigParser):
        self.image_path  = Path(cfg.get("allsky", "image_path")).expanduser().resolve()
        self.interval    = cfg.getint("ftp", "upload_interval_seconds", fallback=60)
        self.ftp_host    = cfg.get("ftp", "host")
        self.ftp_user    = cfg.get("ftp", "username")
        self.ftp_pass    = cfg.get("ftp", "password")
        self.ftp_remote  = cfg.get("ftp", "remote_path")
        self.ftp_timeout = cfg.getint("ftp", "timeout_seconds", fallback=30)
        self.windy_key   = cfg.get("windy", "api_key", fallback="")
        self.windy_url   = cfg.get("windy", "upload_endpoint", fallback="")
        self.windy_on    = cfg.getboolean("windy", "enabled", fallback=False)

        self._running      = True
        self._upload_count = 0
        self._error_count  = 0

        if not self.ftp_host or not self.ftp_user or not self.ftp_pass:
            logging.error("FTP credentials missing — set [ftp] host, username, password in config.ini")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        logging.info("=" * 60)
        logging.info("AllSky → Windy uploader started  (platform: %s)", platform.system())
        logging.info("  Image source : %s", self.image_path)
        logging.info("  FTP host     : %s", self.ftp_host)
        logging.info("  Remote path  : %s", self.ftp_remote)
        logging.info("  Interval     : %d seconds", self.interval)
        logging.info("  Windy POST   : %s", "enabled" if self.windy_on else "disabled")
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

        if self.windy_on and self.windy_url and self.windy_key:
            self._windy_post(image_data)

    # ------------------------------------------------------------------
    # FTP upload (atomic: upload to .tmp then rename)
    # ------------------------------------------------------------------

    def _ftp_upload(self, data: bytes):
        remote_path = self.ftp_remote
        parts       = remote_path.replace("\\", "/").split("/")
        remote_dir  = "/".join(parts[:-1]) or "."
        remote_file = parts[-1]
        temp_file   = remote_file + ".tmp"

        try:
            with ftplib.FTP() as ftp:
                ftp.connect(self.ftp_host, timeout=self.ftp_timeout)
                ftp.login(self.ftp_user, self.ftp_pass)
                ftp.set_pasv(True)

                if remote_dir and remote_dir != ".":
                    ftp.cwd(remote_dir)

                # Upload to temp file so Current.jpg is never partially written
                ftp.storbinary(f"STOR {temp_file}", io.BytesIO(data))

                # Rename temp → final
                try:
                    ftp.rename(temp_file, remote_file)
                except ftplib.error_perm:
                    # Some servers refuse rename over existing file — delete first
                    try:
                        ftp.delete(remote_file)
                    except ftplib.error_perm:
                        pass
                    ftp.rename(temp_file, remote_file)

            self._upload_count += 1
            self._error_count  = 0
            logging.info(
                "FTP upload OK — %d bytes → %s/%s  (total: %d)",
                len(data), self.ftp_host, remote_path, self._upload_count,
            )

        except ftplib.all_errors as exc:
            self._error_count += 1
            logging.error("FTP upload failed (error #%d): %s", self._error_count, exc)
            if self._error_count >= 5:
                logging.warning("5 consecutive FTP errors — check credentials and Hostinger FTP host")

    # ------------------------------------------------------------------
    # Windy API POST (stub — enable once endpoint is confirmed)
    # ------------------------------------------------------------------

    def _windy_post(self, data: bytes):
        """
        POST the image to Windy's webcam upload endpoint.
        Set upload_endpoint and enabled = true in config.ini once Windy
        confirms the URL and request format.
        """
        import urllib.request
        import urllib.error

        # Placeholder — uncomment and adapt once Windy confirms the endpoint:
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

        logging.debug("Windy POST not yet configured — add upload_endpoint to config.ini")


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


def _setup_signals(uploader: "AllskyWindyUploader"):
    """Register shutdown signals — SIGINT works on both platforms; SIGTERM on Linux only."""
    signal.signal(signal.SIGINT, lambda s, f: uploader.stop())
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, lambda s, f: uploader.stop())


def main():
    import argparse
    parser = argparse.ArgumentParser(description="AllSky → Windy.com uploader")
    parser.add_argument(
        "--config",
        default="config.ini",
        help="Path to config file (default: config.ini next to this script)",
    )
    args = parser.parse_args()

    # Resolve config path relative to this script so it works when run from
    # Task Scheduler with a different working directory
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / config_path

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")

    cfg      = load_config(str(config_path))
    log_file = cfg.get("logging", "log_file", fallback="")
    setup_logging(cfg.get("logging", "level", fallback="INFO"), log_file)

    uploader = AllskyWindyUploader(cfg)
    _setup_signals(uploader)
    uploader.run()
    logging.info("Stopped.")


if __name__ == "__main__":
    main()
