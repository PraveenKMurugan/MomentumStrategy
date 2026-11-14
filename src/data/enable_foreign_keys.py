"""
Enable Foreign Keys Helper
Enables foreign keys and checks integrity of existing database
"""

import sqlite3
import argparse


def enable_and_check_foreign_keys(db_path: str):
    """Enable foreign keys and check for violations"""
    
    print("="*80)
    print("ENABLING FOREIGN KEYS")
    print("="*80)
    print(f"\nDatabase: {db_path}\n")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current status
    cursor.execute("PRAGMA foreign_keys")
    result = cursor.fetchone()
    current_status = result[0] if result else 0
    
    print(f"Current status: {'Enabled' if current_status else 'Disabled'}")
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Verify enabled
    cursor.execute("PRAGMA foreign_keys")
    result = cursor.fetchone()
    new_status = result[0] if result else 0
    
    if new_status:
        print("✓ Foreign keys enabled for this connection")
    else:
        print("✗ Failed to enable foreign keys")
        return False
    
    # Check for foreign key violations in existing data
    print("\nChecking for foreign key violations...")
    
    cursor.execute("PRAGMA foreign_key_check")
    violations = cursor.fetchall()
    
    if violations:
        print(f"\n⚠️  Found {len(violations)} foreign key violations:")
        for i, violation in enumerate(violations[:10], 1):
            print(f"  {i}. Table: {violation[0]}, Row: {violation[1]}")
        
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more")
        
        print("\nThese violations should be fixed before enabling foreign keys.")
    else:
        print("✓ No foreign key violations found")
    
    # Show how to enable permanently
    print("\n" + "="*80)
    print("HOW TO ENABLE FOREIGN KEYS PERMANENTLY")
    print("="*80)
    print("\nIn your Python code, always enable foreign keys after connecting:")
    print("""
import sqlite3

# Always enable foreign keys after connecting
conn = sqlite3.connect('indian_stocks.db')
conn.execute('PRAGMA foreign_keys = ON')

# Verify
cursor = conn.cursor()
cursor.execute('PRAGMA foreign_keys')
print('Foreign keys:', 'Enabled' if cursor.fetchone()[0] else 'Disabled')
""")
    
    print("\nThe UnifiedDataManager does this automatically.")
    
    conn.close()
    return len(violations) == 0


def main():
    parser = argparse.ArgumentParser(
        description='Enable foreign keys and check database'
    )
    parser.add_argument(
        '--db-path',
        default='indian_stocks.db',
        help='Path to database file'
    )
    
    args = parser.parse_args()
    
    success = enable_and_check_foreign_keys(args.db_path)
    
    if success:
        print("\n✓ Foreign keys enabled and no violations found!")
    else:
        print("\n⚠️  Foreign keys enabled but violations found")
        print("Consider fixing violations before using foreign keys")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())