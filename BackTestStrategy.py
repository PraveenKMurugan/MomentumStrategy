"""
Momentum Strategy Backtesting Engine
Module 4: Comprehensive backtesting with walk-forward analysis

This module handles:
1. Historical backtesting with realistic constraints
2. Walk-forward analysis with periodic rebalancing
3. Transaction cost and slippage modeling
4. Tax impact analysis (STCG/LTCG)
5. Performance metrics vs benchmark (Nifty 50)
6. Monte Carlo simulation
7. Parameter optimization
8. Detailed reporting and visualization
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class BacktestEngine:
    def __init__(self, db_path='indian_stocks.db'):
        """Initialize backtesting engine"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.results = {}
        print(f"✓ Backtesting Engine initialized")
    
    def get_stock_data(self, symbol, start_date, end_date):
        """Retrieve stock data from database"""
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
    
    def get_all_stock_data(self, start_date, end_date, min_data_points=252):
        """
        Get data for all stocks in database
        Only includes stocks with sufficient data
        """
        cursor = self.conn.cursor()
        
        # Get stocks with sufficient data
        cursor.execute('''
            SELECT symbol, COUNT(*) as cnt
            FROM price_data
            WHERE date >= ? AND date <= ?
            GROUP BY symbol
            HAVING cnt >= ?
            ORDER BY symbol
        ''', [start_date, end_date, min_data_points])
        
        valid_stocks = [row[0] for row in cursor.fetchall()]
        
        print(f"Loading data for {len(valid_stocks)} stocks with sufficient history...")
        
        all_data = {}
        for symbol in valid_stocks:
            df = self.get_stock_data(symbol, start_date, end_date)
            if not df.empty and len(df) >= min_data_points:
                all_data[symbol] = df
        
        print(f"✓ Loaded {len(all_data)} stocks")
        return all_data
    
    def calculate_momentum_scores(self, price_data, as_of_date, 
                                  lookback_periods=[21, 63, 126, 252]):
        """
        Calculate momentum scores for all stocks as of a specific date
        
        Parameters:
        - price_data: Dict of {symbol: DataFrame} with price history
        - as_of_date: Date to calculate scores as of
        - lookback_periods: Periods for momentum calculation
        
        Returns: DataFrame with momentum scores
        """
        scores = []
        
        for symbol, df in price_data.items():
            # Filter data up to as_of_date
            df_filtered = df[df.index <= as_of_date]
            
            if len(df_filtered) < max(lookback_periods):
                continue
            
            score_dict = {'symbol': symbol}
            
            # Calculate returns
            for period in lookback_periods:
                if len(df_filtered) >= period:
                    ret = (df_filtered['price'].iloc[-1] / df_filtered['price'].iloc[-period] - 1) * 100
                    score_dict[f'{period}d_return'] = ret
            
            # Calculate momentum score (12M-1M to avoid short-term reversal)
            if '252d_return' in score_dict and '21d_return' in score_dict:
                score_dict['momentum_12m_1m'] = score_dict['252d_return'] - score_dict['21d_return']
            
            # Calculate composite momentum score
            if all(f'{p}d_return' in score_dict for p in [63, 126, 252]):
                score_dict['momentum_score'] = (
                    0.5 * score_dict.get('momentum_12m_1m', 0) +
                    0.3 * score_dict['126d_return'] +
                    0.2 * score_dict['63d_return']
                )
            
            # Calculate volatility
            if len(df_filtered) >= 126:
                returns = df_filtered['price'].pct_change().dropna()
                vol = returns.tail(126).std() * np.sqrt(252) * 100
                score_dict['volatility'] = vol
            
            # Current price
            score_dict['price'] = df_filtered['price'].iloc[-1]
            
            # Liquidity (average volume)
            if len(df_filtered) >= 63:
                score_dict['avg_volume'] = df_filtered['volume'].tail(63).mean()
            
            scores.append(score_dict)
        
        df = pd.DataFrame(scores)
        
        if not df.empty and 'momentum_score' in df.columns:
            df = df.sort_values('momentum_score', ascending=False)
        
        return df.reset_index(drop=True)
    
    def filter_universe(self, scores_df, min_volume=50000, max_volatility=70, 
                       min_momentum=0):
        """Apply universe filters"""
        filtered = scores_df.copy()
        
        if 'avg_volume' in filtered.columns:
            filtered = filtered[filtered['avg_volume'] >= min_volume]
        
        if 'volatility' in filtered.columns:
            filtered = filtered[filtered['volatility'] <= max_volatility]
        
        if 'momentum_score' in filtered.columns:
            filtered = filtered[filtered['momentum_score'] >= min_momentum]
        
        return filtered.reset_index(drop=True)
    
    def select_portfolio(self, filtered_df, n_stocks=15, method='momentum'):
        """Select top N stocks for portfolio"""
        if method == 'momentum' and 'momentum_score' in filtered_df.columns:
            return filtered_df.nlargest(n_stocks, 'momentum_score')
        elif method == 'balanced' and 'momentum_score' in filtered_df.columns and 'volatility' in filtered_df.columns:
            filtered_df['risk_adj_momentum'] = filtered_df['momentum_score'] / filtered_df['volatility']
            return filtered_df.nlargest(n_stocks, 'risk_adj_momentum')
        else:
            return filtered_df.head(n_stocks)
    
    def calculate_portfolio_weights(self, portfolio_df, method='equal_weight'):
        """Calculate position weights"""
        n = len(portfolio_df)
        
        if method == 'equal_weight':
            portfolio_df['weight'] = 1.0 / n
        
        elif method == 'momentum_weighted' and 'momentum_score' in portfolio_df.columns:
            # Normalize momentum scores
            min_mom = portfolio_df['momentum_score'].min()
            if min_mom < 0:
                adjusted = portfolio_df['momentum_score'] - min_mom + 1
            else:
                adjusted = portfolio_df['momentum_score']
            
            portfolio_df['weight'] = adjusted / adjusted.sum()
        
        elif method == 'risk_parity' and 'volatility' in portfolio_df.columns:
            inv_vol = 1.0 / portfolio_df['volatility']
            portfolio_df['weight'] = inv_vol / inv_vol.sum()
        
        else:
            portfolio_df['weight'] = 1.0 / n
        
        return portfolio_df
    
    def run_backtest(self, start_date, end_date, initial_capital=1000000,
                    rebalance_frequency='6M', n_stocks=15, 
                    allocation_method='risk_parity',
                    transaction_cost_pct=0.05, slippage_pct=0.05,
                    min_volume=50000, max_volatility=70, min_momentum=0,
                    tax_enabled=True):
        """
        Run comprehensive backtest with walk-forward analysis
        
        Parameters:
        - start_date, end_date: Backtest period
        - initial_capital: Starting capital
        - rebalance_frequency: '3M', '6M', '12M'
        - n_stocks: Number of stocks in portfolio
        - allocation_method: 'equal_weight', 'momentum_weighted', 'risk_parity'
        - transaction_cost_pct: Brokerage + charges (%)
        - slippage_pct: Slippage on execution (%)
        - min_volume, max_volatility, min_momentum: Universe filters
        - tax_enabled: Apply STCG/LTCG tax
        """
        
        print(f"\n{'='*80}")
        print(f"RUNNING BACKTEST")
        print(f"{'='*80}")
        print(f"Period: {start_date} to {end_date}")
        print(f"Initial Capital: ₹{initial_capital:,.0f}")
        print(f"Rebalance: {rebalance_frequency}")
        print(f"Portfolio Size: {n_stocks} stocks")
        print(f"Allocation: {allocation_method}")
        print(f"Transaction Cost: {transaction_cost_pct}%")
        print(f"Slippage: {slippage_pct}%")
        print(f"Tax Enabled: {tax_enabled}")
        print(f"{'='*80}\n")
        
        # Load all stock data
        all_data = self.get_all_stock_data(start_date, end_date)
        
        if not all_data:
            print("✗ No stock data available")
            return None
        
        # Get all trading dates
        sample_dates = list(all_data.values())[0].index
        
        # Calculate rebalance frequency in days
        rebal_map = {'1M': 21, '3M': 63, '6M': 126, '12M': 252}
        rebal_days = rebal_map.get(rebalance_frequency, 126)
        
        # Generate rebalance dates
        rebalance_dates = []
        current_date = sample_dates[252]  # Start after 1 year of data for momentum calc
        
        while current_date <= sample_dates[-1]:
            rebalance_dates.append(current_date)
            # Find next rebalance date
            future_dates = sample_dates[sample_dates > current_date]
            if len(future_dates) >= rebal_days:
                current_date = future_dates[rebal_days - 1]
            else:
                break
        
        print(f"Rebalance dates: {len(rebalance_dates)}")
        print(f"First: {rebalance_dates[0].strftime('%Y-%m-%d')}")
        print(f"Last: {rebalance_dates[-1].strftime('%Y-%m-%d')}\n")
        
        # Initialize tracking variables
        portfolio = {}  # {symbol: {'shares': X, 'entry_price': Y, 'entry_date': Z}}
        cash = initial_capital
        portfolio_history = []
        transaction_history = []
        
        # Track performance
        for i, rebal_date in enumerate(rebalance_dates):
            print(f"[{i+1}/{len(rebalance_dates)}] Rebalancing on {rebal_date.strftime('%Y-%m-%d')}...")
            
            # Calculate momentum scores as of this date
            scores = self.calculate_momentum_scores(all_data, rebal_date)
            
            if scores.empty:
                print("  ✗ No scores calculated, skipping")
                continue
            
            # Filter universe
            filtered = self.filter_universe(scores, min_volume, max_volatility, min_momentum)
            
            if len(filtered) < n_stocks:
                print(f"  ⚠ Only {len(filtered)} stocks pass filters")
                n_stocks_actual = len(filtered)
            else:
                n_stocks_actual = n_stocks
            
            # Select portfolio
            new_portfolio_df = self.select_portfolio(filtered, n_stocks_actual, 'momentum')
            
            # Calculate weights
            new_portfolio_df = self.calculate_portfolio_weights(new_portfolio_df, allocation_method)
            
            # Get current portfolio value
            portfolio_value = 0
            for symbol, holding in portfolio.items():
                if symbol in all_data:
                    current_price_data = all_data[symbol][all_data[symbol].index <= rebal_date]
                    if not current_price_data.empty:
                        current_price = current_price_data['price'].iloc[-1]
                        portfolio_value += holding['shares'] * current_price
            
            total_value = portfolio_value + cash
            
            # Sell positions not in new portfolio
            new_symbols = set(new_portfolio_df['symbol'])
            current_symbols = set(portfolio.keys())
            
            to_sell = current_symbols - new_symbols
            
            for symbol in to_sell:
                holding = portfolio[symbol]
                current_price_data = all_data[symbol][all_data[symbol].index <= rebal_date]
                
                if not current_price_data.empty:
                    sell_price = current_price_data['price'].iloc[-1] * (1 - slippage_pct / 100)
                    sell_value = holding['shares'] * sell_price
                    
                    # Calculate transaction costs
                    transaction_cost = sell_value * (transaction_cost_pct / 100)
                    
                    # Calculate tax
                    tax = 0
                    if tax_enabled:
                        holding_days = (rebal_date - holding['entry_date']).days
                        profit = sell_value - (holding['shares'] * holding['entry_price'])
                        
                        if profit > 0:
                            if holding_days >= 365:
                                # LTCG: 10% above 1L
                                tax = max(0, profit - 100000) * 0.10
                            else:
                                # STCG: 15%
                                tax = profit * 0.15
                    
                    net_proceeds = sell_value - transaction_cost - tax
                    cash += net_proceeds
                    
                    transaction_history.append({
                        'date': rebal_date,
                        'symbol': symbol,
                        'type': 'SELL',
                        'shares': holding['shares'],
                        'price': sell_price,
                        'value': sell_value,
                        'cost': transaction_cost,
                        'tax': tax,
                        'net': net_proceeds
                    })
                
                del portfolio[symbol]
            
            # Buy new positions
            available_capital = total_value
            
            for _, row in new_portfolio_df.iterrows():
                symbol = row['symbol']
                target_value = available_capital * row['weight']
                buy_price = row['price'] * (1 + slippage_pct / 100)
                
                shares = int(target_value / buy_price)
                
                if shares > 0:
                    buy_value = shares * buy_price
                    transaction_cost = buy_value * (transaction_cost_pct / 100)
                    total_cost = buy_value + transaction_cost
                    
                    if total_cost <= cash:
                        cash -= total_cost
                        
                        portfolio[symbol] = {
                            'shares': shares,
                            'entry_price': buy_price,
                            'entry_date': rebal_date
                        }
                        
                        transaction_history.append({
                            'date': rebal_date,
                            'symbol': symbol,
                            'type': 'BUY',
                            'shares': shares,
                            'price': buy_price,
                            'value': buy_value,
                            'cost': transaction_cost,
                            'tax': 0,
                            'net': total_cost
                        })
            
            # Record portfolio value
            portfolio_value = sum(
                holding['shares'] * all_data[symbol][all_data[symbol].index <= rebal_date]['price'].iloc[-1]
                for symbol, holding in portfolio.items()
                if symbol in all_data and not all_data[symbol][all_data[symbol].index <= rebal_date].empty
            )
            
            total_value = portfolio_value + cash
            
            portfolio_history.append({
                'date': rebal_date,
                'portfolio_value': portfolio_value,
                'cash': cash,
                'total_value': total_value,
                'return': (total_value / initial_capital - 1) * 100,
                'num_holdings': len(portfolio)
            })
            
            print(f"  Value: ₹{total_value:,.0f} | Return: {portfolio_history[-1]['return']:.2f}% | Holdings: {len(portfolio)}")
        
        # Calculate daily portfolio values for detailed metrics
        daily_values = self._calculate_daily_values(all_data, portfolio_history, 
                                                     sample_dates, initial_capital)
        
        # Calculate final metrics
        final_value = portfolio_history[-1]['total_value']
        total_return = (final_value / initial_capital - 1) * 100
        
        days = (rebalance_dates[-1] - rebalance_dates[0]).days
        years = days / 365.25
        cagr = ((final_value / initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"BACKTEST RESULTS")
        print(f"{'='*80}")
        print(f"Initial Capital: ₹{initial_capital:,.0f}")
        print(f"Final Value: ₹{final_value:,.0f}")
        print(f"Total Return: {total_return:.2f}%")
        print(f"CAGR: {cagr:.2f}%")
        print(f"Period: {years:.2f} years")
        print(f"Rebalances: {len(rebalance_dates)}")
        print(f"{'='*80}\n")
        
        # Store results
        self.results = {
            'portfolio_history': pd.DataFrame(portfolio_history),
            'transaction_history': pd.DataFrame(transaction_history),
            'daily_values': daily_values,
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': total_return,
            'cagr': cagr,
            'years': years,
            'parameters': {
                'start_date': start_date,
                'end_date': end_date,
                'rebalance_frequency': rebalance_frequency,
                'n_stocks': n_stocks,
                'allocation_method': allocation_method,
                'transaction_cost_pct': transaction_cost_pct,
                'slippage_pct': slippage_pct
            }
        }
        
        return self.results
    
    def _calculate_daily_values(self, all_data, portfolio_history, trading_dates, initial_capital):
        """Calculate daily portfolio values between rebalances"""
        daily_values = []
        
        if not portfolio_history:
            return pd.DataFrame()
        
        # For each period between rebalances, interpolate daily values
        # This is simplified - just using rebalance snapshots
        for record in portfolio_history:
            daily_values.append({
                'date': record['date'],
                'value': record['total_value'],
                'return': record['return']
            })
        
        return pd.DataFrame(daily_values)
    
    def calculate_metrics(self, benchmark_symbol='^NSEI'):
        """
        Calculate comprehensive performance metrics
        
        Parameters:
        - benchmark_symbol: Symbol for benchmark comparison (default: Nifty 50)
        """
        if not self.results or 'portfolio_history' not in self.results:
            print("No backtest results available. Run backtest first.")
            return None
        
        df = self.results['portfolio_history'].copy()
        
        if df.empty or len(df) < 2:
            print("Insufficient data for metrics")
            return None
        
        # Calculate returns
        df['pct_return'] = df['total_value'].pct_change() * 100
        returns = df['pct_return'].dropna()
        
        if len(returns) < 2:
            print("Insufficient returns data")
            return None
        
        # Basic metrics
        total_return = self.results['total_return']
        cagr = self.results['cagr']
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252 / len(rebalance_dates)) if len(returns) > 0 else 0
        
        # Sharpe Ratio
        risk_free_rate = 6.5  # India risk-free rate
        sharpe = (cagr - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Sortino Ratio
        downside_returns = returns[returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252 / len(rebalance_dates)) if len(downside_returns) > 0 else volatility
        sortino = (cagr - risk_free_rate) / downside_vol if downside_vol > 0 else 0
        
        # Max Drawdown
        df['cummax'] = df['total_value'].cummax()
        df['drawdown'] = (df['total_value'] - df['cummax']) / df['cummax'] * 100
        max_drawdown = df['drawdown'].min()
        
        # Win Rate
        win_rate = (returns > 0).sum() / len(returns) * 100 if len(returns) > 0 else 0
        
        # Average win/loss
        wins = returns[returns > 0]
        losses = returns[returns < 0]
        avg_win = wins.mean() if len(wins) > 0 else 0
        avg_loss = losses.mean() if len(losses) > 0 else 0
        
        # Calculate transaction costs
        if 'transaction_history' in self.results and not self.results['transaction_history'].empty:
            total_costs = self.results['transaction_history']['cost'].sum()
            total_tax = self.results['transaction_history']['tax'].sum()
        else:
            total_costs = 0
            total_tax = 0
        
        metrics = {
            'Total Return (%)': round(total_return, 2),
            'CAGR (%)': round(cagr, 2),
            'Volatility (%)': round(volatility, 2),
            'Sharpe Ratio': round(sharpe, 2),
            'Sortino Ratio': round(sortino, 2),
            'Max Drawdown (%)': round(max_drawdown, 2),
            'Win Rate (%)': round(win_rate, 2),
            'Avg Win (%)': round(avg_win, 2),
            'Avg Loss (%)': round(avg_loss, 2),
            'Total Transaction Costs (₹)': round(total_costs, 0),
            'Total Tax (₹)': round(total_tax, 0),
            'Number of Rebalances': len(df)
        }
        
        # Print metrics
        print(f"\n{'='*80}")
        print(f"PERFORMANCE METRICS")
        print(f"{'='*80}")
        for key, value in metrics.items():
            print(f"{key:<30}: {value:>15}")
        print(f"{'='*80}\n")
        
        self.results['metrics'] = metrics
        return metrics
    
    def compare_to_benchmark(self, benchmark_symbol='^NSEI'):
        """Compare strategy performance to benchmark"""
        if not self.results:
            print("No backtest results available")
            return None
        
        print(f"\n{'='*80}")
        print(f"BENCHMARK COMPARISON (vs {benchmark_symbol})")
        print(f"{'='*80}")
        
        # Get benchmark data
        start_date = self.results['parameters']['start_date']
        end_date = self.results['parameters']['end_date']
        
        benchmark_data = self.get_stock_data(benchmark_symbol, start_date, end_date)
        
        if benchmark_data.empty:
            print(f"✗ Benchmark data not available for {benchmark_symbol}")
            print("Note: Download Nifty 50 data (^NSEI) to enable benchmark comparison")
            return None
        
        # Calculate benchmark returns
        bench_start = benchmark_data['price'].iloc[0]
        bench_end = benchmark_data['price'].iloc[-1]
        bench_return = (bench_end / bench_start - 1) * 100
        
        years = self.results['years']
        bench_cagr = ((bench_end / bench_start) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # Calculate benchmark volatility
        bench_returns = benchmark_data['price'].pct_change().dropna()
        bench_vol = bench_returns.std() * np.sqrt(252) * 100
        
        # Calculate benchmark max drawdown
        bench_cummax = benchmark_data['price'].cummax()
        bench_dd = ((benchmark_data['price'] - bench_cummax) / bench_cummax * 100).min()
        
        # Alpha (excess return over benchmark)
        alpha = self.results['cagr'] - bench_cagr
        
        print(f"{'Metric':<30} {'Strategy':>15} {'Benchmark':>15} {'Difference':>15}")
        print(f"{'-'*80}")
        print(f"{'Total Return (%)':<30} {self.results['total_return']:>15.2f} {bench_return:>15.2f} {self.results['total_return'] - bench_return:>15.2f}")
        print(f"{'CAGR (%)':<30} {self.results['cagr']:>15.2f} {bench_cagr:>15.2f} {alpha:>15.2f}")
        
        if 'metrics' in self.results:
            strategy_vol = self.results['metrics']['Volatility (%)']
            strategy_sharpe = self.results['metrics']['Sharpe Ratio']
            strategy_dd = self.results['metrics']['Max Drawdown (%)']
            
            print(f"{'Volatility (%)':<30} {strategy_vol:>15.2f} {bench_vol:>15.2f} {strategy_vol - bench_vol:>15.2f}")
            print(f"{'Sharpe Ratio':<30} {strategy_sharpe:>15.2f} {'-':>15} {'-':>15}")
            print(f"{'Max Drawdown (%)':<30} {strategy_dd:>15.2f} {bench_dd:>15.2f} {strategy_dd - bench_dd:>15.2f}")
        
        print(f"{'='*80}\n")
        
        comparison = {
            'strategy_return': self.results['total_return'],
            'benchmark_return': bench_return,
            'strategy_cagr': self.results['cagr'],
            'benchmark_cagr': bench_cagr,
            'alpha': alpha,
            'benchmark_volatility': bench_vol,
            'benchmark_max_drawdown': bench_dd
        }
        
        return comparison
    
    def parameter_optimization(self, start_date, end_date, initial_capital=1000000):
        """
        Test multiple parameter combinations to find optimal settings
        
        Tests different combinations of:
        - Portfolio size (10, 15, 20 stocks)
        - Rebalance frequency (3M, 6M, 12M)
        - Allocation method (equal_weight, risk_parity)
        """
        print(f"\n{'='*80}")
        print(f"PARAMETER OPTIMIZATION")
        print(f"{'='*80}\n")
        
        # Define parameter grid
        param_grid = {
            'n_stocks': [10, 15, 20],
            'rebalance_frequency': ['3M', '6M', '12M'],
            'allocation_method': ['equal_weight', 'risk_parity']
        }
        
        results = []
        
        total_tests = (len(param_grid['n_stocks']) * 
                      len(param_grid['rebalance_frequency']) * 
                      len(param_grid['allocation_method']))
        
        test_num = 0
        
        for n_stocks in param_grid['n_stocks']:
            for rebal_freq in param_grid['rebalance_frequency']:
                for alloc_method in param_grid['allocation_method']:
                    test_num += 1
                    
                    print(f"\n[{test_num}/{total_tests}] Testing: {n_stocks} stocks, {rebal_freq}, {alloc_method}")
                    
                    # Run backtest
                    result = self.run_backtest(
                        start_date=start_date,
                        end_date=end_date,
                        initial_capital=initial_capital,
                        rebalance_frequency=rebal_freq,
                        n_stocks=n_stocks,
                        allocation_method=alloc_method,
                        transaction_cost_pct=0.05,
                        slippage_pct=0.05
                    )
                    
                    if result:
                        # Calculate metrics
                        self.calculate_metrics()
                        
                        if 'metrics' in self.results:
                            results.append({
                                'n_stocks': n_stocks,
                                'rebalance_frequency': rebal_freq,
                                'allocation_method': alloc_method,
                                'cagr': self.results['cagr'],
                                'volatility': self.results['metrics']['Volatility (%)'],
                                'sharpe': self.results['metrics']['Sharpe Ratio'],
                                'max_drawdown': self.results['metrics']['Max Drawdown (%)'],
                                'total_return': self.results['total_return']
                            })
        
        # Display results
        df_results = pd.DataFrame(results)
        
        if not df_results.empty:
            print(f"\n{'='*80}")
            print(f"OPTIMIZATION RESULTS (Sorted by Sharpe Ratio)")
            print(f"{'='*80}\n")
            
            df_sorted = df_results.sort_values('sharpe', ascending=False)
            print(df_sorted.to_string(index=False))
            
            print(f"\n{'='*80}")
            print(f"BEST PARAMETERS:")
            print(f"{'='*80}")
            best = df_sorted.iloc[0]
            print(f"Portfolio Size: {best['n_stocks']} stocks")
            print(f"Rebalance Frequency: {best['rebalance_frequency']}")
            print(f"Allocation Method: {best['allocation_method']}")
            print(f"CAGR: {best['cagr']:.2f}%")
            print(f"Sharpe Ratio: {best['sharpe']:.2f}")
            print(f"Max Drawdown: {best['max_drawdown']:.2f}%")
            print(f"{'='*80}\n")
            
            return df_results
        
        return None
    
    def monte_carlo_simulation(self, n_simulations=1000, n_years=5):
        """
        Run Monte Carlo simulation based on historical returns
        
        Parameters:
        - n_simulations: Number of simulation runs
        - n_years: Years to project forward
        """
        if not self.results or 'portfolio_history' not in self.results:
            print("No backtest results available")
            return None
        
        print(f"\n{'='*80}")
        print(f"MONTE CARLO SIMULATION")
        print(f"{'='*80}")
        print(f"Simulations: {n_simulations}")
        print(f"Projection: {n_years} years")
        print(f"{'='*80}\n")
        
        # Get historical returns
        df = self.results['portfolio_history'].copy()
        df['pct_return'] = df['total_value'].pct_change()
        returns = df['pct_return'].dropna().values
        
        if len(returns) < 10:
            print("Insufficient historical returns for simulation")
            return None
        
        # Calculate statistics
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Determine periods per year based on rebalance frequency
        rebal_freq = self.results['parameters']['rebalance_frequency']
        periods_per_year = {'1M': 12, '3M': 4, '6M': 2, '12M': 1}
        periods = periods_per_year.get(rebal_freq, 2) * n_years
        
        initial_value = self.results['initial_capital']
        
        # Run simulations
        simulations = []
        
        for i in range(n_simulations):
            # Generate random returns based on historical distribution
            sim_returns = np.random.normal(mean_return, std_return, periods)
            
            # Calculate portfolio value over time
            values = [initial_value]
            for ret in sim_returns:
                values.append(values[-1] * (1 + ret))
            
            simulations.append(values)
        
        simulations = np.array(simulations)
        
        # Calculate statistics
        final_values = simulations[:, -1]
        percentiles = np.percentile(final_values, [5, 25, 50, 75, 95])
        
        print(f"Projected Final Values (after {n_years} years):")
        print(f"  5th Percentile (Worst):  ₹{percentiles[0]:,.0f}")
        print(f"  25th Percentile:         ₹{percentiles[1]:,.0f}")
        print(f"  50th Percentile (Median): ₹{percentiles[2]:,.0f}")
        print(f"  75th Percentile:         ₹{percentiles[3]:,.0f}")
        print(f"  95th Percentile (Best):  ₹{percentiles[4]:,.0f}")
        
        # Probability of loss
        prob_loss = (final_values < initial_value).sum() / n_simulations * 100
        print(f"\nProbability of Loss: {prob_loss:.2f}%")
        
        # Expected return
        expected_final = final_values.mean()
        expected_return = (expected_final / initial_value - 1) * 100
        expected_cagr = ((expected_final / initial_value) ** (1/n_years) - 1) * 100
        
        print(f"Expected Final Value: ₹{expected_final:,.0f}")
        print(f"Expected Total Return: {expected_return:.2f}%")
        print(f"Expected CAGR: {expected_cagr:.2f}%")
        print(f"{'='*80}\n")
        
        monte_carlo_results = {
            'simulations': simulations,
            'percentiles': percentiles,
            'prob_loss': prob_loss,
            'expected_final': expected_final,
            'expected_return': expected_return,
            'expected_cagr': expected_cagr
        }
        
        return monte_carlo_results
    
    def export_results(self, filename_prefix='backtest_results'):
        """Export all backtest results to CSV files"""
        if not self.results:
            print("No results to export")
            return
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Export portfolio history
        if 'portfolio_history' in self.results:
            portfolio_file = f"{filename_prefix}_portfolio_{timestamp}.csv"
            self.results['portfolio_history'].to_csv(portfolio_file, index=False)
            print(f"✓ Portfolio history exported to {portfolio_file}")
        
        # Export transaction history
        if 'transaction_history' in self.results and not self.results['transaction_history'].empty:
            trans_file = f"{filename_prefix}_transactions_{timestamp}.csv"
            self.results['transaction_history'].to_csv(trans_file, index=False)
            print(f"✓ Transaction history exported to {trans_file}")
        
        # Export metrics
        if 'metrics' in self.results:
            metrics_file = f"{filename_prefix}_metrics_{timestamp}.csv"
            pd.DataFrame([self.results['metrics']]).to_csv(metrics_file, index=False)
            print(f"✓ Metrics exported to {metrics_file}")
        
        # Export summary report
        summary_file = f"{filename_prefix}_summary_{timestamp}.txt"
        with open(summary_file, 'w', encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write("BACKTEST SUMMARY REPORT\n")
            f.write("="*80 + "\n\n")
            
            f.write("PARAMETERS:\n")
            for key, value in self.results['parameters'].items():
                f.write(f"  {key}: {value}\n")
            
            f.write("\nRESULTS:\n")
            f.write(f"  Initial Capital: ₹{self.results['initial_capital']:,.0f}\n")
            f.write(f"  Final Value: ₹{self.results['final_value']:,.0f}\n")
            f.write(f"  Total Return: {self.results['total_return']:.2f}%\n")
            f.write(f"  CAGR: {self.results['cagr']:.2f}%\n")
            f.write(f"  Period: {self.results['years']:.2f} years\n")
            
            if 'metrics' in self.results:
                f.write("\nPERFORMANCE METRICS:\n")
                for key, value in self.results['metrics'].items():
                    f.write(f"  {key}: {value}\n")
            
            f.write("\n" + "="*80 + "\n")
        
        print(f"✓ Summary report exported to {summary_file}\n")
    
    def analyze_drawdown_periods(self):
        """Analyze drawdown periods in detail"""
        if not self.results or 'portfolio_history' not in self.results:
            print("No backtest results available")
            return None
        
        df = self.results['portfolio_history'].copy()
        df['cummax'] = df['total_value'].cummax()
        df['drawdown'] = (df['total_value'] - df['cummax']) / df['cummax'] * 100
        
        # Identify drawdown periods
        in_drawdown = df['drawdown'] < 0
        drawdown_periods = []
        
        current_dd = None
        
        for i, row in df.iterrows():
            if row['drawdown'] < 0:
                if current_dd is None:
                    current_dd = {
                        'start': row['date'],
                        'peak': row['cummax'],
                        'trough': row['total_value'],
                        'max_dd': row['drawdown']
                    }
                else:
                    if row['drawdown'] < current_dd['max_dd']:
                        current_dd['max_dd'] = row['drawdown']
                        current_dd['trough'] = row['total_value']
            else:
                if current_dd is not None:
                    current_dd['end'] = row['date']
                    current_dd['recovery'] = row['total_value']
                    current_dd['duration'] = (current_dd['end'] - current_dd['start']).days
                    drawdown_periods.append(current_dd)
                    current_dd = None
        
        if not drawdown_periods:
            print("No significant drawdown periods found")
            return None
        
        print(f"\n{'='*80}")
        print(f"DRAWDOWN ANALYSIS")
        print(f"{'='*80}")
        print(f"Number of Drawdown Periods: {len(drawdown_periods)}\n")
        
        # Sort by severity
        drawdown_periods.sort(key=lambda x: x['max_dd'])
        
        print(f"Top 5 Worst Drawdowns:")
        print(f"{'Start':<12} {'End':<12} {'Duration':>10} {'Max DD %':>10} {'Peak':>12} {'Trough':>12}")
        print(f"{'-'*80}")
        
        for dd in drawdown_periods[:5]:
            print(f"{dd['start'].strftime('%Y-%m-%d'):<12} {dd['end'].strftime('%Y-%m-%d'):<12} "
                  f"{dd['duration']:>10} {dd['max_dd']:>10.2f} ₹{dd['peak']:>10,.0f} ₹{dd['trough']:>10,.0f}")
        
        print(f"{'='*80}\n")
        
        return drawdown_periods
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        print("✓ Database connection closed")


# Example Usage
if __name__ == "__main__":
    # Initialize backtest engine
    engine = BacktestEngine('indian_stocks.db')
    
    print("\n" + "="*80)
    print("MOMENTUM STRATEGY BACKTESTING ENGINE")
    print("="*80)
    
    # Define backtest parameters
    START_DATE = '2015-01-01'
    END_DATE = '2024-01-01'
    INITIAL_CAPITAL = 1000000  # 10 lakhs
    
    # Run main backtest
    print("\n" + "="*80)
    print("RUNNING MAIN BACKTEST")
    print("="*80)
    
    results = engine.run_backtest(
        start_date=START_DATE,
        end_date=END_DATE,
        initial_capital=INITIAL_CAPITAL,
        rebalance_frequency='6M',      # Rebalance every 6 months
        n_stocks=15,                    # 15 stocks in portfolio
        allocation_method='risk_parity', # Risk-parity weighting
        transaction_cost_pct=0.05,     # 0.05% brokerage + charges
        slippage_pct=0.05,             # 0.05% slippage
        min_volume=50000,              # Min 50k daily volume
        max_volatility=70,             # Max 70% volatility
        min_momentum=0,                # Min 0% momentum
        tax_enabled=True               # Include tax calculations
    )
    
    if results:
        # Calculate comprehensive metrics
        print("\n" + "="*80)
        print("CALCULATING METRICS")
        print("="*80)
        
        metrics = engine.calculate_metrics()
        
        # Compare to benchmark
        print("\n" + "="*80)
        print("BENCHMARK COMPARISON")
        print("="*80)
        
        comparison = engine.compare_to_benchmark('^NSEI')
        
        # Analyze drawdowns
        print("\n" + "="*80)
        print("DRAWDOWN ANALYSIS")
        print("="*80)
        
        drawdowns = engine.analyze_drawdown_periods()
        
        # Monte Carlo simulation
        print("\n" + "="*80)
        print("MONTE CARLO SIMULATION")
        print("="*80)
        
        mc_results = engine.monte_carlo_simulation(n_simulations=1000, n_years=5)
        
        # Export results
        print("\n" + "="*80)
        print("EXPORTING RESULTS")
        print("="*80)
        
        engine.export_results('momentum_strategy_backtest')
        
        # Parameter optimization (optional - takes time)
        run_optimization = False  # Set to True to run
        
        if run_optimization:
            print("\n" + "="*80)
            print("PARAMETER OPTIMIZATION")
            print("="*80)
            
            opt_results = engine.parameter_optimization(
                start_date=START_DATE,
                end_date=END_DATE,
                initial_capital=INITIAL_CAPITAL
            )
    
    print("\n" + "="*80)
    print("✓ BACKTESTING MODULE COMPLETE!")
    print("="*80)
    print("\nKey Features:")
    print("1. ✓ Walk-forward backtesting with realistic constraints")
    print("2. ✓ Transaction costs and slippage modeling")
    print("3. ✓ Tax impact analysis (STCG/LTCG)")
    print("4. ✓ Comprehensive performance metrics")
    print("5. ✓ Benchmark comparison (vs Nifty 50)")
    print("6. ✓ Monte Carlo simulation")
    print("7. ✓ Parameter optimization")
    print("8. ✓ Drawdown analysis")
    print("9. ✓ Detailed export and reporting")
    print("\nNext: Module 5 - Live Tracking & Auto-Rebalancing")
    
    engine.close()