"""WakeLink Cloud Server - Main Entry Point.

FastAPI server implementing WakeLink Protocol v1.0 with three equal transports:
- HTTP REST API (push/pull endpoints)
- WebSocket Secure (real-time bidirectional communication)
- Transparent relay (server never decrypts payload)

The server acts as a blind relay between clients and devices,
validating only API tokens and forwarding outer JSON packets as-is.

Author: deadboizxc
Version: 1.0
License: NGC License
"""

import logging
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from core import init_db, start_cleanup_thread, settings, logger
from routes.api import router as api_router
from routes.wss import router as wss_router
from routes.home import router as home_router
from routes.auth import router as auth_router
from routes.admin import router as admin_router


def setup_logging() -> None:
    """Configure logging for the server.
    
    Sets up console handler with timestamp format for the wakelink_cloud logger.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler.
    
    Initializes database and starts background cleanup thread on startup.
    
    Args:
        app: The FastAPI application instance.
    """
    logger.info("=" * 50)
    logger.info("WakeLink Cloud Server v1.0 Starting")
    logger.info("=" * 50)
    
    # Initialize database
    init_db()
    logger.info(f"Database: {settings.DATABASE_FILE}")
    
    # Start background cleanup
    start_cleanup_thread()
    
    logger.info(f"Server Port: {settings.CLOUD_PORT}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    logger.info("=" * 50)
    
    yield
    
    logger.info("WakeLink Cloud Server Shutting Down")


# Create FastAPI application
app = FastAPI(
    title="WakeLink Cloud Server",
    description="Secure relay server for WakeLink Protocol v1.0",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for browser clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(api_router)
app.include_router(wss_router)
app.include_router(home_router)
app.include_router(auth_router)
app.include_router(admin_router)


if __name__ == "__main__":
    setup_logging()
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.CLOUD_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        # WebSocket settings for ESP compatibility
        ws_ping_interval=30,  # Send ping every 30 seconds
        ws_ping_timeout=30,   # Wait 30 seconds for pong (ESP is slow)
    )
