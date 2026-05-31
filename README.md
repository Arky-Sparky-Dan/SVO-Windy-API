# SVO Observatory — Windy.com Webcam Integration

Uploads the **ZWO ASI 224MC** all-sky camera image from SVO Observatory to **Windy.com** every 60 seconds.

**Live image:** `https://svo.space/allsky/Current.jpg`
**Observatory site:** https://SVO.space/current-sky/
**Platform:** Windows Embedded PC + AllSky

---

## How it works

```
ASI 224MC camera
      │
      ▼
  AllSky on Windows PC (captures every N seconds, writes image to disk)
      │
      ▼
  allsky_windy.py  (Windows Task Scheduler, runs every 60 s)
      ├─── FTP upload ──→  Hostinger  →  https://svo.space/allsky/Current.jpg
      └─── POST image ──→  Windy.com API  (enabled once endpoint is confirmed)
```

---

## Setup

### Step 1 — Fix the cache header on Hostinger

Upload `hostinger/.htaccess` to `public_html/allsky/` via Hostinger File Manager so Windy always gets a fresh image.

1. Log into [hpanel.hostinger.com](https://hpanel.hostinger.com)
2. **Files → File Manager** → navigate to `public_html/allsky/`
3. **New File** → name it `.htaccess`, paste this content and save:

```apache
<Files "Current.jpg">
    Header set Cache-Control "public, max-age=30, must-revalidate"
    Header unset Pragma
</Files>
```

Verify:
```
curl -sI https://svo.space/allsky/Current.jpg | grep -i cache-control
# Should show: max-age=30
```

---

### Step 2 — Install Python on the observatory PC

1. Download Python 3.9+ from [python.org/downloads](https://www.python.org/downloads/)
2. During install, check **"Add Python to PATH"**
3. Verify in a Command Prompt:
   ```
   python --version
   ```

No third-party packages are needed — the script uses only the Python standard library.

---

### Step 3 — Install the script

1. Download this repo as a ZIP from GitHub (green **Code** button → Download ZIP)  
   — or clone if Git is installed: `git clone https://github.com/Arky-Sparky-Dan/SVO-Windy-API.git`
2. Copy the folder to `C:\allsky-windy\`
3. Copy `config.ini.example` → `config.ini`
4. Edit `config.ini` — fill in the FTP credentials and AllSky image path:

```ini
[allsky]
image_path = C:\allsky\tmp\image.jpg   ← adjust to where AllSky writes its image

[ftp]
host     = files.hostinger.com
username = YOUR_FTP_USERNAME
password = YOUR_FTP_PASSWORD

[logging]
log_file = C:\allsky-windy\allsky_windy.log
```

---

### Step 4 — Test it manually first

Open a Command Prompt, navigate to the folder and run:

```cmd
cd C:\allsky-windy
python allsky_windy.py
```

You should see a line like:
```
FTP upload OK — 190432 bytes → files.hostinger.com/public_html/allsky/Current.jpg  (total: 1)
```

Open `https://svo.space/allsky/Current.jpg` in a browser to confirm the image updated.  
Press **Ctrl+C** to stop.

---

### Step 5 — Register as a Windows scheduled task (auto-start)

**Edit `windows\allsky-windy-task.xml` first** — update the Python path and script path:

```xml
<Command>C:\Python312\python.exe</Command>   ← match your Python install path
<Arguments>C:\allsky-windy\allsky_windy.py --config C:\allsky-windy\config.ini</Arguments>
<WorkingDirectory>C:\allsky-windy</WorkingDirectory>
```

Then run `windows\install.bat` as Administrator (right-click → Run as administrator).

Or import manually:
1. Open **Task Scheduler** (search in Start menu)
2. **Action → Import Task...** → select `windows\allsky-windy-task.xml`
3. Click OK

Verify it's registered:
```cmd
schtasks /query /tn "AllSky-Windy-Uploader"
```

The task starts automatically on boot and restarts itself if it crashes.

---

### Step 6 — Enable Windy POST uploads

Once Windy confirms their upload endpoint:

1. Set `upload_endpoint = <url>` in `config.ini`
2. Confirm `api_key` is set
3. Set `enabled = true`
4. Restart the task:
   ```cmd
   schtasks /end /tn "AllSky-Windy-Uploader"
   schtasks /run /tn "AllSky-Windy-Uploader"
   ```

---

## Finding the AllSky image path on Windows

AllSky writes the current frame to a configurable path. Check AllSky's settings for the output directory. Common locations:

- `C:\allsky\tmp\image.jpg`
- `C:\Users\<username>\allsky\tmp\image.jpg`
- Wherever AllSky was installed + `\tmp\image.jpg`

Run this in PowerShell to search:
```powershell
Get-ChildItem C:\ -Recurse -Filter "image.jpg" -ErrorAction SilentlyContinue | Select-Object FullName
```

---

## Troubleshooting

**FTP upload fails**
- Check credentials in `config.ini` — host/username/password
- Try the Hostinger FTP hostname from hPanel (may differ from `files.hostinger.com`)
- Check the log file: `C:\allsky-windy\allsky_windy.log`

**Image not found warning**
- Confirm AllSky is running and capturing
- Check `image_path` in `config.ini` points to the right file

**Task doesn't start on boot**
- Open Task Scheduler, find `AllSky-Windy-Uploader`, check Last Run Result
- Re-run `install.bat` as Administrator

**Windy shows old image**
- Confirm the `.htaccess` cache fix is applied (Step 1)
- Run: `curl -sI https://svo.space/allsky/Current.jpg | grep cache-control`

---

## Files

| File | Purpose |
|------|---------|
| `allsky_windy.py` | Main uploader — works on Windows and Linux |
| `config.ini.example` | Config template — copy to `config.ini` |
| `hostinger/.htaccess` | Upload to `public_html/allsky/` on Hostinger |
| `windows/allsky-windy-task.xml` | Windows Task Scheduler definition |
| `windows/install.bat` | Registers the scheduled task (run as Admin) |
| `context/new/` | Drop logs/notes about issues here for review |
| `screenshots/new/` | Drop screenshots of issues here for review |

---

## Issue reporting

Randy: drop screenshots in `screenshots/new/` and notes/logs in `context/new/`, then open a pull request. We'll diagnose and push fixes.

---

## License

MIT
