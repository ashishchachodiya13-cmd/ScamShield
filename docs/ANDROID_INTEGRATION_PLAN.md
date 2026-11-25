# ScamShield — Android & Mobile Integration Architecture (Stage 7)

## 1. Executive Summary

ScamShield provides AI-assisted decision support for senior citizens in India to identify fraudulent SMS, WhatsApp, and call communications. Due to mobile operating system sandboxing (both Android and iOS), third-party web applications cannot passively sniff or intercept incoming SMS messages or WhatsApp notifications without explicit user action or dedicated native permissions.

To provide frictionless fraud detection on mobile devices while upholding strict privacy, ScamShield implements a dual-layer mobile strategy:
1. **PWA Web Share Target (Web-Feasible Layer):** Enables direct one-tap sharing of selected messages or screenshots from WhatsApp, SMS, or Telegram directly into ScamShield via the Android system Share sheet.
2. **Native Android Companion App / Accessibility Service Plan (Future Native Layer):** A roadmap for native Android notification listener / accessibility integration conforming to Google Play privacy policies.

---

## 2. PWA Web Share Target Architecture

The Web Share Target API allows installed Progressive Web Apps (PWAs) to register with the host operating system as a share target alongside native apps.

```mermaid
flowchart LR
    A[WhatsApp / SMS App] -->|Select Text or Screenshot + Tap 'Share'| B[Android System Share Sheet]
    B -->|Select 'ScamShield'| C[PWA Manifest: POST /share-target]
    C -->|Ephemeral 5-min In-Memory Store| D[FastAPI Backend /share-target]
    D -->|HTTP 303 Redirect /#scan?share_token=UUID| E[ScamShield Frontend UI]
    E -->|Single-Use Fetch /api/share-target/{UUID}| D
    E -->|Pre-filled Text + Masking| F[Deterministic Rule Engine]
```

### 2.1 Manifest Configuration (`static/manifest.webmanifest`)
- `action`: `/share-target`
- `method`: `POST`
- `enctype`: `multipart/form-data`
- `params`:
  - `title`: `title`
  - `text`: `text`
  - `url`: `url`
  - `files`: accepts `image/png`, `image/jpeg`, `image/webp` (max 5MB)

### 2.2 Privacy & Single-Use Ephemeral Storage
- When a user shares a message or screenshot, `/share-target` extracts text and generates a cryptographic UUID token.
- The shared payload is cached in an in-memory dictionary `_share_store` with a strict 5-minute TTL.
- Once the browser UI loads and requests `GET /api/share-target/{token}`, the payload is popped from memory immediately.
- **Zero Raw Text or Screenshots Persisted:** Neither the shared text nor uploaded screenshots are written to SQLite, filesystem, or permanent logs.

---

## 3. Native Android Companion Architecture (Roadmap)

For full automation on Android without manual sharing, a native Android companion APK can be developed using Kotlin / Jetpack Compose.

### 3.1 Android Components
1. **NotificationListenerService (`ScamNotificationListener`):**
   - Listens for incoming notifications from `com.whatsapp`, `com.google.android.apps.messaging`, and default SMS apps.
   - Extracts notification title and body text in real-time.
   - Applies local regex PII masking before dispatching text to ScamShield local service or loopback endpoint (`127.0.0.1`).
2. **AccessibilityService (`ScamAccessibilityWatcher` - Optional):**
   - Detects on-screen fraud prompts during incoming WhatsApp video calls (e.g. fake police backgrounds, fake court seals).
   - Prompts senior citizens with an overlay warning: *"Law enforcement never arrests anyone over video calls."*

### 3.2 Permission Matrix & Google Play Compliance
- **Notification Access:** `android.permission.BIND_NOTIFICATION_LISTENER_SERVICE`
- **SMS Read (Optional / Highly Restricted):** `android.permission.READ_SMS` (Requires Google Play Core Functionality declaration or SMS Retriever API).
- **Declaration:** Must clearly state in Google Play Console that text processing is 100% decision-support and never sent to external ad/tracking servers.

---

## 4. Multi-Screenshot Batch Processing

Senior citizens frequently receive multi-bubble WhatsApp scam conversations where threat indicators are split across 2 to 4 messages (e.g. bubble 1: "CBI Notice", bubble 2: "Account frozen", bubble 3: "Send money to this UPI ID").

### Technical Flow:
1. User drops or selects up to 5 screenshot images (max 5MB each).
2. Client-side preview grid shows thumbnails with removal controls.
3. Batch processor calls `POST /api/ocr` sequentially for each image.
4. Combined extracted conversation is fed into `POST /api/analyze`.
5. Deterministic rule engine scores all red flags across the entire conversation thread.

---

## 5. Senior Citizen Accessibility Compliance

All mobile views in ScamShield adhere to senior citizen ergonomics:
- Minimum touch target size: 48 × 48 px.
- Base typography: 16px default, 20px+ in Senior Large Text Mode.
- Color contrast: Conforms to WCAG AAA for text and WCAG AA for UI controls.
- Multimodal alert indicators: Every risk badge uses color, text label, and inline SVG iconography (never color alone).
