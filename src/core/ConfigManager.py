
# ============================================================================
# USAGE EXAMPLE: Putting It All Together
# ============================================================================

from src.core.config import ConfigManager
from src.core.logging import LoggerFactory
from src.core.errors import ErrorHandler, with_retry
import json
import requests


"""
Example showing how to use all Priority 1 components together
"""

if __name__ == "__main__":
    import pandas as pd
    import sqlite3
    
    # 1. Initialize configuration
    config = ConfigManager()
    print(f"Running in {config.environment} environment")
    print(f"Database: {config.get('database.path')}")
    
    # 2. Create logger
    logger = LoggerFactory.create_logger(
        'momentum_system',
        config,
        context={'version': '1.0.0', 'component': 'main'}
    )
    
    logger.info("System starting up...")
    
    # 3. Create error handler
    error_handler = ErrorHandler(logger, config)
    
    # 4. Example: Using error handling
    @with_retry(max_attempts=3, backoff_factor=2.0)
    def risky_operation():
        """Example function that might fail"""
        import random
        if random.random() < 0.5:
            raise requests.exceptions.ConnectionError("Network failure")
        return "Success!"
    
    try:
        result = risky_operation()
        logger.info(f"Operation completed: {result}")
    except Exception as e:
        recovery_action = error_handler.handle(
            e,
            context={'function': 'risky_operation'},
            retry_count=3
        )
        logger.info(f"Recovery action: {recovery_action.value}")
    
    # 5. Get error report
    error_report = error_handler.get_error_report()
    logger.info(f"Error report: {json.dumps(error_report, indent=2)}")
    
    print("\n✓ Priority 1 components initialized successfully!")
    print("\nNext steps:")
    print("1. Create config/base.yaml file")
    print("2. Create config/development.yaml file")  
    print("3. Create .env file for secrets")
    print("4. Integrate with existing modules")
    print("5. Add tests for each component")