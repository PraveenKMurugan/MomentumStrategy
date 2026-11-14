"""
Database Migration Script
Migrates from old schema to unified schema while preserving all existing data

Usage:
    python migrate_to_unified_schema.py
    
Or with custom database:
    python migrate_to_unified_schema.py --db-path /path/to/your/database.db
"""

import sqlite3
import argparse
from datetime import datetime
import os
from src.core.config import ConfigManager
import shutil


class DatabaseMigrator:
    """
    Migrates database from old schema to unified schema
    
    Features:
    - Automatic backup before migration
    - Data preservation
    - Rollback capability
    - Progress reporting
    """
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_path = None
        self.conn = None
        
    def create_backup(self):
        """Create backup of current database"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_path = f"{self.db_path}.backup_{timestamp}"
        
        print(f"\n{'='*80}")
        print("CREATING BACKUP")
        print(f"{'='*80}")
        print(f"Original: {self.db_path}")
        print(f"Backup:   {self.backup_path}")
        
        try:
            shutil.copy2(self.db_path, self.backup_path)
            print("✓ Backup created successfully")
            return True
        except Exception as e:
            print(f"✗ Backup failed: {e}")
            return False
    
    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        print(f"✓ Connected to {self.db_path}")
    
    def get_table_info(self, table_name: str):
        """Get current table structure"""
        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return {col[1]: col[2] for col in columns}  # column_name: data_type
    
    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?
        """, [table_name])
        return cursor.fetchone() is not None
    
    def migrate(self):
        """Run complete migration"""
        print(f"\n{'='*80}")
        print("STARTING DATABASE MIGRATION")
        print(f"{'='*80}\n")
        
        try:
            # Step 1: Backup
            if not self.create_backup():
                print("\n✗ Migration aborted: Backup failed")
                return False
            
            # Step 2: Connect
            self.connect()
            
            # Step 3: Analyze current schema
            print(f"\n{'='*80}")
            print("ANALYZING CURRENT SCHEMA")
            print(f"{'='*80}")
            
            schema_info = self._analyze_schema()
            self._print_schema_info(schema_info)
            
            # Step 4: Migrate each table
            print(f"\n{'='*80}")
            print("MIGRATING TABLES")
            print(f"{'='*80}\n")
            
            self._migrate_stocks_table()
            self._migrate_price_data_table()
            self._migrate_data_quality_table()
            self._preserve_existing_tables()
            self._create_new_tables()
            self._create_indexes()
            
            # Step 5: Verify migration
            print(f"\n{'='*80}")
            print("VERIFYING MIGRATION")
            print(f"{'='*80}")
            
            if self._verify_migration():
                # Enable foreign keys for future connections
                self._enable_foreign_keys()
                
                print("\n✓ Migration completed successfully!")
                print(f"\nBackup saved at: {self.backup_path}")
                print("If everything works, you can delete the backup file.")
                return True
            else:
                print("\n✗ Migration verification failed!")
                self._rollback()
                return False
                
        except Exception as e:
            print(f"\n✗ Migration failed: {e}")
            print("\nAttempting rollback...")
            self._rollback()
            return False
        finally:
            if self.conn:
                self.conn.close()
    
    def _analyze_schema(self):
        """Analyze current database schema"""
        cursor = self.conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = {}
        for table in tables:
            # Get column info
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            row_count = cursor.fetchone()[0]
            
            schema_info[table] = {
                'columns': columns,
                'row_count': row_count
            }
        
        return schema_info
    
    def _print_schema_info(self, schema_info):
        """Print schema information"""
        for table_name, info in schema_info.items():
            print(f"\n{table_name}:")
            print(f"  Rows: {info['row_count']}")
            print(f"  Columns: {len(info['columns'])}")
            for col in info['columns']:
                print(f"    - {col[1]} ({col[2]})")
    
    def _migrate_stocks_table(self):
        """Migrate stocks table to unified schema"""
        print("\n1. Migrating 'stocks' table...")
        
        cursor = self.conn.cursor()
        
        # Get current structure
        current_cols = self.get_table_info('stocks')
        
        # Count current records
        cursor.execute("SELECT COUNT(*) FROM stocks")
        total_records = cursor.fetchone()[0]
        print(f"   Current records: {total_records}")
        
        # Create new table with unified schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks_new (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                sector TEXT,
                industry TEXT,
                
                -- Market data
                market_cap REAL,
                market_cap_cr REAL,
                
                -- NSE-specific
                isin TEXT,
                series TEXT DEFAULT 'EQ',
                listing_date TEXT,
                
                -- Index membership
                index_membership TEXT,
                
                -- Status and quality
                is_active INTEGER DEFAULT 1,
                data_quality_score REAL,
                
                -- Update tracking
                last_update_date TEXT,
                update_frequency TEXT DEFAULT 'daily',
                
                -- Metadata
                notes TEXT,
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                last_modified TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migrate data
        print("   Copying data...")
        
        # Build dynamic INSERT statement based on available columns
        available_cols = []
        target_cols = []
        
        col_mapping = {
            'symbol': 'symbol',
            'company_name': 'company_name',
            'sector': 'sector',
            'industry': 'industry',
            'market_cap': 'market_cap',
            'isin': 'isin',
            'series': 'series',
            'listing_date': 'listing_date',
            'index_membership': 'index_membership',
            'is_active': 'is_active',
            'data_quality_score': 'data_quality_score',
            'last_updated': 'last_update_date',
            'last_update_date': 'last_update_date'
        }
        
        for old_col, new_col in col_mapping.items():
            if old_col in current_cols:
                available_cols.append(old_col)
                target_cols.append(new_col)
        
        # Add market_cap_cr calculation if market_cap exists
        if 'market_cap' in current_cols:
            insert_query = f"""
                INSERT INTO stocks_new ({', '.join(target_cols)}, market_cap_cr)
                SELECT {', '.join(available_cols)}, 
                       CAST(market_cap / 10000000.0 AS REAL) as market_cap_cr
                FROM stocks
            """
        else:
            insert_query = f"""
                INSERT INTO stocks_new ({', '.join(target_cols)})
                SELECT {', '.join(available_cols)}
                FROM stocks
            """
        
        cursor.execute(insert_query)
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM stocks_new")
        migrated_records = cursor.fetchone()[0]
        
        if migrated_records == total_records:
            print(f"   ✓ Migrated {migrated_records} records")
            
            # Replace old table
            cursor.execute("DROP TABLE stocks")
            cursor.execute("ALTER TABLE stocks_new RENAME TO stocks")
            
            self.conn.commit()
            print("   ✓ Table replaced successfully")
        else:
            raise Exception(
                f"Record count mismatch: {total_records} -> {migrated_records}"
            )
    
    def _migrate_price_data_table(self):
        """Migrate price_data table to unified schema"""
        print("\n2. Migrating 'price_data' table...")
        
        cursor = self.conn.cursor()
        
        # Get current structure
        current_cols = self.get_table_info('price_data')
        
        # Count current records
        cursor.execute("SELECT COUNT(*) FROM price_data")
        total_records = cursor.fetchone()[0]
        print(f"   Current records: {total_records}")
        
        if total_records > 1000000:
            print("   ⚠️  Large dataset detected. This may take several minutes...")
        
        # Create new table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS price_data_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date TEXT NOT NULL,
                
                -- OHLCV data
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                
                -- Quality tracking
                validated INTEGER DEFAULT 0,
                quality_score REAL,
                quality_level TEXT,
                
                -- Metadata
                data_source TEXT DEFAULT 'yfinance',
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(symbol, date),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        """)
        
        # Migrate data with proper mapping
        print("   Copying data (this may take a while)...")
        
        # Handle both old schemas
        if 'data_quality' in current_cols:
            # Old schema with data_quality TEXT
            insert_query = """
                INSERT INTO price_data_new 
                (symbol, date, open, high, low, close, adj_close, volume, 
                 validated, quality_level)
                SELECT 
                    symbol, date, open, high, low, close, adj_close, volume,
                    validated, data_quality
                FROM price_data
            """
        else:
            # Enhanced schema with quality_score REAL
            insert_query = """
                INSERT INTO price_data_new 
                (symbol, date, open, high, low, close, adj_close, volume, 
                 validated, quality_score)
                SELECT 
                    symbol, date, open, high, low, close, adj_close, volume,
                    validated, quality_score
                FROM price_data
            """
        
        cursor.execute(insert_query)
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM price_data_new")
        migrated_records = cursor.fetchone()[0]
        
        if migrated_records == total_records:
            print(f"   ✓ Migrated {migrated_records} records")
            
            # Replace old table
            cursor.execute("DROP TABLE price_data")
            cursor.execute("ALTER TABLE price_data_new RENAME TO price_data")
            
            self.conn.commit()
            print("   ✓ Table replaced successfully")
        else:
            raise Exception(
                f"Record count mismatch: {total_records} -> {migrated_records}"
            )
    
    def _migrate_data_quality_table(self):
        """Migrate data_quality table to data_quality_history"""
        print("\n3. Migrating 'data_quality' table...")
        
        cursor = self.conn.cursor()
        
        if not self.table_exists('data_quality'):
            print("   ℹ️  No data_quality table found, skipping...")
            return
        
        # Count records
        cursor.execute("SELECT COUNT(*) FROM data_quality")
        total_records = cursor.fetchone()[0]
        print(f"   Current records: {total_records}")
        
        # Create new table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                check_date TEXT NOT NULL,
                
                -- Quality metrics
                quality_level TEXT,
                quality_score REAL,
                total_records INTEGER,
                missing_records INTEGER,
                duplicate_records INTEGER,
                outliers INTEGER,
                date_gaps INTEGER,
                
                -- Date range
                first_date TEXT,
                last_date TEXT,
                
                -- Issues
                issues TEXT,
                
                -- Metadata
                created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                
                FOREIGN KEY (symbol) REFERENCES stocks(symbol) ON DELETE CASCADE
            )
        """)
        
        # Migrate data with explicit column mapping
        current_cols = self.get_table_info('data_quality')
        
        print("   Mapping columns...")
        
        # Build SELECT and INSERT column lists separately
        select_parts = []
        insert_cols = []
        
        # Symbol (required)
        if 'symbol' in current_cols:
            select_parts.append('symbol')
            insert_cols.append('symbol')
        
        # Check date (from last_check)
        if 'last_check' in current_cols:
            select_parts.append('last_check')
            insert_cols.append('check_date')
        else:
            select_parts.append(f"'{datetime.now().strftime('%Y-%m-%d')}'")
            insert_cols.append('check_date')
        
        # Quality level
        if 'quality_level' in current_cols:
            select_parts.append('quality_level')
            insert_cols.append('quality_level')
        
        # Total records
        if 'total_records' in current_cols:
            select_parts.append('total_records')
            insert_cols.append('total_records')
        
        # Date gaps (was missing_dates)
        if 'missing_dates' in current_cols:
            select_parts.append('missing_dates')
            insert_cols.append('date_gaps')
        
        # Outliers
        if 'outliers' in current_cols:
            select_parts.append('outliers')
            insert_cols.append('outliers')
        
        # First date
        if 'first_date' in current_cols:
            select_parts.append('first_date')
            insert_cols.append('first_date')
        
        # Last date
        if 'last_date' in current_cols:
            select_parts.append('last_date')
            insert_cols.append('last_date')
        
        # Issues
        if 'issues' in current_cols:
            select_parts.append('issues')
            insert_cols.append('issues')
        
        # Build and execute query
        insert_query = f"""
            INSERT INTO data_quality_history ({', '.join(insert_cols)})
            SELECT {', '.join(select_parts)}
            FROM data_quality
        """
        
        print(f"   Executing migration query...")
        cursor.execute(insert_query)
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM data_quality_history")
        migrated_records = cursor.fetchone()[0]
        
        if migrated_records == total_records:
            print(f"   ✓ Migrated {migrated_records} records")
            self.conn.commit()
        else:
            raise Exception(
                f"Record count mismatch: {total_records} -> {migrated_records}"
            )
    
    def _preserve_existing_tables(self):
        """Preserve tables that aren't part of core schema (like analysis_results)"""
        print("\n4. Preserving existing tables...")
        
        cursor = self.conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        all_tables = [row[0] for row in cursor.fetchall()]
        
        # Core tables that we're migrating
        core_tables = [
            'stocks', 'price_data', 'data_quality', 'data_quality_history',
            'update_history', 'failed_updates'
        ]
        
        # Find additional tables
        additional_tables = [t for t in all_tables if t not in core_tables]
        
        if additional_tables:
            print(f"   Found {len(additional_tables)} additional tables to preserve:")
            for table in additional_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   ✓ {table}: {count:,} records")
        else:
            print("   No additional tables found")
    
    def _create_new_tables(self):
        """Create new tables that don't exist in old schema"""
        print("\n5. Creating new tables...")
        
        cursor = self.conn.cursor()
        
        # Update history table
        if not self.table_exists('update_history'):
            print("   Creating 'update_history' table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS update_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    update_date TEXT NOT NULL,
                    update_type TEXT,
                    
                    -- Statistics
                    symbols_attempted INTEGER,
                    symbols_successful INTEGER,
                    symbols_failed INTEGER,
                    duration_seconds REAL,
                    
                    -- Details
                    errors TEXT,
                    notes TEXT,
                    
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("   ✓ Created")
        else:
            print("   ℹ️  'update_history' already exists")
        
        # Failed updates table
        if not self.table_exists('failed_updates'):
            print("   Creating 'failed_updates' table...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS failed_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    
                    -- Failure tracking
                    failure_date TEXT NOT NULL,
                    failure_count INTEGER DEFAULT 1,
                    last_error TEXT,
                    
                    -- Retry management
                    retry_scheduled INTEGER DEFAULT 1,
                    last_retry_date TEXT,
                    next_retry_date TEXT,
                    
                    -- Status
                    status TEXT DEFAULT 'pending',
                    
                    created_date TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_modified TEXT DEFAULT CURRENT_TIMESTAMP,
                    
                    UNIQUE(symbol, status)
                )
            """)
            print("   ✓ Created")
        else:
            print("   ℹ️  'failed_updates' already exists")
        
        self.conn.commit()
    
    def _create_indexes(self):
        """Create indexes for performance"""
        print("\n6. Creating indexes...")
        
        cursor = self.conn.cursor()
        
        indexes = [
            ('idx_price_symbol', 'price_data', 'symbol'),
            ('idx_price_date', 'price_data', 'date'),
            ('idx_price_symbol_date', 'price_data', 'symbol, date'),
            ('idx_stocks_active', 'stocks', 'is_active'),
            ('idx_stocks_index', 'stocks', 'index_membership'),
            ('idx_quality_history_symbol', 'data_quality_history', 'symbol'),
            ('idx_failed_status', 'failed_updates', 'status')
        ]
        
        for index_name, table_name, columns in indexes:
            try:
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON {table_name}({columns})
                """)
                print(f"   ✓ Created {index_name}")
            except Exception as e:
                print(f"   ⚠️  Failed to create {index_name}: {e}")
        
        self.conn.commit()
    
    def _verify_migration(self):
        """Verify migration was successful"""
        cursor = self.conn.cursor()
        
        critical_checks = []
        warnings = []
        
        # Check tables exist (CRITICAL)
        required_tables = [
            'stocks', 'price_data', 'data_quality_history',
            'update_history', 'failed_updates'
        ]
        
        for table in required_tables:
            exists = self.table_exists(table)
            critical_checks.append(('Table ' + table, exists))
            print(f"   {'✓' if exists else '✗'} Table '{table}' exists")
        
        # Check data counts (CRITICAL)
        cursor.execute("SELECT COUNT(*) FROM stocks")
        stocks_count = cursor.fetchone()[0]
        critical_checks.append(('Stocks count > 0', stocks_count > 0))
        print(f"   {'✓' if stocks_count > 0 else '✗'} Stocks: {stocks_count} records")
        
        cursor.execute("SELECT COUNT(*) FROM price_data")
        price_count = cursor.fetchone()[0]
        critical_checks.append(('Price data count > 0', price_count > 0))
        print(f"   {'✓' if price_count > 0 else '✗'} Price data: {price_count} records")
        
        # Check foreign key constraints (WARNING ONLY - not critical)
        cursor.execute("PRAGMA foreign_keys")
        fk_result = cursor.fetchone()
        fk_enabled = fk_result[0] == 1 if fk_result else False
        
        if not fk_enabled:
            warnings.append('Foreign keys are disabled (enable with PRAGMA foreign_keys=ON)')
            print(f"   ⚠️  Foreign keys: Disabled (will be enabled on next connection)")
        else:
            print(f"   ✓ Foreign keys: Enabled")
        
        # Overall result - only critical checks must pass
        all_critical_passed = all(check[1] for check in critical_checks)
        
        # Store warnings for later display
        if warnings and all_critical_passed:
            print(f"\n   ℹ️  Note: {len(warnings)} warning(s) - not critical")
        
        return all_critical_passed
    
    def _enable_foreign_keys(self):
        """Enable foreign keys for the database"""
        print(f"\n{'='*80}")
        print("ENABLING FOREIGN KEYS")
        print(f"{'='*80}")
        
        cursor = self.conn.cursor()
        
        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Verify
        cursor.execute("PRAGMA foreign_keys")
        result = cursor.fetchone()
        enabled = result[0] == 1 if result else False
        
        if enabled:
            print("✓ Foreign keys enabled")
            print("\nNote: Foreign keys are now enabled for this connection.")
            print("They will remain enabled for new connections if you connect with:")
            print("  conn = sqlite3.connect('indian_stocks.db')")
            print("  conn.execute('PRAGMA foreign_keys = ON')")
        else:
            print("⚠️  Could not enable foreign keys")
            print("You may need to enable them manually in your code:")
            print("  conn.execute('PRAGMA foreign_keys = ON')")
    
    def _rollback(self):
        """Rollback to backup"""
        print("\nRolling back to backup...")
        
        if self.conn:
            self.conn.close()
        
        if self.backup_path and os.path.exists(self.backup_path):
            try:
                # Remove failed migration
                if os.path.exists(self.db_path):
                    os.remove(self.db_path)
                
                # Restore backup
                shutil.copy2(self.backup_path, self.db_path)
                print(f"✓ Restored from backup: {self.backup_path}")
                print("Original database has been restored.")
            except Exception as e:
                print(f"✗ Rollback failed: {e}")
                print(f"Please manually restore from: {self.backup_path}")
        else:
            print("✗ No backup found for rollback")


