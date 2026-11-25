# ScamShield — Mobile Testing Checklist & Real-Device Matrix

> **Rule Compliance Notice (AGENTS.md):** Features requiring physical hardware, cellular SMS networks, or real mobile device OS integrations are explicitly flagged below as **"NOT VERIFIED - manual test needed"**. Do not claim these features have been verified unless tested on physical hardware.

---

## 1. Feature Verification Status Matrix

| ID | Feature Description | Target Environment | Verification Status | Automated Test Reference | Notes & Manual Verification Instructions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **MOB-01** | PWA Manifest Parsing | Browser / Chromium | **VERIFIED** | Static Asset Inspection | `static/manifest.webmanifest` verified with valid JSON, theme color, icons, and `share_target`. |
| **MOB-02** | Web Share Target Backend Handler | FastAPI Backend | **VERIFIED** | `tests/test_stage5_8.py::test_share_target_flow` | `POST /share-target` receives form-data, stores ephemeral item, redirects to `/#scan?share_token=`, single-use consumed on GET. |
| **MOB-03** | Ephemeral Share Store Expiry (5-min TTL) | FastAPI In-Memory | **VERIFIED** | `tests/test_stage5_8.py::test_share_target_expiry` | Expired tokens return 404; memory is cleared without leaks. |
| **MOB-04** | Multi-Screenshot Batch Upload (up to 5 files) | Frontend Client | **VERIFIED** | Functional Browser QA | Verified file filtering (images <=5MB), preview grid, thumbnail removal, and batch OCR. |
| **MOB-05** | Android System Share Sheet Integration (WhatsApp/SMS) | Physical Android Phone | **NOT VERIFIED - manual test needed** | None (Requires Android OS) | **Manual Test Steps:**<br>1. Install PWA on Android Chrome via "Add to Home screen".<br>2. Open WhatsApp, select a suspicious message, tap 'Share'.<br>3. Verify 'ScamShield' appears in the Android system Share sheet.<br>4. Tap ScamShield and verify message pre-fills into scanner. |
| **MOB-06** | Android Screenshot Direct Share | Physical Android Phone | **NOT VERIFIED - manual test needed** | None (Requires Android OS) | **Manual Test Steps:**<br>1. Take a screenshot in WhatsApp.<br>2. From Android gallery or screenshot popup, tap 'Share' -> 'ScamShield'.<br>3. Verify screenshot uploads to `/share-target` and triggers OCR review. |
| **MOB-07** | PWA Standalone Mode Launch & Splash Screen | Physical Android Phone | **NOT VERIFIED - manual test needed** | None (Requires Android OS) | Verify app opens in standalone window without Chrome browser address bar. |
| **MOB-08** | iOS Safari Screenshot Workflow | Physical iPhone / iOS | **NOT VERIFIED - manual test needed** | None (Requires iOS Safari) | iOS does not support Web Share Target. Verify user can upload screenshot via Safari file chooser and review OCR. |
| **MOB-09** | Touch Target Accessibility on 360px Viewport | Chrome DevTools (360px) | **VERIFIED** | Visual Inspection | Verified buttons have minimum 48px height and form inputs do not overflow horizontally. |
| **MOB-10** | Senior Large Text Mode on Mobile | Chrome DevTools (390px) | **VERIFIED** | Functional Browser QA | Verified `.large-text-mode` scales typography to 20px+ cleanly without breaking layouts. |

---

## 2. Step-by-Step Manual QA Procedure for Physical Android Phone

To execute manual verification for `MOB-05`, `MOB-06`, and `MOB-07`:

1. **Prerequisites:**
   - Android smartphone (Android 10 or later).
   - Phone connected to the same Wi-Fi network as the development machine or hosted on an HTTPS server (PWA Web Share Target requires HTTPS or `localhost`).
   - For local network testing: use `adb reverse tcp:8000 tcp:8000` over USB debugging, or run with an SSL tunnel (e.g. Cloudflare tunnel or ngrok).

2. **Installation Verification:**
   - Open Chrome on Android, navigate to `https://<your-scamshield-domain>/`.
   - Tap the 3-dot menu -> select **"Install app"** or **"Add to Home screen"**.
   - Confirm ScamShield icon (`icon-192.png`) appears on the home screen.

3. **Share Target Text Verification:**
   - Open WhatsApp or Google Messages.
   - Long press any suspicious SMS text (e.g. *"Dear customer, your electricity power will be disconnected tonight. Call 9876543210"*).
   - Tap **Share** in the top action bar.
   - Select **ScamShield** from the Android system share sheet.
   - *Expected Result:* ScamShield launches instantly, pre-fills the message into the scanner input box, and shows toast: *"Received shared message from mobile. Ready to analyze."*

4. **Share Target Image Verification:**
   - In WhatsApp, take a screenshot of a suspicious chat bubble.
   - Open Google Photos or screenshot preview, tap **Share**.
   - Select **ScamShield**.
   - *Expected Result:* ScamShield uploads image to `/share-target`, opens OCR review window, and displays extracted text for confirmation.
