"""
Complete System Test Suite
Tests all components after migration and updates
"""

import sys
import traceback
from datetime import datetime


class SystemTester:
    """Complete system test suite"""
    
    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []
    
    def test_imports(self):
        """Test 1: Verify all imports work"""
        print("\n" + "="*80)
        print("TEST 1: IMPORTS")
        print("="*80)
        
        imports_to_test = [
            ('UnifiedDataManager', 'src.data.unified_data_manager'),
            ('DynamicStockAnalyzer', 'src.analysis.dynamic_analyzer'),
            ('StrategyConfig', 'src.analysis.dynamic_analyzer'),
            ('PresetStrategies', 'src.analysis.dynamic_analyzer'),
            ('EnterprisePortfolioManager', 'src.portfolio.portfolio_manager'),
            ('EnterpriseBacktestEngine', 'src.backtest.backtest_engine'),
            ('IntegratedWorkflowManager', 'src.workflow.integrated_manager'),
            ('ConfigManager', 'src.core.config'),
            ('LoggerFactory', 'src.core.logging'),
        ]
        
        all_passed = True
        
        for class_name, module_name in imports_to_test:
            try:
                module = __import__(module_name, fromlist=[class_name])
                getattr(module, class_name)
                print(f"✓ {class_name}")
            except ImportError as e:
                print(f"✗ {class_name}: {e}")
                self.failed.append(f"Import {class_name}")
                all_passed = False
            except AttributeError as e:
                print(f"✗ {class_name}: Not found in module")
                self.failed.append(f"Import {class_name}")
                all_passed = False
        
        if all_passed:
            self.passed.append("Imports")
            return True
        return False
    
    def test_database_connections(self):
        """Test 2: Verify database connections and foreign keys"""
        print("\n" + "="*80)
        print("TEST 2: DATABASE CONNECTIONS")
        print("="*80)
        
        try:
            from src.data.unified_data_manager import UnifiedDataManager
            from src.analysis.dynamic_analyzer import DynamicStockAnalyzer
            from src.portfolio.portfolio_manager import EnterprisePortfolioManager
            from src.backtest.backtest_engine import EnterpriseBacktestEngine
            from src.workflow.integrated_manager import IntegratedWorkflowManager
            
            components = [
                ('UnifiedDataManager', UnifiedDataManager),
                ('DynamicStockAnalyzer', DynamicStockAnalyzer),
                ('PortfolioManager', EnterprisePortfolioManager),
                ('BacktestEngine', EnterpriseBacktestEngine),
                ('WorkflowManager', IntegratedWorkflowManager),
            ]
            
            all_passed = True
            
            for name, ComponentClass in components:
                try:
                    print(f"\n{name}:")
                    component = ComponentClass()
                    
                    # Check connection
                    cursor = component.conn.cursor()
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    
                    if result[0] == 1:
                        print(f"  ✓ Connection OK")
                    else:
                        print(f"  ✗ Connection test failed")
                        all_passed = False
                    
                    # Check foreign keys
                    cursor.execute("PRAGMA foreign_keys")
                    fk_result = cursor.fetchone()
                    fk_enabled = fk_result[0] if fk_result else 0
                    
                    if fk_enabled:
                        print(f"  ✓ Foreign keys: Enabled")
                    else:
                        print(f"  ⚠️  Foreign keys: Disabled")
                        self.warnings.append(f"{name}: FK disabled")
                    
                    component.close()
                    
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    self.failed.append(f"Connection {name}")
                    all_passed = False
            
            if all_passed:
                self.passed.append("Database Connections")
                return True
            return False
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            traceback.print_exc()
            self.failed.append("Database Connections")
            return False
    
    def test_data_access(self):
        """Test 3: Verify data access"""
        print("\n" + "="*80)
        print("TEST 3: DATA ACCESS")
        print("="*80)
        
        try:
            from src.data.unified_data_manager import UnifiedDataManager
            
            manager = UnifiedDataManager()
            
            # Test 1: Get stock list
            print("\n1. Stock List:")
            stocks = manager.get_stock_list()
            if len(stocks) > 0:
                print(f"   ✓ Loaded {len(stocks)} stocks")
            else:
                print(f"   ⚠️  No stocks found")
                self.warnings.append("No stocks in database")
            
            # Test 2: Get system health
            print("\n2. System Health:")
            health = manager.get_system_health()
            print(f"   Total stocks: {health['total_stocks']}")
            print(f"   Total records: {health['total_records']}")
            print(f"   Avg quality: {health['avg_data_quality']}")
            
            if health['total_stocks'] > 0:
                print("   ✓ Database has data")
            else:
                print("   ⚠️  Database is empty")
                self.warnings.append("Empty database")
            
            # Test 3: Get data quality report
            print("\n3. Data Quality Report:")
            quality_df = manager.get_data_quality_report()
            if not quality_df.empty:
                print(f"   ✓ Quality report: {len(quality_df)} entries")
            else:
                print(f"   ℹ️  No quality data yet")
            
            manager.close()
            
            self.passed.append("Data Access")
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            traceback.print_exc()
            self.failed.append("Data Access")
            return False
    
    def test_analyzer(self):
        """Test 4: Test stock analyzer"""
        print("\n" + "="*80)
        print("TEST 4: STOCK ANALYZER")
        print("="*80)
        
        try:
            from src.analysis.dynamic_analyzer import (
                DynamicStockAnalyzer, 
                PresetStrategies
            )
            
            analyzer = DynamicStockAnalyzer()
            
            # Test 1: Strategy configuration
            print("\n1. Strategy Configuration:")
            strategy = PresetStrategies.balanced_momentum()
            analyzer.set_config(strategy)
            print(f"   ✓ Strategy loaded: {strategy.config_name}")
            
            # Test 2: Get universe
            print("\n2. Universe Symbols:")
            symbols = analyzer.get_universe_symbols()
            print(f"   ✓ Universe: {len(symbols)} stocks")
            
            if len(symbols) == 0:
                self.warnings.append("No symbols in universe")
            
            analyzer.close()
            
            self.passed.append("Stock Analyzer")
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            traceback.print_exc()
            self.failed.append("Stock Analyzer")
            return False
    
    def test_workflow_manager(self):
        """Test 5: Test workflow manager"""
        print("\n" + "="*80)
        print("TEST 5: WORKFLOW MANAGER")
        print("="*80)
        
        try:
            from src.workflow.integrated_manager import IntegratedWorkflowManager
            
            wfm = IntegratedWorkflowManager()
            
            # Test 1: Workflow history
            print("\n1. Workflow History:")
            history = wfm.get_workflow_history(limit=5)
            print(f"   ✓ History entries: {len(history)}")
            
            # Test 2: System stats
            print("\n2. System Stats:")
            cursor = wfm.conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM workflows")
            workflow_count = cursor.fetchone()[0]
            print(f"   Total workflows: {workflow_count}")
            
            cursor.execute("SELECT COUNT(*) FROM update_history")
            update_count = cursor.fetchone()[0]
            print(f"   Update history: {update_count}")
            
            cursor.execute("SELECT COUNT(*) FROM failed_updates WHERE status='pending'")
            failed_count = cursor.fetchone()[0]
            print(f"   Pending failures: {failed_count}")
            
            print("   ✓ Workflow manager operational")
            
            wfm.close()
            
            self.passed.append("Workflow Manager")
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            traceback.print_exc()
            self.failed.append("Workflow Manager")
            return False
    
    def test_schema_verification(self):
        """Test 6: Verify unified schema"""
        print("\n" + "="*80)
        print("TEST 6: SCHEMA VERIFICATION")
        print("="*80)
        
        try:
            import sqlite3
            
            conn = sqlite3.connect('indian_stocks.db')
            cursor = conn.cursor()
            
            # Check required tables
            print("\n1. Required Tables:")
            required_tables = [
                'stocks', 'price_data', 'data_quality_history',
                'update_history', 'failed_updates'
            ]
            
            all_exist = True
            for table in required_tables:
                cursor.execute(f"""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name=?
                """, [table])
                
                if cursor.fetchone():
                    print(f"   ✓ {table}")
                else:
                    print(f"   ✗ {table} - NOT FOUND")
                    all_exist = False
            
            if not all_exist:
                self.failed.append("Schema Verification")
                return False
            
            # Check new columns in stocks
            print("\n2. New Columns in 'stocks':")
            cursor.execute("PRAGMA table_info(stocks)")
            columns = [col[1] for col in cursor.fetchall()]
            
            new_columns = [
                'market_cap_cr', 'update_frequency', 
                'created_date', 'last_modified'
            ]
            
            for col in new_columns:
                if col in columns:
                    print(f"   ✓ {col}")
                else:
                    print(f"   ⚠️  {col} - Missing")
                    self.warnings.append(f"Missing column: {col}")
            
            # Check indexes
            print("\n3. Indexes:")
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
            """)
            indexes = [row[0] for row in cursor.fetchall()]
            print(f"   ✓ Found {len(indexes)} indexes")
            
            conn.close()
            
            self.passed.append("Schema Verification")
            return True
            
        except Exception as e:
            print(f"✗ Test failed: {e}")
            traceback.print_exc()
            self.failed.append("Schema Verification")
            return False
    
    def run_all_tests(self):
        """Run all tests"""
        print("="*80)
        print("COMPLETE SYSTEM TEST SUITE")
        print("="*80)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        tests = [
            self.test_imports,
            self.test_database_connections,
            self.test_data_access,
            self.test_analyzer,
            self.test_workflow_manager,
            self.test_schema_verification,
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                print(f"\n✗ Test crashed: {e}")
                traceback.print_exc()
        
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        
        total = len(self.passed) + len(self.failed)
        
        print(f"\nTotal Tests: {total}")
        print(f"Passed: {len(self.passed)}")
        print(f"Failed: {len(self.failed)}")
        print(f"Warnings: {len(self.warnings)}")
        
        if self.passed:
            print("\n✓ PASSED:")
            for test in self.passed:
                print(f"  • {test}")
        
        if self.failed:
            print("\n✗ FAILED:")
            for test in self.failed:
                print(f"  • {test}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        print("\n" + "="*80)
        
        if len(self.failed) == 0:
            print("🎉 ALL TESTS PASSED!")
            print("="*80)
            print("\nYour system is ready to use!")
            print("\nNext steps:")
            print("1. Start using the UnifiedDataManager")
            print("2. Run workflows with IntegratedWorkflowManager")
            print("3. Launch dashboard: streamlit run dashboard/enhanced_app.py")
        else:
            print("⚠️  SOME TESTS FAILED")
            print("="*80)
            print("\nPlease address the failed tests before proceeding.")
            print("Check the error messages above for details.")
        
        return len(self.failed) == 0


def main():
    """Main test function"""
    tester = SystemTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())