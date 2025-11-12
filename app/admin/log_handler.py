"""
In-memory log handler for admin panel.
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from typing import Deque


class AdminLogHandler(logging.Handler):
    """Log handler that stores logs in memory for admin panel display."""
    
    def __init__(self, max_logs: int = 1000):
        super().__init__()
        self.max_logs = max_logs
        self.logs: Deque[dict] = deque(maxlen=max_logs)
        self.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    def emit(self, record: logging.LogRecord) -> None:
        """Store log record in memory."""
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": self.format(record),
                "raw_message": record.getMessage(),
            }
            self.logs.append(log_entry)
        except Exception:
            pass  # Ignore errors in log handler
    
    def get_logs(self, level: str | None = None, limit: int = 500) -> list[dict]:
        """Get recent logs, optionally filtered by level."""
        logs = list(self.logs)
        if level:
            logs = [log for log in logs if log["level"] == level.upper()]
        return logs[-limit:]
    
    def clear(self) -> None:
        """Clear all logs."""
        self.logs.clear()


# Global log handler instance
_admin_log_handler = AdminLogHandler(max_logs=2000)


def get_admin_log_handler() -> AdminLogHandler:
    """Get the global admin log handler."""
    return _admin_log_handler


def setup_admin_logging() -> None:
    """Setup logging to capture logs for admin panel."""
    # Add handler to root logger to catch all logs
    root_logger = logging.getLogger()
    if _admin_log_handler not in root_logger.handlers:
        root_logger.addHandler(_admin_log_handler)
        root_logger.setLevel(logging.INFO)
    
    # Also add to specific loggers we care about
    loggers_to_capture = [
        "app.ingestion.crawler",
        "app.ingestion.custom_crawler_adapter",
        "app.admin.routes",
        "app.services.embeddings",
        "app.vectorstore.pinecone_store",
        "app.ingestion.pdf_loader",
        "app.ingestion.text_loader",
        "app.ingestion.pipeline",
        "app",
    ]
    
    for logger_name in loggers_to_capture:
        logger = logging.getLogger(logger_name)
        # Only add if not already added
        if _admin_log_handler not in logger.handlers:
            logger.addHandler(_admin_log_handler)
        logger.setLevel(logging.INFO)

