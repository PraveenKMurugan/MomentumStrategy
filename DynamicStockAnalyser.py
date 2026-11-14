"""
Dynamic Strategy Configuration System
Flexible configuration for stock analysis with customizable:
- Universe selection (Nifty 50, 500, custom lists)
- Performance periods (any combination)
- Volatility periods
- Custom weightages for scoring
- Filter criteria
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

class StrategyConfig:
    """
    Configuration class for dynamic strategy customization
    """
    
    def __init__(self, config_name="default"):
        """Initialize strategy configuration"""
        self.config_name = config_name
        self.universe = "NIFTY500"
        self.performance_periods = {}
        self.volatility_periods = {}
        self.filters = {}
        self.momentum_weights = {}
        
    def set_universe(self, universe_type, custom_symbols=None):
        """
        Set stock universe
        
        Parameters:
        - universe_type: 'NIFTY50', 'NIFTY500', 'NIFTY_MIDCAP', 'NIFTY_SMALLCAP', 
                        'ALL', 'CUSTOM'
        - custom_symbols: List of symbols if universe_type='CUSTOM'
        """
        self.universe = universe_type
        self.custom_symbols = custom_symbols
        return self
    
    def add_performance_period(self, name, days, weight=1.0):
        """
        Add a performance period for momentum calculation
        
        Parameters:
        - name: Identifier (e.g., '3M', '6M', '12M', '12M-1M')
        - days: Number of trading days (21=1M, 63=3M, 126=6M, 252=12M)
        - weight: Weight in final momentum score (default 1.0)
        
        Examples:
        config.add_performance_period('6M', 126, weight=0.5)
        config.add_performance_period('3M', 63, weight=0.3)
        """
        self.performance_periods[name] = {
            'days': days,
            'weight': weight
        }
        return self
    
    def add_volatility_period(self, name, days):
        """
        Add a volatility measurement period
        
        Parameters:
        - name: Identifier (e.g., '3M_vol', '6M_vol')
        - days: Number of trading days
        """
        self.volatility_periods[name] = days
        return self
    
    def set_momentum_weights(self, weights_dict):
        """
        Set custom weights for momentum scoring
        
        Example:
        config.set_momentum_weights({
            '6M': 0.5,
            '3M': 0.3,
            '1M': 0.2
        })
        """
        self.momentum_weights = weights_dict
        return self
    
    def add_filter(self, filter_name, **kwargs):
        """
        Add filter criteria
        
        Examples:
        config.add_filter('market_cap', min_value=1000)  # Min 1000cr
        config.add_filter('volume', min_value=100000)     # Min 100k daily
        config.add_filter('volatility', max_value=60)     # Max 60% vol
        config.add_filter('momentum', min_value=10)       # Min 10% momentum
        """
        self.filters[filter_name] = kwargs
        return self
    
    def to_dict(self):
        """Convert configuration to dictionary"""
        return {
            'config_name': self.config_name,
            'universe': self.universe,
            'custom_symbols': getattr(self, 'custom_symbols', None),
            'performance_periods': self.performance_periods,
            'volatility_periods': self.volatility_periods,
            'momentum_weights': self.momentum_weights,
            'filters': self.filters
        }
    
    def save(self, filename=None):
        """Save configuration to JSON file"""
        if filename is None:
            filename = f"strategy_config_{self.config_name}.json"
        
        with open(filename, 'w', encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        
        print(f"✓ Configuration saved to {filename}")
        return filename
    
    @classmethod
    def load(cls, filename):
        """Load configuration from JSON file"""
        with open(filename, 'r', encoding="utf-8") as f:
            data = json.load(f)
        
        config = cls(data['config_name'])
        config.universe = data['universe']
        config.custom_symbols = data.get('custom_symbols')
        config.performance_periods = data['performance_periods']
        config.volatility_periods = data['volatility_periods']
        config.momentum_weights = data['momentum_weights']
        config.filters = data['filters']
        
        return config
    
    def display(self):
        """Display configuration in readable format"""
        print(f"\n{'='*80}")
        print(f"STRATEGY CONFIGURATION: {self.config_name}")
        print(f"{'='*80}")
        
        print(f"\nUniverse: {self.universe}")
        if hasattr(self, 'custom_symbols') and self.custom_symbols:
            print(f"  Custom Symbols: {len(self.custom_symbols)} stocks")
        
        if self.performance_periods:
            print(f"\nPerformance Periods:")
            for name, config in self.performance_periods.items():
                print(f"  {name}: {config['days']} days (weight: {config['weight']})")
        
        if self.volatility_periods:
            print(f"\nVolatility Periods:")
            for name, days in self.volatility_periods.items():
                print(f"  {name}: {days} days")
        
        if self.momentum_weights:
            print(f"\nMomentum Weights:")
            for name, weight in self.momentum_weights.items():
                print(f"  {name}: {weight}")
        
        if self.filters:
            print(f"\nFilters:")
            for name, criteria in self.filters.items():
                print(f"  {name}: {criteria}")
        
        print(f"{'='*80}\n")


class DynamicStockAnalyzer:
    """
    Dynamic stock analyzer that uses StrategyConfig
    """
    
    def __init__(self, db_path='indian_stocks.db'):
        """Initialize analyzer"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.config = None
        print(f"✓ Dynamic Stock Analyzer initialized")
    
    def set_config(self, config):
        """Set the strategy configuration"""
        self.config = config
        return self
    
    def get_universe_symbols(self):
        """Get symbols based on configured universe"""
        cursor = self.conn.cursor()
        
        if self.config.universe == 'ALL':
            cursor.execute('SELECT symbol FROM stocks ORDER BY symbol')
            symbols = [row[0] for row in cursor.fetchall()]
        
        elif self.config.universe == 'CUSTOM':
            symbols = self.config.custom_symbols
        
        else:
            # For named indices, use predefined lists or database
            # You can expand this with actual Nifty 50/500 lists
            index_stocks = self._get_index_stocks(self.config.universe)
            symbols = index_stocks
        
        print(f"Universe '{self.config.universe}': {len(symbols)} stocks")
        return symbols
    
    def _get_index_stocks(self, index_name):
        """
        Get stocks for specific index
        You can load this from database or predefined lists
        """
        # Simplified - you can load actual Nifty 50/500 constituents
        cursor = self.conn.cursor()
        cursor.execute('SELECT symbol FROM stocks LIMIT 500')
        return [row[0] for row in cursor.fetchall()]
    
    def get_stock_data(self, symbol, start_date, end_date=None):
        """Retrieve stock data from database"""
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        query = '''
            SELECT date, adj_close, volume
            FROM price_data
            WHERE symbol = ? AND date >= ? AND date <= ?
            ORDER BY date
        '''
        
        df = pd.read_sql_query(query, self.conn, params=[symbol, start_date, end_date])
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.columns = ['price', 'volume']
        
        return df
    
    def calculate_metrics(self, symbol, as_of_date=None):
        """
        Calculate all configured metrics for a stock
        
        Parameters:
        - symbol: Stock symbol
        - as_of_date: Calculate metrics as of this date (default: latest)
        
        Returns: Dict with all calculated metrics
        """
        if as_of_date is None:
            as_of_date = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate lookback based on configured periods
        max_days = 252  # Start with 1 year minimum
        if self.config.performance_periods:
            max_days = max(max_days, max(p['days'] for p in self.config.performance_periods.values()))
        if self.config.volatility_periods:
            max_days = max(max_days, max(self.config.volatility_periods.values()))
        
        # Get data
        start_date = (datetime.strptime(as_of_date, '%Y-%m-%d') - timedelta(days=int(max_days * 1.5))).strftime('%Y-%m-%d')
        df = self.get_stock_data(symbol, start_date, as_of_date)
        
        if df.empty or len(df) < max_days:
            return None
        
        metrics = {'symbol': symbol}
        
        # Calculate performance metrics
        for name, config in self.config.performance_periods.items():
            days = config['days']
            if len(df) >= days:
                # Check if this is a differential return (e.g., 12M-1M)
                if '-' in name:
                    # Parse something like "12M-1M" -> 252 days - 21 days
                    parts = name.split('-')
                    # This is simplified - you can make it smarter
                    ret = (df['price'].iloc[-1] / df['price'].iloc[-days] - 1) * 100
                else:
                    ret = (df['price'].iloc[-1] / df['price'].iloc[-days] - 1) * 100
                
                metrics[f'{name}_return'] = round(ret, 2)
                metrics[f'{name}_weight'] = config['weight']
        
        # Calculate volatility metrics
        for name, days in self.config.volatility_periods.items():
            if len(df) >= days:
                returns = df['price'].pct_change().dropna()
                vol = returns.tail(days).std() * np.sqrt(252) * 100
                metrics[f'{name}_volatility'] = round(vol, 2)
        
        # Calculate composite momentum score using configured weights
        if self.config.momentum_weights:
            momentum_score = 0
            total_weight = 0
            
            for period_name, weight in self.config.momentum_weights.items():
                return_key = f'{period_name}_return'
                if return_key in metrics:
                    momentum_score += metrics[return_key] * weight
                    total_weight += weight
            
            if total_weight > 0:
                metrics['momentum_score'] = round(momentum_score, 2)
        
        # Calculate liquidity metrics
        if len(df) >= 63:
            metrics['avg_volume'] = int(df['volume'].tail(63).mean())
            metrics['avg_turnover'] = round((df['volume'] * df['price']).tail(63).mean(), 2)
        
        # Current price
        metrics['current_price'] = round(df['price'].iloc[-1], 2)
        metrics['calculation_date'] = as_of_date
        
        return metrics
    
    def analyze_universe(self, as_of_date=None, show_progress=True):
        """
        Analyze entire configured universe
        
        Returns: DataFrame with all metrics for all stocks
        """
        if self.config is None:
            raise ValueError("No configuration set. Use set_config() first.")
        
        symbols = self.get_universe_symbols()
        
        print(f"\n{'='*80}")
        print(f"ANALYZING UNIVERSE: {self.config.config_name}")
        print(f"Stocks: {len(symbols)}")
        print(f"{'='*80}\n")
        
        results = []
        success = 0
        failed = 0
        
        for i, symbol in enumerate(symbols, 1):
            if show_progress:
                print(f"[{i}/{len(symbols)}] {symbol}...", end=' ', flush=True)
            
            metrics = self.calculate_metrics(symbol, as_of_date)
            
            if metrics:
                results.append(metrics)
                if show_progress:
                    print("✓")
                success += 1
            else:
                if show_progress:
                    print("✗")
                failed += 1
        
        print(f"\n{'='*80}")
        print(f"Analysis Complete: {success} success, {failed} failed")
        print(f"{'='*80}\n")
        
        df = pd.DataFrame(results)
        
        # Sort by momentum score if available
        if 'momentum_score' in df.columns:
            df = df.sort_values('momentum_score', ascending=False)
        
        return df.reset_index(drop=True)
    
    def apply_filters(self, df):
        """Apply configured filters to analysis results"""
        filtered = df.copy()
        initial_count = len(filtered)
        
        print(f"\n{'='*80}")
        print(f"APPLYING FILTERS")
        print(f"Initial stocks: {initial_count}")
        print(f"{'='*80}\n")
        
        for filter_name, criteria in self.config.filters.items():
            # Volume filter
            if filter_name == 'volume':
                if 'min_value' in criteria and 'avg_volume' in filtered.columns:
                    filtered = filtered[filtered['avg_volume'] >= criteria['min_value']]
                    print(f"✓ Volume >= {criteria['min_value']:,}: {len(filtered)} remain")
            
            # Volatility filter
            elif filter_name == 'volatility':
                vol_cols = [col for col in filtered.columns if 'volatility' in col]
                if vol_cols and 'max_value' in criteria:
                    # Use first volatility column
                    filtered = filtered[filtered[vol_cols[0]] <= criteria['max_value']]
                    print(f"✓ Volatility <= {criteria['max_value']}%: {len(filtered)} remain")
            
            # Momentum filter
            elif filter_name == 'momentum':
                if 'min_value' in criteria and 'momentum_score' in filtered.columns:
                    filtered = filtered[filtered['momentum_score'] >= criteria['min_value']]
                    print(f"✓ Momentum >= {criteria['min_value']}: {len(filtered)} remain")
            
            # Market cap filter (if you have this data)
            elif filter_name == 'market_cap':
                if 'min_value' in criteria and 'market_cap_cr' in filtered.columns:
                    filtered = filtered[filtered['market_cap_cr'] >= criteria['min_value']]
                    print(f"✓ Market Cap >= {criteria['min_value']}cr: {len(filtered)} remain")
        
        print(f"\n{'='*80}")
        print(f"FILTERING COMPLETE")
        print(f"Initial: {initial_count} → Final: {len(filtered)} ({len(filtered)/initial_count*100:.1f}%)")
        print(f"{'='*80}\n")
        
        return filtered.reset_index(drop=True)
    
    def display_results(self, df, top_n=20):
        """Display analysis results in formatted table"""
        display_df = df.head(top_n).copy()
        
        print(f"\n{'='*80}")
        print(f"TOP {top_n} STOCKS BY MOMENTUM SCORE")
        print(f"{'='*80}")
        
        # Select columns to display
        display_cols = ['symbol']
        
        # Add return columns
        return_cols = [col for col in display_df.columns if '_return' in col and '_weight' not in col]
        display_cols.extend(return_cols)
        
        # Add volatility columns
        vol_cols = [col for col in display_df.columns if 'volatility' in col]
        display_cols.extend(vol_cols)
        
        # Add momentum score
        if 'momentum_score' in display_df.columns:
            display_cols.append('momentum_score')
        
        # Add current price
        if 'current_price' in display_df.columns:
            display_cols.append('current_price')
        
        # Display
        print(display_df[display_cols].to_string(index=False))
        print(f"{'='*80}\n")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


