# SVO Observatory — Windy.com Webcam Integration

Connects the **ZWO ASI 224MC** all-sky camera at SVO Observatory to **Windy.com's** live webcam map.

**Live image:** `https://svo.space/allsky/Current.jpg`
**Observatory site:** https://SVO.space/current-sky/

---

## How Windy works

Windy.com uses a **pull model** — you give them a public image URL and they fetch it on their schedule (~every 60 seconds). No upload API exists; the image just needs to be at a stable, publicly accessible URL.

```
ASI 224MC camera
      │
      ▼
  AllSky (captures every N seconds, overwrites Current.jpg)
      │
      ▼
  https://svo.space/allsky/Current.jpg   ← stable public URL
      │
      ▼  Windy fetches ~every 60 s
  windy.com/webcams/...  ← SVO Observatory appears here
```

---

## Current status

| Item | Status |
|------|--------|
| AllSky running + capturing | ✅ |
| Image publicly accessible | ✅ `https://svo.space/allsky/Current.jpg` |
| Cache-Control header fixed | ⚠️ see below |
| Windy webcam registered | ⏳ pending |

---

## ⚠️ Fix required: Cache-Control header

The web server currently sends `Cache-Control: public, max-age=604800` (7 days) for `Current.jpg`. This means CDNs and Windy's fetcher may serve a week-old image instead of the latest frame.

**Fix on the web server** — add a location rule for `Current.jpg` to send a short max-age. Example for **nginx**:

```nginx
location = /allsky/Current.jpg {
    expires 30s;
    add_header Cache-Control "public, max-age=30, must-revalidate";
}
```

For **Apache** (`.htaccess` or vhost config):

```apache
<Files "Current.jpg">
    Header set Cache-Control "public, max-age=30, must-revalidate"
    Header set Expires "30"
</Files>
```

After updating, verify with:

```bash
curl -sI https://svo.space/allsky/Current.jpg | grep -i cache
# Should show: cache-control: public, max-age=30, must-revalidate
```

---

## Register on Windy.com

1. Go to [windy.com/webcams/add](https://www.windy.com/webcams/add)
2. Fill in:
   - **Location:** SVO Observatory coordinates
   - **Name:** e.g. `SVO Observatory All-Sky Camera`
   - **Description:** ZWO ASI 224MC fisheye all-sky camera
   - **Image URL:** `https://svo.space/allsky/Current.jpg`
3. Submit — Windy reviews and approves within a few days

---

## Optional: `allsky_windy.py` monitoring companion

The script in this repo is **not required** for Windy integration (the image is already public), but it provides:

- Live logging of every time the image file updates on disk
- Staleness warnings if AllSky stops capturing
- A `/status` JSON health endpoint
- A local browser preview page at `http://localhost:8080`

### Run it

```bash
cp config.ini.example config.ini
# Edit config.ini — set image_path to your AllSky output file
python3 allsky_windy.py
```

### Run as a systemd service (auto-start on boot)

```bash
nano systemd/allsky-windy.service   # update User and WorkingDirectory
sudo cp systemd/allsky-windy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable allsky-windy
sudo systemctl start allsky-windy
sudo journalctl -u allsky-windy -f  # live logs
```

### Configuration (`config.ini`)

| Key | Default | Description |
|-----|---------|-------------|
| `allsky.image_path` | `~/allsky/tmp/image.jpg` | Path AllSky writes its current frame to |
| `allsky.stale_threshold_seconds` | `120` | Warn if image hasn't updated in this many seconds |
| `server.port` | `8080` | Local HTTP port for the companion server |
| `logging.level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `logging.log_file` | *(blank)* | Optional log file path |

### Endpoints

| URL | Description |
|-----|-------------|
| `GET /image.jpg` | Serves the AllSky image directly from disk |
| `GET /status` | JSON: last update time, age, file size |
| `GET /` | Browser status page with live image preview |

---

## Troubleshooting

**Windy shows a stale image**
- Fix the `Cache-Control` header (see above) — most likely cause

**AllSky stops updating**
- `systemctl status allsky` on the observatory PC
- The monitoring companion will log a staleness warning after 120 s

**Image returns 404 or 500**
- Confirm AllSky is writing to the path in `config.ini`
- Typical path on AllskyTeam/allsky: `/home/pi/allsky/tmp/image.jpg`

---

## ASI 224MC notes

- Full 180° fisheye frames, typically captured every 30–120 seconds at night
- During the day AllSky may slow down or pause capture
- Image is overwritten in-place as `Current.jpg` on each capture

---

## License

MIT
