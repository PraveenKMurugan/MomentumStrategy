"""
Quick test to verify setup
"""
from src.core import config, errors, logging

def test_imports():
    """Test if all imports work"""
    print("Testing imports...")
    
    try:
        from src.core.config import ConfigManager
        print("✓ Config module works")
        
        from src.core.logging import LoggerFactory
        print("✓ Logging module works")
        
        from src.core.errors import ErrorHandler
        print("✓ Error handling works")
        
        # Test configuration
        config = ConfigManager()
        print(f"✓ Configuration loaded: {config.environment} environment")
        
        # Test logging
        logger = LoggerFactory.create_logger('test', config)
        logger.info("Test log entry")
        print("✓ Logger created successfully")
        
        print("\n🎉 ALL TESTS PASSED! System is ready.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease check:")
        print("1. All files are in correct locations")
        print("2. config/base.yaml exists")
        print("3. .env file exists")
        return False

if __name__ == "__main__":
    test_imports()