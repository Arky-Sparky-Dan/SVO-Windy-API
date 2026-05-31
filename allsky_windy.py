#!/usr/bin/env python3
"""
allsky_windy.py — AllSky image freshness monitor for SVO Observatory

Watches the AllSky output image on disk and logs whenever it updates.
Warns if the image goes stale so you know AllSky has stopped capturing.

Windy.com integration does NOT require this script to run.
Windy pulls directly from https://svo.space/allsky/Current.jpg on its
own schedule. This script is a convenience tool only.

Usage (Windows):
  python allsky_windy.py
  python allsky_windy.py --config C:\\allsky-windy\\config.ini

Usage (Linux):
  python3 allsky_windy.py
"""

import argparse
import configparser
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
            "image_path": r"C:\allsky\tmp\image.jpg" if IS_WINDOWS else "~/allsky/tmp/image.jpg",
            "stale_threshold_seconds": "120",
        },
        "logging": {
            "level": "INFO",
            "log_file": "",
        },
    })
    if not Path(path).exists():
        logging.warning("config.ini not found — using defaults. Copy config.ini.example to get started.")
        return cfg
    cfg.read(path)
    logging.info("Loaded config from %s", path)
    return cfg


# ---------------------------------------------------------------------------
# Monitor
# ---------------------------------------------------------------------------

class ImageMonitor:
    def __init__(self, cfg: configparser.ConfigParser):
        self.image_path = Path(cfg.get("allsky", "image_path")).expanduser().resolve()
        self.stale_threshold = cfg.getint("allsky", "stale_threshold_seconds", fallback=120)
        self._running = True
        self._last_mtime: float = 0.0
        self._update_count: int = 0

    def run(self):
        logging.info("=" * 60)
        logging.info("AllSky image monitor started  (platform: %s)", platform.system())
        logging.info("  Watching : %s", self.image_path)
        logging.info("  Stale after : %d seconds", self.stale_threshold)
        logging.info("  Windy pulls from : https://svo.space/allsky/Current.jpg")
        logging.info("=" * 60)

        warned_missing = False
        warned_stale   = False

        while self._running:
            try:
                if not self.image_path.exists():
                    if not warned_missing:
                        logging.warning("Image not found: %s — is AllSky running?", self.image_path)
                        warned_missing = True
                    time.sleep(5)
                    continue

                warned_missing = False
                stat = self.image_path.stat()

                if stat.st_mtime != self._last_mtime:
                    self._last_mtime  = stat.st_mtime
                    self._update_count += 1
                    warned_stale = False
                    logging.info(
                        "Image updated — %d bytes  (update #%d)",
                        stat.st_size, self._update_count,
                    )
                else:
                    age = time.time() - stat.st_mtime
                    if age > self.stale_threshold and not warned_stale:
                        logging.warning(
                            "Image has not updated in %.0f s (threshold: %d s) — "
                            "check AllSky is capturing",
                            age, self.stale_threshold,
                        )
                        warned_stale = True

            except Exception as exc:
                logging.error("Monitor error: %s", exc)

            time.sleep(5)

    def stop(self):
        logging.info("Stopping monitor...")
        self._running = False


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
    parser = argparse.ArgumentParser(description="AllSky image freshness monitor")
    parser.add_argument(
        "--config", default="config.ini",
        help="Path to config file (default: config.ini next to this script)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = Path(__file__).parent / config_path

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-8s  %(message)s")

    cfg     = load_config(str(config_path))
    setup_logging(cfg.get("logging", "level", fallback="INFO"),
                  cfg.get("logging", "log_file", fallback=""))

    monitor = ImageMonitor(cfg)

    signal.signal(signal.SIGINT, lambda s, f: monitor.stop())
    if not IS_WINDOWS:
        signal.signal(signal.SIGTERM, lambda s, f: monitor.stop())

    monitor.run()
    logging.info("Stopped.")


if __name__ == "__main__":
    main()
