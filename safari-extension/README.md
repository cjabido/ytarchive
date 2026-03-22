# YTArchive Safari Extension

Capture YouTube videos directly into your local YTArchive database.

## Setup (one-time)

1. Make sure the YTArchive backend is running:
   cd backend && python3 -m uvicorn main:app --reload --reload-exclude venv
2. Run the Xcode converter from the project root:
   xcrun safari-web-extension-converter safari-extension/ --project-location . --app-name YTArchive --macos-only
3. Open YTArchive/YTArchive.xcodeproj in Xcode
4. Build and run (Cmd+R)
5. Enable in Safari -> Settings -> Extensions -> YTArchive
6. Grant permission for youtube.com

## Configuration

Edit `safari-extension/config.js` to change the backend URL:
```js
const CONFIG = { API_BASE_URL: 'http://localhost:8000' };
```

## Reloading after changes

- **JS/HTML/CSS changes:** Toggle the extension off/on in Safari -> Settings -> Extensions
- **manifest.json changes or new files added:** Re-run xcrun safari-web-extension-converter and rebuild in Xcode
