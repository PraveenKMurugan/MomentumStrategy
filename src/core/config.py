# ============================================================================
# FILE 1: src/core/config.py
# Enterprise Configuration Management
# ============================================================================

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
import logging

class ConfigurationError(Exception):
    """Custom exception for configuration errors"""
    pass

class ConfigManager:
    """
    Enterprise configuration management system
    
    Features:
    - Environment-specific configs (dev/staging/prod)
    - Environment variable overrides
    - Configuration validation
    - Hot reload capability
    - Secrets management
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern - only one config instance"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize configuration"""
        if self._initialized:
            return
            
        # Load environment variables from .env file
        load_dotenv()
        
        # Determine environment
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Set up paths
        self.base_dir = Path(__file__).parent.parent.parent
        self.config_dir = self.base_dir / 'config'
        
        # Load configuration
        self.config = self._load_config()
        
        # Validate
        self._validate_config()
        
        self._initialized = True
    
    def _load_config(self) -> Dict:
        """Load and merge configuration files"""
        # Load base config
        base_config_path = self.config_dir / 'base.yaml'
        if not base_config_path.exists():
            raise ConfigurationError(f"Base config not found: {base_config_path}")
        
        with open(base_config_path, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        
        # Load environment-specific config
        env_config_path = self.config_dir / f'{self.environment}.yaml'
        if env_config_path.exists():
            with open(env_config_path, 'r', encoding="utf-8") as f:
                env_config = yaml.safe_load(f) or {}
            
            # Deep merge configs
            config = self._deep_merge(config, env_config)
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        return config
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: Dict) -> Dict:
        """Apply environment variable overrides"""
        # Database path
        if os.getenv('DB_PATH'):
            config['database']['path'] = os.getenv('DB_PATH')
        
        # API settings
        if os.getenv('API_RATE_LIMIT'):
            config['api']['rate_limit'] = int(os.getenv('API_RATE_LIMIT'))
        
        if os.getenv('API_TIMEOUT'):
            config['api']['timeout'] = int(os.getenv('API_TIMEOUT'))
        
        # Logging
        if os.getenv('LOG_LEVEL'):
            config['logging']['level'] = os.getenv('LOG_LEVEL')
        
        # Secrets
        if os.getenv('EMAIL_PASSWORD'):
            config['alerts']['email_password'] = os.getenv('EMAIL_PASSWORD')
        
        if os.getenv('SLACK_WEBHOOK'):
            config['alerts']['slack_webhook'] = os.getenv('SLACK_WEBHOOK')
        
        return config
    
    def _validate_config(self):
        """Validate configuration values"""
        required_sections = ['database', 'api', 'trading', 'risk', 'logging']
        
        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f"Missing required config section: {section}")
        
        # Validate specific values
        trading = self.config['trading']
        if not 0 <= trading['transaction_cost_pct'] <= 1:
            raise ConfigurationError("transaction_cost_pct must be between 0 and 1")
        
        if not 0 < trading['max_position_size'] <= 1:
            raise ConfigurationError("max_position_size must be between 0 and 1")
        
        risk = self.config['risk']
        if not -1 <= risk['max_drawdown_threshold'] <= 0:
            raise ConfigurationError("max_drawdown_threshold must be between -1 and 0")
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key_path: Dot-separated path (e.g., 'database.path')
            default: Default value if key not found
        
        Returns:
            Configuration value
        
        Example:
            config.get('trading.transaction_cost_pct')
            config.get('database.path')
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def reload(self):
        """Reload configuration from files"""
        self.config = self._load_config()
        self._validate_config()
        logging.info("Configuration reloaded successfully")
    
    def get_all(self) -> Dict:
        """Get complete configuration dictionary"""
        return self.config.copy()
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == 'development'
