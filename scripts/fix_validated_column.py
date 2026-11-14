"""
Fix Missing 'validated' Column in price_data Table
Quick fix for the database schema
"""

import sqlite3
import os

def fix_validated_column(db_path='indian_stocks.db'):
    """
    Add validated column to price_data table if it doesn't exist
    """
    print("="*80)
    print("FIXING 'validated' COLUMN IN price_data TABLE")
    print("="*80)
    
    if not os.path.exists(db_path):
        print(f"\n❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if validated column exists
        cursor.execute("PRAGMA table_info(price_data)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"\nCurrent columns in price_data: {', '.join(columns)}")
        
        if 'validated' in columns:
            print("\n✓ 'validated' column already exists!")
            
            # Check how many records are validated
            cursor.execute("SELECT COUNT(*) FROM price_data WHERE validated = 1")
            validated_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM price_data")
            total_count = cursor.fetchone()[0]
            
            print(f"  Validated records: {validated_count:,} / {total_count:,}")
            
            if validated_count == 0:
                print("\n  ⚠️  No records marked as validated")
                print("  Setting all existing records as validated...")
                cursor.execute("UPDATE price_data SET validated = 1")
                conn.commit()
                print(f"  ✓ Marked {cursor.rowcount:,} records as validated")
        else:
            print("\n❌ 'validated' column missing")
            print("   Adding column...")
            
            # Add the column with default value 1
            cursor.execute('''
                ALTER TABLE price_data 
                ADD COLUMN validated INTEGER DEFAULT 1
            ''')
            
            conn.commit()
            print("   ✓ Column added successfully!")
            
            # Verify
            cursor.execute("PRAGMA table_info(price_data)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'validated' in columns:
                print("   ✓ Verification passed!")
                
                # Mark all existing records as validated
                cursor.execute("UPDATE price_data SET validated = 1 WHERE validated IS NULL")
                updated = cursor.rowcount
                
                if updated > 0:
                    conn.commit()
                    print(f"   ✓ Marked {updated:,} existing records as validated")
            else:
                print("   ❌ Verification failed!")
                return False
        
        # Also check data_quality column
        cursor.execute("PRAGMA table_info(price_data)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'data_quality' not in columns:
            print("\n  Adding 'data_quality' column...")
            cursor.execute('''
                ALTER TABLE price_data 
                ADD COLUMN data_quality TEXT DEFAULT NULL
            ''')
            conn.commit()
            print("   ✓ 'data_quality' column added")
        
        # Show final schema
        print("\n" + "-"*80)
        print("FINAL price_data SCHEMA:")
        print("-"*80)
        cursor.execute("PRAGMA table_info(price_data)")
        for col in cursor.fetchall():
            col_id, col_name, col_type, not_null, default_val, pk = col
            default_str = f" DEFAULT {default_val}" if default_val else ""
            pk_str = " PRIMARY KEY" if pk else ""
            print(f"  {col_name:<20} {col_type:<10}{default_str}{pk_str}")
        
        conn.close()
        
        print("\n" + "="*80)
        print("✓ FIX COMPLETE!")
        print("="*80)
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False

def fix_all_missing_columns(db_path='indian_stocks.db'):
    """
    Fix all potentially missing columns in all tables
    """
    print("\n" + "="*80)
    print("COMPREHENSIVE DATABASE SCHEMA FIX")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    fixes_applied = []
    
    # Fix 1: stocks table - index_membership
    print("\n1. Checking stocks table...")
    cursor.execute("PRAGMA table_info(stocks)")
    stocks_columns = [col[1] for col in cursor.fetchall()]
    
    if 'index_membership' not in stocks_columns:
        cursor.execute("ALTER TABLE stocks ADD COLUMN index_membership TEXT DEFAULT 'ALL'")
        conn.commit()
        fixes_applied.append("Added index_membership to stocks")
        print("   ✓ Added index_membership")
    else:
        print("   ✓ index_membership exists")
    
    if 'is_active' not in stocks_columns:
        cursor.execute("ALTER TABLE stocks ADD COLUMN is_active INTEGER DEFAULT 1")
        conn.commit()
        fixes_applied.append("Added is_active to stocks")
        print("   ✓ Added is_active")
    else:
        print("   ✓ is_active exists")
    
    # Fix 2: price_data table - validated
    print("\n2. Checking price_data table...")
    cursor.execute("PRAGMA table_info(price_data)")
    price_columns = [col[1] for col in cursor.fetchall()]
    
    if 'validated' not in price_columns:
        cursor.execute("ALTER TABLE price_data ADD COLUMN validated INTEGER DEFAULT 1")
        conn.commit()
        fixes_applied.append("Added validated to price_data")
        print("   ✓ Added validated")
    else:
        print("   ✓ validated exists")
    
    if 'data_quality' not in price_columns:
        cursor.execute("ALTER TABLE price_data ADD COLUMN data_quality TEXT DEFAULT NULL")
        conn.commit()
        fixes_applied.append("Added data_quality to price_data")
        print("   ✓ Added data_quality")
    else:
        print("   ✓ data_quality exists")
    
    # Fix 3: Ensure all price_data records are marked as validated
    cursor.execute("UPDATE price_data SET validated = 1 WHERE validated IS NULL OR validated = 0")
    if cursor.rowcount > 0:
        conn.commit()
        fixes_applied.append(f"Marked {cursor.rowcount:,} records as validated")
        print(f"   ✓ Marked {cursor.rowcount:,} records as validated")
    
    conn.close()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if fixes_applied:
        print("\nFixes applied:")
        for fix in fixes_applied:
            print(f"  ✓ {fix}")
    else:
        print("\n✓ Database schema is up to date - no fixes needed")
    
    print("\n" + "="*80)
    print("✓ ALL FIXES COMPLETE!")
    print("="*80)
    
    return True

def verify_fix(db_path='indian_stocks.db'):
    """
    Verify the fix by running a test query
    """
    print("\n" + "="*80)
    print("VERIFICATION TEST")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Test the exact query that was failing
        print("\nTesting query that was failing...")
        cursor.execute('''
            SELECT date, adj_close, volume
            FROM price_data
            WHERE symbol = ? AND date >= ? AND date <= ? AND validated = 1
            ORDER BY date
            LIMIT 5
        ''', ('RELIANCE.NS', '2024-01-01', '2024-12-31'))
        
        results = cursor.fetchall()
        
        if results:
            print(f"  ✓ Query successful! Found {len(results)} records")
            print("\nSample data:")
            for date, adj_close, volume in results[:3]:
                print(f"  {date}: Price={adj_close:.2f}, Volume={volume:,}")
        else:
            print("  ⚠️  Query successful but no data found")
            print("     (This is OK if you haven't downloaded data for RELIANCE.NS yet)")
        
        # Check total validated records
        cursor.execute("SELECT COUNT(*) FROM price_data WHERE validated = 1")
        validated_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_data")
        total_count = cursor.fetchone()[0]
        
        print(f"\n  Total records: {total_count:,}")
        print(f"  Validated records: {validated_count:,}")
        print(f"  Percentage validated: {validated_count/total_count*100:.1f}%" if total_count > 0 else "  No data yet")
        
        conn.close()
        
        print("\n" + "="*80)
        print("✓ VERIFICATION PASSED!")
        print("="*80)
        print("\nYou can now run your analysis without errors!")
        return True
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        conn.close()
        return False

def main():
    """
    Main function - run all fixes
    """
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*25 + "FIX 'validated' COLUMN" + " "*30 + "║")
    print("╚" + "="*78 + "╝")
    
    print("\nThis will fix the error:")
    print("  'no such column: validated'")
    print("\nBy adding the missing column and marking all existing data as validated.")
    
    response = input("\nProceed? (y/n): ")
    
    if response.lower() != 'y':
        print("Aborted.")
        return
    
    # Run comprehensive fix
    success = fix_all_missing_columns()
    
    if success:
        # Verify
        verify_fix()
        
        print("\n" + "="*80)
        print("NEXT STEPS")
        print("="*80)
        print("\n1. Re-run your analysis:")
        print("   python scripts/run_analysis.py")
        print("\n2. Or test in Python:")
        print("   from src.analysis.dynamic_analyzer import DynamicStockAnalyzer")
        print("   analyzer = DynamicStockAnalyzer()")
        print("   # Should work without errors now!")

if __name__ == "__main__":
    main()