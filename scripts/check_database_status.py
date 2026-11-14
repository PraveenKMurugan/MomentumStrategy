"""
Check Database Status
Quick script to see what's in your database
"""

import sqlite3
import os
from datetime import datetime

def check_database_status(db_path='indian_stocks.db'):
    """Check what's currently in the database"""
    
    print("\n" + "="*80)
    print("DATABASE STATUS CHECK")
    print("="*80)
    
    # Check if database exists
    if not os.path.exists(db_path):
        print(f"\n❌ Database not found: {db_path}")
        print("\nThe database will be created automatically when you:")
        print("1. Run: python scripts/download_data.py")
        print("2. Or initialize: from src.data.enterprise_data_manager import EnterpriseDataManager; dm = EnterpriseDataManager()")
        return
    
    print(f"\n✓ Database found: {db_path}")
    print(f"  Size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
    print(f"  Modified: {datetime.fromtimestamp(os.path.getmtime(db_path)).strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check tables
    print("\n" + "-"*80)
    print("TABLES")
    print("-"*80)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    
    if not tables:
        print("  No tables found. Database is empty.")
        conn.close()
        return
    
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  ✓ {table_name}: {count:,} records")
    
    # Check stocks table schema
    print("\n" + "-"*80)
    print("STOCKS TABLE SCHEMA")
    print("-"*80)
    
    cursor.execute("PRAGMA table_info(stocks)")
    columns = cursor.fetchall()
    
    required_columns = ['symbol', 'company_name', 'index_membership', 'is_active']
    
    print(f"  Total columns: {len(columns)}")
    for col in columns:
        col_name = col[1]
        col_type = col[2]
        status = "✓" if col_name in required_columns else " "
        print(f"  {status} {col_name:<20} ({col_type})")
    
    # Check if index_membership exists
    has_index_membership = any(col[1] == 'index_membership' for col in columns)
    has_is_active = any(col[1] == 'is_active' for col in columns)
    
    if not has_index_membership:
        print("\n  ⚠️  Missing: index_membership column")
        print("     Run: python fix_database_and_strategies.py")
    
    if not has_is_active:
        print("\n  ⚠️  Missing: is_active column")
        print("     Run: python fix_database_and_strategies.py")
    
    # Check stock distribution
    if has_index_membership:
        print("\n" + "-"*80)
        print("INDEX MEMBERSHIP DISTRIBUTION")
        print("-"*80)
        
        cursor.execute("""
            SELECT 
                COALESCE(index_membership, 'NULL') as membership,
                COUNT(*) as count
            FROM stocks
            GROUP BY membership
            ORDER BY count DESC
            LIMIT 10
        """)
        
        for membership, count in cursor.fetchall():
            print(f"  {membership:<40} : {count:>5} stocks")
    
    # Check price data
    print("\n" + "-"*80)
    print("PRICE DATA")
    print("-"*80)
    
    cursor.execute("SELECT COUNT(*) FROM price_data")
    total_records = cursor.fetchone()[0]
    
    if total_records > 0:
        cursor.execute("""
            SELECT 
                MIN(date) as first_date,
                MAX(date) as last_date,
                COUNT(DISTINCT symbol) as num_stocks,
                COUNT(*) as total_records
            FROM price_data
        """)
        
        first_date, last_date, num_stocks, total = cursor.fetchone()
        
        print(f"  Total Records: {total:,}")
        print(f"  Stocks with Data: {num_stocks:,}")
        print(f"  Date Range: {first_date} to {last_date}")
        
        # Average records per stock
        avg_records = total / num_stocks if num_stocks > 0 else 0
        print(f"  Avg Records/Stock: {avg_records:.0f}")
        
        # Data quality
        cursor.execute("""
            SELECT 
                COUNT(*) as validated_count
            FROM price_data
            WHERE validated = 1
        """)
        
        validated = cursor.fetchone()[0]
        validated_pct = (validated / total * 100) if total > 0 else 0
        
        print(f"  Validated Records: {validated:,} ({validated_pct:.1f}%)")
        
    else:
        print("  ⚠️  No price data found")
        print("     Run: python scripts/download_data.py")
    
    # Check recent stocks
    print("\n" + "-"*80)
    print("SAMPLE STOCKS (First 10)")
    print("-"*80)
    
    cursor.execute("""
        SELECT symbol, company_name, index_membership
        FROM stocks
        LIMIT 10
    """)
    
    for symbol, name, membership in cursor.fetchall():
        membership = membership or "UNKNOWN"
        print(f"  {symbol:<15} {(name or 'N/A'):<40} [{membership}]")
    
    conn.close()
    
    print("\n" + "="*80)
    print("STATUS CHECK COMPLETE")
    print("="*80)
    
    # Recommendations
    print("\n📋 RECOMMENDATIONS:")
    
    if not has_index_membership or not has_is_active:
        print("  1. ⚠️  Fix database schema:")
        print("     python fix_database_and_strategies.py")
    
    if total_records == 0:
        print("  2. ⚠️  Download stock data:")
        print("     python scripts/download_data.py")
    
    if has_index_membership and total_records > 0:
        print("  ✓ Database looks good! You can:")
        print("     - Run analysis: python scripts/run_analysis.py")
        print("     - Create portfolio: python scripts/create_portfolio.py")
        print("     - Launch dashboard: streamlit run dashboard/app.py")

def check_strategy_files():
    """Check if strategy files exist"""
    
    print("\n" + "="*80)
    print("STRATEGY FILES CHECK")
    print("="*80)
    
    strategy_dir = 'config/strategies'
    
    if not os.path.exists(strategy_dir):
        print(f"\n❌ Directory not found: {strategy_dir}")
        print("\nRun: python fix_database_and_strategies.py")
        return
    
    print(f"\n✓ Directory exists: {strategy_dir}")
    
    expected_files = [
        'classic_momentum.json',
        'balanced_momentum.json',
        'short_term_momentum.json',
        'conservative.json',
        'aggressive.json',
        'custom_strategies.json'
    ]
    
    print("\nStrategy Files:")
    
    missing = []
    for filename in expected_files:
        filepath = os.path.join(strategy_dir, filename)
        if os.path.exists(filepath):
            size = os.path.getsize(filepath)
            print(f"  ✓ {filename:<30} ({size} bytes)")
        else:
            print(f"  ✗ {filename:<30} (missing)")
            missing.append(filename)
    
    if missing:
        print(f"\n⚠️  {len(missing)} files missing")
        print("   Run: python fix_database_and_strategies.py")
    else:
        print("\n✓ All strategy files present!")

def main():
    """Run all checks"""
    check_database_status()
    check_strategy_files()
    
    print("\n" + "="*80)
    print("✓ CHECK COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()