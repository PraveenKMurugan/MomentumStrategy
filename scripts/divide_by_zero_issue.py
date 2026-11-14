"""
Fix Analysis Errors & Debug Why No Stocks Found
This script will:
1. Fix the division by zero error
2. Check why no stocks are being analyzed
3. Verify your data
4. Test the analyzer step-by-step
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta

def check_data_availability(db_path='indian_stocks.db'):
    """
    Check what data is actually in the database
    """
    print("="*80)
    print("CHECKING DATA AVAILABILITY")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check stocks table
    print("\n1. STOCKS TABLE:")
    cursor.execute("SELECT COUNT(*) FROM stocks")
    stock_count = cursor.fetchone()[0]
    print(f"   Total stocks: {stock_count:,}")
    
    if stock_count == 0:
        print("   ❌ No stocks in database!")
        print("   Run: python scripts/download_data.py")
        conn.close()
        return False
    
    # Check stocks with index_membership
    cursor.execute("SELECT COUNT(*) FROM stocks WHERE index_membership LIKE '%NIFTY500%'")
    nifty500_count = cursor.fetchone()[0]
    print(f"   NIFTY500 stocks: {nifty500_count:,}")
    
    # Check price data
    print("\n2. PRICE DATA:")
    cursor.execute("SELECT COUNT(*) FROM price_data")
    price_count = cursor.fetchone()[0]
    print(f"   Total price records: {price_count:,}")
    
    if price_count == 0:
        print("   ❌ No price data in database!")
        print("   Run: python scripts/download_data.py")
        conn.close()
        return False
    
    # Check how many stocks have data
    cursor.execute("SELECT COUNT(DISTINCT symbol) FROM price_data")
    stocks_with_data = cursor.fetchone()[0]
    print(f"   Stocks with price data: {stocks_with_data:,}")
    
    # Check date range
    cursor.execute("SELECT MIN(date), MAX(date) FROM price_data")
    min_date, max_date = cursor.fetchone()
    print(f"   Date range: {min_date} to {max_date}")
    
    # Check if we have enough historical data (need at least 252 days for 1 year)
    cursor.execute("""
        SELECT symbol, COUNT(*) as cnt
        FROM price_data
        GROUP BY symbol
        HAVING cnt >= 252
        ORDER BY cnt DESC
        LIMIT 10
    """)
    
    stocks_with_enough_data = cursor.fetchall()
    
    print("\n3. STOCKS WITH SUFFICIENT DATA (>= 252 days):")
    if stocks_with_enough_data:
        for symbol, count in stocks_with_enough_data:
            print(f"   {symbol}: {count} records")
        
        # Count total with enough data
        cursor.execute("""
            SELECT COUNT(DISTINCT symbol)
            FROM price_data
            GROUP BY symbol
            HAVING COUNT(*) >= 252
        """)
        total_sufficient = len(cursor.fetchall())
        print(f"\n   Total with >= 252 days: {total_sufficient:,}")
    else:
        print("   ❌ No stocks have enough data (need >= 252 days)!")
        print("   Your data might be incomplete.")
    
    # Check a specific popular stock
    print("\n4. SAMPLE STOCK CHECK (RELIANCE.NS):")
    cursor.execute("""
        SELECT COUNT(*), MIN(date), MAX(date)
        FROM price_data
        WHERE symbol = 'RELIANCE.NS'
    """)
    result = cursor.fetchone()
    
    if result and result[0] > 0:
        count, first, last = result
        print(f"   Records: {count}")
        print(f"   Range: {first} to {last}")
    else:
        print("   ❌ RELIANCE.NS not found in database")
        print("   This is a basic stock - if missing, your download is incomplete")
    
    conn.close()
    
    print("\n" + "="*80)
    
    return stocks_with_data > 0 and total_sufficient > 0

def fix_analyzer_code():
    """
    Create a fixed version of the analyzer code
    """
    print("\n" + "="*80)
    print("FIX FOR apply_filters FUNCTION")
    print("="*80)
    
    fixed_code = '''
def apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
    """Apply configured filters to analysis results"""
    if self.strategy_config is None:
        raise ValueError("Strategy configuration not set")
    
    filtered = df.copy()
    initial_count = len(filtered)
    
    # Handle empty DataFrame
    if initial_count == 0:
        self.logger.warning("No stocks to filter - input DataFrame is empty")
        return filtered
    
    self.logger.info(f"Applying filters to {initial_count} stocks")
    
    for filter_name, criteria in self.strategy_config.filters.items():
        # Volume filter
        if filter_name == 'volume':
            if 'min_value' in criteria and 'avg_volume' in filtered.columns:
                filtered = filtered[filtered['avg_volume'] >= criteria['min_value']]
                self.logger.info(f"Volume filter: {len(filtered)} stocks remain")
        
        # Volatility filter
        elif filter_name == 'volatility':
            vol_cols = [col for col in filtered.columns if 'volatility' in col]
            if vol_cols and 'max_value' in criteria:
                filtered = filtered[filtered[vol_cols[0]] <= criteria['max_value']]
                self.logger.info(f"Volatility filter: {len(filtered)} stocks remain")
        
        # Momentum filter
        elif filter_name == 'momentum':
            if 'min_value' in criteria and 'momentum_score' in filtered.columns:
                filtered = filtered[filtered['momentum_score'] >= criteria['min_value']]
                self.logger.info(f"Momentum filter: {len(filtered)} stocks remain")
        
        # Market cap filter
        elif filter_name == 'market_cap':
            if 'min_value' in criteria and 'market_cap_cr' in filtered.columns:
                filtered = filtered[filtered['market_cap_cr'] >= criteria['min_value']]
                self.logger.info(f"Market cap filter: {len(filtered)} stocks remain")
    
    # Safe percentage calculation
    if initial_count > 0:
        percentage = len(filtered) / initial_count * 100
        self.logger.info(
            f"Filtering complete: {initial_count} → {len(filtered)} "
            f"({percentage:.1f}%)"
        )
    else:
        self.logger.warning("Filtering complete: No stocks to filter")
    
    return filtered.reset_index(drop=True)
'''
    
    print("\n✓ Fixed code for apply_filters method")
    print("\nThe fix adds:")
    print("  1. Check if DataFrame is empty before filtering")
    print("  2. Safe division that handles zero initial_count")
    print("  3. Better logging for debugging")
    
    print("\nTo apply this fix:")
    print("  1. Open: src/analysis/dynamic_analyzer.py")
    print("  2. Find: def apply_filters(self, df: pd.DataFrame)")
    print("  3. Replace with the code above")
    
    return fixed_code

def test_analyzer_step_by_step(db_path='indian_stocks.db'):
    """
    Test the analyzer step by step to find where it fails
    """
    print("\n" + "="*80)
    print("STEP-BY-STEP ANALYZER TEST")
    print("="*80)
    
    try:
        # Import
        print("\n1. Importing modules...")
        from src.analysis.dynamic_analyzer import DynamicStockAnalyzer, PresetStrategies
        print("   ✓ Import successful")
        
        # Initialize
        print("\n2. Initializing analyzer...")
        analyzer = DynamicStockAnalyzer(db_path)
        print("   ✓ Analyzer initialized")
        
        # Load strategy
        print("\n3. Loading strategy...")
        config = PresetStrategies.balanced_momentum()
        analyzer.set_config(config)
        print(f"   ✓ Strategy loaded: {config.config_name}")
        print(f"   Universe: {config.universe}")
        
        # Get symbols
        print("\n4. Getting universe symbols...")
        symbols = analyzer.get_universe_symbols()
        print(f"   ✓ Found {len(symbols)} symbols in universe")
        
        if len(symbols) == 0:
            print("   ❌ NO SYMBOLS FOUND!")
            print("   This is why analysis returns 0 stocks")
            print("\n   Possible causes:")
            print("   - No stocks in database")
            print("   - index_membership not set correctly")
            print("   - Universe filter too strict")
            return False
        
        print(f"   First 10 symbols: {symbols[:10]}")
        
        # Test data for one stock
        print("\n5. Testing data retrieval for one stock...")
        test_symbol = symbols[0]
        print(f"   Testing: {test_symbol}")
        
        from datetime import datetime, timedelta
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=500)).strftime('%Y-%m-%d')
        
        df = analyzer.get_stock_data(test_symbol, start_date, end_date)
        
        if df.empty:
            print(f"   ❌ No data for {test_symbol}")
            print("   Your price_data table might be empty")
            return False
        else:
            print(f"   ✓ Got {len(df)} records for {test_symbol}")
            print(f"   Date range: {df.index[0]} to {df.index[-1]}")
        
        # Test metric calculation
        print("\n6. Testing metric calculation...")
        metrics = analyzer.calculate_metrics(test_symbol)
        
        if metrics:
            print(f"   ✓ Metrics calculated for {test_symbol}")
            print(f"   Keys: {list(metrics.keys())}")
            if 'momentum_score' in metrics:
                print(f"   Momentum Score: {metrics['momentum_score']}")
        else:
            print(f"   ❌ No metrics calculated for {test_symbol}")
            print("   Stock might not have enough data")
        
        # Test analyze_universe (on small sample)
        print("\n7. Testing universe analysis (first 5 stocks)...")
        
        # Temporarily limit symbols for testing
        test_symbols = symbols[:5]
        
        # Create temp data dict
        all_data = {}
        for sym in test_symbols:
            df = analyzer.get_stock_data(sym, start_date, end_date)
            if not df.empty:
                all_data[sym] = df
        
        print(f"   Stocks with data: {len(all_data)}")
        
        results = []
        for sym in all_data.keys():
            metrics = analyzer.calculate_metrics(sym)
            if metrics:
                results.append(metrics)
        
        if results:
            print(f"   ✓ Successfully analyzed {len(results)} stocks")
            results_df = pd.DataFrame(results)
            print(f"   Columns: {list(results_df.columns)}")
            
            if 'momentum_score' in results_df.columns:
                print(f"   Momentum scores range: {results_df['momentum_score'].min():.2f} to {results_df['momentum_score'].max():.2f}")
        else:
            print("   ❌ No results from analysis")
            print("   Stocks don't have enough data for momentum calculation")
        
        print("\n" + "="*80)
        print("✓ DIAGNOSIS COMPLETE")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_quick_fix_patch():
    """
    Create a quick patch file for the apply_filters function
    """
    print("\n" + "="*80)
    print("CREATING QUICK FIX PATCH")
    print("="*80)
    
    patch_code = '''"""
