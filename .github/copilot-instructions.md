# 🔗 WakeLink AI Coding Guide

> **Protocol v1.0** • ChaCha20 + HMAC-SHA256 • ESP8266/ESP32 + Python + FastAPI

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WakeLink Protocol v1.0                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐   │
│   │    Client    │◄───────►│    Server    │◄───────►│   Firmware   │   │
│   │   (Python)   │  HTTP/  │   (FastAPI)  │   WSS   │  (ESP8266)   │   │
│   │              │   WSS   │              │         │              │   │
│   └──────────────┘         └──────────────┘         └──────────────┘   │
│          │                        │                        │           │
│          │                        │                        │           │
│          └────────────────────────┼────────────────────────┘           │
│                                   │                                     │
│                        Local TCP (port 99)                              │
│                         Direct LAN Access                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Three Cohesive Parts

| Component | Location | Purpose |
|-----------|----------|---------|
| **Firmware** | `firmware/WakeLink/` | ESP8266/ESP32 device running TCP server + WSS client |
| **CLI Client** | `client/` | Python command-line interface for device management |
| **Relay Server** | `server/` | FastAPI blind relay (never decrypts payload) |

### Transport Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **TCP** | Port 99, direct socket | Local LAN, fastest response |
| **WSS** | WebSocket Secure | Cloud relay, NAT traversal, real-time |
| **HTTP** | REST API push/pull | CLI fallback when WSS unavailable |

---

## 🔐 Security Architecture

### Encryption Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    Packet Encryption Flow                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  device_token ──► SHA256 ──┬──► chacha_key (32 bytes)      │
│                            └──► hmac_key (32 bytes)         │
│                                                             │
│  plaintext + nonce + chacha_key ──► ChaCha20 ──► ciphertext │
│                                                             │
│  hex_payload + hmac_key ──► HMAC-SHA256 ──► signature       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Packet Structure

**Outer JSON Envelope:**
```json
{
  "device_id": "WL35080814",
  "payload": "<hex-encoded encrypted data>",
  "signature": "<HMAC-SHA256 of payload only>",
  "version": "1.0"
}
```

**Inner Encrypted JSON:**
```json
{
  "command": "wake",
  "data": {"mac": "AA:BB:CC:DD:EE:FF"},
  "request_id": "a1b2c3d4",
  "timestamp": 1732924800000
}
```

**Hex Payload Binary Layout:**
```
┌────────────┬──────────────────────┬────────────────┐
│ 2B length  │ ChaCha20 ciphertext  │ 16B nonce      │
│ (big-end)  │ (variable)           │ (first 12 used)│
└────────────┴──────────────────────┴────────────────┘
```

### Critical Rules

| Rule | Implementation |
|------|----------------|
| Key derivation | `SHA256(device_token)` → split into chacha_key + hmac_key |
| Signature scope | HMAC covers **only** hex `payload`, not full JSON |
| Request counter | EEPROM stored, increment on decrypt, persist every 10 ops |
| Nonce | 16 bytes random, first 12 used by ChaCha20 |

---

## 🔧 Firmware Patterns

### File Structure
```
firmware/WakeLink/
├── WakeLink.ino          # Main entry, orchestrates all modules
├── config.h/cpp          # EEPROM config (addresses 0/382/384/388)
├── CryptoManager.h/cpp   # ChaCha20 + SHA256 + HMAC implementation
├── packet.h/cpp          # Protocol packet encrypt/decrypt/sign
├── command.h/cpp         # Command registry and execution
├── tcp_handler.h/cpp     # Local TCP server (port 99)
├── cloud.h/cpp           # WSS client for cloud relay
├── udp_handler.h/cpp     # Wake-on-LAN UDP broadcast
├── wifi_manager.h/cpp    # WiFi station + AP mode
├── web_server.h/cpp      # Configuration web UI
├── ota_manager.h/cpp     # Arduino OTA updates
└── platform.h            # ESP8266/ESP32 abstraction layer
```

### Required Libraries
- `ArduinoJson` (v6+)
- `ESP8266WiFi` / `WiFi`
- `ESP8266WebServer` / `WebServer`
- `WebSocketsClient`

### Adding New Commands

1. **Create handler in `command.cpp`:**
```cpp
JsonDocument cmdMyCommand(JsonObject& data) {
    JsonDocument result;
    result["status"] = "success";
    result["data"] = "response";
    return result;
}
```

2. **Register in `commandMap`:**
```cpp
{"my_command", cmdMyCommand},
```

3. **Mirror in Python `client/core/protocol/commands.py`**

### Error Response Format
```cpp
// Always plain strings, never JSON errors
"ERROR:INVALID_SIGNATURE"
"ERROR:LIMIT_EXCEEDED"
"ERROR:DECRYPT_FAILED"
```

Python checks: `response.startswith("ERROR:")`

### Cloud Module (`cloud.cpp`)
- **WSS only** — no HTTP polling on ESP
- Single `cloud_url` config field
- Auto-converts `https://` → `wss://`
- Heartbeat ping every 15s (Cloudflare compatible)
- Reconnect interval: 5s

---

## 🐍 Client Workflows

### File Structure
```
client/
├── wakelink.py              # Main entry point
├── requirements.txt         # Dependencies
└── core/
    ├── crypto.py            # ChaCha20 + HMAC (mirrors firmware)
    ├── device_manager.py    # ~/.wakelink/devices.json registry
    ├── helpers.py           # MAC validation, formatting
    ├── handlers/
    │   ├── tcp_handler.py   # Local TCP socket client
    │   └── cloud_client.py  # WSS + HTTP fallback client
    └── protocol/
        ├── commands.py      # Command implementations
        └── packet.py        # Packet encryption/signing
```

