# 🔗 WakeLink

<div align="center">

[![Protocol](https://img.shields.io/badge/Protocol-v1.0-blue.svg)](https://github.com/deadboizxc/wakelink)
[![License](https://img.shields.io/badge/License-NGC%20v1.0-green.svg)](LICENSE)
[![ESP8266](https://img.shields.io/badge/ESP8266-Compatible-orange.svg)](https://www.espressif.com/)
[![ESP32](https://img.shields.io/badge/ESP32-Compatible-orange.svg)](https://www.espressif.com/)

**Secure Remote Wake-on-LAN Device Management**

English | [Українська](README_UA.md) | [Русский](README_RU.md)

</div>

---

## 📖 Description

WakeLink is a secure system for remotely waking computers via Wake-on-LAN (WoL). The system consists of three components: ESP8266/ESP32 firmware, Python CLI client, and a cloud relay server.

### Key Features

- 🔐 **End-to-end encryption** — ChaCha20 + HMAC-SHA256
- 🌐 **Cloud relay** — manage devices from anywhere in the world
- 🏠 **Local mode** — direct TCP connection in LAN
- ⚡ **Wake-on-LAN** — wake computers by MAC address
- 🔄 **OTA updates** — over-the-air firmware updates
- 🖥️ **Web interface** — device configuration via browser
- 🔑 **Token refresh** — update device tokens remotely

---

## 📐 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WakeLink Protocol v1.0                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐    │
│   │    Client    │◄───────►│    Server    │◄───────►│   Firmware   │    │
│   │   (Python)   │ HTTP/   │   (FastAPI)  │   WSS   │  (ESP8266/   │    │
│   │              │  WSS    │              │  only   │   ESP32)     │    │
│   └──────────────┘         └──────────────┘         └──────────────┘    │
│                                   │                                     │
│                            Blind Relay                                  │
│                        (never decrypts)                                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐         ┌──────────────┐                             │
│   │    Client    │◄───────►│   Firmware   │  Local TCP (port 99)        │
│   │   (Python)   │   TCP   │  (ESP8266)   │  Direct LAN Access          │
│   └──────────────┘         └──────────────┘                             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Transport Modes

| Mode | Protocol | Description |
|------|----------|-------------|
| **TCP** | TCP:99 | Direct connection in local network, minimal latency |
| **Cloud HTTP** | HTTPS | Client → Server: HTTP push/pull with long polling |
| **Cloud WSS** | WSS | Client ↔ Server ↔ ESP: WebSocket, real-time communication |

> **Important:** ESP device **always** connects to the server via WSS. HTTP is only used between client and server as a fallback.

---

## 🚀 Quick Start

### 1. Flash the Device

```bash
# Clone the repository
git clone https://github.com/deadboizxc/wakelink.git
cd wakelink/firmware/WakeLink

# Open in Arduino IDE or PlatformIO
# Install dependencies:
# - ArduinoJson (v6+)
# - ESP8266WiFi / WiFi
# - WebSocketsClient
```

### 2. Initial Setup

1. Flash the device
2. Connect to Wi-Fi hotspot `WakeLink-XXXXXX`
3. Open `http://192.168.4.1` in browser
4. Enter Wi-Fi credentials and device token

### 3. Install Client

```bash
cd client
pip install -r requirements.txt

# Optional: for WebSocket support
pip install websocket-client
```

### 4. Add Device

**Local mode (TCP):**
```bash
python wakelink.py add myesp token YOUR_DEVICE_TOKEN ip 192.168.1.100
```

**Cloud mode:**
```bash
# Register on server (once)
python wakelink.py register myesp device-id WL35080814 api-token YOUR_API_TOKEN token YOUR_DEVICE_TOKEN

# Or add with custom URLs
python wakelink.py add myesp token YOUR_TOKEN http-url https://wakelink.deadboizxc.org wss-url wss://wakelink.deadboizxc.org
```

### 5. Usage

```bash
# Check connection
python wakelink.py myesp ping

# Device information
python wakelink.py myesp info

# Wake a computer
python wakelink.py myesp wake AA:BB:CC:DD:EE:FF

# Enable OTA (30 seconds)
python wakelink.py myesp ota

# Update device token
python wakelink.py myesp update-token
```

---

## 📋 CLI Commands

### Device Management

| Command | Description |
|---------|-------------|
| `add <name> token <TOKEN> ip <IP> [port <PORT>]` | Add local TCP device |
| `add <name> token <TOKEN> http-url <URL> wss-url <URL>` | Add cloud device |
| `register <name> device-id <ID> api-token <TOKEN> token <TOKEN>` | Register device on cloud server |
| `update <name> <field> <value> [<field> <value>...]` | Update device fields |
| `remove <name>` | Remove device |
| `list` | List all devices |

### Device Commands

| Command | Description |
|---------|-------------|
| `<name> ping` | Check device connectivity |
| `<name> info` | Get device information |
| `<name> wake <MAC>` | Send Wake-on-LAN packet |
| `<name> restart` | Restart the device |
| `<name> ota` | Enable OTA update mode (30s) |
| `<name> setup` | Enter configuration mode (AP) |
| `<name> site-on` | Enable web server |
| `<name> site-off` | Disable web server |
| `<name> site-status` | Get web server status |
| `<name> cloud-on` | Enable cloud mode (WSS) |
| `<name> cloud-off` | Disable cloud mode (WSS) |
| `<name> cloud-status` | Get cloud connection status |
| `<name> crypto` | Cryptography information |
| `<name> update-token` | Generate new device token |

### On-the-fly Mode Switch

```bash
# Force specific transport for single command
wl myesp ping tcp      # Use local TCP
wl myesp info http     # Use HTTP relay
wl myesp info wss      # Use WebSocket
```

---

## 🖥️ Server Deployment

### Docker (Recommended)

```bash
docker-compose up -d
```

Server will be available at `http://localhost:9009`

### Manual Installation

```bash
cd server
pip install -r requirements.txt
python main.py
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|--------|
| `DATABASE_FILE` | Database file path | `wakelink_cloud.db` |
| `CLOUD_PORT` | Server port | `9009` |
| `API_ENV` | Environment (production/development) | `development` |

### Default Cloud Server

The client uses `wakelink.deadboizxc.org` as the default cloud server:
- HTTP: `https://wakelink.deadboizxc.org`
- WSS: `wss://wakelink.deadboizxc.org`

---

## 🔐 Security

### Encryption

- **ChaCha20** — symmetric payload encryption
- **HMAC-SHA256** — message authentication
- **Unique nonce** — 16 bytes per message
- **Key derivation** — SHA256 from device_token (32+32 bytes)

### Packet Format

```
┌────────────────────────────────────────────────────────┐
│                    JSON Envelope                       │
├────────────────────────────────────────────────────────┤
│  device_id: "WL35080814"                               │
│  payload: "<hex-encoded encrypted data>"               │
│  signature: "<HMAC-SHA256>"                            │
│  version: "1.0"                                        │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│               Encrypted Payload (hex)                  │
├────────────┬──────────────────────────┬───────────────┤
│  2 bytes   │      Variable length     │   16 bytes    │
│  length    │   ChaCha20 ciphertext    │     nonce     │
│ (big-end)  │                          │               │
└────────────┴──────────────────────────┴───────────────┘
```

---

## 🔧 API Endpoints

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Server health check |
| `/api/stats` | GET | Server statistics |
| `/api/push` | POST | Send command to device |
| `/api/pull` | POST | Get response (supports long polling) |
| `/api/register_device` | POST | Register new device |
| `/api/delete_device` | POST | Delete device |
| `/api/devices` | GET | List user's devices |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/{device_id}` | WebSocket for ESP device |
| `/ws/client/{client_id}` | WebSocket for CLI client |

#### WebSocket Authentication

After connecting, client must send an authentication message:

```json
{"type": "auth", "token": "<api_token>"}
```

Server responds with:
- Success: `{"type": "welcome", "status": "connected", ...}`
- Error: `{"status": "error", "error": "INVALID_TOKEN", ...}`

> **Note:** Header-based authentication (`Authorization`, `X-API-Token`) is still supported for backwards compatibility.

---

## 🐛 Debugging

### Serial Monitor (115200 baud)

| Tag | Meaning |
|-----|---------|
| `[CLOUD]` | WSS connection events |
| `[HMAC]` | Signature verification |
| `[CMD]` | Command execution |
| `[TCP]` | Local TCP events |
| `[WIFI]` | WiFi status |
| `[CRYPTO]` | Encryption operations |
| `[TOKEN]` | Token update events |
| `[RESTART]` | Scheduled restart |

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ERROR:INVALID_SIGNATURE` | Token mismatch | Check `device_token` on both sides |
| `ERROR:LIMIT_EXCEEDED` | Counter overflow | Run `reset-counter` command |
| `ERROR:DECRYPT_FAILED` | Decryption error | Re-sync tokens, restart device |
| `Timeout` | No response | Check connection |
| `WSS unavailable` | Missing dependency | `pip install websocket-client` |

---

## 📁 Project Structure

```
wakelink/
├── firmware/WakeLink/       # ESP8266/ESP32 firmware
│   ├── WakeLink.ino         # Main file
│   ├── config.cpp/h         # EEPROM configuration
│   ├── CryptoManager.cpp/h  # ChaCha20 + HMAC
│   ├── packet.cpp/h         # Packet protocol
│   ├── command.cpp/h        # Command handlers
│   ├── tcp_handler.cpp/h    # TCP server (port 99)
│   ├── cloud.cpp/h          # WSS client
│   ├── web_server.cpp/h     # Configuration web UI
│   ├── ota_manager.cpp/h    # OTA updates
│   └── wifi_manager.cpp/h   # WiFi management
├── client/                  # Python CLI
│   ├── wakelink.py          # Entry point
│   └── core/
│       ├── crypto.py        # Cryptography
│       ├── device_manager.py # Device storage
│       ├── helpers.py       # Utilities
│       ├── handlers/        # Transport handlers
│       │   ├── tcp_handler.py
│       │   ├── cloud_client.py
│       │   └── wss_client.py
│       └── protocol/
│           ├── commands.py  # Command implementations
│           └── packet.py    # Packet encryption
├── server/                  # FastAPI server
│   ├── main.py              # Entry point
│   ├── core/
│   │   ├── auth.py          # Authentication
│   │   ├── database.py      # SQLite via SQLAlchemy
│   │   ├── models.py        # User, Device, Message
│   │   ├── relay.py         # Message queue
│   │   └── schemas.py       # Pydantic validation
│   └── routes/
│       ├── api.py           # REST API
│       ├── wss.py           # WebSocket
│       └── auth.py          # Login/register
├── docker-compose.yml       # Docker config
└── Dockerfile               # Docker image
```

---

## 📄 License

This project is distributed under the **NGC License v1.0**.

- ✅ Personal use allowed
- ❌ Commercial use requires written permission

See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

1. Fork the repository
2. Create a branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

<div align="center">

**Made with ❤️ for the IoT community**

[GitHub](https://github.com/deadboizxc/wakelink) • [Issues](https://github.com/deadboizxc/wakelink/issues)

</div>
