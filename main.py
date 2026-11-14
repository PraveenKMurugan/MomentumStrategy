# from tests import test_setup
from scripts import download_data
from src.data import database_update
from scripts import fix_validated_column, divide_by_zero_issue, create_portfolio, run_backtest
from src.data import unified_data_manager
from src.data.unified_data_manager import UnifiedDataManager
from dashboard import app, enhanced_app
from src.portfolio import portfolio_manager
from src.migration import migrate_to_unified_schema
from src.migration import verify_migration
from src.data import get_data_example_unified
from scripts import fix_unicode
from scripts import auto_file_updater, test_complete_system, download_data, run_analysis
import sys
import io
from scripts import momentum_debugger

# # Fix Windows console encoding
# if sys.platform == 'win32':
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test():
    # Test 1: Check database
    import sqlite3
    conn = sqlite3.connect('indian_stocks.db')
    cursor = conn.cursor()

    cursor.execute("SELECT index_membership, COUNT(*) FROM stocks GROUP BY index_membership")
    print(cursor.fetchall())
    # Should show: [('NIFTY50,NIFTY500,ALL', 50), ('NIFTY500,ALL', xxx), ...]

    # Test 2: Load strategy
    from src.analysis.dynamic_analyzer import StrategyConfig
    config = StrategyConfig.load('config/strategies/balanced_momentum.json')
    print(config.config_name)
    # Should print: Balanced_Momentum

    # Test 3: Check strategy files
    import os
    files = os.listdir('config/strategies')
    print(files)
    # Should list all 6 .json files

def get_nse_stock_list():
    edm = UnifiedDataManager()
    stock_list = edm._get_nse_stocks_csv()
    edm.save_stock_list(stock_list)
    return 

def get_portfolio(id: str):
    pm = portfolio_manager.EnterprisePortfolioManager()
    portfolio = pm.get_portfolio_summary(id)
    print("Portfolio Summary:\n\n", portfolio)
    return portfolio


if __name__ == "__main__":
    # test_setup.test_imports()
    # download_data.main()
    # get_nse_stock_list()
    # edm.save_stock_list(stock_list)    
    # run_analysis.main()
    # enhanced_app.main()
    # get_portfolio("1")
    # create_portfolio.main()
    # run_backtest.main()
    # database_update.main()
    # test()
    # fix_validated_column.main()
    # divide_by_zero_issue.main()
    # migrate_to_unified_schema.main()
    # verify_migration.main()
    # auto_file_updater.main()
    # test_complete_system.main()
    # unified_data_manager.main()
    # get_data_example_unified.main()
    # fix_unicode.main()
    momentum_debugger.quick_diagnostic()