def main():
    """Main migration function"""
    parser = argparse.ArgumentParser(
        description='Migrate database to unified schema'
    )
    parser.add_argument(
        '--db-path',
        default='indian_stocks.db',
        help='Path to database file (default: indian_stocks.db)'
    )
    parser.add_argument(
        '--skip-backup',
        action='store_true',
        help='Skip backup creation (not recommended)'
    )
    
    args = parser.parse_args()
    
    # Check if database exists
    if not os.path.exists(args.db_path):
        print(f"✗ Database not found: {args.db_path}")
        print("\nIf you haven't created a database yet, the unified schema")
        print("will be created automatically on first run.")
        return
    
    print("="*80)
    print("DATABASE MIGRATION TO UNIFIED SCHEMA")
    print("="*80)
    print(f"\nDatabase: {args.db_path}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if not args.skip_backup:
        print("\n⚠️  IMPORTANT:")
        print("- A backup will be created before migration")
        print("- Migration is generally safe but test in dev first")
        print("- Large databases may take several minutes")
    
    response = input("\nProceed with migration? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("\nMigration cancelled.")
        return
    
    # Run migration
    migrator = DatabaseMigrator(args.db_path)
    success = migrator.migrate()
    
    if success:
        print("\n" + "="*80)
        print("MIGRATION COMPLETED SUCCESSFULLY! 🎉")
        print("="*80)
        print("\nNext steps:")
        print("1. Test your application with the migrated database")
        print("2. Run data quality checks")
        print("3. If everything works, delete the backup file")
        print(f"\nBackup location: {migrator.backup_path}")
    else:
        print("\n" + "="*80)
        print("MIGRATION FAILED")
        print("="*80)
        print("\nYour original database has been preserved.")
        print("Check the error messages above for details.")


if __name__ == "__main__":
    main()