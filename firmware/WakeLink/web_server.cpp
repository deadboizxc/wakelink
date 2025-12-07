/**
 * @file web_server.cpp
 * @brief Web server implementation for WakeLink firmware.
 *
 * Provides configuration web interface for WiFi setup and device management.
 * Uses premium dark theme matching the cloud server UI.
 */

#include "platform.h"
#include "web_server.h"
#include "web_assets.h"

extern CryptoManager crypto;

/**
 * @brief Helper to build HTML page header with CSS
 */
String buildPageHead() {
    String html;
    html.reserve(4096);
    html += FPSTR(HTML_HEAD);
    html += FPSTR(WEB_CSS);
    html += FPSTR(HTML_HEAD_END);
    return html;
}

/**
 * @brief Get WiFi mode badge HTML
 */
String getModeBadge() {
    if (inAPMode) {
        return F("<span class='badge badge-warning'><span class='dot'></span>AP Mode</span>");
    }
    return F("<span class='badge badge-success'><span class='dot'></span>Connected</span>");
}

/**
 * @brief Get encryption status badge HTML
 */
String getCryptoBadge() {
    if (crypto.isEnabled()) {
        return F("<span class='badge badge-success'><span class='dot'></span>Enabled</span>");
    }
    return F("<span class='badge badge-error'><span class='dot'></span>Disabled</span>");
}

/**
 * @brief Initialize web server and register HTTP routes.
 */