# Pre-defined strategy configurations
class PresetStrategies:
    """Common strategy presets"""
    
    @staticmethod
    def classic_momentum():
        """
        Classic momentum: 12M-1M return
        """
        config = StrategyConfig("Classic_Momentum")
        config.set_universe("NIFTY500")
        config.add_performance_period('12M', 252, weight=1.0)
        config.add_performance_period('1M', 21, weight=-1.0)  # Subtract 1M
        config.add_volatility_period('6M_vol', 126)
        config.set_momentum_weights({'12M': 1.0, '1M': -1.0})
        config.add_filter('volume', min_value=100000)
        config.add_filter('volatility', max_value=60)
        return config
    
    @staticmethod
    def short_term_momentum():
        """
        Short-term: 6M + 3M momentum
        """
        config = StrategyConfig("Short_Term_Momentum")
        config.set_universe("NIFTY500")
        config.add_performance_period('6M', 126, weight=0.6)
        config.add_performance_period('3M', 63, weight=0.4)
        config.add_volatility_period('3M_vol', 63)
        config.set_momentum_weights({'6M': 0.6, '3M': 0.4})
        config.add_filter('volume', min_value=100000)
        config.add_filter('volatility', max_value=50)
        return config
    
    @staticmethod
    def balanced_momentum():
        """
        Balanced: 12M, 6M, 3M weighted
        """
        config = StrategyConfig("Balanced_Momentum")
        config.set_universe("NIFTY500")
        config.add_performance_period('12M', 252, weight=0.5)
        config.add_performance_period('6M', 126, weight=0.3)
        config.add_performance_period('3M', 63, weight=0.2)
        config.add_volatility_period('6M_vol', 126)
        config.set_momentum_weights({'12M': 0.5, '6M': 0.3, '3M': 0.2})
        config.add_filter('volume', min_value=100000)
        config.add_filter('volatility', max_value=60)
        config.add_filter('momentum', min_value=10)
        return config
    
    @staticmethod
    def conservative():
        """
        Conservative: Lower volatility, blue chips
        """
        config = StrategyConfig("Conservative")
        config.set_universe("NIFTY50")
        config.add_performance_period('12M', 252, weight=0.6)
        config.add_performance_period('6M', 126, weight=0.4)
        config.add_volatility_period('6M_vol', 126)
        config.set_momentum_weights({'12M': 0.6, '6M': 0.4})
        config.add_filter('volume', min_value=500000)
        config.add_filter('volatility', max_value=40)
        config.add_filter('momentum', min_value=5)
        return config


