"""
Migration Verification Script
Verifies database schema and data integrity after migration

Usage:
    python verify_migration.py
    python verify_migration.py --db-path /path/to/database.db
"""

import sqlite3
import argparse
from datetime import datetime
from typing import Dict, List, Tuple
from src.core.config import ConfigManager


class MigrationVerifier:
    """Verify database migration was successful"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.issues = []
        self.warnings = []
    
    def verify_all(self) -> bool:
        """Run all verification checks"""
        print("="*80)
        print("DATABASE MIGRATION VERIFICATION")
        print("="*80)
        print(f"\nDatabase: {self.db_path}")
        print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        checks = [
            ("Schema Structure", self.verify_schema),
            ("Data Integrity", self.verify_data_integrity),
            ("Foreign Keys", self.verify_foreign_keys),
            ("Indexes", self.verify_indexes),
            ("Data Counts", self.verify_data_counts),
            ("Column Types", self.verify_column_types)
        ]
        
        results = []
        
        for check_name, check_func in checks:
            print(f"\n{'='*80}")
            print(f"CHECK: {check_name}")
            print(f"{'='*80}")
            
            try:
                passed = check_func()
                results.append((check_name, passed))
                
                if passed:
                    print(f"\n✓ {check_name}: PASSED")
                else:
                    print(f"\n✗ {check_name}: FAILED")
            except Exception as e:
                print(f"\n✗ {check_name}: ERROR - {e}")
                results.append((check_name, False))
                self.issues.append(f"{check_name}: {e}")
        
        # Summary
        print(f"\n{'='*80}")
        print("VERIFICATION SUMMARY")
        print(f"{'='*80}")
        
        for check_name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{check_name:.<50} {status}")
        
        all_passed = all(result[1] for result in results)
        
        if all_passed:
            print("\n🎉 All checks passed! Migration was successful.")
        else:
            print("\n⚠️  Some checks failed. Review issues above.")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if self.issues:
            print("\n✗ ISSUES:")
            for issue in self.issues:
                print(f"  - {issue}")
        
        return all_passed
    
    def verify_schema(self) -> bool:
        """Verify all required tables and columns exist"""
        cursor = self.conn.cursor()
        
        # Expected schema
        expected_schema = {
            'stocks': [
                'symbol', 'company_name', 'sector', 'industry',
                'market_cap', 'market_cap_cr', 'isin', 'series',
                'listing_date', 'index_membership', 'is_active',
                'data_quality_score', 'last_update_date',
                'update_frequency', 'notes', 'created_date', 'last_modified'
            ],
            'price_data': [
                'id', 'symbol', 'date', 'open', 'high', 'low',
                'close', 'adj_close', 'volume', 'validated',
                'quality_score', 'quality_level', 'data_source',
                'created_date'
            ],
            'data_quality_history': [
                'id', 'symbol', 'check_date', 'quality_level',
                'quality_score', 'total_records', 'missing_records',
                'duplicate_records', 'outliers', 'date_gaps',
                'first_date', 'last_date', 'issues', 'created_date'
            ],
            'update_history': [
                'id', 'update_date', 'update_type', 'symbols_attempted',
                'symbols_successful', 'symbols_failed', 'duration_seconds',
                'errors', 'notes', 'created_date'
            ],
            'failed_updates': [
                'id', 'symbol', 'failure_date', 'failure_count',
                'last_error', 'retry_scheduled', 'last_retry_date',
                'next_retry_date', 'status', 'created_date', 'last_modified'
            ]
        }
        
        all_good = True
        
        for table_name, expected_columns in expected_schema.items():
            # Check table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name=?
            """, [table_name])
            
            if not cursor.fetchone():
                print(f"✗ Table '{table_name}' not found")
                self.issues.append(f"Missing table: {table_name}")
                all_good = False
                continue
            
            # Check columns
            cursor.execute(f"PRAGMA table_info({table_name})")
            actual_columns = [col[1] for col in cursor.fetchall()]
            
            missing_cols = set(expected_columns) - set(actual_columns)
            extra_cols = set(actual_columns) - set(expected_columns)
            
            if missing_cols:
                print(f"✗ Table '{table_name}' missing columns: {missing_cols}")
                self.issues.append(
                    f"{table_name}: Missing columns {missing_cols}"
                )
                all_good = False
            
            if extra_cols:
                print(f"⚠️  Table '{table_name}' has extra columns: {extra_cols}")
                self.warnings.append(
                    f"{table_name}: Extra columns {extra_cols}"
                )
            
            if not missing_cols and not extra_cols:
                print(f"✓ Table '{table_name}': All columns present")
        
        return all_good
    
    def verify_data_integrity(self) -> bool:
        """Verify data integrity"""
        cursor = self.conn.cursor()
        all_good = True
        
        # Check for NULL values in required fields
        print("\nChecking for NULL values in required fields...")
        
        # Stocks: symbol should not be NULL
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE symbol IS NULL")
        null_symbols = cursor.fetchone()[0]
        if null_symbols > 0:
            print(f"✗ Found {null_symbols} stocks with NULL symbol")
            self.issues.append(f"Stocks: {null_symbols} NULL symbols")
            all_good = False
        else:
            print("✓ No NULL symbols in stocks")
        
        # Price data: symbol and date should not be NULL
        cursor.execute("""
            SELECT COUNT(*) FROM price_data 
            WHERE symbol IS NULL OR date IS NULL
        """)
        null_price_data = cursor.fetchone()[0]
        if null_price_data > 0:
            print(f"✗ Found {null_price_data} price records with NULL symbol/date")
            self.issues.append(f"Price data: {null_price_data} NULL symbol/date")
            all_good = False
        else:
            print("✓ No NULL symbol/date in price_data")
        
        # Check for duplicate records
        print("\nChecking for duplicate records...")
        
        cursor.execute("""
            SELECT symbol, date, COUNT(*) as cnt
            FROM price_data
            GROUP BY symbol, date
            HAVING cnt > 1
        """)
        duplicates = cursor.fetchall()
        
        if duplicates:
            print(f"✗ Found {len(duplicates)} duplicate records in price_data")
            self.issues.append(f"Price data: {len(duplicates)} duplicates")
            all_good = False
        else:
            print("✓ No duplicate records in price_data")
        
        # Check OHLC logic
        print("\nChecking OHLC data integrity...")
        
        cursor.execute("""
            SELECT COUNT(*) FROM price_data
            WHERE high < low 
               OR high < open 
               OR high < close
               OR low > open
               OR low > close
        """)
        invalid_ohlc = cursor.fetchone()[0]
        
        if invalid_ohlc > 0:
            print(f"⚠️  Found {invalid_ohlc} records with invalid OHLC data")
            self.warnings.append(f"Price data: {invalid_ohlc} invalid OHLC records")
        else:
            print("✓ All OHLC data is valid")
        
        return all_good
    
    def verify_foreign_keys(self) -> bool:
        """Verify foreign key constraints"""
        cursor = self.conn.cursor()
        
        # Check if foreign keys are enabled
        cursor.execute("PRAGMA foreign_keys")
        fk_enabled = cursor.fetchone()[0] == 1
        
        if not fk_enabled:
            print("⚠️  Foreign keys are NOT enabled")
            self.warnings.append("Foreign keys not enabled - enable in production")
        else:
            print("✓ Foreign keys are enabled")
        
        # Check orphaned records in price_data
        cursor.execute("""
            SELECT COUNT(DISTINCT p.symbol)
            FROM price_data p
            LEFT JOIN stocks s ON p.symbol = s.symbol
            WHERE s.symbol IS NULL
        """)
        orphaned_price = cursor.fetchone()[0]
        
        if orphaned_price > 0:
            print(f"✗ Found {orphaned_price} orphaned symbols in price_data")
            self.issues.append(f"Price data: {orphaned_price} orphaned symbols")
            return False
        else:
            print("✓ No orphaned records in price_data")
        
        # Check orphaned records in data_quality_history
        cursor.execute("""
            SELECT COUNT(DISTINCT dqh.symbol)
            FROM data_quality_history dqh
            LEFT JOIN stocks s ON dqh.symbol = s.symbol
            WHERE s.symbol IS NULL
        """)
        orphaned_quality = cursor.fetchone()[0]
        
        if orphaned_quality > 0:
            print(f"✗ Found {orphaned_quality} orphaned symbols in data_quality_history")
            self.issues.append(f"Quality history: {orphaned_quality} orphaned symbols")
            return False
        else:
            print("✓ No orphaned records in data_quality_history")
        
        return True
    
    def verify_indexes(self) -> bool:
        """Verify indexes exist"""
        cursor = self.conn.cursor()
        
        expected_indexes = [
            'idx_price_symbol',
            'idx_price_date',
            'idx_price_symbol_date',
            'idx_stocks_active',
            'idx_stocks_index',
            'idx_quality_history_symbol',
            'idx_failed_status'
        ]
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
        """)
        actual_indexes = [row[0] for row in cursor.fetchall()]
        
        missing_indexes = set(expected_indexes) - set(actual_indexes)
        
        if missing_indexes:
            print(f"⚠️  Missing indexes: {missing_indexes}")
            self.warnings.append(f"Missing indexes: {missing_indexes}")
            return False
        else:
            print(f"✓ All {len(expected_indexes)} required indexes exist")
            return True
    
    def verify_data_counts(self) -> bool:
        """Verify data counts are reasonable"""
        cursor = self.conn.cursor()
        
        # Get counts
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stocks_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM price_data")
        price_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM data_quality_history")
        quality_count = cursor.fetchone()[0]
        
        print(f"\nData counts:")
        print(f"  Stocks: {stocks_count:,}")
        print(f"  Price records: {price_count:,}")
        print(f"  Quality records: {quality_count:,}")
        
        # Verify counts are reasonable
        if stocks_count == 0:
            print("✗ No stocks in database")
            self.issues.append("No stocks found")
            return False
        
        if price_count == 0:
            print("⚠️  No price data in database")
            self.warnings.append("No price data found")
        
        # Check average records per stock
        if stocks_count > 0 and price_count > 0:
            avg_records = price_count / stocks_count
            print(f"  Average records per stock: {avg_records:.1f}")
            
            if avg_records < 10:
                print("⚠️  Very few price records per stock")
                self.warnings.append(f"Only {avg_records:.1f} records per stock")
        
        print("\n✓ Data counts verified")
        return True
    
    def verify_column_types(self) -> bool:
        """Verify column data types"""
        cursor = self.conn.cursor()
        
        # Critical columns that should have specific types
        type_checks = [
            ('stocks', 'symbol', 'TEXT'),
            ('stocks', 'market_cap', 'REAL'),
            ('stocks', 'is_active', 'INTEGER'),
            ('price_data', 'symbol', 'TEXT'),
            ('price_data', 'date', 'TEXT'),
            ('price_data', 'open', 'REAL'),
            ('price_data', 'volume', 'INTEGER')
        ]
        
        all_good = True
        
        for table, column, expected_type in type_checks:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = {col[1]: col[2] for col in cursor.fetchall()}
            
            if column not in columns:
                print(f"✗ Column {table}.{column} not found")
                self.issues.append(f"Missing column: {table}.{column}")
                all_good = False
                continue
            
            actual_type = columns[column]
            
            if actual_type.upper() != expected_type.upper():
                print(f"⚠️  {table}.{column}: Expected {expected_type}, got {actual_type}")
                self.warnings.append(
                    f"{table}.{column}: Type mismatch ({actual_type} vs {expected_type})"
                )
        
        if all_good:
            print(f"✓ All {len(type_checks)} critical column types verified")
        
        return all_good
    
    def generate_report(self, output_file: str = "migration_report.txt"):
        """Generate detailed verification report"""
        cursor = self.conn.cursor()
        
        with open(output_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("DATABASE MIGRATION VERIFICATION REPORT\n")
            f.write("="*80 + "\n\n")
            f.write(f"Database: {self.db_path}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Schema info
            f.write("="*80 + "\n")
            f.write("SCHEMA INFORMATION\n")
            f.write("="*80 + "\n\n")
            
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                f.write(f"\n{table} ({count:,} records)\n")
                f.write("-" * 40 + "\n")
                
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                
                for col in columns:
                    f.write(f"  {col[1]:<30} {col[2]:<15}\n")
            
            # Data summary
            f.write("\n" + "="*80 + "\n")
            f.write("DATA SUMMARY\n")
            f.write("="*80 + "\n\n")
            
            # Stocks by index
            cursor.execute("""
                SELECT index_membership, COUNT(*) 
                FROM stocks 
                WHERE is_active = 1
                GROUP BY index_membership
            """)
            
            f.write("Stocks by Index:\n")
            for row in cursor.fetchall():
                index_name = row[0] or 'Unknown'
                count = row[1]
                f.write(f"  {index_name:<30} {count:>10,}\n")
            
            # Price data date range
            cursor.execute("""
                SELECT 
                    MIN(date) as first_date,
                    MAX(date) as last_date,
                    COUNT(DISTINCT symbol) as symbols,
                    COUNT(*) as records
                FROM price_data
            """)
            result = cursor.fetchone()
            
            f.write(f"\nPrice Data:\n")
            f.write(f"  Date range: {result[0]} to {result[1]}\n")
            f.write(f"  Symbols: {result[2]:,}\n")
            f.write(f"  Total records: {result[3]:,}\n")
            
            # Issues and warnings
            if self.issues:
                f.write("\n" + "="*80 + "\n")
                f.write("ISSUES\n")
                f.write("="*80 + "\n\n")
                for issue in self.issues:
                    f.write(f"✗ {issue}\n")
            
            if self.warnings:
                f.write("\n" + "="*80 + "\n")
                f.write("WARNINGS\n")
                f.write("="*80 + "\n\n")
                for warning in self.warnings:
                    f.write(f"⚠️  {warning}\n")
        
        print(f"\n✓ Detailed report saved to: {output_file}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(
        description='Verify database migration'
    )
    parser.add_argument(
        '--db-path',
        default='indian_stocks.db',
        help='Path to database file'
    )
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed report'
    )
    
    args = parser.parse_args()
    
    # Verify
    verifier = MigrationVerifier(args.db_path)
    success = verifier.verify_all()
    
    # Generate report if requested
    if args.report:
        verifier.generate_report()
    
    verifier.close()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())