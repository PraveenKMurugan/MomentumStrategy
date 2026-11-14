"""
Fix SQLite Threading Issues in All Managers

The issue: SQLite connections created in one thread can't be used in another.
Solution: Use check_same_thread=False OR create connection per operation.

Apply these fixes to ALL manager classes.
"""

# ============================================================================
# FIX 1: IntegratedWorkflowManager (src/workflow/integrated_manager.py)
# ============================================================================

# FIND (around line 54-60):
"""
self.db_path = db_path
self.conn = sqlite3.connect(db_path)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# REPLACE WITH:
"""
self.db_path = db_path
self.conn = sqlite3.connect(db_path, check_same_thread=False)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# ============================================================================
# FIX 2: DynamicStockAnalyzer (src/analysis/dynamic_analyzer.py)
# ============================================================================

# FIND (around line 67-70):
"""
self.db_path = db_path
self.conn = sqlite3.connect(db_path)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# REPLACE WITH:
"""
self.db_path = db_path
self.conn = sqlite3.connect(db_path, check_same_thread=False)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# ============================================================================
# FIX 3: EnterprisePortfolioManager (src/portfolio/portfolio_manager.py)
# ============================================================================

# FIND (around line 46-49):
"""
self.conn = sqlite3.connect(db_path)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# REPLACE WITH:
"""
self.conn = sqlite3.connect(db_path, check_same_thread=False)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# ============================================================================
# FIX 4: EnterpriseBacktestEngine (src/backtest/backtest_engine.py)
# ============================================================================

# FIND (around line 46-49):
"""
self.conn = sqlite3.connect(db_path)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# REPLACE WITH:
"""
self.conn = sqlite3.connect(db_path, check_same_thread=False)
# Enable foreign keys
self.conn.execute("PRAGMA foreign_keys = ON")
"""

# ============================================================================
# AUTOMATED FIX SCRIPT
# ============================================================================

import os
import re


def fix_sqlite_threading(file_path):
    """Fix SQLite threading in a file"""
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
    
    print(f"Fixing threading in: {file_path}")
    
    # Read file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Pattern to find sqlite3.connect without check_same_thread
    pattern = r'sqlite3\.connect\(([^)]+)\)(?!\s*,\s*check_same_thread)'
    
    # Check if fix needed
    matches = re.findall(pattern, content)
    
    if not matches:
        print("  No threading issues found or already fixed")
        return True
    
    print(f"  Found {len(matches)} connection(s) to fix")
    
    # Backup original
    backup_path = file_path + '.backup_threading'
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Backup created: {backup_path}")
    except Exception as e:
        print(f"  Warning: Could not create backup: {e}")
    
    # Fix all occurrences
    # Replace sqlite3.connect(path) with sqlite3.connect(path, check_same_thread=False)
    new_content = re.sub(
        r'sqlite3\.connect\(([^)]+)\)(?!\s*,\s*check_same_thread)',
        r'sqlite3.connect(\1, check_same_thread=False)',
        content
    )
    
    # Write fixed content
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  ✓ Fixed {len(matches)} connection(s)")
        return True
    except Exception as e:
        print(f"  Error writing file: {e}")
        return False


def main():
    """Fix threading issues in all manager files"""
    
    print("="*80)
    print("SQLITE THREADING FIX")
    print("="*80)
    print("\nThis will add check_same_thread=False to all SQLite connections")
    print("to fix threading issues in Streamlit.\n")
    
    files_to_fix = [
        'src/workflow/integrated_manager.py',
        'src/analysis/dynamic_analyzer.py',
        'src/portfolio/portfolio_manager.py',
        'src/backtest/backtest_engine.py',
        'src/data/unified_data_manager.py',
    ]
    
    fixed = 0
    failed = 0
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_sqlite_threading(file_path):
                fixed += 1
            else:
                failed += 1
        else:
            print(f"File not found: {file_path}")
            failed += 1
        print()
    
    print("="*80)
    print(f"SUMMARY: Fixed {fixed} files, {failed} failed")
    print("="*80)
    
    if fixed > 0:
        print("\n✓ SQLite connections now support multi-threading")
        print("Backups created with .backup_threading extension")
        print("\nYour Streamlit app should work now!")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())