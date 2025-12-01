# 🔗 WakeLink

<div align="center">

[![Protocol](https://img.shields.io/badge/Protocol-v1.0-blue.svg)](https://github.com/deadboizxc/wakelink)
[![License](https://img.shields.io/badge/License-NGC%20v1.0-green.svg)](LICENSE)
[![ESP8266](https://img.shields.io/badge/ESP8266-Compatible-orange.svg)](https://www.espressif.com/)
[![ESP32](https://img.shields.io/badge/ESP32-Compatible-orange.svg)](https://www.espressif.com/)

**Безпечне віддалене керування пристроями Wake-on-LAN**

[English](README.md) | Українська | [Русский](README_RU.md)

</div>

---

## 📖 Опис

WakeLink — це захищена система для віддаленого пробудження комп'ютерів через Wake-on-LAN (WoL). Система складається з трьох компонентів: прошивки для ESP8266/ESP32, Python CLI-клієнта та хмарного relay-сервера.

### Основні можливості

- 🔐 **Наскрізне шифрування** — ChaCha20 + HMAC-SHA256
- 🌐 **Хмарний relay** — керування пристроями з будь-якої точки світу
- 🏠 **Локальний режим** — пряме TCP-підключення в LAN
- ⚡ **Wake-on-LAN** — пробудження комп'ютерів за MAC-адресою
- 🔄 **OTA-оновлення** — оновлення прошивки по повітрю
- 🖥️ **Web-інтерфейс** — налаштування пристрою через браузер
- 🔑 **Оновлення токена** — зміна токена пристрою віддалено

---

## 📐 Архітектура

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WakeLink Protocol v1.0                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐         ┌──────────────┐         ┌──────────────┐   │
│   │    Client    │◄───────►│    Server    │◄───────►│   Firmware   │   │
│   │   (Python)   │ HTTP/   │   (FastAPI)  │   WSS   │  (ESP8266/   │   │
│   │              │  WSS    │              │  only   │   ESP32)     │   │
│   └──────────────┘         └──────────────┘         └──────────────┘   │
│                                   │                                     │
│                            Blind Relay                                  │
│                        (не розшифровує)                                 │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────────┐         ┌──────────────┐                            │
│   │    Client    │◄───────►│   Firmware   │  Local TCP (port 99)       │
│   │   (Python)   │   TCP   │  (ESP8266)   │  Direct LAN Access         │
│   └──────────────┘         └──────────────┘                            │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Режими транспорту

| Режим | Протокол | Опис |
|-------|----------|------|
| **TCP** | TCP:99 | Пряме підключення в локальній мережі, мінімальна затримка |
| **Cloud HTTP** | HTTPS | Клієнт → Сервер: HTTP push/pull, fallback якщо WSS недоступний |
| **Cloud WSS** | WSS | Клієнт ↔ Сервер ↔ ESP: WebSocket, real-time зв'язок |

> **Важливо:** ESP-пристрій **завжди** підключається до сервера по WSS. HTTP використовується тільки між клієнтом і сервером як fallback.

---

## 🚀 Швидкий старт

### 1. Прошивка пристрою

```bash
# Клонуємо репозиторій
git clone https://github.com/deadboizxc/wakelink.git
cd wakelink/firmware/WakeLink

# Відкриваємо в Arduino IDE або PlatformIO
# Встановлюємо залежності:
# - ArduinoJson (v6+)
# - ESP8266WiFi / WiFi
# - WebSocketsClient
```

### 2. Початкове налаштування

1. Прошийте пристрій
2. Підключіться до Wi-Fi точки `WakeLink-XXXXXX`
3. Відкрийте `http://192.168.4.1` в браузері
4. Введіть параметри Wi-Fi та токен пристрою

### 3. Встановлення клієнта

```bash
cd client
pip install -r requirements.txt

# Опціонально: для підтримки WebSocket
pip install websocket-client
```

### 4. Додавання пристрою

**Локальний режим (TCP):**
```bash
python wakelink.py add myesp token YOUR_DEVICE_TOKEN ip 192.168.1.100
```

**Хмарний режим:**
```bash
# Реєстрація на сервері (один раз)
python wakelink.py register myesp device-id WL35080814 api-token YOUR_API_TOKEN token YOUR_DEVICE_TOKEN

# Або додати з власними URL
python wakelink.py add myesp token YOUR_TOKEN http-url https://wakelink.deadboizxc.org wss-url wss://wakelink.deadboizxc.org
```

### 5. Використання

```bash
# Перевірка зв'язку
python wakelink.py myesp ping

# Інформація про пристрій
python wakelink.py myesp info

# Пробудження комп'ютера
python wakelink.py myesp wake AA:BB:CC:DD:EE:FF

# Увімкнення OTA (30 секунд)
python wakelink.py myesp ota

# Оновлення токена пристрою
python wakelink.py myesp update-token
```

---

## 📋 Команди CLI

### Керування пристроями

| Команда | Опис |
|---------|------|
| `add <name> token <TOKEN> ip <IP> [port <PORT>]` | Додати локальний TCP пристрій |
| `add <name> token <TOKEN> http-url <URL> wss-url <URL>` | Додати хмарний пристрій |
| `register <name> device-id <ID> api-token <TOKEN> token <TOKEN>` | Зареєструвати пристрій на сервері |
| `update <name> <field> <value> [<field> <value>...]` | Оновити поля пристрою |
| `remove <name>` | Видалити пристрій |
| `list` | Список всіх пристроїв |

### Команди пристрою

| Команда | Опис |
|---------|------|
| `<name> ping` | Перевірити зв'язок з пристроєм |
| `<name> info` | Отримати інформацію про пристрій |
| `<name> wake <MAC>` | Відправити Wake-on-LAN пакет |
| `<name> restart` | Перезавантажити пристрій |
| `<name> ota` | Увімкнути режим OTA-оновлення (30с) |
| `<name> setup` | Увійти в режим налаштування (AP) |
| `<name> site-on` | Увімкнути веб-сервер |
| `<name> site-off` | Вимкнути веб-сервер |
| `<name> site-status` | Статус веб-сервера |
| `<name> cloud-on` | Увімкнути cloud mode (WSS) |
| `<name> cloud-off` | Вимкнути cloud mode (WSS) |
| `<name> cloud-status` | Статус cloud-підключення |
| `<name> crypto` | Інформація про криптографію |
| `<name> update-token` | Згенерувати новий токен |

### Перемикання режиму на льоту

```bash
# Примусово використати конкретний транспорт для однієї команди
wl myesp ping tcp      # Використати локальний TCP
wl myesp info http     # Використати HTTP relay
wl myesp info wss      # Використати WebSocket
```

---

## 🖥️ Розгортання сервера

### Docker (рекомендовано)

```bash
docker-compose up -d
```

Сервер буде доступний на `http://localhost:9009`

### Ручне встановлення

```bash
cd server
pip install -r requirements.txt
python main.py
```

### Змінні оточення

| Змінна | Опис | За замовчуванням |
|--------|------|------------------|
| `DATABASE_FILE` | Шлях до бази даних | `wakelink_cloud.db` |
| `CLOUD_PORT` | Порт сервера | `9009` |
| `API_ENV` | Середовище | `development` |

### Хмарний сервер за замовчуванням

Клієнт використовує `wakelink.deadboizxc.org` як хмарний сервер:
- HTTP: `https://wakelink.deadboizxc.org`
- WSS: `wss://wakelink.deadboizxc.org`

---

## 🔐 Безпека

### Шифрування

- **ChaCha20** — симетричне шифрування payload
- **HMAC-SHA256** — аутентифікація повідомлень
- **Унікальний nonce** — 16 байт для кожного повідомлення
- **Деривація ключа** — SHA256 від device_token (32+32 байти)

### Формат пакета

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

| Endpoint | Method | Опис |
|----------|--------|------|
| `/api/health` | GET | Перевірка стану сервера |
| `/api/stats` | GET | Статистика сервера |
| `/api/push` | POST | Відправити команду пристрою |
| `/api/pull` | POST | Отримати відповідь (підтримує long polling) |
| `/api/register_device` | POST | Зареєструвати новий пристрій |
| `/api/delete_device` | POST | Видалити пристрій |
| `/api/devices` | GET | Список пристроїв користувача |

### WebSocket

| Endpoint | Опис |
|----------|------|
| `/ws/{device_id}` | WebSocket для ESP-пристрою |
| `/ws/client/{client_id}` | WebSocket для CLI-клієнта |

#### Аутентифікація WebSocket

Після підключення клієнт повинен відправити повідомлення аутентифікації:

```json
{"type": "auth", "token": "<api_token>"}
```

Сервер відповідає:
- Успіх: `{"type": "welcome", "status": "connected", ...}`
- Помилка: `{"status": "error", "error": "INVALID_TOKEN", ...}`

> **Примітка:** Аутентифікація через заголовки (`Authorization`, `X-API-Token`) досі підтримується для зворотної сумісності.

---

## 🐛 Налагодження

### Serial Monitor (115200 baud)

| Тег | Значення |
|-----|----------|
| `[CLOUD]` | Події WSS-підключення |
| `[HMAC]` | Перевірка підпису |
| `[CMD]` | Виконання команд |
| `[TCP]` | Локальні TCP-події |
| `[WIFI]` | Стан Wi-Fi |
| `[CRYPTO]` | Операції шифрування |
| `[TOKEN]` | Події оновлення токена |
| `[RESTART]` | Заплановане перезавантаження |

### Часті помилки

| Помилка | Причина | Рішення |
|---------|---------|--------|
| `ERROR:INVALID_SIGNATURE` | Неспівпадіння токенів | Перевірте `device_token` з обох сторін |
| `ERROR:LIMIT_EXCEEDED` | Переповнення лічильника | Виконайте `reset-counter` |
| `ERROR:DECRYPT_FAILED` | Помилка розшифрування | Пересинхронізуйте токени, перезавантажте пристрій |
| `Timeout` | Немає відповіді | Перевірте підключення |
| `WSS unavailable` | Відсутня залежність | `pip install websocket-client` |

---

## 📁 Структура проекту

```
wakelink/
├── firmware/WakeLink/       # Прошивка ESP8266/ESP32
│   ├── WakeLink.ino         # Головний файл
│   ├── config.cpp/h         # Конфігурація EEPROM
│   ├── CryptoManager.cpp/h  # ChaCha20 + HMAC
│   ├── packet.cpp/h         # Протокол пакетів
│   ├── command.cpp/h        # Обробники команд
│   ├── tcp_handler.cpp/h    # TCP сервер (порт 99)
│   ├── cloud.cpp/h          # WSS клієнт
│   ├── web_server.cpp/h     # Веб-інтерфейс налаштування
│   ├── ota_manager.cpp/h    # OTA оновлення
│   └── wifi_manager.cpp/h   # Керування WiFi
├── client/                  # Python CLI
│   ├── wakelink.py          # Точка входу
│   └── core/
│       ├── crypto.py        # Криптографія
│       ├── device_manager.py # Зберігання пристроїв
│       ├── helpers.py       # Утиліти
│       ├── handlers/        # Транспортні обробники
│       │   ├── tcp_handler.py
│       │   ├── cloud_client.py
│       │   └── wss_client.py
│       └── protocol/
│           ├── commands.py  # Реалізація команд
│           └── packet.py    # Шифрування пакетів
├── server/                  # FastAPI сервер
│   ├── main.py              # Точка входу
│   ├── core/
│   │   ├── auth.py          # Аутентифікація
│   │   ├── database.py      # SQLite через SQLAlchemy
│   │   ├── models.py        # User, Device, Message
│   │   ├── relay.py         # Черга повідомлень
│   │   └── schemas.py       # Pydantic валідація
│   └── routes/
│       ├── api.py           # REST API
│       ├── wss.py           # WebSocket
│       └── auth.py          # Логін/реєстрація
├── docker-compose.yml       # Docker конфігурація
└── Dockerfile               # Docker образ
```

---

## 📄 Ліцензія

Цей проект поширюється під ліцензією **NGC License v1.0**.

- ✅ Особисте використання дозволено
- ❌ Комерційне використання вимагає письмового дозволу

Детальніше див. файл [LICENSE](LICENSE).

---

## 🤝 Внесок у проект

1. Зробіть форк репозиторію
2. Створіть гілку (`git checkout -b feature/amazing`)
3. Зафіксуйте зміни (`git commit -m 'Add amazing feature'`)
4. Відправте в гілку (`git push origin feature/amazing`)
5. Відкрийте Pull Request

---

<div align="center">

**Made with ❤️ for the IoT community**

[GitHub](https://github.com/deadboizxc/wakelink) • [Issues](https://github.com/deadboizxc/wakelink/issues)

</div>