# Example Usage
if __name__ == "__main__":
    print("\n" + "="*80)
    print("DYNAMIC STRATEGY CONFIGURATION SYSTEM")
    print("="*80)
    
    # Example 1: Use preset strategy
    print("\n--- EXAMPLE 1: PRESET STRATEGY ---")
    config1 = PresetStrategies.balanced_momentum()
    config1.display()
    config1.save()
    
    # Example 2: Custom strategy - Your specific example
    print("\n--- EXAMPLE 2: CUSTOM STRATEGY (6M + 3M) ---")
    config2 = StrategyConfig("Custom_6M_3M")
    config2.set_universe("NIFTY500")
    config2.add_performance_period('6M', 126, weight=0.6)
    config2.add_performance_period('3M', 63, weight=0.4)
    config2.add_volatility_period('3M_vol', 63)
    config2.set_momentum_weights({'6M': 0.6, '3M': 0.4})
    config2.add_filter('volume', min_value=100000)
    config2.add_filter('volatility', max_value=55)
    config2.add_filter('momentum', min_value=8)
    config2.display()
    config2.save()
    
    # Example 3: Another custom strategy - 6M only
    print("\n--- EXAMPLE 3: SIMPLE 6M MOMENTUM ---")
    config3 = StrategyConfig("Simple_6M")
    config3.set_universe("NIFTY500")
    config3.add_performance_period('6M', 126, weight=1.0)
    config3.add_volatility_period('6M_vol', 126)
    config3.set_momentum_weights({'6M': 1.0})
    config3.add_filter('volume', min_value=50000)
    config3.add_filter('volatility', max_value=70)
    config3.display()
    
    # Example 4: Analyze with dynamic config
    print("\n--- EXAMPLE 4: RUN ANALYSIS ---")
    
    analyzer = DynamicStockAnalyzer('indian_stocks.db')
    analyzer.set_config(config2)  # Use the 6M+3M config
    
    # Analyze universe
    results = analyzer.analyze_universe()
    
    # Apply filters
    filtered_results = analyzer.apply_filters(results)
    
    # Display top stocks
    analyzer.display_results(filtered_results, top_n=20)
    
    # Export results
    filtered_results.to_csv('dynamic_analysis_results.csv', index=False)
    print("✓ Results exported to dynamic_analysis_results.csv")
    
    # Example 5: Compare multiple strategies
    print("\n--- EXAMPLE 5: COMPARE STRATEGIES ---")
    
    strategies = {
        'Classic': PresetStrategies.classic_momentum(),
        'Short Term': PresetStrategies.short_term_momentum(),
        'Balanced': PresetStrategies.balanced_momentum()
    }
    
    comparison_results = {}
    
    for name, config in strategies.items():
        print(f"\nAnalyzing strategy: {name}")
        analyzer.set_config(config)
        results = analyzer.analyze_universe(show_progress=False)
        filtered = analyzer.apply_filters(results)
        
        comparison_results[name] = {
            'total_stocks': len(results),
            'filtered_stocks': len(filtered),
            'top_10_avg_momentum': filtered.head(10)['momentum_score'].mean() if 'momentum_score' in filtered.columns else 0
        }
    
    print(f"\n{'='*80}")
    print(f"STRATEGY COMPARISON")
    print(f"{'='*80}")
    print(f"{'Strategy':<20} {'Total':>10} {'Filtered':>10} {'Top 10 Avg':>15}")
    print(f"{'-'*80}")
    for name, metrics in comparison_results.items():
        print(f"{name:<20} {metrics['total_stocks']:>10} {metrics['filtered_stocks']:>10} "
              f"{metrics['top_10_avg_momentum']:>15.2f}")
    print(f"{'='*80}\n")
    
    analyzer.close()
    
    print("\n" + "="*80)
    print("✓ DYNAMIC CONFIGURATION SYSTEM READY!")
    print("="*80)
    print("\nYou can now:")
    print("1. Create unlimited custom strategies")
    print("2. Mix any performance periods with any weights")
    print("3. Apply any combination of filters")
    print("4. Save/load strategies as JSON")
    print("5. Compare multiple strategies")
    print("6. Backtest each configuration separately")
    print("="*80)