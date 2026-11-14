
# ============================================================================
# QUICK START SCRIPT
# ============================================================================

"""
FILE: setup_enterprise.py
Quick setup script to initialize enterprise system
"""

import os
import shutil

def setup_enterprise_system():
    """Set up directory structure and config files"""
    
    # Create directories
    dirs = [
        'config',
        'logs',
        'cache',
        'src/core',
        'src/data',
        'src/utils',
        'tests'
    ]
    
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        print(f"✓ Created {dir_name}/")
    
    # Create .env file
    env_content = """# Environment Configuration
ENVIRONMENT=development

# Database
DB_PATH=indian_stocks.db

# API Settings
API_RATE_LIMIT=100
API_TIMEOUT=30

# Logging
LOG_LEVEL=INFO

# Alerts (fill in your credentials)
EMAIL_PASSWORD=
SLACK_WEBHOOK=
"""
    
    with open('.env', 'w', encoding="utf-8") as f:
        f.write(env_content)
    print("✓ Created .env file")
    
    # Create __init__.py files
    for init_dir in ['src', 'src/core', 'src/data', 'src/utils']:
        with open(f'{init_dir}/__init__.py', 'w', encoding="utf-8") as f:
            f.write('')
    print("✓ Created __init__.py files")
    
    print("\n✓ Enterprise system structure ready!")
    print("\nNext steps:")
    print("1. pip install -r requirements.txt")
    print("2. Fill in config/base.yaml")
    print("3. Fill in config/development.yaml")
    print("4. Update .env with your credentials")
    print("5. Run python -m src.data.enterprise_data_manager")

if __name__ == "__main__":
    setup_enterprise_system()
