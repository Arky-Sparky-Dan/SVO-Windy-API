# SVO Observatory — Windy.com Webcam Integration

Connects the **ZWO ASI 224MC** all-sky camera at SVO Observatory to **Windy.com's** live webcam map.

**Live image:** `https://svo.space/allsky/Current.jpg`
**Observatory site:** https://SVO.space/current-sky/

---

## How it works

Windy.com uses a **pull model** — you give them a public URL and they fetch it on their schedule (~every 60 seconds). No upload API exists and no API key is required for webcam registration.

```
ASI 224MC camera
      │
      ▼
  AllSky (captures & FTPs image to Hostinger automatically)
      │
      ▼
  https://svo.space/allsky/Current.jpg   ← stable public URL
      │
      ▼  Windy fetches ~every 60 s
  windy.com/webcams/...
```

---

## Setup — 3 steps

### Step 1 — Fix cache headers on Hostinger

The server currently caches `Current.jpg` for 7 days. Windy would show a week-old image without this fix.

1. Log into [hpanel.hostinger.com](https://hpanel.hostinger.com)
2. **Files → File Manager** → navigate to `public_html/allsky/`
3. Create a new file called `.htaccess` and paste:

```apache
<Files "Current.jpg">
    Header set Cache-Control "public, max-age=30, must-revalidate"
    Header unset Pragma
</Files>
```

4. Save, then verify:
```
curl -sI https://svo.space/allsky/Current.jpg | grep cache-control
# Should show: max-age=30
```

The file is also at `hostinger/.htaccess` in this repo for reference.

---

### Step 2 — Register on Windy.com

1. Go to [windy.com/webcams/add](https://www.windy.com/webcams/add)
2. Fill in:
   - **Location:** SVO Observatory GPS coordinates
   - **Name:** `SVO Observatory All-Sky Camera`
   - **Description:** ZWO ASI 224MC 180° all-sky camera
   - **Image URL:** `https://svo.space/allsky/Current.jpg`
3. Submit — Windy approves within a few days

> The Windy API key is **not needed** for webcam registration. It is only used if you later want to query Windy's webcam database via their read-only API.

---

### Step 3 — Done

Windy will start fetching `Current.jpg` automatically once approved. No script needs to run on the observatory PC for Windy to work — AllSky handles the upload natively.

---

## Optional: image freshness monitor

`allsky_windy.py` is an optional companion that watches the AllSky output file on disk and logs a warning if it stops updating. Useful for catching AllSky outages early.

### Run manually
```cmd
cd C:\allsky-windy
python allsky_windy.py
```

### Run on boot (Windows Task Scheduler)

1. Edit `windows\allsky-windy-task.xml` — update the Python and script paths
2. Right-click `windows\install.bat` → **Run as administrator**

```cmd
# Check status
schtasks /query /tn "AllSky-Windy-Uploader"

# View logs
type C:\allsky-windy\allsky_windy.log
```

### Configuration (`config.ini`)

Copy `config.ini.example` → `config.ini` and set `image_path` to where AllSky writes its image.

| Key | Default | Description |
|-----|---------|-------------|
| `allsky.image_path` | `C:\allsky\tmp\image.jpg` | Path AllSky writes its current frame to |
| `allsky.stale_threshold_seconds` | `120` | Warn if image hasn't updated in this many seconds |
| `logging.level` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `logging.log_file` | *(blank)* | Optional log file path |

---

## Troubleshooting

**Windy shows a stale image**
Fix the `.htaccess` cache header (Step 1). Run `curl -sI https://svo.space/allsky/Current.jpg | grep cache-control` to confirm.

**Image stops updating on svo.space**
Check AllSky is running and its FTP upload is configured. The monitor script will log a staleness warning after 120 s.

**Windy registration not approved**
Contact webcams@windy.com — approvals normally take 1–3 days.

---

## Issue reporting (for Randy)

Drop screenshots in `screenshots/new/` and notes/logs in `context/new/`, then open a pull request.

---

## Files

| File | Purpose |
|------|---------|
| `allsky_windy.py` | Optional image freshness monitor |
| `config.ini.example` | Config template |
| `hostinger/.htaccess` | Upload to `public_html/allsky/` on Hostinger |
| `windows/allsky-windy-task.xml` | Task Scheduler definition |
| `windows/install.bat` | Registers the scheduled task (run as Admin) |
| `docs/how-to.docx` | Step-by-step install guide for Randy |

---

## License

MIT
