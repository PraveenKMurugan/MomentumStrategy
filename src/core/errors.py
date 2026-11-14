# ============================================================================
# FILE 3: src/core/errors.py
# Enterprise Error Handling
# ============================================================================

from enum import Enum
from typing import Optional, Callable, Any
import time
import requests
from datetime import datetime
import logging
from src.core.config import ConfigManager, ConfigurationError
import pandas as pd
import sqlite3
import json
from typing import Dict


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    DATA_QUALITY = "data_quality"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    UNKNOWN = "unknown"

class RecoveryAction(Enum):
    """Recovery action recommendations"""
    RETRY = "retry"
    SKIP = "skip"
    FAIL = "fail"
    FALLBACK = "fallback"
    ALERT = "alert"

class MomentumSystemError(Exception):
    """Base exception for momentum system"""
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recovery_action: RecoveryAction = RecoveryAction.FAIL,
        original_exception: Optional[Exception] = None
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.recovery_action = recovery_action
        self.original_exception = original_exception
        self.timestamp = datetime.now()

class DataFetchError(MomentumSystemError):
    """Error during data fetching"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.EXTERNAL_API,
            **kwargs
        )

class ValidationError(MomentumSystemError):
    """Error during data validation"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.VALIDATION,
            **kwargs
        )

class DataQualityError(MomentumSystemError):
    """Error due to poor data quality"""
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.DATA_QUALITY,
            **kwargs
        )

class ErrorHandler:
    """
    Centralized error handling with recovery strategies
    
    Features:
    - Error classification and categorization
    - Recovery action recommendations
    - Error statistics tracking
    - Alert triggering for critical errors
    """
    
    def __init__(self, logger: logging.Logger, config: ConfigManager):
        self.logger = logger
        self.config = config
        self.error_counts = {}
        self.error_history = []
    
    def handle(
        self,
        error: Exception,
        context: Dict[str, Any] = None,
        retry_count: int = 0
    ) -> RecoveryAction:
        """
        Handle an error and return recovery action
        
        Args:
            error: The exception that occurred
            context: Additional context about where error occurred
            retry_count: Number of retries already attempted
        
        Returns:
            Recommended recovery action
        """
        # Classify error
        category, severity, recovery = self._classify_error(error, retry_count)
        
        # Track error
        self._track_error(error, category, severity)
        
        # Log error
        self._log_error(error, category, severity, context)
        
        # Alert if critical
        if severity == ErrorSeverity.CRITICAL:
            self._trigger_alert(error, context)
        
        return recovery
    
    def _classify_error(
        self,
        error: Exception,
        retry_count: int
    ) -> tuple[ErrorCategory, ErrorSeverity, RecoveryAction]:
        """Classify error and determine recovery action"""
        
        # Network errors
        if isinstance(error, (requests.exceptions.ConnectionError, 
                            requests.exceptions.Timeout)):
            if retry_count < 3:
                return (ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, 
                       RecoveryAction.RETRY)
            else:
                return (ErrorCategory.NETWORK, ErrorSeverity.HIGH, 
                       RecoveryAction.SKIP)
        
        # HTTP errors
        elif isinstance(error, requests.exceptions.HTTPError):
            status_code = error.response.status_code if hasattr(error, 'response') else 0
            
            if status_code == 429:  # Rate limit
                return (ErrorCategory.EXTERNAL_API, ErrorSeverity.MEDIUM, 
                       RecoveryAction.RETRY)
            elif 500 <= status_code < 600:  # Server error
                return (ErrorCategory.EXTERNAL_API, ErrorSeverity.HIGH, 
                       RecoveryAction.RETRY)
            else:
                return (ErrorCategory.EXTERNAL_API, ErrorSeverity.MEDIUM, 
                       RecoveryAction.SKIP)
        
        # Data quality errors
        elif isinstance(error, (DataQualityError, pd.errors.EmptyDataError)):
            return (ErrorCategory.DATA_QUALITY, ErrorSeverity.LOW, 
                   RecoveryAction.SKIP)
        
        # Validation errors
        elif isinstance(error, (ValidationError, ValueError)):
            return (ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, 
                   RecoveryAction.SKIP)
        
        # Configuration errors
        elif isinstance(error, ConfigurationError):
            return (ErrorCategory.CONFIGURATION, ErrorSeverity.CRITICAL, 
                   RecoveryAction.FAIL)
        
        # Database errors
        elif isinstance(error, sqlite3.Error):
            return (ErrorCategory.DATABASE, ErrorSeverity.HIGH, 
                   RecoveryAction.RETRY)
        
        # Unknown errors
        else:
            return (ErrorCategory.UNKNOWN, ErrorSeverity.HIGH, 
                   RecoveryAction.FAIL)
    
    def _track_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity
    ):
        """Track error statistics"""
        error_type = type(error).__name__
        
        if error_type not in self.error_counts:
            self.error_counts[error_type] = {
                'count': 0,
                'category': category.value,
                'severity': severity.value
            }
        
        self.error_counts[error_type]['count'] += 1
        
        # Keep recent error history
        self.error_history.append({
            'timestamp': datetime.now(),
            'type': error_type,
            'message': str(error),
            'category': category.value,
            'severity': severity.value
        })
        
        # Keep only last 1000 errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
    
    def _log_error(
        self,
        error: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any] = None
    ):
        """Log error with appropriate level"""
        error_msg = f"[{category.value}] {type(error).__name__}: {str(error)}"
        
        if context:
            error_msg += f" | Context: {context}"
        
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error_msg, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            self.logger.error(error_msg, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            self.logger.warning(error_msg)
        else:
            self.logger.info(error_msg)
    
    def _trigger_alert(self, error: Exception, context: Dict[str, Any] = None):
        """Trigger alert for critical errors"""
        # This would integrate with your alerting system
        # (email, Slack, PagerDuty, etc.)
        alert_message = f"CRITICAL ERROR: {type(error).__name__}: {str(error)}"
        if context:
            alert_message += f"\nContext: {json.dumps(context, indent=2)}"
        
        self.logger.critical(f"ALERT TRIGGERED: {alert_message}")
        
        # TODO: Implement actual alert delivery
        # self._send_email_alert(alert_message)
        # self._send_slack_alert(alert_message)
    
    def get_error_report(self) -> Dict:
        """Generate error summary report"""
        total_errors = sum(e['count'] for e in self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_breakdown': self.error_counts,
            'recent_errors': self.error_history[-10:],  # Last 10 errors
            'generated_at': datetime.now().isoformat()
        }


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator for automatic retry with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        backoff_factor: Multiplier for wait time between retries
        exceptions: Tuple of exceptions to catch and retry
    
    Example:
        @with_retry(max_attempts=3, backoff_factor=2.0)
        def fetch_data(symbol):
            return yf.download(symbol)
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait_time = backoff_factor ** attempt
                        logging.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time}s..."
                        )
                        time.sleep(wait_time)
                    else:
                        logging.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator
