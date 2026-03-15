"""
Centralized logging system with structured logging
"""
import logging
import sys
from pathlib import Path
try:
    from pythonjsonlogger import jsonlogger
except ImportError:
    jsonlogger = None
from app.core.config.settings import get_settings


def setup_logging():
    """Configure structured logging system"""
    settings = get_settings()
    
    # Create logs directory
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level))
    
    # Console handler with JSON format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level))
    
    if jsonlogger:
        json_formatter = jsonlogger.JsonFormatter()
        console_handler.setFormatter(json_formatter)
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
    
    root_logger.addHandler(console_handler)
    
    # File handler with JSON format
    file_handler = logging.FileHandler(settings.log_file)
    file_handler.setLevel(getattr(logging, settings.log_level))
    
    if jsonlogger:
        file_handler.setFormatter(json_formatter)
    else:
        file_handler.setFormatter(formatter)
    
    root_logger.addHandler(file_handler)
    
    # Disable overly verbose loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    return root_logger


class SystemLogger:
    """Application-level logger"""
    
    def __init__(self, name: str = "app"):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, **extras):
        self.logger.info(message, extra=extras)
    
    def error(self, message: str, **extras):
        self.logger.error(message, extra=extras)
    
    def warning(self, message: str, **extras):
        self.logger.warning(message, extra=extras)
    
    def debug(self, message: str, **extras):
        self.logger.debug(message, extra=extras)


# Initialize logging on module import
setup_logging()
