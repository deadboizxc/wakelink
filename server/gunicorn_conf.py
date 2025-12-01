import multiprocessing
from core.config import settings

# Socket binding
bind = f"0.0.0.0:{settings.CLOUD_PORT}"

# Worker processes (optimal for I/O bound applications)
workers = multiprocessing.cpu_count() * 2

# Use uvicorn workers for ASGI
worker_class = "uvicorn.workers.UvicornWorker"

# Performance settings
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 5

# WebSocket settings for ESP compatibility
# Note: These are passed to uvicorn worker via environment
# Set WS_PING_INTERVAL=30 and WS_PING_TIMEOUT=30 in environment

# Logging
accesslog = "/var/log/wakelink/access.log"
errorlog = "/var/log/wakelink/error.log"
loglevel = "info"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Process naming
proc_name = "wakelink_cloud_server"