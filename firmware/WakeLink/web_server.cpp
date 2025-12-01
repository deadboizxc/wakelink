/**
 * @file web_server.cpp
 * @brief Web server implementation for WakeLink firmware.
 *
 * Provides configuration web interface for WiFi setup and device management.
 */

#include "platform.h"
#include "web_server.h"

extern CryptoManager crypto;

/**
 * @brief Get WiFi status string.
 *
 * Returns a description of the current network mode: Access Point or Station.
 *
 * @return String describing WiFi status.
 */
String getWiFiStatus() {
    return inAPMode ? "Access Point (Configuration)" : "Station (Connected to WiFi)";
}

/**
 * @brief Get encryption status string.
 *
 * Returns "Enabled" if crypto is enabled, otherwise "Disabled".
 *
 * @return String describing encryption status.
 */
String getEncryptionStatus() {
    return crypto.isEnabled() ? "Enabled" : "Disabled";
}

// Static HTML fragments used in web server responses
const char MAIN_HTML_HEAD[] = R"rawliteral(
<!DOCTYPE html><html><head>
<meta charset='UTF-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>WakeLink Setup</title>
<style>
body{font-family:Arial,sans-serif;margin:20px;background:#f0f0f0;}
.box{max-width:500px;margin:auto;background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}
h2{color:#333;text-align:center;}
input[type='text'],input[type='password']{width:100%;padding:8px;margin:5px 0;border:1px solid #ddd;border-radius:4px;box-sizing:border-box;}
button{background:#007cba;color:white;padding:10px 20px;border:none;border-radius:4px;cursor:pointer;width:100%;}
button:hover{background:#005a87;}
.status{background:#e7f3ff;padding:10px;border-radius:4px;margin:10px 0;}
.checkbox-label{display:block;margin:10px 0;font-weight:normal;}
.checkbox-label input{margin-right:8px;}
.links{margin:20px 0;text-align:center;}
.links a{margin:0 10px;text-decoration:none;color:#007cba;}
.links a:hover{text-decoration:underline;}
</style>
</head><body>
<div class='box'>
<h2>WakeLink Setup</h2>
)rawliteral";

const char MAIN_HTML_FOOT[] = R"rawliteral(
</div></body></html>
)rawliteral";

const char RESET_HTML[] = R"rawliteral(
<!DOCTYPE html><html><head><meta charset='UTF-8'>
<title>Factory Reset</title></head><body>
<h2>Factory Reset</h2>
<p>Are you sure you want to reset all settings?</p>
<form action='/reset' method='post'>
<button type='submit'>Yes, reset</button>
</form>
<br><a href='/'>Cancel</a>
</body></html>
)rawliteral";

/**
 * @brief Initialize web server and register HTTP routes.
 *
 * Registers routes for displaying main page, device info, saving settings,
 * WiFi scanning, and factory reset.
 * On settings save, writes cfg to EEPROM and reboots device into STA mode.
 */
void initWebServer() {
    server.on("/", HTTP_GET, []() {
        String html = MAIN_HTML_HEAD;

        html += F("<div class='status'>");
        html += F("<strong>Mode:</strong> ");
        html += getWiFiStatus();
        html += F("<br><strong>Device ID:</strong> ");
        html += DEVICE_ID;
        html += F("<br><strong>IP:</strong> ");
        html += inAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
        html += F("<br><strong>Encryption:</strong> ");
        html += getEncryptionStatus();
        html += F("</div>");

        html += F("<form action='/save' method='post'>"
                  "<h3>WiFi Settings</h3>"
                  "SSID:<br><input type='text' name='ssid' value='");
        html += String(cfg.wifi_ssid);
        html += F("' placeholder='Your WiFi name' required><br><br>"
                  "Password:<br><input type='password' name='pass' value='");
        html += String(cfg.wifi_pass);
        html += F("' placeholder='Your WiFi password'><br><br>"
                  "<h3>Device Settings</h3>"
                  "Access Token:<br><input type='text' name='token' value='");
        html += DEVICE_TOKEN;
        html += F("' readonly style='background:#f5f5f5;'><br><br>"
                  "<h3>Cloud Settings</h3>"
                  "Cloud URL:<br><input type='text' name='cloud_url' value='");
        html += String(cfg.cloud_url);
        html += F("' placeholder='wss://wakelink.deadboizxc.org'><br><br>"
                  "Cloud API Token:<br><input type='text' name='cloud_token' value='");
        html += String(cfg.cloud_api_token);
        html += F("' placeholder='Your API token'><br><br>"
                  "<label class='checkbox-label'><input type='checkbox' name='cloud_enabled' value='1'");
        if (cfg.cloud_enabled) html += F(" checked");
        html += F("> Enable Cloud Mode (WSS)</label><br><br>"
                  "<button type='submit'>Save Settings & Reboot</button>"
                  "</form><hr>"
                  "<div class='links'>"
                  "<a href='/info'>Device Info</a> | "
                  "<a href='/scan'>Scan WiFi</a> | "
                  "<a href='/reset'>Factory Reset</a>"
                  "</div>");

        html += MAIN_HTML_FOOT;
        server.send(200, "text/html; charset=UTF-8", html);
    });

    server.on("/info", HTTP_GET, []() {
        String html = F("<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                        "<title>Device Info</title>"
                        "<style>"
                        "body{font-family:Arial,sans-serif;margin:20px;background:#f0f0f0;}"
                        ".info-box{max-width:500px;margin:auto;background:#fff;padding:20px;border-radius:8px;}"
                        "</style>"
                        "</head><body>"
                        "<div class='info-box'>"
                        "<h2>Device Info</h2><p>");

        html += F("<strong>Device ID:</strong> ");
        html += DEVICE_ID;
        html += F("<br><strong>IP:</strong> ");
        html += inAPMode ? WiFi.softAPIP().toString() : WiFi.localIP().toString();
        html += F("<br><strong>SSID:</strong> ");
        html += String(cfg.wifi_ssid);
        html += F("<br><strong>WiFi Configured:</strong> ");
        html += (cfg.wifi_configured ? "Yes" : "No");
        html += F("<br><strong>Cloud:</strong> ");
        html += (cfg.cloud_enabled ? "Enabled" : "Disabled");
        html += F("<br><strong>Encryption:</strong> ");
        html += getEncryptionStatus();
        html += F("<br><strong>Mode:</strong> ");
        html += getWiFiStatus();
        html += F("<br><strong>Requests:</strong> ");
        html += String(crypto.getRequestCount());
        html += F("/");
        html += String(crypto.getRequestLimit());
        html += F("</p><a href='/'>Back</a></div></body></html>");

        server.send(200, "text/html; charset=UTF-8", html);
    });

    server.on("/save", HTTP_POST, []() {
        Serial.println(F("=== SAVING SETTINGS ==="));

        // SSID: only update if a non-empty value was provided
        if (server.hasArg("ssid")) {
            String ssid = server.arg("ssid");
            ssid.trim();
            if (ssid.length() > 0) {
                ssid.toCharArray(cfg.wifi_ssid, sizeof(cfg.wifi_ssid));
                cfg.wifi_configured = 1;
                Serial.printf("SSID: %s\n", cfg.wifi_ssid);
            } else {
                Serial.println(F("SSID field empty; keeping previous SSID"));
            }
        }

        // Password: update only if provided (allow empty password to clear)
        if (server.hasArg("pass")) {
            String pass = server.arg("pass");
            pass.trim();
            if (pass.length() > 0) {
                pass.toCharArray(cfg.wifi_pass, sizeof(cfg.wifi_pass));
                Serial.println(F("Password: [set]"));
            } else {
                // If user submitted an empty password, clear stored password
                cfg.wifi_pass[0] = '\0';
                Serial.println(F("Password cleared"));
            }
        }

        // Cloud URL (single field for WSS)
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

        // Cloud enabled checkbox
        cfg.cloud_enabled = server.hasArg("cloud_enabled") ? 1 : 0;
        Serial.printf("Cloud enabled: %d\n", cfg.cloud_enabled);

        // Ensure wifi_configured flag is consistent with stored SSID
        if (strlen(cfg.wifi_ssid) == 0) cfg.wifi_configured = 0;

        bool saveSuccess = saveConfig();
        if (saveSuccess) {
            Serial.println(F("Config saved to EEPROM"));
        } else {
            Serial.println(F("Config save failed"));
        }

        server.send(200, "text/html",
            "<!DOCTYPE html><html><head>"
            "<meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Settings Saved</title>"
            "<style>"
            "body{font-family:Arial,sans-serif;text-align:center;margin:50px;background:#f0f0f0;}"
            ".box{max-width:400px;margin:auto;background:#fff;padding:30px;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1);}"
            "h2{color:#4CAF50;}"
            "</style>"
            "</head><body>"
            "<div class='box'>"
            "<h2>Settings Saved!</h2>"
            "<p>Device is rebooting and will try to connect to your WiFi.</p>"
            "<p>Check the serial monitor for status.</p>"
            "</div>"
            "<script>setTimeout(function(){window.location.href='/';},3000);</script>"
            "</body></html>");

        delay(300);
        Serial.println(F("=== REBOOTING WITH NEW SETTINGS ==="));
        server.stop();
        delay(100);

        // Ensure we reboot into STA mode so the device will attempt to connect to saved WiFi
        WiFi.mode(WIFI_STA);
        WiFi.disconnect(true);
        delay(200);
        ESP.restart();
    });

    server.on("/scan", HTTP_GET, []() {
        String html = F("<!DOCTYPE html><html><head><meta charset='UTF-8'>"
                        "<title>WiFi Scan</title>"
                        "<style>"
                        "body{font-family:Arial,sans-serif;margin:20px;background:#f0f0f0;}"
                        ".scan-box{max-width:500px;margin:auto;background:#fff;padding:20px;border-radius:8px;}"
                        ".network{background:#f9f9f9;padding:10px;margin:5px 0;border-radius:4px;border-left:4px solid #007cba;}"
                        "</style>"
                        "</head><body>"
                        "<div class='scan-box'>"
                        "<h2>Available WiFi Networks</h2>");

        Serial.println(F("Scanning WiFi networks..."));
        int n = WiFi.scanNetworks();

        if (n == 0) {
            html += F("<div class='network'>No networks found</div>");
        } else {
            html += F("<p>Found ");
            html += String(n);
            html += F(" networks:</p>");

            for (int i = 0; i < n; ++i) {
                html += F("<div class='network'>");
                html += F("<strong>");
                html += WiFi.SSID(i);
                html += F("</strong> (");
                html += String(WiFi.RSSI(i));
                html += F(" dBm)");

                if (WiFi.encryptionType(i) != WIFI_AUTH_OPEN) html += F(" [Encrypted]");

                html += F("</div>");
            }
        }

        html += F("<br><a href='/'>Back</a>");
        html += F("</div></body></html>");

        server.send(200, "text/html; charset=UTF-8", html);
        WiFi.scanDelete();
    });

    server.on("/reset", HTTP_GET, []() {
        server.send(200, "text/html; charset=UTF-8", RESET_HTML);
    });

    server.on("/reset", HTTP_POST, []() {
        server.send(200, "text/html",
            "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
            "<title>Reset Complete</title></head><body>"
            "<h2>Factory Reset Complete!</h2>"
            "<p>Rebooting...</p>"
            "</body></html>");

        delay(500);

        // Reset configuration and crypto request counter
        crypto.resetRequestCounter();
        memset(&cfg, 0, sizeof(cfg));
        saveConfig();
        delay(500);
        ESP.restart();
    });

    server.begin();
    Serial.println(F("Web server OK"));
}