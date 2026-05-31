# SVO Observatory — Windy.com Webcam Integration

Connects the **ZWO ASI 224MC** all-sky camera at SVO Observatory to **Windy.com's** live webcam map.

**Live image:** `https://svo.space/allsky/Current.jpg`
**Observatory site:** https://SVO.space/current-sky/

---

## Architecture

AllSky already handles everything — it captures the image and FTPs it to Hostinger automatically. This repo documents the setup and contains the one config file needed to fix caching.

```
ASI 224MC camera
      │
      ▼
  AllSky (captures every N seconds)
      │  FTP upload (built into AllSky)
      ▼
  Hostinger  →  https://svo.space/allsky/Current.jpg
                          │
                          ▼  Windy fetches ~every 60 s
                 windy.com/webcams/...
```

---

## Setup checklist

| Step | Status |
|------|--------|
| AllSky running + capturing | ✅ |
| AllSky FTP upload to Hostinger configured | ✅ |
| Image publicly accessible | ✅ `https://svo.space/allsky/Current.jpg` |
| Cache-Control header fixed | ⚠️ do this first — see below |
| Windy webcam registered | ⏳ do after cache fix |

---

## Step 1 — Fix the cache header on Hostinger

The web server currently tells browsers and CDNs to cache `Current.jpg` for **7 days**. Windy would show a week-old image. Fix this by uploading a `.htaccess` file to the `/allsky/` folder on Hostinger.

**Option A — Hostinger File Manager (easiest)**
1. Log into [hpanel.hostinger.com](https://hpanel.hostinger.com)
2. Go to **Files → File Manager**
3. Navigate to the `public_html/allsky/` folder
4. Click **New File**, name it `.htaccess`
5. Paste the contents of `hostinger/.htaccess` from this repo
6. Save

**Option B — FTP**
1. Connect to Hostinger via FTP (credentials in hPanel → FTP Accounts)
2. Upload `hostinger/.htaccess` to `public_html/allsky/.htaccess`

**Verify it worked:**
```bash
curl -sI https://svo.space/allsky/Current.jpg | grep -i cache-control
# Should show: cache-control: public, max-age=30, must-revalidate
```

---

## Step 2 — Register on Windy.com

Once the cache header is confirmed fixed:

1. Go to [windy.com/webcams/add](https://www.windy.com/webcams/add)
2. Fill in:
   - **Location:** SVO Observatory GPS coordinates
   - **Name:** `SVO Observatory All-Sky Camera`
   - **Description:** ZWO ASI 224MC 180° fisheye all-sky camera
   - **Image URL:** `https://svo.space/allsky/Current.jpg`
3. Submit — Windy reviews and approves within a few days

---

## AllSky FTP upload configuration

AllSky uploads `Current.jpg` to Hostinger automatically. To review or change the FTP settings, open the AllSky web interface on the observatory PC and go to **Settings → FTP**.

Key settings:
| Setting | Value |
|---------|-------|
| FTP host | (Hostinger FTP hostname from hPanel) |
| Remote path | `public_html/allsky/Current.jpg` |
| Upload frequency | every capture (or every N captures) |

---

## Troubleshooting

**Windy shows a stale/old image**
- Confirm the `.htaccess` fix is in place: `curl -sI https://svo.space/allsky/Current.jpg | grep cache`
- Check AllSky FTP logs to confirm uploads are succeeding

**Image stops updating on svo.space**
- Check AllSky is running on the observatory PC
- Check AllSky FTP settings — Hostinger FTP password may have changed
- Confirm disk space on Hostinger account hasn't been exhausted

**Windy can't reach the image**
- Verify `https://svo.space/allsky/Current.jpg` loads in a browser
- Check Hostinger service status at [status.hostinger.com](https://status.hostinger.com)

---

## Files in this repo

| File | Purpose |
|------|---------|
| `hostinger/.htaccess` | Upload to `public_html/allsky/` on Hostinger to fix cache headers |
| `allsky_windy.py` | Optional monitoring companion — logs image update times and staleness warnings |
| `config.ini.example` | Config template for the monitoring companion |
| `systemd/allsky-windy.service` | Run the monitoring companion as a systemd service |

---

## License

MIT
