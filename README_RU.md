# 🔗 WakeLink

<div align="center">

[![Protocol](https://img.shields.io/badge/Protocol-v1.0-blue.svg)](https://github.com/deadboizxc/wakelink)
[![License](https://img.shields.io/badge/License-NGC%20v1.0-green.svg)](LICENSE)
[![ESP8266](https://img.shields.io/badge/ESP8266-Compatible-orange.svg)](https://www.espressif.com/)
[![ESP32](https://img.shields.io/badge/ESP32-Compatible-orange.svg)](https://www.espressif.com/)

**Безопасное удалённое управление устройствами Wake-on-LAN**

[English](README.md) | [Українська](README_UA.md) | Русский

</div>

---

## 📖 Описание

WakeLink — это защищённая система для удалённого пробуждения компьютеров через Wake-on-LAN (WoL). Система состоит из трёх компонентов: прошивки для ESP8266/ESP32, Python CLI-клиента и облачного relay-сервера.

### Основные возможности

- 🔐 **Сквозное шифрование** — ChaCha20 + HMAC-SHA256
- 🌐 **Облачный relay** — управление устройствами из любой точки мира
- 🏠 **Локальный режим** — прямое TCP-подключение в LAN
- ⚡ **Wake-on-LAN** — пробуждение компьютеров по MAC-адресу
- 🔄 **OTA-обновления** — обновление прошивки по воздуху
- 🖥️ **Web-интерфейс** — настройка устройства через браузер
- 🔑 **Обновление токена** — смена токена устройства удалённо

---

## 📐 Архитектура

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
│                       (не расшифровывает)                               │
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

### Режимы транспорта

| Режим | Протокол | Описание |
|-------|----------|----------|
| **TCP** | TCP:99 | Прямое подключение в локальной сети, минимальная задержка |
| **Cloud HTTP** | HTTPS | Клиент → Сервер: HTTP push/pull с long polling |
| **Cloud WSS** | WSS | Клиент ↔ Сервер ↔ ESP: WebSocket, real-time связь |

> **Важно:** ESP-устройство **всегда** подключается к серверу по WSS. HTTP используется только между клиентом и сервером как fallback.

---

## 🚀 Быстрый старт

### 1. Прошивка устройства

```bash
# Клонируем репозиторий
git clone https://github.com/deadboizxc/wakelink.git
cd wakelink/firmware/WakeLink

# Открываем в Arduino IDE или PlatformIO
# Устанавливаем зависимости:
# - ArduinoJson (v6+)
# - ESP8266WiFi / WiFi
# - WebSocketsClient
```

### 2. Первоначальная настройка

1. Прошейте устройство
2. Подключитесь к Wi-Fi точке `WakeLink-XXXXXX`
3. Откройте `http://192.168.4.1` в браузере
4. Введите параметры Wi-Fi и токен устройства

### 3. Установка клиента

```bash
cd client
pip install -r requirements.txt

# Опционально: для поддержки WebSocket
pip install websocket-client
```

### 4. Добавление устройства

**Локальный режим (TCP):**
```bash
python wakelink.py add myesp token YOUR_DEVICE_TOKEN ip 192.168.1.100
```

**Облачный режим:**
```bash
# Регистрация на сервере (один раз)
python wakelink.py register myesp device-id WL35080814 api-token YOUR_API_TOKEN token YOUR_DEVICE_TOKEN

# Или добавить с пользовательскими URL
python wakelink.py add myesp token YOUR_TOKEN http-url https://wakelink.deadboizxc.org wss-url wss://wakelink.deadboizxc.org
```

### 5. Использование

```bash
# Проверка связи
python wakelink.py myesp ping

# Информация об устройстве
python wakelink.py myesp info

# Пробуждение компьютера
python wakelink.py myesp wake AA:BB:CC:DD:EE:FF

# Включение OTA (30 секунд)
python wakelink.py myesp ota

# Обновление токена устройства
python wakelink.py myesp update-token
```

---

## 📋 Команды CLI

### Управление устройствами

| Команда | Описание |
|---------|----------|
| `add <name> token <TOKEN> ip <IP> [port <PORT>]` | Добавить локальное TCP устройство |
| `add <name> token <TOKEN> http-url <URL> wss-url <URL>` | Добавить облачное устройство |
| `register <name> device-id <ID> api-token <TOKEN> token <TOKEN>` | Зарегистрировать устройство на сервере |
| `update <name> <field> <value> [<field> <value>...]` | Обновить поля устройства |
| `remove <name>` | Удалить устройство |
| `list` | Список всех устройств |

### Команды устройства

| Команда | Описание |
|---------|----------|
| `<name> ping` | Проверить связь с устройством |
| `<name> info` | Получить информацию об устройстве |
| `<name> wake <MAC>` | Отправить Wake-on-LAN пакет |
| `<name> restart` | Перезагрузить устройство |
| `<name> ota` | Включить режим OTA-обновления (30с) |
| `<name> setup` | Войти в режим настройки (AP) |
| `<name> site-on` | Включить веб-сервер |
| `<name> site-off` | Выключить веб-сервер |
| `<name> site-status` | Статус веб-сервера |
| `<name> cloud-on` | Включить cloud mode (WSS) |
| `<name> cloud-off` | Выключить cloud mode (WSS) |
| `<name> cloud-status` | Статус cloud-подключения |
| `<name> crypto` | Информация о криптографии |
| `<name> update-token` | Сгенерировать новый токен |

### Переключение режима на лету

```bash
# Принудительно использовать конкретный транспорт для одной команды
wl myesp ping tcp      # Использовать локальный TCP
wl myesp info http     # Использовать HTTP relay
wl myesp info wss      # Использовать WebSocket
```

---

## 🖥️ Развёртывание сервера

### Docker (рекомендуется)

```bash
docker-compose up -d
```

Сервер будет доступен на `http://localhost:9009`

### Ручная установка

```bash
cd server
pip install -r requirements.txt
python main.py
```

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `DATABASE_FILE` | Путь к файлу базы данных | `wakelink_cloud.db` |
| `CLOUD_PORT` | Порт сервера | `9009` |
| `API_ENV` | Окружение (production/development) | `development` |

### Облачный сервер по умолчанию

Клиент использует `wakelink.deadboizxc.org` как облачный сервер по умолчанию:
- HTTP: `https://wakelink.deadboizxc.org`
- WSS: `wss://wakelink.deadboizxc.org`

---

## 🔐 Безопасность

### Шифрование

- **ChaCha20** — симметричное шифрование payload
- **HMAC-SHA256** — аутентификация сообщений
- **Уникальный nonce** — 16 байт для каждого сообщения
- **Деривация ключа** — SHA256 от device_token (32+32 байта)

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

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/api/health` | GET | Проверка состояния сервера |
| `/api/stats` | GET | Статистика сервера |
| `/api/push` | POST | Отправить команду устройству |
| `/api/pull` | POST | Получить ответ (поддерживает long polling) |
| `/api/register_device` | POST | Зарегистрировать новое устройство |
| `/api/delete_device` | POST | Удалить устройство |
| `/api/devices` | GET | Список устройств пользователя |

### WebSocket

| Endpoint | Описание |
|----------|----------|
| `/ws/{device_id}` | WebSocket для ESP-устройства |
| `/ws/client/{client_id}` | WebSocket для CLI-клиента |

#### Аутентификация WebSocket

После подключения клиент должен отправить сообщение аутентификации:

```json
{"type": "auth", "token": "<api_token>"}
```

Сервер отвечает:
- Успех: `{"type": "welcome", "status": "connected", ...}`
- Ошибка: `{"status": "error", "error": "INVALID_TOKEN", ...}`

> **Примечание:** Аутентификация через заголовки (`Authorization`, `X-API-Token`) всё ещё поддерживается для обратной совместимости.

---

## 🐛 Отладка

### Serial Monitor (115200 baud)

| Тег | Значение |
|-----|----------|
| `[CLOUD]` | События WSS-подключения |
| `[HMAC]` | Проверка подписи |
| `[CMD]` | Выполнение команд |
| `[TCP]` | Локальные TCP-события |
| `[WIFI]` | Состояние Wi-Fi |
| `[CRYPTO]` | Операции шифрования |
| `[TOKEN]` | События обновления токена |
| `[RESTART]` | Запланированная перезагрузка |

### Частые ошибки

| Ошибка | Причина | Решение |
|--------|---------|---------|
| `ERROR:INVALID_SIGNATURE` | Несовпадение токенов | Проверьте `device_token` с обеих сторон |
| `ERROR:LIMIT_EXCEEDED` | Переполнение счётчика | Выполните `reset-counter` команду |
| `ERROR:DECRYPT_FAILED` | Ошибка расшифровки | Пересинхронизируйте токены, перезагрузите устройство |
| `Timeout` | Нет ответа | Проверьте подключение |
| `WSS unavailable` | Отсутствует зависимость | `pip install websocket-client` |

---

## 📁 Структура проекта

```
wakelink/
├── firmware/WakeLink/       # Прошивка ESP8266/ESP32
│   ├── WakeLink.ino         # Главный файл
│   ├── config.cpp/h         # Конфигурация EEPROM
│   ├── CryptoManager.cpp/h  # ChaCha20 + HMAC
│   ├── packet.cpp/h         # Протокол пакетов
│   ├── command.cpp/h        # Обработчики команд
│   ├── tcp_handler.cpp/h    # TCP сервер (порт 99)
│   ├── cloud.cpp/h          # WSS клиент
│   ├── web_server.cpp/h     # Веб-интерфейс настройки
│   ├── ota_manager.cpp/h    # OTA обновления
│   └── wifi_manager.cpp/h   # Управление WiFi
├── client/                  # Python CLI
│   ├── wakelink.py          # Точка входа
│   └── core/
│       ├── crypto.py        # Криптография
│       ├── device_manager.py # Хранение устройств
│       ├── helpers.py       # Утилиты
│       ├── handlers/        # Транспортные обработчики
│       │   ├── tcp_handler.py
│       │   ├── cloud_client.py
│       │   └── wss_client.py
│       └── protocol/
│           ├── commands.py  # Реализация команд
│           └── packet.py    # Шифрование пакетов
├── server/                  # FastAPI сервер
│   ├── main.py              # Точка входа
│   ├── core/
│   │   ├── auth.py          # Аутентификация
│   │   ├── database.py      # SQLite через SQLAlchemy
│   │   ├── models.py        # User, Device, Message
│   │   ├── relay.py         # Очередь сообщений
│   │   └── schemas.py       # Pydantic валидация
│   └── routes/
│       ├── api.py           # REST API
│       ├── wss.py           # WebSocket
│       └── auth.py          # Логин/регистрация
├── docker-compose.yml       # Docker конфигурация
└── Dockerfile               # Docker образ
```

---

## 📄 Лицензия

Этот проект распространяется под лицензией **NGC License v1.0**.

- ✅ Личное использование разрешено
- ❌ Коммерческое использование требует письменного разрешения

Подробнее см. файл [LICENSE](LICENSE).

---

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/amazing`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing`)
5. Откройте Pull Request

---

<div align="center">

**Made with ❤️ for the IoT community**

[GitHub](https://github.com/deadboizxc/wakelink) • [Issues](https://github.com/deadboizxc/wakelink/issues)

</div>
