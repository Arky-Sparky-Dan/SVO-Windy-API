@echo off
REM -----------------------------------------------------------------------
REM install.bat — Register allsky_windy.py as a Windows scheduled task
REM Run this file as Administrator (right-click → Run as administrator)
REM -----------------------------------------------------------------------

echo Installing AllSky-Windy-Uploader scheduled task...

REM Remove old task if it exists
schtasks /delete /tn "AllSky-Windy-Uploader" /f >nul 2>&1

REM Import the task from the XML file in the same folder as this script
schtasks /create /xml "%~dp0allsky-windy-task.xml" /tn "AllSky-Windy-Uploader"

IF %ERRORLEVEL% EQU 0 (
    echo.
    echo Task registered successfully.
    echo.
    echo Next steps:
    echo   1. Edit C:\allsky-windy\config.ini with your FTP credentials
    echo   2. Start the task now:
    echo      schtasks /run /tn "AllSky-Windy-Uploader"
    echo   3. Check it is running:
    echo      schtasks /query /tn "AllSky-Windy-Uploader"
    echo   4. View logs in: C:\allsky-windy\allsky_windy.log
) ELSE (
    echo.
    echo ERROR: Task registration failed. Make sure you ran this as Administrator.
)

pause
