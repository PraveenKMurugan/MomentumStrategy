"""
Fix for Unicode Error in dynamic_analyzer.py

Find and replace these lines in src/analysis/dynamic_analyzer.py
"""

# ============================================================================
# FIND THIS (around line 455):
# ============================================================================

# OLD CODE:
"""
percentage = (len(filtered) / initial_count * 100) if initial_count > 0 else 0
self.logger.info(
    f"Filtering complete: {initial_count} → {len(filtered)} ({percentage:.1f}%)"
)
"""

# ============================================================================
# REPLACE WITH:
# ============================================================================

# NEW CODE:
"""
percentage = (len(filtered) / initial_count * 100) if initial_count > 0 else 0
self.logger.info(
    f"Filtering complete: {initial_count} -> {len(filtered)} ({percentage:.1f}%)"
)
"""

# ============================================================================
# Complete fix script - Save as fix_unicode.py and run it
# ============================================================================

import os
import sys

def fix_unicode_in_file(file_path):
    """Fix Unicode characters in a file"""
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
    
    print(f"Fixing Unicode in: {file_path}")
    
    # Read file
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Track changes
    changes = 0
    
    # Replace all Unicode arrows with ASCII
    replacements = {
        '→': '->',
        '←': '<-',
        '↑': '^',
        '↓': 'v',
        '✓': 'OK',
        '✗': 'X',
        '⚠': '!',
        '•': '*',
        '–': '-',
        '—': '--',
        '₹': 'Rs',
    }
    
    for unicode_char, ascii_char in replacements.items():
        if unicode_char in content:
            count = content.count(unicode_char)
            content = content.replace(unicode_char, ascii_char)
            changes += count
            print(f"  Replaced {count} instances of '{unicode_char}' with '{ascii_char}'")
    
    if changes == 0:
        print("  No Unicode characters found")
        return True
    
    # Backup original
    backup_path = file_path + '.backup_unicode'
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            # Write original content to backup
            with open(file_path, 'r', encoding='utf-8') as orig:
                f.write(orig.read())
        print(f"  Backup created: {backup_path}")
    except Exception as e:
        print(f"  Warning: Could not create backup: {e}")
    
    # Write fixed content
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✓ Fixed {changes} Unicode characters")
        return True
    except Exception as e:
        print(f"  Error writing file: {e}")
        return False


def main():
    """Fix Unicode in all Python files"""
    
    print("="*80)
    print("UNICODE CHARACTER FIX")
    print("="*80)
    print("\nThis will replace Unicode characters with ASCII equivalents")
    print("to avoid encoding errors on Windows.\n")
    
    files_to_fix = [
        'src/analysis/dynamic_analyzer.py',
        'src/portfolio/portfolio_manager.py',
        'src/backtest/backtest_engine.py',
        'src/data/unified_data_manager.py',
        'src/workflow/integrated_manager.py',
        'src/backtest/backtest_engine.py',
    ]
    
    fixed = 0
    failed = 0
    
    for file_path in files_to_fix:
        if os.path.exists(file_path):
            if fix_unicode_in_file(file_path):
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
        print("\n✓ Unicode characters have been replaced with ASCII equivalents")
        print("Backups created with .backup_unicode extension")
        print("\nYou can now run your scripts without Unicode errors!")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())