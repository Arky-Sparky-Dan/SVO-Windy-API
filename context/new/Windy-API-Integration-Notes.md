# Windy API Integration Notes

## Purpose

This document describes the Windy.com API integration used by `allsky_windy.py`.

## Current flow

1. `allsky_windy.py` reads the latest AllSky image from disk.
2. It uploads the image to Hostinger using FTP.
3. The image is published at `https://svo.space/allsky/Current.jpg`.
4. Windy fetches the image from that URL.

## Windy API details

- The script currently prepares Windy integration but may require an endpoint confirmation.
- `config.ini` includes Windy settings:
  - `api_key`
  - `upload_endpoint`
  - `enabled`

## Notes

- Ensure the Hostinger `public_html/allsky/` folder has the `.htaccess` cache-control rule.
- Confirm the `upload_endpoint` is correct if Windy expects a specific POST endpoint.
- If Windy requires a separate upload payload, document its JSON format and headers.

## Recommendations

- Add explicit logging around the Windy upload path so failures are easy to diagnose.
- Keep the API key out of source control and only in `config.ini`.
- Verify the `enabled` flag before trying Windy POST requests.