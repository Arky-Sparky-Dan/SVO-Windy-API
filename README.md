# SVO Observatory — Windy.com Webcam Integration

Uploads the **ZWO ASI 224MC** all-sky camera image from SVO Observatory to **Windy.com** every 60 seconds.

**Live image:** `https://svo.space/allsky/Current.jpg`
**Observatory site:** https://SVO.space/current-sky/

---

## How it works

```
ASI 224MC camera
      │
      ▼
  AllSky (captures every N seconds, writes image to disk)
      │
      ▼
  allsky_windy.py  (runs every 60 s)
      ├─── FTP upload ──→  Hostinger  →  https://svo.space/allsky/Current.jpg
      └─── POST image ──→  Windy.com API  (enabled once endpoint is confirmed)
```

---

## Setup

### 1 — Fix the cache header on Hostinger

Upload `hostinger/.htaccess` to the `public_html/allsky/` folder on Hostinger so Windy always fetches a fresh image instead of a 7-day-old cached one.

**Via Hostinger File Manager:**
1. Log into [hpanel.hostinger.com](https://hpanel.hostinger.com)
2. **Files → File Manager** → navigate to `public_html/allsky/`
3. **New File** → name it `.htaccess`
4. Paste the contents below and save:

```apache
<Files "Current.jpg">
    Header set Cache-Control "public, max-age=30, must-revalidate"
    Header unset Pragma
</Files>
```

Verify it worked:
```bash
curl -sI https://svo.space/allsky/Current.jpg | grep -i cache-control
# Should show: cache-control: public, max-age=30, must-revalidate
```

---

### 2 — Install the uploader on the observatory PC

```bash
git clone https://github.com/Arky-Sparky-Dan/SVO-Windy-API.git
cd SVO-Windy-API

cp config.ini.example config.ini
nano config.ini   # fill in FTP credentials and Windy API key
```

**Run it:**
```bash
python3 allsky_windy.py
```

---

### 3 — Configure (`config.ini`)

| Section | Key | Description |
|---------|-----|-------------|
| `[allsky]` | `image_path` | Path AllSky writes its latest frame to |
| `[ftp]` | `host` | Hostinger FTP hostname (from hPanel → FTP Accounts) |
| `[ftp]` | `username` | FTP username |
| `[ftp]` | `password` | FTP password |
| `[ftp]` | `remote_path` | Destination path on server |
| `[ftp]` | `upload_interval_seconds` | How often to upload (default: 60) |
| `[windy]` | `api_key` | Your Windy.com API key |
| `[windy]` | `upload_endpoint` | Windy upload URL — fill in once confirmed |
| `[windy]` | `enabled` | Set to `true` to enable Windy POST uploads |

---

### 4 — Run as a service (auto-start on boot)

```bash
nano systemd/allsky-windy.service   # update User and WorkingDirectory
sudo cp systemd/allsky-windy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable allsky-windy
sudo systemctl start allsky-windy

# Check status
sudo systemctl status allsky-windy

# Live logs
sudo journalctl -u allsky-windy -f
```

---

### 5 — Enable Windy POST uploads

Once Windy confirms the upload endpoint:

1. Set `upload_endpoint = <url from Windy>` in `config.ini`
2. Confirm `api_key` is set
3. Set `enabled = true`
4. Restart the service: `sudo systemctl restart allsky-windy`

---

## Hostinger FTP credentials

Find them in **hPanel → Hosting → FTP Accounts**.

The FTP root maps to `public_html/`, so `remote_path = public_html/allsky/Current.jpg` puts the file at `https://svo.space/allsky/Current.jpg`.

---

## Troubleshooting

**FTP upload fails**
- Double-check host/username/password in `config.ini`
- Try connecting manually: `ftp files.hostinger.com`
- Hostinger FTP hostname may vary — check hPanel for the exact value

**Image on svo.space is stale**
- Check the script is running: `sudo systemctl status allsky-windy`
- Check logs for FTP errors: `sudo journalctl -u allsky-windy -f`
- Confirm AllSky is writing to the path in `config.ini`

**Windy shows old image**
- Confirm the `.htaccess` fix is in place (Step 1 above)
- Run: `curl -sI https://svo.space/allsky/Current.jpg | grep cache-control`

---

## Files

| File | Purpose |
|------|---------|
| `allsky_windy.py` | Main uploader — FTP + Windy POST |
| `config.ini.example` | Config template — copy to `config.ini` |
| `hostinger/.htaccess` | Upload to `public_html/allsky/` on Hostinger |
| `systemd/allsky-windy.service` | systemd unit for auto-start |

---

## License

MIT
