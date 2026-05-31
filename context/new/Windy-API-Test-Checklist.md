# Windy API Test Checklist

Use this checklist to verify the Windy upload integration.

- [ ] Confirm `config.ini` has valid FTP credentials.
- [ ] Confirm `config.ini` has the correct `remote_path` and `upload_interval_seconds`.
- [ ] Confirm `config.ini` has a valid `windy.api_key`.
- [ ] Confirm `windy.upload_endpoint` is set if Windy POST is enabled.
- [ ] Run `allsky_windy.py` locally and check that the image uploads to Hostinger.
- [ ] Verify `https://svo.space/allsky/Current.jpg` returns the fresh image.
- [ ] Confirm HTTP caching headers are correct for `Current.jpg`.
- [ ] If Windy POST is enabled, verify the response from the upload endpoint.
- [ ] Look for errors in the script log and fix any FTP or API failures.

If these pass, the Windy API helpers are working correctly.