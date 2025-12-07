/**
 * @file web_assets.h
 * @brief HTML and CSS assets for WakeLink ESP web interface.
 * 
 * Premium dark theme matching the cloud server UI.
 * Uses modern glassmorphism design with gradient accents.
 */

#ifndef WEB_ASSETS_H
#define WEB_ASSETS_H

#include <Arduino.h>

// CSS Styles - Premium dark theme matching server
const char WEB_CSS[] PROGMEM = R"rawliteral(
:root {
    --bg: #09090b;
    --bg-card: rgba(17,17,21,0.9);
    --border: rgba(255,255,255,0.06);
    --text: #fafafa;
    --text-sec: #a1a1aa;
    --text-muted: #71717a;
    --accent: #7c3aed;
    --accent2: #a855f7;
    --success: #22c55e;
    --error: #ef4444;
    --warning: #eab308;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    padding: 20px;
    line-height: 1.6;
}
.container {
    max-width: 480px;
    margin: 0 auto;
}
.card {
    background: var(--bg-card);
    backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
}
.card::before {
    content: '';
    display: block;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    margin: -24px -24px 20px;
    border-radius: 16px 16px 0 0;
}
h1 {
    font-size: 1.75rem;
    font-weight: 700;
    text-align: center;
    margin-bottom: 8px;
}
h1 span { color: var(--accent); }
.subtitle {
    text-align: center;
    color: var(--text-sec);
    font-size: 0.9rem;
    margin-bottom: 24px;
}
h3 {
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    margin: 20px 0 12px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.status-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-bottom: 20px;
}
.status-item {
    background: rgba(255,255,255,0.02);
    padding: 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
}
.status-label {
    font-size: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.status-value {
    font-size: 0.9rem;
    color: var(--text);
    font-weight: 500;
    word-break: break-all;
}
.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 500;
}
.badge-success {
    background: rgba(34,197,94,0.15);
    color: var(--success);
}
.badge-warning {
    background: rgba(234,179,8,0.15);
    color: var(--warning);
}
.badge-error {
    background: rgba(239,68,68,0.15);
    color: var(--error);
}
.dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
}
input[type='text'],
input[type='password'] {
    width: 100%;
    padding: 12px 14px;
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 0.95rem;
    margin-bottom: 12px;
    transition: all 0.2s;
}
input:focus {
    outline: none;
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(124,58,237,0.15);
}
input::placeholder { color: var(--text-muted); }
input[readonly] {
    background: rgba(0,0,0,0.3);
    cursor: not-allowed;
}
.checkbox-label {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px;
    background: rgba(255,255,255,0.02);
    border: 1px solid var(--border);
    border-radius: 8px;
    cursor: pointer;
    margin-bottom: 12px;
}
.checkbox-label input[type='checkbox'] {
    width: 18px;
    height: 18px;
    accent-color: var(--accent);
}
button, .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    width: 100%;
    padding: 14px 20px;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    border: none;
    border-radius: 10px;
    color: white;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
}
button:hover, .btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 24px rgba(124,58,237,0.3);
}
button:active { transform: translateY(0); }
.btn-secondary {
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
}
.btn-secondary:hover {
    background: rgba(255,255,255,0.08);
    box-shadow: none;
}
.btn-danger {
    background: linear-gradient(135deg, var(--error), #dc2626);
}
.links {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-top: 20px;
    flex-wrap: wrap;
}
.links a {
    color: var(--accent2);
    text-decoration: none;
    font-size: 0.9rem;
    transition: color 0.2s;
}
.links a:hover { color: var(--text); }
.network-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.network-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: rgba(255,255,255,0.02);
    border: 1px solid var(--border);
    border-radius: 8px;
}
.network-name { font-weight: 500; }
.network-info {
    font-size: 0.8rem;
    color: var(--text-sec);
}
.msg-box {
    padding: 16px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 16px;
}
.msg-success {
    background: rgba(34,197,94,0.15);
    border: 1px solid rgba(34,197,94,0.3);
    color: var(--success);
}
.msg-error {
    background: rgba(239,68,68,0.15);
    border: 1px solid rgba(239,68,68,0.3);
    color: var(--error);
}
@media (max-width: 480px) {
    body { padding: 12px; }
    .card { padding: 16px; }
    .card::before { margin: -16px -16px 16px; }
    .status-grid { grid-template-columns: 1fr; }
}
)rawliteral";

// HTML Head template
const char HTML_HEAD[] PROGMEM = R"rawliteral(
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WakeLink Setup</title>
    <style>
)rawliteral";

// HTML Head close and body start
const char HTML_HEAD_END[] PROGMEM = R"rawliteral(
    </style>
</head>
<body>
<div class="container">
)rawliteral";

// HTML Footer
const char HTML_FOOT[] PROGMEM = R"rawliteral(
</div>
</body>
</html>
)rawliteral";

// Main page card header
const char MAIN_CARD_HEAD[] PROGMEM = R"rawliteral(
<div class="card">
    <h1>Wake<span>Link</span></h1>
    <p class="subtitle">Device Configuration</p>
)rawliteral";

// Info page template
const char INFO_PAGE_HEAD[] PROGMEM = R"rawliteral(
<div class="card">
    <h1>Device <span>Info</span></h1>
    <p class="subtitle">System diagnostics</p>
)rawliteral";

// Scan page template
const char SCAN_PAGE_HEAD[] PROGMEM = R"rawliteral(
<div class="card">
    <h1>WiFi <span>Networks</span></h1>
    <p class="subtitle">Available networks nearby</p>
)rawliteral";

// Reset confirmation page
const char RESET_PAGE[] PROGMEM = R"rawliteral(
<div class="card">
    <h1>Factory <span>Reset</span></h1>
    <p class="subtitle">This will erase all settings</p>
    <div class="msg-box msg-error" style="margin-top: 20px;">
        <strong>Warning!</strong><br>
        All WiFi credentials, tokens, and settings will be erased.
    </div>
    <form action="/reset" method="post">
        <button type="submit" class="btn-danger">Yes, Reset Everything</button>
    </form>
    <div class="links" style="margin-top: 16px;">
        <a href="/">← Cancel</a>
    </div>
</div>
)rawliteral";

// Success message after save
const char SAVE_SUCCESS[] PROGMEM = R"rawliteral(
<div class="card">
    <h1>Settings <span>Saved</span></h1>
    <div class="msg-box msg-success">
        <strong>Success!</strong><br>
        Device is rebooting and will connect to your WiFi.
    </div>
    <p style="text-align: center; color: var(--text-sec); margin-top: 16px;">
        Redirecting in 3 seconds...
    </p>
</div>
<script>setTimeout(function(){window.location.href='/';},3000);</script>
)rawliteral";

// Reset complete message
const char RESET_COMPLETE[] PROGMEM = R"rawliteral(
<div class="card">
    <h1>Reset <span>Complete</span></h1>
    <div class="msg-box msg-success">
        Settings have been erased. Device is rebooting...
    </div>
</div>
)rawliteral";

#endif // WEB_ASSETS_H
