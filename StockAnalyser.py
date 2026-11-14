"""
Stock Analysis & Universe Filtering Module
Module 2: Process data, calculate metrics, filter universe, rank stocks

This module handles:
1. Calculate momentum scores (3M, 6M, 12M, 12M-1M)
2. Calculate volatility metrics
3. Add fundamental filters (Market Cap, Volume, Quality)
4. Universe filtering (indices, sectors, custom criteria)
5. Stock ranking and scoring
6. Export filtered universe for portfolio construction
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

class StockAnalyzer:
    def __init__(self, db_path='indian_stocks.db'):
        """Initialize analyzer with database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        print(f"✓ Connected to database: {db_path}")
    
    def get_stock_data(self, symbol, start_date=None, end_date=None):
        """Retrieve stock data from database"""
        query = '''
            SELECT date, open, high, low, close, adj_close, volume 
            FROM price_data 
            WHERE symbol = ?
        '''
        params = [symbol]
        
        if start_date:
            query += ' AND date >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND date <= ?'
            params.append(end_date)
        
        query += ' ORDER BY date'
        
        df = pd.read_sql_query(query, self.conn, params=params)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Adj_Close', 'Volume']
        
        return df
    
    def calculate_returns(self, df, periods=[21, 63, 126, 252]):
        """
        Calculate returns for different lookback periods
        
        Parameters:
        - df: DataFrame with price data
        - periods: List of periods in trading days [1M, 3M, 6M, 12M]
        
        Returns: Dictionary with period returns
        """
        returns = {}
        
        for period in periods:
            if len(df) >= period:
                period_return = (df['Adj_Close'].iloc[-1] / df['Adj_Close'].iloc[-period] - 1) * 100
                returns[f'{period}d_return'] = round(period_return, 2)
            else:
                returns[f'{period}d_return'] = None
        
        return returns
    
    def calculate_volatility(self, df, periods=[63, 126, 252]):
        """
        Calculate annualized volatility for different periods
        
        Parameters:
        - df: DataFrame with price data
        - periods: List of periods in trading days
        
        Returns: Dictionary with volatility metrics
        """
        volatility = {}
        daily_returns = df['Adj_Close'].pct_change().dropna()
        
        for period in periods:
            if len(daily_returns) >= period:
                period_vol = daily_returns.tail(period).std() * np.sqrt(252) * 100
                volatility[f'{period}d_volatility'] = round(period_vol, 2)
            else:
                volatility[f'{period}d_volatility'] = None
        
        return volatility
    
    def calculate_max_drawdown(self, df, period=252):
        """Calculate maximum drawdown over specified period"""
        if len(df) < period:
            return None
        #why tail is used in multiple places?
        prices = df['Adj_Close'].tail(period)
        cummax = prices.cummax()
        drawdown = ((prices - cummax) / cummax * 100).min()
        
        return round(drawdown, 2)
    
    def calculate_sharpe_ratio(self, df, period=252, risk_free_rate=6.5):
        """
        Calculate Sharpe ratio (annualized)
        Using India's typical risk-free rate ~6.5%
        """
        if len(df) < period:
            return None
        
        daily_returns = df['Adj_Close'].pct_change().dropna().tail(period)
        
        if len(daily_returns) < period:
            return None
        
        # Annualized return
        annual_return = daily_returns.mean() * 252 * 100
        
        # Annualized volatility
        annual_vol = daily_returns.std() * np.sqrt(252) * 100
        
        if annual_vol == 0:
            return None
        
        sharpe = (annual_return - risk_free_rate) / annual_vol
        
        return round(sharpe, 2)
    
    def calculate_liquidity_metrics(self, df, period=63):
        """
        Calculate liquidity metrics
        - Average daily volume
        - Average daily turnover
        - Days with zero volume
        """
        if len(df) < period:
            return {}
        
        recent_data = df.tail(period)
        
        avg_volume = recent_data['Volume'].mean()
        avg_turnover = (recent_data['Volume'] * recent_data['Close']).mean()
        zero_volume_days = (recent_data['Volume'] == 0).sum()
        
        return {
            'avg_volume_3m': int(avg_volume),
            'avg_turnover_3m': round(avg_turnover, 2),
            'zero_volume_days_3m': zero_volume_days
        }
    
    def get_fundamental_data(self, symbol):
        """
        Fetch fundamental data from Yahoo Finance
        Market Cap, P/E, P/B, ROE, Debt/Equity, etc.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            fundamentals = {
                'market_cap': info.get('marketCap', None),
                'market_cap_cr': round(info.get('marketCap', 0) / 10000000, 2) if info.get('marketCap') else None,
                'pe_ratio': info.get('trailingPE', None),
                'pb_ratio': info.get('priceToBook', None),
                'roe': info.get('returnOnEquity', None),
                'debt_to_equity': info.get('debtToEquity', None),
                'profit_margin': info.get('profitMargins', None),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
            }
            
            return fundamentals
        
        except Exception as e:
            return {
                'market_cap': None,
                'market_cap_cr': None,
                'pe_ratio': None,
                'pb_ratio': None,
                'roe': None,
                'debt_to_equity': None,
                'profit_margin': None,
                'sector': '',
                'industry': '',
            }
    
    def analyze_all_stocks(self, lookback_date=None, include_fundamentals=False):
        """
        Analyze all stocks in database
        Calculate all metrics for momentum screening
        
        Parameters:
        - lookback_date: Start date for analysis (default: 2 years ago)
        - include_fundamentals: Fetch fundamental data (slower)
        """
        if lookback_date is None:
            lookback_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        
        # Get all symbols
        cursor = self.conn.cursor()
        cursor.execute('SELECT symbol FROM stocks ORDER BY symbol')
        symbols = [row[0] for row in cursor.fetchall()]
        
        print(f"\n{'='*80}")
        print(f"ANALYZING {len(symbols)} STOCKS")
        print(f"Lookback Date: {lookback_date}")
        print(f"Include Fundamentals: {include_fundamentals}")
        print(f"{'='*80}\n")
        
        results = []
        success = 0
        failed = 0
        
        for i, symbol in enumerate(symbols, 1):
            try:
                print(f"[{i}/{len(symbols)}] {symbol}...", end=' ', flush=True)
                
                # Get price data
                df = self.get_stock_data(symbol, start_date=lookback_date)
                
                if df.empty or len(df) < 252:  # Need at least 1 year of data
                    print("✗ Insufficient data")
                    failed += 1
                    continue
                
                # Initialize result dictionary
                result = {'symbol': symbol}
                
                # Calculate returns
                returns = self.calculate_returns(df, periods=[21, 63, 126, 252])
                result.update(returns)
                
                # Calculate volatility
                volatility = self.calculate_volatility(df, periods=[63, 126, 252])
                result.update(volatility)
                
                # Calculate momentum score (12M-1M strategy)
                if result['252d_return'] is not None and result['21d_return'] is not None:
                    result['momentum_12m_1m'] = round(result['252d_return'] - result['21d_return'], 2)
                else:
                    result['momentum_12m_1m'] = None
                
                # Calculate composite momentum score
                # Weighted: 50% (12M-1M), 30% (6M), 20% (3M)

                ## Analyze : if one component is None, is ignorign it correct
                if all(result.get(k) is not None for k in ['momentum_12m_1m', '126d_return', '63d_return']):
                    result['momentum_score'] = round(
                        0.5 * result['momentum_12m_1m'] + 
                        0.3 * result['126d_return'] + 
                        0.2 * result['63d_return'], 
                        2
                    )
                else:
                    result['momentum_score'] = None
                
                # Calculate other metrics
                result['max_drawdown_1y'] = self.calculate_max_drawdown(df, 252)
                result['sharpe_ratio_1y'] = self.calculate_sharpe_ratio(df, 252)
                
                # Liquidity metrics
                liquidity = self.calculate_liquidity_metrics(df, 63)
                result.update(liquidity)
                
                # Current price
                result['current_price'] = round(df['Adj_Close'].iloc[-1], 2)
                result['last_date'] = df.index[-1].strftime('%Y-%m-%d')
                
                # Fundamentals (optional, slow)
                if include_fundamentals:
                    fundamentals = self.get_fundamental_data(symbol)
                    result.update(fundamentals)
                
                results.append(result)
                print("✓")
                success += 1
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:30]}")
                failed += 1
                continue
        
        print(f"\n{'='*80}")
        print(f"ANALYSIS COMPLETE")
        print(f"Success: {success} | Failed: {failed}")
        print(f"{'='*80}\n")
        
        # Convert to DataFrame
        df_results = pd.DataFrame(results)
        
        # Sort by momentum score
        if 'momentum_score' in df_results.columns:
            df_results = df_results.sort_values('momentum_score', ascending=False, na_position='last')
        
        return df_results.reset_index(drop=True)
    
    def filter_universe(self, df, **criteria):
        """
        Filter stocks based on various criteria
        
        Parameters (all optional):
        - min_market_cap_cr: Minimum market cap in crores
        - max_market_cap_cr: Maximum market cap in crores
        - min_volume: Minimum average daily volume
        - max_volatility: Maximum volatility %
        - min_momentum: Minimum momentum score
        - max_drawdown: Maximum acceptable drawdown %
        - sectors: List of sectors to include
        - exclude_sectors: List of sectors to exclude
        - min_sharpe: Minimum Sharpe ratio
        - max_zero_volume_days: Max days with zero volume
        """
        filtered = df.copy()
        initial_count = len(filtered)
        
        print(f"\n{'='*80}")
        print(f"FILTERING UNIVERSE")
        print(f"Initial stocks: {initial_count}")
        print(f"{'='*80}\n")
        
        # Market cap filters
        if 'min_market_cap_cr' in criteria and criteria['min_market_cap_cr'] is not None:
            if 'market_cap_cr' in filtered.columns:
                filtered = filtered[filtered['market_cap_cr'] >= criteria['min_market_cap_cr']]
                print(f"✓ Min Market Cap {criteria['min_market_cap_cr']}cr: {len(filtered)} stocks remain")
        
        if 'max_market_cap_cr' in criteria and criteria['max_market_cap_cr'] is not None:
            if 'market_cap_cr' in filtered.columns:
                filtered = filtered[filtered['market_cap_cr'] <= criteria['max_market_cap_cr']]
                print(f"✓ Max Market Cap {criteria['max_market_cap_cr']}cr: {len(filtered)} stocks remain")
        
        # Volume filter
        if 'min_volume' in criteria and criteria['min_volume'] is not None:
            if 'avg_volume_3m' in filtered.columns:
                filtered = filtered[filtered['avg_volume_3m'] >= criteria['min_volume']]
                print(f"✓ Min Volume {criteria['min_volume']:,}: {len(filtered)} stocks remain")
        
        # Volatility filter
        if 'max_volatility' in criteria and criteria['max_volatility'] is not None:
            if '126d_volatility' in filtered.columns:
                filtered = filtered[filtered['126d_volatility'] <= criteria['max_volatility']]
                print(f"✓ Max Volatility {criteria['max_volatility']}%: {len(filtered)} stocks remain")
        
        # Momentum filter
        if 'min_momentum' in criteria and criteria['min_momentum'] is not None:
            if 'momentum_score' in filtered.columns:
                filtered = filtered[filtered['momentum_score'] >= criteria['min_momentum']]
                print(f"✓ Min Momentum {criteria['min_momentum']}: {len(filtered)} stocks remain")
        
        # Drawdown filter
        if 'max_drawdown' in criteria and criteria['max_drawdown'] is not None:
            if 'max_drawdown_1y' in filtered.columns:
                filtered = filtered[filtered['max_drawdown_1y'] >= criteria['max_drawdown']]
                print(f"✓ Max Drawdown {criteria['max_drawdown']}%: {len(filtered)} stocks remain")
        
        # Sharpe ratio filter
        if 'min_sharpe' in criteria and criteria['min_sharpe'] is not None:
            if 'sharpe_ratio_1y' in filtered.columns:
                filtered = filtered[filtered['sharpe_ratio_1y'] >= criteria['min_sharpe']]
                print(f"✓ Min Sharpe {criteria['min_sharpe']}: {len(filtered)} stocks remain")
        
        # Zero volume days filter
        if 'max_zero_volume_days' in criteria and criteria['max_zero_volume_days'] is not None:
            if 'zero_volume_days_3m' in filtered.columns:
                filtered = filtered[filtered['zero_volume_days_3m'] <= criteria['max_zero_volume_days']]
                print(f"✓ Max Zero Volume Days {criteria['max_zero_volume_days']}: {len(filtered)} stocks remain")
        
        # Sector filters
        if 'sectors' in criteria and criteria['sectors']:
            if 'sector' in filtered.columns:
                filtered = filtered[filtered['sector'].isin(criteria['sectors'])]
                print(f"✓ Sectors {criteria['sectors']}: {len(filtered)} stocks remain")
        
        if 'exclude_sectors' in criteria and criteria['exclude_sectors']:
            if 'sector' in filtered.columns:
                filtered = filtered[~filtered['sector'].isin(criteria['exclude_sectors'])]
                print(f"✓ Exclude Sectors {criteria['exclude_sectors']}: {len(filtered)} stocks remain")
        
        print(f"\n{'='*80}")
        print(f"FILTERING COMPLETE")
        print(f"Initial: {initial_count} → Final: {len(filtered)} ({len(filtered)/initial_count*100:.1f}%)")
        print(f"{'='*80}\n")
        
        return filtered.reset_index(drop=True)
    
    ## analyze how to rewrite this function to be more generic as per criteria
    def select_top_stocks(self, df, n=20, method='momentum'):
        """
        Select top N stocks based on various methods
        
        Methods:
        - 'momentum': Top by momentum score
        - 'sharpe': Top by Sharpe ratio
        - 'balanced': Balance momentum and low volatility
        """
        if method == 'momentum':
            if 'momentum_score' in df.columns:
                return df.nlargest(n, 'momentum_score')
        
        elif method == 'sharpe':
            if 'sharpe_ratio_1y' in df.columns:
                return df.nlargest(n, 'sharpe_ratio_1y')
        
        elif method == 'balanced':
            # Create balanced score: momentum / volatility
            if 'momentum_score' in df.columns and '126d_volatility' in df.columns:
                df_copy = df.copy()
                df_copy['balanced_score'] = df_copy['momentum_score'] / df_copy['126d_volatility']
                return df_copy.nlargest(n, 'balanced_score')
        
        return df.head(n)
    
    def save_analysis_to_db(self, df):
        """Save analysis results to database for quick access"""
        # Create analysis table if it doesn't exist
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_analysis (
                symbol TEXT PRIMARY KEY,
                analysis_date TEXT,
                return_1m REAL,
                return_3m REAL,
                return_6m REAL,
                return_12m REAL,
                volatility_3m REAL,
                volatility_6m REAL,
                volatility_12m REAL,
                momentum_score REAL,
                momentum_12m_1m REAL,
                sharpe_ratio REAL,
                max_drawdown REAL,
                avg_volume REAL,
                current_price REAL
            )
        ''')
        
        # Insert data
        for _, row in df.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO stock_analysis
                (symbol, analysis_date, return_1m, return_3m, return_6m, return_12m,
                 volatility_3m, volatility_6m, volatility_12m, momentum_score, 
                 momentum_12m_1m, sharpe_ratio, max_drawdown, avg_volume, current_price)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                row.get('symbol'),
                datetime.now().strftime('%Y-%m-%d'),
                row.get('21d_return'),
                row.get('63d_return'),
                row.get('126d_return'),
                row.get('252d_return'),
                row.get('63d_volatility'),
                row.get('126d_volatility'),
                row.get('252d_volatility'),
                row.get('momentum_score'),
                row.get('momentum_12m_1m'),
                row.get('sharpe_ratio_1y'),
                row.get('max_drawdown_1y'),
                row.get('avg_volume_3m'),
                row.get('current_price')
            ))
        
        self.conn.commit()
        print(f"✓ Saved analysis for {len(df)} stocks to database")
    
    def export_to_csv(self, df, filename='stock_analysis.csv'):
        """Export analysis results to CSV"""
        df.to_csv(filename, index=False)
        print(f"✓ Exported {len(df)} stocks to {filename}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        print("✓ Database connection closed")


# Example Usage
if __name__ == "__main__":
    # Initialize analyzer
    analyzer = StockAnalyzer('indian_stocks.db')
    
    print("\n" + "="*80)
    print("STOCK ANALYSIS & FILTERING MODULE")
    print("="*80)
    
    # Step 1: Analyze all stocks
    print("\nStep 1: Analyzing all stocks...")
    print("Note: Set include_fundamentals=True for market cap, P/E etc (slower)")
    
    df_analysis = analyzer.analyze_all_stocks(
        lookback_date='2022-01-01',
        include_fundamentals=False  # Set True if you want fundamentals
    )
    
    print(f"\nAnalysis complete! {len(df_analysis)} stocks analyzed")
    print("\nTop 20 by Momentum Score:")
    print(df_analysis[['symbol', 'momentum_score', '252d_return', '126d_return', 
                       '63d_volatility', 'sharpe_ratio_1y']].head(20))
    
    # Step 2: Filter universe
    print("\n" + "="*80)
    print("Step 2: Filtering universe with criteria...")
    print("="*80)
    
    filtered = analyzer.filter_universe(
        df_analysis,
        # min_market_cap_cr=1000,      # Min 1000 cr market cap (enable if fundamentals fetched)
        min_volume=100000,              # Min 1 lakh daily volume
        max_volatility=60,              # Max 60% volatility
        min_momentum=10,                # Min 10% momentum score
        max_drawdown=-40,               # Max -40% drawdown acceptable
        min_sharpe=0.5,                 # Min Sharpe ratio 0.5
        max_zero_volume_days=5          # Max 5 days with zero volume
    )
    
    print(f"\nFiltered universe: {len(filtered)} stocks")
    
    # Step 3: Select top stocks
    print("\n" + "="*80)
    print("Step 3: Selecting top stocks...")
    print("="*80)
    
    top_momentum = analyzer.select_top_stocks(filtered, n=20, method='momentum')
    top_sharpe = analyzer.select_top_stocks(filtered, n=20, method='sharpe')
    top_balanced = analyzer.select_top_stocks(filtered, n=20, method='balanced')
    
    print("\nTop 20 by Momentum:")
    print(top_momentum[['symbol', 'momentum_score', '126d_volatility', 'current_price']].head(20))
    
    # Step 4: Save results
    print("\n" + "="*80)
    print("Step 4: Saving results...")
    print("="*80)
    
    # Save to database
    analyzer.save_analysis_to_db(df_analysis)
    
    # Export to CSV
    analyzer.export_to_csv(df_analysis, 'all_stocks_analysis.csv')
    analyzer.export_to_csv(filtered, 'filtered_universe.csv')
    analyzer.export_to_csv(top_momentum, 'top_momentum_stocks.csv')
    
    print("\n" + "="*80)
    print("✓ ANALYSIS MODULE COMPLETE!")
    print("="*80)
    print("\nFiles created:")
    print("1. all_stocks_analysis.csv - All analyzed stocks")
    print("2. filtered_universe.csv - Filtered universe")
    print("3. top_momentum_stocks.csv - Top 20 momentum stocks")
    print("\nNext step: Portfolio Construction Module")
    
    analyzer.close()