Quick patch for apply_filters division by zero error
Add this at the start of apply_filters function in dynamic_analyzer.py
"""

# Add this check at the start of apply_filters method
if len(df) == 0:
    self.logger.warning("No stocks to filter - input DataFrame is empty")
    return df

# Add this for safe percentage calculation
# Replace the line with division:
# f"({len(filtered)/initial_count*100:.1f}%)"
# With:
percentage = (len(filtered) / initial_count * 100) if initial_count > 0 else 0
self.logger.info(
    f"Filtering complete: {initial_count} → {len(filtered)} ({percentage:.1f}%)"
)
'''
    
    with open('fix_apply_filters.patch', 'w', encoding="utf-8") as f:
        f.write(patch_code)
    
    print("\n✓ Created fix_apply_filters.patch")
    print("\nQuick fix:")
    print("  1. Open: src/analysis/dynamic_analyzer.py")
    print("  2. Go to: apply_filters method (around line 440)")
    print("  3. Add at start:")
    print("     if len(df) == 0:")
    print("         self.logger.warning('No stocks to filter')")
    print("         return df")
    print("  4. Change line ~451 to safe division")

def main():
    """
    Main diagnostic and fix routine
    """
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "ANALYZER ERROR DIAGNOSIS & FIX" + " "*28 + "║")
    print("╚" + "="*78 + "╝")
    
    print("\nThis will:")
    print("  1. Check your database for data")
    print("  2. Test the analyzer step-by-step")
    print("  3. Identify why you're getting 0 stocks")
    print("  4. Provide fixes")
    
    # Step 1: Check data
    print("\n" + "="*80)
    print("STEP 1: DATA AVAILABILITY CHECK")
    print("="*80)
    
    has_data = check_data_availability()
    
    if not has_data:
        print("\n❌ PROBLEM IDENTIFIED: Insufficient data in database")
        print("\n📋 SOLUTION:")
        print("  1. Download stock data:")
        print("     python scripts/download_data.py")
        print("  2. Then re-run your analysis")
        return
    
    # Step 2: Test analyzer
    print("\n" + "="*80)
    print("STEP 2: ANALYZER STEP-BY-STEP TEST")
    print("="*80)
    
    test_passed = test_analyzer_step_by_step()
    
    # Step 3: Provide fixes
    print("\n" + "="*80)
    print("STEP 3: APPLYING FIXES")
    print("="*80)
    
    fix_analyzer_code()
    create_quick_fix_patch()
    
    print("\n" + "="*80)
    print("SUMMARY & NEXT STEPS")
    print("="*80)
    
    if not has_data:
        print("\n❌ Main Issue: No/insufficient data")
        print("   → Download data first: python scripts/download_data.py")
    elif not test_passed:
        print("\n⚠️  Analyzer has issues")
        print("   → Check the error messages above")
    else:
        print("\n✓ Data looks OK")
    
    print("\n📝 Immediate fixes:")
    print("  1. Apply the code fix to src/analysis/dynamic_analyzer.py")
    print("     (See fix_apply_filters.patch)")
    print("  2. Ensure you have data: python scripts/download_data.py")
    print("  3. Re-test: python scripts/run_analysis.py")

if __name__ == "__main__":
    main()