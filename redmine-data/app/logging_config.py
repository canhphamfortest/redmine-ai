"""
Logging configuration for the application
Logs are written to /app/logs/ which is mounted from host ./logs/
"""
import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path("/app/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Log file paths with date
TODAY = datetime.now().strftime("%Y-%m-%d")
LOG_FILE = LOG_DIR / f"app-{TODAY}.log"
ERROR_LOG_FILE = LOG_DIR / f"error-{TODAY}.log"


def setup_logging(service_name: str = "backend", level: str = "INFO"):
    """
    Setup logging configuration for the service
    
    Args:
        service_name: Name of the service (backend, scheduler, etc.)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Suppress verbose SQLAlchemy logging (only show WARNING and above)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
    
    # Suppress uvicorn access logs (we use custom middleware instead)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    
    # Console handler (stdout) - for docker logs command
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - All logs (INFO and above) with daily rotation
    # Compressed rotated files to save disk space
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / f"{service_name}.log",
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days (reduced from 90)
        encoding='utf-8',
        utc=False
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(detailed_formatter)
    file_handler.suffix = "%Y-%m-%d"  # Add date suffix to rotated files
    file_handler.namer = lambda name: name + ".gz"  # Add .gz extension for compression
    
    # Custom rotator to compress logs
    def gzip_rotator(source, dest):
        import gzip
        import shutil
        with open(source, 'rb') as f_in:
            with gzip.open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(source)
    
    file_handler.rotator = gzip_rotator
    root_logger.addHandler(file_handler)
    
    # File handler - Error logs only (ERROR and above)
    error_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / f"{service_name}-error.log",
        when='midnight',
        interval=1,
        backupCount=30,  # Keep 30 days (reduced from 90)
        encoding='utf-8',
        utc=False
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    error_handler.suffix = "%Y-%m-%d"
    error_handler.namer = lambda name: name + ".gz"  # Add .gz extension for compression
    error_handler.rotator = gzip_rotator
    root_logger.addHandler(error_handler)
    
    # Access log handler - HTTP requests only
    access_logger = logging.getLogger('access')
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False  # Don't propagate to root logger
    
    access_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / f"{service_name}-access.log",
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8',
        utc=False
    )
    access_handler.setLevel(logging.INFO)
    access_handler.setFormatter(simple_formatter)
    access_handler.suffix = "%Y-%m-%d"
    access_handler.namer = lambda name: name + ".gz"
    access_handler.rotator = gzip_rotator
    access_logger.addHandler(access_handler)
    
    # Log startup message
    logging.info(f"="*80)
    logging.info(f"{service_name.upper()} - Logging initialized")
    logging.info(f"Log directory: {LOG_DIR}")
    logging.info(f"Log level: {level}")
    logging.info(f"Time-based rotation: Daily, keeping 30 days")
    logging.info(f"Log compression: Enabled (gzip)")
    logging.info(f"SQLAlchemy logging: Suppressed (WARNING+ only)")
    logging.info(f"Access logging: Enabled (separate file: {service_name}-access.log)")
    logging.info(f"="*80)
    
    return root_logger


def get_logger(name: str):
    """
    Get a logger with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)


# For backward compatibility
def configure_logging(service_name: str = "backend", level: str = "INFO"):
    """Alias for setup_logging"""
    return setup_logging(service_name, level)
