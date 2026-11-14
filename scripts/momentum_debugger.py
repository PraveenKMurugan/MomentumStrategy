"""
Debug Script for Momentum Strategy Issues

This will help identify why strategies are showing negative returns
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta


class MomentumDebugger:
    """Debug momentum calculation issues"""
    
    def __init__(self, db_path='indian_stocks.db'):
        self.conn = sqlite3.connect(db_path)
    
    def check_data_quality(self):
        """Check overall data quality"""
        print("="*80)
        print("DATA QUALITY CHECK")
        print("="*80)
        
        cursor = self.conn.cursor()
        
        # 1. Check total stocks and records
        cursor.execute("SELECT COUNT(*) FROM stocks WHERE is_active = 1")
        total_stocks = cursor.fetchone()[0]
        print(f"\n1. Total Active Stocks: {total_stocks}")
        
        cursor.execute("SELECT COUNT(*) FROM price_data")
        total_records = cursor.fetchone()[0]
        print(f"   Total Price Records: {total_records:,}")
        
        if total_stocks == 0:
            print("   ❌ ISSUE: No stocks in database!")
            return False
        
        if total_records == 0:
            print("   ❌ ISSUE: No price data in database!")
            return False
        
        # 2. Check date range
        cursor.execute("""
            SELECT MIN(date), MAX(date), COUNT(DISTINCT symbol)
            FROM price_data
        """)
        min_date, max_date, symbols_with_data = cursor.fetchone()
        
        print(f"\n2. Date Range:")
        print(f"   First Date: {min_date}")
        print(f"   Last Date: {max_date}")
        print(f"   Symbols with data: {symbols_with_data}")
        
        # Check if data is recent
        if max_date:
            last_date = datetime.strptime(max_date, '%Y-%m-%d')
            days_old = (datetime.now() - last_date).days
            print(f"   Data age: {days_old} days old")
            
            if days_old > 30:
                print(f"   ⚠️  WARNING: Data is {days_old} days old! Consider updating.")
        
        # 3. Check data per stock
        cursor.execute("""
            SELECT 
                symbol,
                COUNT(*) as records,
                MIN(date) as first_date,
                MAX(date) as last_date
            FROM price_data
            GROUP BY symbol
            ORDER BY records DESC
            LIMIT 10
        """)
        
        print(f"\n3. Top 10 Stocks by Data Points:")
        print(f"   {'Symbol':<15} {'Records':>10} {'First Date':<12} {'Last Date':<12}")
        print(f"   {'-'*55}")
        
        for row in cursor.fetchall():
            print(f"   {row[0]:<15} {row[1]:>10} {row[2]:<12} {row[3]:<12}")
        
        # 4. Check for stocks with insufficient data
        cursor.execute("""
            SELECT symbol, COUNT(*) as records
            FROM price_data
            GROUP BY symbol
            HAVING records < 252
            ORDER BY records ASC
            LIMIT 10
        """)
        
        insufficient = cursor.fetchall()
        if insufficient:
            print(f"\n4. Stocks with Insufficient Data (<252 days):")
            for symbol, count in insufficient:
                print(f"   {symbol}: {count} records")
        
        return True
    
    def test_momentum_calculation(self, symbol='RELIANCE.NS'):
        """Test momentum calculation for a single stock"""
        print("\n" + "="*80)
        print(f"MOMENTUM CALCULATION TEST: {symbol}")
        print("="*80)
        
        # Get data
        query = """
            SELECT date, close
            FROM price_data
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 300
        """
        
        df = pd.read_sql_query(query, self.conn, params=[symbol])
        
        if df.empty:
            print(f"❌ No data found for {symbol}")
            return
        
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df.set_index('date', inplace=True)
        
        print(f"\n1. Data Summary:")
        print(f"   Records: {len(df)}")
        print(f"   First Date: {df.index[0].strftime('%Y-%m-%d')}")
        print(f"   Last Date: {df.index[-1].strftime('%Y-%m-%d')}")
        print(f"   First Price: ₹{df['close'].iloc[0]:.2f}")
        print(f"   Last Price: ₹{df['close'].iloc[-1]:.2f}")
        
        if len(df) < 252:
            print(f"   ⚠️  WARNING: Only {len(df)} days of data (need 252+)")
        
        # Calculate returns for different periods
        print(f"\n2. Return Calculations:")
        
        periods = [
            ('1M', 21),
            ('3M', 63),
            ('6M', 126),
            ('12M', 252)
        ]
        
        for period_name, days in periods:
            if len(df) >= days:
                ret = (df['close'].iloc[-1] / df['close'].iloc[-days] - 1) * 100
                print(f"   {period_name:>3} Return: {ret:>7.2f}%")
            else:
                print(f"   {period_name:>3} Return: Insufficient data")
        
        # Calculate volatility
        returns = df['close'].pct_change().dropna()
        if len(returns) >= 126:
            vol = returns.tail(126).std() * np.sqrt(252) * 100
            print(f"\n3. Volatility (6M): {vol:.2f}%")
        
        # Check for data issues
        print(f"\n4. Data Quality Checks:")
        
        # Check for zeros
        zeros = (df['close'] == 0).sum()
        print(f"   Zero prices: {zeros}")
        if zeros > 0:
            print(f"   ❌ ISSUE: Found {zeros} zero prices!")
        
        # Check for NaNs
        nans = df['close'].isna().sum()
        print(f"   NaN prices: {nans}")
        if nans > 0:
            print(f"   ❌ ISSUE: Found {nans} NaN prices!")
        
        # Check for extreme jumps
        daily_returns = df['close'].pct_change()
        extreme_moves = (abs(daily_returns) > 0.5).sum()
        print(f"   Extreme moves (>50%): {extreme_moves}")
        if extreme_moves > 5:
            print(f"   ⚠️  WARNING: Many extreme price movements!")
        
        return df
    
    def test_backtest_logic(self):
        """Test backtest calculation logic"""
        print("\n" + "="*80)
        print("BACKTEST LOGIC TEST")
        print("="*80)
        
        # Simulate a simple backtest
        print("\n1. Simulating Simple Backtest:")
        
        # Test data
        initial_capital = 1000000
        n_stocks = 10
        per_stock = initial_capital / n_stocks
        
        print(f"   Initial Capital: ₹{initial_capital:,.0f}")
        print(f"   Number of Stocks: {n_stocks}")
        print(f"   Per Stock: ₹{per_stock:,.0f}")
        
        # Simulate buying
        stock_price = 100
        shares = int(per_stock / stock_price)
        actual_invested = shares * stock_price
        
        print(f"\n2. Example Stock Purchase:")
        print(f"   Stock Price: ₹{stock_price}")
        print(f"   Shares to Buy: {shares}")
        print(f"   Actual Invested: ₹{actual_invested:,.0f}")
        
        # Simulate returns
        print(f"\n3. Return Scenarios:")
        
        scenarios = [
            ("10% gain", 110),
            ("20% gain", 120),
            ("-10% loss", 90),
            ("-20% loss", 80)
        ]
        
        for scenario, new_price in scenarios:
            new_value = shares * new_price
            pnl = new_value - actual_invested
            pnl_pct = (pnl / actual_invested) * 100
            print(f"   {scenario:12}: ₹{new_value:>10,.0f} (P&L: {pnl_pct:+.2f}%)")
    
    def check_backtest_parameters(self):
        """Check if backtest parameters make sense"""
        print("\n" + "="*80)
        print("BACKTEST PARAMETER CHECK")
        print("="*80)
        
        from src.analysis.dynamic_analyzer import PresetStrategies
        
        strategies = [
            ("Classic", PresetStrategies.classic_momentum()),
            ("Balanced", PresetStrategies.balanced_momentum()),
            ("Short Term", PresetStrategies.short_term_momentum())
        ]
        
        for name, strategy in strategies:
            print(f"\n{name} Momentum Strategy:")
            print(f"  Performance Periods:")
            for period_name, config in strategy.performance_periods.items():
                print(f"    {period_name}: {config['days']} days, weight={config['weight']}")
            
            print(f"  Momentum Weights:")
            for period, weight in strategy.momentum_weights.items():
                print(f"    {period}: {weight}")
            
            print(f"  Filters:")
            for filter_name, criteria in strategy.filters.items():
                print(f"    {filter_name}: {criteria}")
    
    def find_problematic_stocks(self):
        """Find stocks that might be causing issues"""
        print("\n" + "="*80)
        print("PROBLEMATIC STOCKS CHECK")
        print("="*80)
        
        cursor = self.conn.cursor()
        
        # 1. Stocks with extreme negative returns
        print("\n1. Stocks with Extreme Negative 6M Returns:")
        
        cursor.execute("""
            SELECT symbol, 
                   MIN(date) as first_date,
                   MAX(date) as last_date,
                   COUNT(*) as records
            FROM price_data
            GROUP BY symbol
            HAVING records >= 126
        """)
        
        problem_stocks = []
        for symbol, first_date, last_date, records in cursor.fetchall():
            # Get 6M return
            cursor.execute("""
                SELECT close
                FROM price_data
                WHERE symbol = ?
                ORDER BY date DESC
                LIMIT 126
            """, [symbol])
            
            prices = [row[0] for row in cursor.fetchall()]
            if len(prices) >= 126:
                ret_6m = (prices[0] / prices[-1] - 1) * 100
                if ret_6m < -50:  # More than 50% loss
                    problem_stocks.append((symbol, ret_6m))
        
        if problem_stocks:
            print(f"   Found {len(problem_stocks)} stocks with >50% loss:")
            for symbol, ret in sorted(problem_stocks, key=lambda x: x[1])[:10]:
                print(f"   {symbol}: {ret:.2f}%")
        else:
            print("   ✓ No stocks with extreme losses")
        
        return problem_stocks
    
    def comprehensive_debug(self):
        """Run all debug checks"""
        print("\n" + "="*100)
        print(" "*30 + "MOMENTUM STRATEGY DEBUGGER")
        print("="*100)
        
        # Check 1: Data Quality
        if not self.check_data_quality():
            print("\n❌ CRITICAL: Fix data quality issues first!")
            return
        
        # Check 2: Test momentum calculation
        self.test_momentum_calculation('RELIANCE.NS')
        
        # Check 3: Test backtest logic
        self.test_backtest_logic()
        
        # Check 4: Check parameters
        self.check_backtest_parameters()
        
        # Check 5: Find problematic stocks
        problem_stocks = self.find_problematic_stocks()
        
        # Summary
        print("\n" + "="*100)
        print("SUMMARY & RECOMMENDATIONS")
        print("="*100)
        
        if problem_stocks and len(problem_stocks) > 10:
            print("\n⚠️  ISSUE FOUND: Many stocks have extreme negative returns")
            print("   This suggests:")
            print("   1. Data might be stale or incorrect")
            print("   2. Wrong date format or sorting")
            print("   3. Corporate actions not adjusted")
            print("\n   RECOMMENDATION: Update your data and verify dates")
        
        print("\n" + "="*100)
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# ============================================================================
# QUICK DIAGNOSTIC SCRIPT
# ============================================================================

def quick_diagnostic():
    """Quick diagnostic for momentum issues"""
    
    debugger = MomentumDebugger()
    
    print("Running comprehensive diagnostics...")
    print("This will check:")
    print("  1. Data quality and coverage")
    print("  2. Momentum calculations")
    print("  3. Backtest logic")
    print("  4. Strategy parameters")
    print("  5. Problematic stocks")
    print()
    
    debugger.comprehensive_debug()
    
    debugger.close()


if __name__ == "__main__":
    quick_diagnostic()