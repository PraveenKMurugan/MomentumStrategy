"""
Automatic File Updater
Adds foreign key enables to all necessary files
"""

import os
import re
import shutil
from datetime import datetime


class FileUpdater:
    """Automatically update files with foreign key enables"""
    
    def __init__(self):
        self.updated_files = []
        self.skipped_files = []
        self.failed_files = []
    
    def backup_file(self, file_path):
        """Create backup of file before modification"""
        backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def add_foreign_key_enable(self, file_path):
        """Add foreign key enable after sqlite3.connect()"""
        
        if not os.path.exists(file_path):
            self.failed_files.append((file_path, "File not found"))
            return False
        
        # Read file
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already updated
        if 'PRAGMA foreign_keys = ON' in content or 'pragma foreign_keys' in content.lower():
            self.skipped_files.append((file_path, "Already updated"))
            return False
        
        # Pattern to find sqlite3.connect lines
        patterns = [
            # Pattern 1: Direct assignment
            (r'([ \t]+)(self\.conn = sqlite3\.connect\([^)]+\))',
             r'\1\2\n\1# Enable foreign keys\n\1self.conn.execute("PRAGMA foreign_keys = ON")'),
            
            # Pattern 2: With check_same_thread
            (r'([ \t]+)(self\.conn = sqlite3\.connect\([^)]+, check_same_thread=[^)]+\))',
             r'\1\2\n\1# Enable foreign keys\n\1self.conn.execute("PRAGMA foreign_keys = ON")'),
            
            # Pattern 3: conn variable (not self.conn)
            (r'([ \t]+)(conn = sqlite3\.connect\([^)]+\))',
             r'\1\2\n\1# Enable foreign keys\n\1conn.execute("PRAGMA foreign_keys = ON")'),
        ]
        
        new_content = content
        matched = False
        
        for pattern, replacement in patterns:
            if re.search(pattern, content):
                new_content = re.sub(pattern, replacement, new_content, count=1)
                matched = True
                break
        
        if not matched:
            self.failed_files.append((file_path, "Pattern not found"))
            return False
        
        # Create backup
        backup_path = self.backup_file(file_path)
        
        # Write updated content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        self.updated_files.append((file_path, backup_path))
        return True
    
    def update_all_files(self):
        """Update all required files"""
        
        print("="*80)
        print("AUTOMATIC FILE UPDATER")
        print("="*80)
        print("\nAdding 'PRAGMA foreign_keys = ON' to all database connections...\n")
        
        files_to_update = [
            'src/analysis/dynamic_analyzer.py',
            'src/portfolio/portfolio_manager.py',
            'src/backtest/backtest_engine.py',
            'src/workflow/integrated_manager.py',
            'src/data/unified_data_manager.py',
        ]
        
        for i, file_path in enumerate(files_to_update, 1):
            print(f"{i}. {file_path}...")
            
            if self.add_foreign_key_enable(file_path):
                print(f"   ✓ Updated")
            else:
                # Check if in skipped or failed
                reason = None
                for fp, r in self.skipped_files:
                    if fp == file_path:
                        reason = r
                        break
                
                if reason:
                    print(f"   ℹ️  Skipped: {reason}")
                else:
                    for fp, r in self.failed_files:
                        if fp == file_path:
                            reason = r
                            break
                    print(f"   ⚠️  Failed: {reason}")
        
        self.print_summary()
    
    def print_summary(self):
        """Print update summary"""
        print("\n" + "="*80)
        print("UPDATE SUMMARY")
        print("="*80)
        
        if self.updated_files:
            print(f"\n✓ Updated: {len(self.updated_files)} files")
            for file_path, backup_path in self.updated_files:
                print(f"  • {file_path}")
                print(f"    Backup: {backup_path}")
        
        if self.skipped_files:
            print(f"\nℹ️  Skipped: {len(self.skipped_files)} files")
            for file_path, reason in self.skipped_files:
                print(f"  • {file_path} - {reason}")
        
        if self.failed_files:
            print(f"\n⚠️  Failed: {len(self.failed_files)} files")
            for file_path, reason in self.failed_files:
                print(f"  • {file_path} - {reason}")
        
        if self.updated_files:
            print("\n" + "-"*80)
            print("NEXT STEPS:")
            print("-"*80)
            print("1. Review the changes in updated files")
            print("2. Run: python test_connections.py")
            print("3. If everything works, delete backup files")
            print("4. If issues occur, restore from backups")


def main():
    """Main update function"""
    
    # Confirm with user
    print("="*80)
    print("AUTOMATIC FILE UPDATER")
    print("="*80)
    print("\nThis will add 'PRAGMA foreign_keys = ON' to all database connections.")
    print("\nFiles to be updated:")
    print("  • src/analysis/dynamic_analyzer.py")
    print("  • src/portfolio/portfolio_manager.py")
    print("  • src/backtest/backtest_engine.py")
    print("  • src/workflow/integrated_manager.py")
    print("  • src/data/unified_data_manager.py")
    
    print("\n⚠️  Backups will be created for all modified files.")
    
    response = input("\nProceed with automatic updates? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("\nUpdate cancelled.")
        return
    
    # Run updater
    updater = FileUpdater()
    updater.update_all_files()


if __name__ == "__main__":
    main()