void initWebServer() {
    
    // Main configuration page
    server.on("/", HTTP_GET, []() {
        String html = buildPageHead();
        html += FPSTR(MAIN_CARD_HEAD);

        // Status grid
        html += F("<div class='status-grid'>");
        html += F("<div class='status-item'><div class='status-label'>Mode</div><div class='status-value'>");
        html += getModeBadge();
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>Device ID</div><div class='status-value'>");
        html += DEVICE_ID;
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>IP Address</div><div class='status-value'>");
        html += inAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>Encryption</div><div class='status-value'>");
        html += getCryptoBadge();
        html += F("</div></div></div>");

        // WiFi settings form
        html += F("<form action='/save' method='post'>");
        html += F("<h3>📶 WiFi Settings</h3>");
        html += F("<input type='text' name='ssid' value='");
        html += String(cfg.wifi_ssid);
        html += F("' placeholder='WiFi Network Name' required>");
        html += F("<input type='password' name='pass' value='");
        html += String(cfg.wifi_pass);
        html += F("' placeholder='WiFi Password'>");

        // Device settings
        html += F("<h3>🔑 Device Token</h3>");
        html += F("<input type='text' value='");
        html += DEVICE_TOKEN;
        html += F("' readonly>");

        // Cloud settings
        html += F("<h3>☁️ Cloud Settings</h3>");
        html += F("<input type='text' name='cloud_url' value='");
        html += String(cfg.cloud_url);
        html += F("' placeholder='wss://wakelink.example.com'>");
        html += F("<input type='text' name='cloud_token' value='");
        html += String(cfg.cloud_api_token);
        html += F("' placeholder='Cloud API Token'>");
        html += F("<label class='checkbox-label'><input type='checkbox' name='cloud_enabled' value='1'");
        if (cfg.cloud_enabled) html += F(" checked");
        html += F("><span>Enable Cloud Connection (WSS)</span></label>");

        html += F("<button type='submit'>💾 Save & Reboot</button>");
        html += F("</form>");

        // Navigation links
        html += F("<div class='links'>");
        html += F("<a href='/info'>📊 Device Info</a>");
        html += F("<a href='/scan'>📡 Scan WiFi</a>");
        html += F("<a href='/reset'>⚠️ Factory Reset</a>");
        html += F("</div></div>");

        html += FPSTR(HTML_FOOT);
        server.send(200, "text/html; charset=UTF-8", html);
    });

    // Device info page
    server.on("/info", HTTP_GET, []() {
        String html = buildPageHead();
        html += FPSTR(INFO_PAGE_HEAD);

        html += F("<div class='status-grid'>");
        html += F("<div class='status-item'><div class='status-label'>Device ID</div><div class='status-value'>");
        html += DEVICE_ID;
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>IP Address</div><div class='status-value'>");
        html += inAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>SSID</div><div class='status-value'>");
        html += strlen(cfg.wifi_ssid) > 0 ? String(cfg.wifi_ssid) : F("Not set");
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>WiFi Status</div><div class='status-value'>");
        html += cfg.wifi_configured ? F("Configured") : F("Not configured");
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>Cloud</div><div class='status-value'>");
        html += cfg.cloud_enabled ? F("Enabled") : F("Disabled");
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>Encryption</div><div class='status-value'>");
        html += getCryptoBadge();
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>Mode</div><div class='status-value'>");
        html += getModeBadge();
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>Requests</div><div class='status-value'>");
        html += String(crypto.getRequestCount());
        html += F(" / ");
        html += String(crypto.getRequestLimit());
        html += F("</div></div>");
        html += F("<div class='status-item'><div class='status-label'>Free Heap</div><div class='status-value'>");
        html += String(ESP.getFreeHeap());
        html += F(" bytes</div></div>");
        html += F("<div class='status-item'><div class='status-label'>RSSI</div><div class='status-value'>");
        html += inAPMode ? F("N/A") : String(WiFi.RSSI()) + F(" dBm");
        html += F("</div></div></div>");

        html += F("<div class='links'><a href='/'>← Back to Setup</a></div>");
        html += F("</div>");
        html += FPSTR(HTML_FOOT);
        server.send(200, "text/html; charset=UTF-8", html);
    });

    // Save settings
    server.on("/save", HTTP_POST, []() {
        Serial.println(F("=== SAVING SETTINGS ==="));

        if (server.hasArg("ssid")) {
            String ssid = server.arg("ssid");
            ssid.trim();
            if (ssid.length() > 0) {
                ssid.toCharArray(cfg.wifi_ssid, sizeof(cfg.wifi_ssid));
                cfg.wifi_configured = 1;
                Serial.printf("SSID: %s\n", cfg.wifi_ssid);
            }
        }

        if (server.hasArg("pass")) {
            String pass = server.arg("pass");
            pass.trim();
            if (pass.length() > 0) {
                pass.toCharArray(cfg.wifi_pass, sizeof(cfg.wifi_pass));
                Serial.println(F("Password: [set]"));
            } else {
                cfg.wifi_pass[0] = '\0';
                Serial.println(F("Password cleared"));
            }
        }

        if (server.hasArg("cloud_url")) {
            String cloud_url = server.arg("cloud_url");
            cloud_url.trim();
            cloud_url.toCharArray(cfg.cloud_url, sizeof(cfg.cloud_url));
            Serial.printf("Cloud URL: %s\n", cfg.cloud_url);
        }

        if (server.hasArg("cloud_token")) {
            String cloud_token = server.arg("cloud_token");
            cloud_token.trim();
            cloud_token.toCharArray(cfg.cloud_api_token, sizeof(cfg.cloud_api_token));
            Serial.println(F("Cloud API Token: [set]"));
        }

        cfg.cloud_enabled = server.hasArg("cloud_enabled") ? 1 : 0;
        Serial.printf("Cloud enabled: %d\n", cfg.cloud_enabled);

        if (strlen(cfg.wifi_ssid) == 0) cfg.wifi_configured = 0;

        bool saveSuccess = saveConfig();
        Serial.println(saveSuccess ? F("Config saved to EEPROM") : F("Config save failed"));

        String html = buildPageHead();
        html += FPSTR(SAVE_SUCCESS);
        html += FPSTR(HTML_FOOT);
        server.send(200, "text/html; charset=UTF-8", html);

        delay(300);
        Serial.println(F("=== REBOOTING WITH NEW SETTINGS ==="));
        server.stop();
        delay(100);
        WiFi.mode(WIFI_STA);
        WiFi.disconnect(true);
        delay(200);
        ESP.restart();
    });

    // WiFi scan page
    server.on("/scan", HTTP_GET, []() {
        String html = buildPageHead();
        html += FPSTR(SCAN_PAGE_HEAD);

        Serial.println(F("Scanning WiFi networks..."));
        int n = WiFi.scanNetworks();

        html += F("<div class='network-list'>");
        if (n == 0) {
            html += F("<div class='network-item'><span class='network-name'>No networks found</span></div>");
        } else {
            for (int i = 0; i < n; ++i) {
                html += F("<div class='network-item'><span class='network-name'>");
                html += WiFi.SSID(i);
                html += F("</span><span class='network-info'>");
                html += String(WiFi.RSSI(i));
                html += F(" dBm");
                if (WiFi.encryptionType(i) != WIFI_AUTH_OPEN) {
                    html += F(" 🔒");
                }
                html += F("</span></div>");
            }
        }
        html += F("</div>");

        html += F("<div class='links' style='margin-top: 20px;'><a href='/'>← Back to Setup</a></div>");
        html += F("</div>");
        html += FPSTR(HTML_FOOT);
        server.send(200, "text/html; charset=UTF-8", html);
        WiFi.scanDelete();
    });

    // Factory reset confirmation
    server.on("/reset", HTTP_GET, []() {
        String html = buildPageHead();
        html += FPSTR(RESET_PAGE);
        html += FPSTR(HTML_FOOT);
        server.send(200, "text/html; charset=UTF-8", html);
    });

    // Execute factory reset
    server.on("/reset", HTTP_POST, []() {
        String html = buildPageHead();
        html += FPSTR(RESET_COMPLETE);
        html += FPSTR(HTML_FOOT);
        server.send(200, "text/html; charset=UTF-8", html);

        delay(500);
        crypto.resetRequestCounter();
        memset(&cfg, 0, sizeof(cfg));
        saveConfig();
        delay(500);
        ESP.restart();
    });

    server.begin();
    Serial.println(F("Web server OK"));
}
