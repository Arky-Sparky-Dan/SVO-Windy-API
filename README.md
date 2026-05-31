# AllSky → Windy.com Webcam Image Server

Serves your AllSky all-sky camera image over HTTP so **Windy.com** can pull it for their live webcam map.

Built for the **ZWO ASI 224MC** camera running **AllSky** on a Raspberry Pi / Linux observatory PC.

---

## How it works

Windy.com uses a **pull model** for webcam images — you host your latest image at a public URL, and Windy fetches it on their schedule (approximately every 60 seconds). This script:

1. Watches the image file that AllSky continuously overwrites with each capture
2. Serves it at `http://YOUR_IP:8080/image.jpg`
3. Logs image freshness so you can see it's updating

```
AllSky (ASI 224MC)
       │  writes image every N seconds
       ▼
  ~/allsky/tmp/image.jpg
       │
       ▼
  allsky_windy.py  (HTTP server, port 8080)
       │
       ▼  Windy.com pulls /image.jpg ~every 60 s
  windy.com/webcams/...  ←  your observatory appears here
```

---

## Requirements

- Python 3.9 or newer (standard library only — no pip installs needed)
- AllSky running and writing images to `~/allsky/tmp/image.jpg`
- A way to expose port 8080 publicly (see [Making it public](#making-it-public))

---

## Installation

```bash
# 1. Clone the repo onto your observatory PC
git clone https://github.com/YOUR_USERNAME/SVO-Windy-API.git
cd SVO-Windy-API

# 2. Copy and edit the config file
cp config.ini.example config.ini
nano config.ini        # set image_path to your AllSky output image

# 3. Run it
python3 allsky_windy.py

# Open http://localhost:8080 in a browser to confirm it's working
```

---

## Configuration (`config.ini`)

| Key | Default | Description |
|-----|---------|-------------|
| `allsky.image_path` | `~/allsky/tmp/image.jpg` | Full path to the AllSky live image |
| `allsky.stale_threshold_seconds` | `120` | Warn if image hasn't updated in this many seconds |
| `server.host` | `0.0.0.0` | Bind address (`0.0.0.0` = all interfaces) |
| `server.port` | `8080` | HTTP port |
| `logging.level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `logging.log_file` | *(blank)* | Optional log file path |

---

## Making it public

Windy needs to reach your image from the internet. Pick one option:

### Option A — Router port forwarding (recommended for permanent setups)
1. Log into your router admin page (usually `192.168.1.1`)
2. Add a port forwarding rule: **external port 8080 → your observatory PC IP:8080**
3. Find your public IP at [whatismyip.com](https://www.whatismyip.com)
4. Your image URL will be: `http://YOUR_PUBLIC_IP:8080/image.jpg`

### Option B — Cloudflare Tunnel (no router access needed, free)
```bash
# Install cloudflared on the observatory PC
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o cloudflared
chmod +x cloudflared

# Start a quick tunnel (gives you a public https URL)
./cloudflared tunnel --url http://localhost:8080
# Copy the https://xxxx.trycloudflare.com URL — use that as your Windy image URL
```

### Option C — ngrok (simplest for testing)
```bash
# Install ngrok: https://ngrok.com/download
ngrok http 8080
# Copy the https://xxxx.ngrok.io URL
```

---

## Register your webcam on Windy.com

1. Go to [windy.com/webcams/add](https://www.windy.com/webcams/add)
2. Fill in your location, camera name (e.g. "SVO Observatory All-Sky"), and description
3. In the **image URL** field, paste your public URL: `http://YOUR_PUBLIC_IP:8080/image.jpg`
4. Submit for review — Windy typically approves within a few days

---

## Run as a systemd service (auto-start on boot)

```bash
# Edit the service file first — update User and WorkingDirectory paths
nano systemd/allsky-windy.service

sudo cp systemd/allsky-windy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable allsky-windy
sudo systemctl start allsky-windy

# Check it's running
sudo systemctl status allsky-windy

# Live logs
sudo journalctl -u allsky-windy -f
```

---

## HTTP endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /image.jpg` | Latest AllSky frame — this is the URL you give Windy |
| `GET /status` | JSON health check (last update time, file size, age) |
| `GET /` | Browser-friendly status page with live image preview |

---

## Troubleshooting

**Image not found (503 error)**
- Confirm AllSky is running: `systemctl status allsky`
- Check the `image_path` in `config.ini` matches where AllSky actually writes its image
- On AllskyTeam/allsky the path is typically `/home/pi/allsky/tmp/image.jpg`

**Image appears stale / not updating**
- Check AllSky is capturing: open AllSky's web interface
- The `stale_threshold_seconds` warning in the logs will tell you how old the image is

**Windy can't reach the image**
- Confirm the server is running: `curl http://localhost:8080/image.jpg -o /tmp/test.jpg`
- Confirm it's reachable from outside: try your public URL from a mobile browser (not on your home WiFi)
- Check your router's port forwarding rule or confirm the tunnel is still running

---

## ASI 224MC + AllSky notes

- AllSky captures full 180° fisheye frames from the ASI 224MC at whatever interval you configure (typically 30–120 seconds at night)
- The script monitors the output file and logs whenever it changes
- During the day AllSky may capture less frequently or stop — the stale warning will alert you

---

## License

MIT
