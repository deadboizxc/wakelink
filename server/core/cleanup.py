import time
import threading
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import Message

def cleanup_old_messages():
    """Background task: delete messages older than MESSAGE_RETENTION_MINUTES"""
    while True:
        time.sleep(60)
        db = SessionLocal()
        try:
            cutoff_time = datetime.now().astimezone() - timedelta(minutes=settings.MESSAGE_RETENTION_MINUTES)
            deleted = db.query(Message).filter(Message.timestamp < cutoff_time).delete()
            db.commit()
            if deleted > 0:
                from . import logger
                logger.info(f"Cleaned {deleted} old messages")
        except Exception as e:
            from . import logger
            logger.error(f"Error cleaning messages: {e}")
        finally:
            db.close()

def start_cleanup_thread():
    """Start background message cleanup"""
    thread = threading.Thread(target=cleanup_old_messages, daemon=True)
    thread.start()
    from . import logger
    logger.info("Background message cleanup started")