### Device Configuration
Stored in `~/.wakelink/devices.json`:
```json
{
  "myesp": {
    "device_token": "...",
    "ip": "192.168.1.100",
    "mode": "tcp"
  },
  "cloud-esp": {
    "device_token": "...",
    "device_id": "WL35080814",
    "api_token": "sk-xxx",
    "cloud_url": "https://wakelink.example.com",
    "mode": "cloud"
  }
}
```

### Transport Priority
1. **WSS** (if `websocket-client` installed)
2. **HTTP Long Polling** (fallback, `wait=30` param)

### Typical Commands
```bash
# Add local device
wl add myesp token TOKEN ip 192.168.1.100

# Add cloud device
wl register myesp device-id WL001 api-token sk-xxx

# Test connection
wl myesp ping

# Wake-on-LAN
wl myesp wake AA:BB:CC:DD:EE:FF

# Device info
wl myesp info

# Enable OTA (30s window)
wl myesp ota

# Cloud mode control
wl myesp cloud-on        # Enable WSS connection
wl myesp cloud-off       # Disable WSS connection
wl myesp cloud-status    # Check cloud connection status
```

---

## 🌐 Server Architecture

### File Structure
```
server/
├── main.py                  # FastAPI app entry
├── requirements.txt         # Dependencies
├── gunicorn_conf.py         # Production config
├── core/
│   ├── auth.py              # JWT + API token validation
│   ├── database.py          # SQLite via SQLAlchemy
│   ├── models.py            # User, Device, Session models
│   ├── relay.py             # Message queue (never mutates payload)
│   └── schemas.py           # Pydantic validation
├── routes/
│   ├── api.py               # REST API + long polling
│   ├── wss.py               # WebSocket relay
│   ├── auth.py              # Login/register
│   └── admin.py             # Dashboard routes
└── templates/               # Jinja2 HTML
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Server health check |
| `/api/push` | POST | Send command to device queue |
| `/api/pull` | GET | Poll responses (supports `?wait=30`) |
| `/api/device/create` | POST | Register new device |
| `/ws/{device_id}` | WSS | Device persistent connection |
| `/ws/client/{client_id}` | WSS | CLI client connection |

### WebSocket Authentication

After WebSocket connection is established, client must send an auth message:

```json
{"type": "auth", "token": "<api_token>"}
```

Server responds with:
- Success: `{"type": "welcome", "status": "connected", ...}`
- Error: `{"status": "error", "error": "INVALID_TOKEN", ...}`

> **Backwards compatibility:** Header-based auth (`Authorization`, `X-API-Token`) still works.

### HTTP Authentication
```
Authorization: Bearer <API_TOKEN>
```

### WebSocket Settings (ESP compatible)
```python
ws_ping_interval=30
ws_ping_timeout=30
```

### Deployment
```bash
# Docker (recommended)
docker-compose up -d
# → http://localhost:9009

# Manual
cd server && pip install -r requirements.txt && python main.py
```

---

## 🐛 Debugging Guide

### Serial Monitor Tags (115200 baud)
| Tag | Meaning |
|-----|---------|
| `[CLOUD]` | WSS connection events |
| `[HMAC]` | Signature verification |
| `[CMD]` | Command execution |
| `[TCP]` | Local TCP events |
| `[WIFI]` | WiFi connection status |
| `[CRYPTO]` | Encryption operations |

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ERROR:INVALID_SIGNATURE` | Token mismatch | Verify `device_token` on both sides |
| `ERROR:LIMIT_EXCEEDED` | Counter overflow | Run `reset-counter` command |
| `ERROR:DECRYPT_FAILED` | Wrong key/corrupted | Re-sync tokens, restart device |
| `ECONNREFUSED` | TCP server down | Device in AP mode or offline |
| WSS timeout | Ping failure | Check `ws_ping_timeout` settings |

### Debug Commands
```bash
# Device diagnostics
wl myesp info              # IP, RSSI, heap, uptime
wl myesp crypto            # Key hash, counter status

# Server health
curl http://localhost:9009/api/health
```

---

## ⚠️ Version & Licensing

### Version Lock
Protocol, firmware, client, and server are **all locked to v1.0**.

Any breaking change requires simultaneous updates to:
- `firmware/WakeLink/`
- `client/`
- `server/`

### Breaking Changes Include
- Nonce size modification
- Signature scope changes
- Packet structure changes
- New required fields

### License
**NGC License v1.0** — Personal use only.
- ❌ Do not suggest GPL/commercial dependencies
- ✅ Keep existing license headers intact
- 📝 Commercial use requires written permission

---

## 🚀 Quick Reference

### Crypto Functions
| Location | Function | Purpose |
|----------|----------|---------|
| Firmware | `CryptoManager::encrypt()` | ChaCha20 encryption |
| Firmware | `CryptoManager::calculateHmac()` | HMAC-SHA256 |
| Client | `crypto.py::encrypt_packet()` | Python encryption |
| Client | `crypto.py::calculate_hmac()` | Python HMAC |

### Config Addresses (EEPROM)
| Address | Data |
|---------|------|
| 0 | Initialized flag |
| 382 | Cloud enabled |
| 384 | Web server enabled |
| 388 | Request counter |

### Ports
| Port | Protocol | Service |
|------|----------|---------|
| 99 | TCP | Encrypted commands |
| 80 | HTTP | Device web UI |
| 9 | UDP | Wake-on-LAN broadcast |
| 9009 | HTTP/WSS | Cloud relay server |
