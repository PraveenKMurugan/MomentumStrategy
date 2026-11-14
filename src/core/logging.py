# ============================================================================
# FILE 2: src/core/logging.py
# Enterprise Logging System
# ============================================================================

import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime
import json
import traceback
from typing import Dict, Any
from src.core.config import ConfigManager

class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging
    Compatible with log aggregation tools (ELK, Splunk, etc.)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'thread': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        
        return json.dumps(log_data)


class ContextFilter(logging.Filter):
    """Add contextual information to log records"""
    
    def __init__(self, context: Dict[str, Any] = None):
        super().__init__()
        self.context = context or {}
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add context to record"""
        for key, value in self.context.items():
            setattr(record, key, value)
        return True


class LoggerFactory:
    """
    Factory for creating enterprise-grade loggers
    
    Features:
    - Multiple handlers (console, file, rotating, timed)
    - JSON formatting for production
    - Separate error log files
    - Context injection
    - Performance tracking
    """
    
    @staticmethod
    def create_logger(
        name: str,
        config: ConfigManager,
        context: Dict[str, Any] = None
    ) -> logging.Logger:
        """
        Create a fully configured logger
        
        Args:
            name: Logger name (usually module name)
            config: Configuration manager instance
            context: Additional context to include in logs
        
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Get log level from config
        log_level = getattr(logging, config.get('logging.level', 'INFO'))
        logger.setLevel(log_level)
        
        # Clear existing handlers
        logger.handlers = []
        
        # Create logs directory
        log_dir = Path(config.get('logging.directory', 'logs'))
        log_dir.mkdir(exist_ok=True)
        
        # 1. Console Handler (for development)
        if config.is_development():
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.DEBUG)
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # 2. Rotating File Handler (size-based rotation)
        file_handler = RotatingFileHandler(
            log_dir / f'{name}.log',
            maxBytes=config.get('logging.max_bytes', 10*1024*1024),  # 10MB default
            backupCount=config.get('logging.backup_count', 5)
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # 3. Error File Handler (only errors and critical)
        error_handler = RotatingFileHandler(
            log_dir / f'{name}_errors.log',
            maxBytes=config.get('logging.max_bytes', 10*1024*1024),
            backupCount=config.get('logging.backup_count', 5)
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)
        
        # 4. JSON Handler (for production log aggregation)
        if config.is_production():
            json_handler = RotatingFileHandler(
                log_dir / f'{name}_json.log',
                maxBytes=config.get('logging.max_bytes', 10*1024*1024),
                backupCount=config.get('logging.backup_count', 5)
            )
            json_handler.setLevel(logging.INFO)
            json_handler.setFormatter(JsonFormatter())
            logger.addHandler(json_handler)
        
        # 5. Timed Rotating Handler (daily rotation)
        if config.get('logging.daily_rotation', False):
            daily_handler = TimedRotatingFileHandler(
                log_dir / f'{name}_daily.log',
                when='midnight',
                interval=1,
                backupCount=config.get('logging.retention_days', 30)
            )
            daily_handler.setLevel(logging.INFO)
            daily_handler.setFormatter(file_formatter)
            logger.addHandler(daily_handler)
        
        # Add context filter if provided
        if context:
            context_filter = ContextFilter(context)
            logger.addFilter(context_filter)
        
        # Prevent propagation to root logger
        logger.propagate = False
        
        return logger
