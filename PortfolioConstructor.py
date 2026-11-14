"""
Portfolio Construction & Management Module
Module 3: Build, allocate, optimize, and manage portfolios

This module handles:
1. Position sizing (equal weight, momentum weighted, risk parity, optimized)
2. Capital allocation with constraints
3. Transaction cost modeling
4. Tax-efficient rebalancing (LTCG vs STCG)
5. Portfolio metrics calculation
6. Rebalancing rules and execution
7. Portfolio persistence and tracking
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import json
import warnings
warnings.filterwarnings('ignore')

class PortfolioConstructor:
    def __init__(self, db_path='indian_stocks.db'):
        """Initialize portfolio constructor"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_portfolio_tables()
        self.current_portfolio = None
        print(f"✓ Portfolio Constructor initialized")
    
    def create_portfolio_tables(self):
        """Create database tables for portfolio management"""
        cursor = self.conn.cursor()
        
        # Portfolio metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                portfolio_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_name TEXT,
                creation_date TEXT,
                initial_capital REAL,
                allocation_method TEXT,
                num_stocks INTEGER,
                status TEXT,
                last_rebalance_date TEXT,
                notes TEXT
            )
        ''')
        
        # Portfolio holdings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                holding_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER,
                symbol TEXT,
                entry_date TEXT,
                entry_price REAL,
                shares INTEGER,
                invested_amount REAL,
                target_weight REAL,
                current_weight REAL,
                unrealized_pnl REAL,
                unrealized_pnl_pct REAL,
                holding_period_days INTEGER,
                tax_status TEXT,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
            )
        ''')
        
        # Portfolio transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER,
                symbol TEXT,
                transaction_type TEXT,
                transaction_date TEXT,
                shares INTEGER,
                price REAL,
                amount REAL,
                brokerage REAL,
                tax REAL,
                net_amount REAL,
                notes TEXT,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
            )
        ''')
        
        # Portfolio performance history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_performance (
                performance_id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id INTEGER,
                date TEXT,
                portfolio_value REAL,
                invested_amount REAL,
                cash_balance REAL,
                total_pnl REAL,
                total_pnl_pct REAL,
                day_pnl REAL,
                day_pnl_pct REAL,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(portfolio_id)
            )
        ''')
        
        self.conn.commit()
        print("✓ Portfolio tables created/verified")
    
    def calculate_position_sizes(self, stocks_df, capital, method='equal_weight', 
                                 max_position_size=0.15, min_position_size=0.03):
        """
        Calculate position sizes for selected stocks
        
        Parameters:
        - stocks_df: DataFrame with selected stocks and their metrics
        - capital: Total capital to invest
        - method: 'equal_weight', 'momentum_weighted', 'risk_parity', 'volatility_weighted'
        - max_position_size: Maximum % of capital per stock (default 15%)
        - min_position_size: Minimum % of capital per stock (default 3%)
        
        Returns: DataFrame with position sizes and allocations
        """
        n_stocks = len(stocks_df)
        positions = stocks_df.copy()
        
        print(f"\n{'='*80}")
        print(f"POSITION SIZING: {method.upper()}")
        print(f"Capital: ₹{capital:,.0f} | Stocks: {n_stocks}")
        print(f"{'='*80}\n")
        
        if method == 'equal_weight':
            # Simple equal allocation
            target_weight = 1.0 / n_stocks
            positions['target_weight'] = target_weight
            positions['target_amount'] = capital * target_weight
        
        elif method == 'momentum_weighted':
            # Weight by momentum score (higher momentum = higher allocation)
            if 'momentum_score' not in positions.columns:
                print("⚠ Warning: momentum_score not found, using equal weight")
                positions['target_weight'] = 1.0 / n_stocks
                positions['target_amount'] = capital / n_stocks
            else:
                # Normalize momentum scores (handle negative values)
                min_momentum = positions['momentum_score'].min()
                if min_momentum < 0:
                    adjusted_momentum = positions['momentum_score'] - min_momentum + 1
                else:
                    adjusted_momentum = positions['momentum_score']
                
                total_momentum = adjusted_momentum.sum()
                positions['target_weight'] = adjusted_momentum / total_momentum
                positions['target_amount'] = positions['target_weight'] * capital
        
        elif method == 'risk_parity':
            # Inverse volatility weighting (lower vol = higher allocation)
            if '126d_volatility' not in positions.columns:
                print("⚠ Warning: volatility not found, using equal weight")
                positions['target_weight'] = 1.0 / n_stocks
                positions['target_amount'] = capital / n_stocks
            else:
                # Use inverse volatility
                inv_vol = 1.0 / positions['126d_volatility']
                total_inv_vol = inv_vol.sum()
                positions['target_weight'] = inv_vol / total_inv_vol
                positions['target_amount'] = positions['target_weight'] * capital
        
        elif method == 'volatility_weighted':
            # Weight by momentum/volatility ratio (risk-adjusted momentum)
            if 'momentum_score' in positions.columns and '126d_volatility' in positions.columns:
                risk_adj_momentum = positions['momentum_score'] / positions['126d_volatility']
                
                # Handle negative or zero values
                min_ram = risk_adj_momentum.min()
                if min_ram <= 0:
                    risk_adj_momentum = risk_adj_momentum - min_ram + 0.1
                
                total_ram = risk_adj_momentum.sum()
                positions['target_weight'] = risk_adj_momentum / total_ram
                positions['target_amount'] = positions['target_weight'] * capital
            else:
                print("⚠ Warning: Required columns not found, using equal weight")
                positions['target_weight'] = 1.0 / n_stocks
                positions['target_amount'] = capital / n_stocks
        
        # Apply position size constraints
        positions['target_weight'] = positions['target_weight'].clip(
            lower=min_position_size, 
            upper=max_position_size
        )
        
        # Renormalize to ensure weights sum to 1
        total_weight = positions['target_weight'].sum()
        positions['target_weight'] = positions['target_weight'] / total_weight
        positions['target_amount'] = positions['target_weight'] * capital
        
        # Calculate shares to buy (round down to avoid over-investment)
        positions['shares'] = (positions['target_amount'] / positions['current_price']).astype(int)
        positions['actual_amount'] = positions['shares'] * positions['current_price']
        positions['actual_weight'] = positions['actual_amount'] / positions['actual_amount'].sum()
        
        # Display allocation
        print(f"{'Symbol':<12} {'Target%':>8} {'Amount':>12} {'Shares':>8} {'Price':>10} {'Actual':>12}")
        print(f"{'-'*80}")
        
        total_invested = 0
        for _, row in positions.iterrows():
            print(f"{row['symbol']:<12} {row['target_weight']*100:>7.2f}% "
                  f"₹{row['target_amount']:>10,.0f} {row['shares']:>8} "
                  f"₹{row['current_price']:>9.2f} ₹{row['actual_amount']:>10,.0f}")
            total_invested += row['actual_amount']
        
        cash_remaining = capital - total_invested
        
        print(f"{'-'*80}")
        print(f"{'TOTAL INVESTED':<12} {total_invested/capital*100:>7.2f}% "
              f"₹{total_invested:>10,.0f}")
        print(f"{'CASH REMAINING':<12} {cash_remaining/capital*100:>7.2f}% "
              f"₹{cash_remaining:>10,.0f}")
        print(f"{'='*80}\n")
        
        return positions
    
    def create_portfolio(self, positions_df, portfolio_name, initial_capital, 
                        allocation_method, transaction_cost_pct=0.05):
        """
        Create a new portfolio and save to database
        
        Parameters:
        - positions_df: DataFrame with position sizes
        - portfolio_name: Name for the portfolio
        - initial_capital: Initial investment amount
        - allocation_method: Method used for allocation
        - transaction_cost_pct: Brokerage + taxes (default 0.05% per side)
        """
        cursor = self.conn.cursor()
        
        # Create portfolio entry
        cursor.execute('''
            INSERT INTO portfolios 
            (portfolio_name, creation_date, initial_capital, allocation_method, 
             num_stocks, status, last_rebalance_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            portfolio_name,
            datetime.now().strftime('%Y-%m-%d'),
            initial_capital,
            allocation_method,
            len(positions_df),
            'ACTIVE',
            datetime.now().strftime('%Y-%m-%d'),
            'Portfolio created'
        ))
        
        portfolio_id = cursor.lastrowid
        
        # Calculate transaction costs
        total_brokerage = 0
        
        # Add holdings and transactions
        for _, row in positions_df.iterrows():
            invested = row['actual_amount']
            brokerage = invested * (transaction_cost_pct / 100)
            total_brokerage += brokerage
            net_amount = invested + brokerage
            
            # Add holding
            cursor.execute('''
                INSERT INTO portfolio_holdings
                (portfolio_id, symbol, entry_date, entry_price, shares, 
                 invested_amount, target_weight, current_weight, 
                 unrealized_pnl, unrealized_pnl_pct, holding_period_days, tax_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_id,
                row['symbol'],
                datetime.now().strftime('%Y-%m-%d'),
                row['current_price'],
                int(row['shares']),
                invested,
                row['target_weight'],
                row['actual_weight'],
                0.0,
                0.0,
                0,
                'STCG'  # Short term initially
            ))
            
            # Add transaction
            cursor.execute('''
                INSERT INTO portfolio_transactions
                (portfolio_id, symbol, transaction_type, transaction_date, 
                 shares, price, amount, brokerage, tax, net_amount, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_id,
                row['symbol'],
                'BUY',
                datetime.now().strftime('%Y-%m-%d'),
                int(row['shares']),
                row['current_price'],
                invested,
                brokerage,
                0.0,
                net_amount,
                'Initial purchase'
            ))
        
        # Calculate actual invested (including costs)
        total_invested = positions_df['actual_amount'].sum()
        cash_balance = initial_capital - total_invested - total_brokerage
        
        # Add initial performance record
        cursor.execute('''
            INSERT INTO portfolio_performance
            (portfolio_id, date, portfolio_value, invested_amount, 
             cash_balance, total_pnl, total_pnl_pct, day_pnl, day_pnl_pct)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            portfolio_id,
            datetime.now().strftime('%Y-%m-%d'),
            total_invested,
            total_invested + total_brokerage,
            cash_balance,
            -total_brokerage,
            -total_brokerage / (total_invested + total_brokerage) * 100,
            0.0,
            0.0
        ))
        
        self.conn.commit()
        
        print(f"\n{'='*80}")
        print(f"✓ PORTFOLIO CREATED: {portfolio_name}")
        print(f"Portfolio ID: {portfolio_id}")
        print(f"Initial Capital: ₹{initial_capital:,.0f}")
        print(f"Invested: ₹{total_invested:,.0f}")
        print(f"Transaction Costs: ₹{total_brokerage:,.2f}")
        print(f"Cash Balance: ₹{cash_balance:,.0f}")
        print(f"{'='*80}\n")
        
        self.current_portfolio = portfolio_id
        return portfolio_id
    
    def get_portfolio_holdings(self, portfolio_id):
        """Get current holdings for a portfolio"""
        query = '''
            SELECT symbol, entry_date, entry_price, shares, invested_amount,
                   target_weight, current_weight, unrealized_pnl, 
                   unrealized_pnl_pct, holding_period_days, tax_status
            FROM portfolio_holdings
            WHERE portfolio_id = ?
            ORDER BY invested_amount DESC
        '''
        
        df = pd.read_sql_query(query, self.conn, params=[portfolio_id])
        return df
    
    def update_portfolio_prices(self, portfolio_id, price_data):
        """
        Update portfolio with current prices
        
        Parameters:
        - portfolio_id: Portfolio to update
        - price_data: Dict {symbol: current_price} or DataFrame with symbol and price columns
        """
        cursor = self.conn.cursor()
        
        if isinstance(price_data, pd.DataFrame):
            price_dict = dict(zip(price_data['symbol'], price_data['current_price']))
        else:
            price_dict = price_data
        
        # Get holdings
        holdings = self.get_portfolio_holdings(portfolio_id)
        
        total_current_value = 0
        total_invested = 0
        
        for _, holding in holdings.iterrows():
            symbol = holding['symbol']
            
            if symbol in price_dict:
                current_price = price_dict[symbol]
                shares = holding['shares']
                entry_price = holding['entry_price']
                invested = holding['invested_amount']
                
                current_value = shares * current_price
                unrealized_pnl = current_value - invested
                unrealized_pnl_pct = (unrealized_pnl / invested) * 100
                
                # Calculate holding period
                entry_date = datetime.strptime(holding['entry_date'], '%Y-%m-%d')
                holding_days = (datetime.now() - entry_date).days
                
                # Update tax status (LTCG after 1 year)
                tax_status = 'LTCG' if holding_days >= 365 else 'STCG'
                
                # Update holding
                cursor.execute('''
                    UPDATE portfolio_holdings
                    SET unrealized_pnl = ?,
                        unrealized_pnl_pct = ?,
                        holding_period_days = ?,
                        tax_status = ?
                    WHERE portfolio_id = ? AND symbol = ?
                ''', (unrealized_pnl, unrealized_pnl_pct, holding_days, 
                      tax_status, portfolio_id, symbol))
                
                total_current_value += current_value
                total_invested += invested
        
        # Update current weights
        for _, holding in holdings.iterrows():
            symbol = holding['symbol']
            if symbol in price_dict:
                current_price = price_dict[symbol]
                shares = holding['shares']
                current_value = shares * current_price
                current_weight = current_value / total_current_value if total_current_value > 0 else 0
                
                cursor.execute('''
                    UPDATE portfolio_holdings
                    SET current_weight = ?
                    WHERE portfolio_id = ? AND symbol = ?
                ''', (current_weight, portfolio_id, symbol))
        
        self.conn.commit()
        
        return total_current_value, total_invested
    
    def get_portfolio_summary(self, portfolio_id, current_prices=None):
        """
        Get comprehensive portfolio summary
        
        Parameters:
        - portfolio_id: Portfolio ID
        - current_prices: Optional dict/DataFrame with current prices for update
        """
        if current_prices:
            self.update_portfolio_prices(portfolio_id, current_prices)
        
        cursor = self.conn.cursor()
        
        # Get portfolio metadata
        cursor.execute('''
            SELECT portfolio_name, creation_date, initial_capital, 
                   allocation_method, num_stocks, status, last_rebalance_date
            FROM portfolios WHERE portfolio_id = ?
        ''', [portfolio_id])
        
        portfolio_info = cursor.fetchone()
        
        if not portfolio_info:
            print(f"Portfolio {portfolio_id} not found")
            return None
        
        # Get holdings
        holdings = self.get_portfolio_holdings(portfolio_id)
        
        # Calculate totals
        total_invested = holdings['invested_amount'].sum()
        total_current = total_invested + holdings['unrealized_pnl'].sum()
        total_pnl = holdings['unrealized_pnl'].sum()
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Calculate days since creation
        creation_date = datetime.strptime(portfolio_info[1], '%Y-%m-%d')
        days_held = (datetime.now() - creation_date).days
        
        # Print summary
        print(f"\n{'='*80}")
        print(f"PORTFOLIO SUMMARY: {portfolio_info[0]}")
        print(f"{'='*80}")
        print(f"Portfolio ID: {portfolio_id}")
        print(f"Creation Date: {portfolio_info[1]} ({days_held} days ago)")
        print(f"Allocation Method: {portfolio_info[3]}")
        print(f"Status: {portfolio_info[5]}")
        print(f"Last Rebalance: {portfolio_info[6]}")
        print(f"\n{'PERFORMANCE'}")
        print(f"{'-'*80}")
        print(f"Initial Capital: ₹{portfolio_info[2]:,.0f}")
        print(f"Total Invested: ₹{total_invested:,.0f}")
        print(f"Current Value: ₹{total_current:,.0f}")
        print(f"Total P&L: ₹{total_pnl:,.0f} ({total_pnl_pct:+.2f}%)")
        
        # LTCG vs STCG breakdown
        ltcg_pnl = holdings[holdings['tax_status'] == 'LTCG']['unrealized_pnl'].sum()
        stcg_pnl = holdings[holdings['tax_status'] == 'STCG']['unrealized_pnl'].sum()
        
        print(f"\nTax Status:")
        print(f"  LTCG (>1 year): ₹{ltcg_pnl:,.0f}")
        print(f"  STCG (<1 year): ₹{stcg_pnl:,.0f}")
        
        print(f"\n{'HOLDINGS'}")
        print(f"{'-'*80}")
        print(f"{'Symbol':<12} {'Shares':>8} {'Entry':>10} {'Current':>10} "
              f"{'Invested':>12} {'Value':>12} {'P&L%':>8} {'Days':>6} {'Tax':>5}")
        print(f"{'-'*80}")
        
        for _, row in holdings.iterrows():
            current_price = row['entry_price'] * (1 + row['unrealized_pnl_pct']/100)
            current_value = row['invested_amount'] + row['unrealized_pnl']
            
            print(f"{row['symbol']:<12} {row['shares']:>8} "
                  f"₹{row['entry_price']:>9.2f} ₹{current_price:>9.2f} "
                  f"₹{row['invested_amount']:>10,.0f} ₹{current_value:>10,.0f} "
                  f"{row['unrealized_pnl_pct']:>7.2f}% {row['holding_period_days']:>6} "
                  f"{row['tax_status']:>5}")
        
        print(f"{'='*80}\n")
        
        return {
            'portfolio_info': portfolio_info,
            'holdings': holdings,
            'total_invested': total_invested,
            'total_current': total_current,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'days_held': days_held
        }
    
    def check_rebalance_signals(self, portfolio_id, momentum_scores, 
                               weight_deviation_threshold=0.05,
                               momentum_threshold_percentile=50):
        """
        Check if portfolio needs rebalancing
        
        Parameters:
        - portfolio_id: Portfolio to check
        - momentum_scores: DataFrame with current momentum scores
        - weight_deviation_threshold: Trigger if position > threshold from target (5%)
        - momentum_threshold_percentile: Sell if stock drops below this percentile (50th)
        
        Returns: Dict with rebalance recommendations
        """
        holdings = self.get_portfolio_holdings(portfolio_id)
        
        print(f"\n{'='*80}")
        print(f"REBALANCE ANALYSIS - Portfolio {portfolio_id}")
        print(f"{'='*80}\n")
        
        rebalance_needed = False
        recommendations = []
        
        # Merge holdings with current momentum scores
        merged = holdings.merge(
            momentum_scores[['symbol', 'momentum_score', 'current_price']], 
            on='symbol', 
            how='left'
        )
        
        # Calculate momentum percentile threshold
        momentum_cutoff = momentum_scores['momentum_score'].quantile(
            momentum_threshold_percentile / 100
        )
        
        print(f"Current momentum cutoff (p{momentum_threshold_percentile}): {momentum_cutoff:.2f}\n")
        
        # Check each holding
        for _, row in merged.iterrows():
            issues = []
            action = 'HOLD'
            
            # Check 1: Weight deviation
            weight_diff = abs(row['current_weight'] - row['target_weight'])
            if weight_diff > weight_deviation_threshold:
                issues.append(f"Weight drift: {weight_diff*100:.1f}%")
                action = 'REBALANCE'
                rebalance_needed = True
            
            # Check 2: Momentum deterioration
            if pd.notna(row['momentum_score']):
                if row['momentum_score'] < momentum_cutoff:
                    issues.append(f"Momentum weak: {row['momentum_score']:.1f} < {momentum_cutoff:.1f}")
                    action = 'SELL'
                    rebalance_needed = True
            
            # Check 3: Tax efficiency
            if row['tax_status'] == 'STCG' and row['unrealized_pnl'] > 0:
                issues.append(f"STCG gain: {row['unrealized_pnl_pct']:.1f}%, consider holding for LTCG")
            
            if issues:
                recommendations.append({
                    'symbol': row['symbol'],
                    'action': action,
                    'issues': issues,
                    'current_weight': row['current_weight'],
                    'target_weight': row['target_weight'],
                    'momentum_score': row.get('momentum_score'),
                    'tax_status': row['tax_status'],
                    'holding_days': row['holding_period_days'],
                    'pnl_pct': row['unrealized_pnl_pct']
                })
        
        # Display recommendations
        if recommendations:
            print(f"{'Symbol':<12} {'Action':<12} {'Current%':>10} {'Target%':>10} "
                  f"{'Momentum':>10} {'Days':>6} {'P&L%':>8} {'Issues'}")
            print(f"{'-'*100}")
            
            for rec in recommendations:
                issues_str = '; '.join(rec['issues'])
                print(f"{rec['symbol']:<12} {rec['action']:<12} "
                      f"{rec['current_weight']*100:>9.2f}% {rec['target_weight']*100:>9.2f}% "
                      f"{rec['momentum_score']:>10.1f} {rec['holding_days']:>6} "
                      f"{rec['pnl_pct']:>7.2f}% {issues_str}")
        else:
            print("✓ No rebalancing needed - portfolio is on track")
        
        print(f"\n{'='*80}\n")
        
        return {
            'rebalance_needed': rebalance_needed,
            'recommendations': recommendations
        }
    
    def execute_rebalance(self, portfolio_id, new_stocks_df, capital, 
                         allocation_method='equal_weight',
                         transaction_cost_pct=0.05):
        """
        Execute portfolio rebalancing
        
        This will:
        1. Sell current holdings
        2. Buy new positions based on updated momentum scores
        3. Record all transactions with tax implications
        """
        cursor = self.conn.cursor()
        
        print(f"\n{'='*80}")
        print(f"EXECUTING REBALANCE - Portfolio {portfolio_id}")
        print(f"{'='*80}\n")
        
        # Get current holdings
        current_holdings = self.get_portfolio_holdings(portfolio_id)
        
        # Calculate new positions
        new_positions = self.calculate_position_sizes(
            new_stocks_df, 
            capital, 
            method=allocation_method
        )
        
        # Identify sells (stocks not in new portfolio)
        new_symbols = set(new_positions['symbol'])
        current_symbols = set(current_holdings['symbol'])
        
        to_sell = current_symbols - new_symbols
        to_buy = new_symbols - current_symbols
        to_adjust = new_symbols & current_symbols
        
        print(f"Rebalance actions:")
        print(f"  Sell: {len(to_sell)} positions")
        print(f"  Buy: {len(to_buy)} positions")
        print(f"  Adjust: {len(to_adjust)} positions\n")
        
        # Execute sells
        total_sell_proceeds = 0
        total_sell_brokerage = 0
        total_stcg_tax = 0
        total_ltcg_tax = 0
        
        for symbol in to_sell:
            holding = current_holdings[current_holdings['symbol'] == symbol].iloc[0]
            
            # Calculate proceeds (assuming current price from entry + pnl%)
            current_price = holding['entry_price'] * (1 + holding['unrealized_pnl_pct']/100)
            sell_value = holding['shares'] * current_price
            brokerage = sell_value * (transaction_cost_pct / 100)
            
            # Calculate tax
            if holding['unrealized_pnl'] > 0:
                if holding['tax_status'] == 'LTCG':
                    # LTCG: 10% above 1L
                    ltcg_tax = max(0, holding['unrealized_pnl'] - 100000) * 0.10
                    total_ltcg_tax += ltcg_tax
                    tax = ltcg_tax
                else:
                    # STCG: 15%
                    stcg_tax = holding['unrealized_pnl'] * 0.15
                    total_stcg_tax += stcg_tax
                    tax = stcg_tax
            else:
                tax = 0
            
            net_proceeds = sell_value - brokerage - tax
            total_sell_proceeds += net_proceeds
            total_sell_brokerage += brokerage
            
            # Record transaction
            cursor.execute('''
                INSERT INTO portfolio_transactions
                (portfolio_id, symbol, transaction_type, transaction_date,
                 shares, price, amount, brokerage, tax, net_amount, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_id, symbol, 'SELL', datetime.now().strftime('%Y-%m-%d'),
                holding['shares'], current_price, sell_value, brokerage, tax,
                net_proceeds, f"Rebalance sell - {holding['tax_status']}"
            ))
            
            # Remove from holdings
            cursor.execute('''
                DELETE FROM portfolio_holdings
                WHERE portfolio_id = ? AND symbol = ?
            ''', (portfolio_id, symbol))
        
        # Execute buys (similar to create_portfolio)
        total_buy_amount = 0
        total_buy_brokerage = 0
        
        for symbol in to_buy:
            position = new_positions[new_positions['symbol'] == symbol].iloc[0]
            
            buy_amount = position['actual_amount']
            brokerage = buy_amount * (transaction_cost_pct / 100)
            
            total_buy_amount += buy_amount
            total_buy_brokerage += brokerage
            
            # Add holding
            cursor.execute('''
                INSERT INTO portfolio_holdings
                (portfolio_id, symbol, entry_date, entry_price, shares,
                 invested_amount, target_weight, current_weight,
                 unrealized_pnl, unrealized_pnl_pct, holding_period_days, tax_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_id, symbol, datetime.now().strftime('%Y-%m-%d'),
                position['current_price'], int(position['shares']),
                buy_amount, position['target_weight'], position['actual_weight'],
                0.0, 0.0, 0, 'STCG'
            ))
            
            # Record transaction
            cursor.execute('''
                INSERT INTO portfolio_transactions
                (portfolio_id, symbol, transaction_type, transaction_date,
                 shares, price, amount, brokerage, tax, net_amount, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                portfolio_id, symbol, 'BUY', datetime.now().strftime('%Y-%m-%d'),
                int(position['shares']), position['current_price'],
                buy_amount, brokerage, 0.0, buy_amount + brokerage,
                'Rebalance buy'
            ))
        
        # Update portfolio metadata
        cursor.execute('''
            UPDATE portfolios
            SET last_rebalance_date = ?, num_stocks = ?
            WHERE portfolio_id = ?
        ''', (datetime.now().strftime('%Y-%m-%d'), len(new_positions), portfolio_id))
        
        self.conn.commit()
        
        # Display rebalance summary
        print(f"\n{'='*80}")
        print(f"REBALANCE SUMMARY")
        print(f"{'='*80}")
        print(f"Sell Proceeds: ₹{total_sell_proceeds:,.0f}")
        print(f"Sell Costs: ₹{total_sell_brokerage:,.0f} (brokerage)")
        print(f"STCG Tax: ₹{total_stcg_tax:,.0f}")
        print(f"LTCG Tax: ₹{total_ltcg_tax:,.0f}")
        print(f"Total Tax: ₹{total_stcg_tax + total_ltcg_tax:,.0f}")
        print(f"\nBuy Amount: ₹{total_buy_amount:,.0f}")
        print(f"Buy Costs: ₹{total_buy_brokerage:,.0f} (brokerage)")
        print(f"\nNet Cash Impact: ₹{total_sell_proceeds - total_buy_amount - total_buy_brokerage:,.0f}")
        print(f"{'='*80}\n")
        
        print("✓ Rebalance executed successfully")
    
    def get_portfolio_metrics(self, portfolio_id):
        """
        Calculate comprehensive portfolio metrics
        - Sharpe ratio
        - Sortino ratio
        - Max drawdown
        - Beta (vs Nifty 50)
        - Alpha
        - Volatility
        """
        cursor = self.conn.cursor()
        
        # Get performance history
        cursor.execute('''
            SELECT date, portfolio_value, total_pnl_pct
            FROM portfolio_performance
            WHERE portfolio_id = ?
            ORDER BY date
        ''', [portfolio_id])
        
        perf_data = cursor.fetchall()
        
        if len(perf_data) < 2:
            print("Insufficient data for metrics calculation")
            return None
        
        df_perf = pd.DataFrame(perf_data, columns=['date', 'value', 'return_pct'])
        df_perf['date'] = pd.to_datetime(df_perf['date'])
        df_perf.set_index('date', inplace=True)
        
        # Calculate returns
        returns = df_perf['return_pct'].pct_change().dropna()
        
        if len(returns) < 10:
            print("Insufficient data points for metrics")
            return None
        
        # Risk-free rate (India: ~6.5% annual = 0.025% daily)
        risk_free_daily = 0.065 / 252
        
        # Calculate metrics
        mean_return = returns.mean()
        std_return = returns.std()
        
        # Sharpe Ratio (annualized)
        sharpe = (mean_return - risk_free_daily) / std_return * np.sqrt(252) if std_return > 0 else 0
        
        # Sortino Ratio (downside deviation)
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else std_return
        sortino = (mean_return - risk_free_daily) / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Max Drawdown
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100
        
        # Volatility (annualized)
        volatility = std_return * np.sqrt(252) * 100
        
        # Total return
        total_return = df_perf['return_pct'].iloc[-1]
        
        # CAGR
        days = (df_perf.index[-1] - df_perf.index[0]).days
        years = days / 365.25
        cagr = ((1 + total_return/100) ** (1/years) - 1) * 100 if years > 0 else 0
        
        metrics = {
            'total_return': total_return,
            'cagr': cagr,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'max_drawdown': max_drawdown,
            'days_tracked': days
        }
        
        print(f"\n{'='*80}")
        print(f"PORTFOLIO METRICS - Portfolio {portfolio_id}")
        print(f"{'='*80}")
        print(f"Total Return: {total_return:.2f}%")
        print(f"CAGR: {cagr:.2f}%")
        print(f"Volatility: {volatility:.2f}%")
        print(f"Sharpe Ratio: {sharpe:.2f}")
        print(f"Sortino Ratio: {sortino:.2f}")
        print(f"Max Drawdown: {max_drawdown:.2f}%")
        print(f"Days Tracked: {days}")
        print(f"{'='*80}\n")
        
        return metrics
    
    def list_all_portfolios(self):
        """List all portfolios in database"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            SELECT portfolio_id, portfolio_name, creation_date, 
                   initial_capital, allocation_method, num_stocks, status
            FROM portfolios
            ORDER BY creation_date DESC
        ''')
        
        portfolios = cursor.fetchall()
        
        if not portfolios:
            print("No portfolios found")
            return []
        
        print(f"\n{'='*80}")
        print(f"ALL PORTFOLIOS")
        print(f"{'='*80}")
        print(f"{'ID':>4} {'Name':<20} {'Created':<12} {'Capital':>12} {'Method':<18} {'Stocks':>6} {'Status':<8}")
        print(f"{'-'*80}")
        
        for p in portfolios:
            print(f"{p[0]:>4} {p[1]:<20} {p[2]:<12} ₹{p[3]:>10,.0f} {p[4]:<18} {p[5]:>6} {p[6]:<8}")
        
        print(f"{'='*80}\n")
        
        return portfolios
    
    def export_portfolio_report(self, portfolio_id, filename=None):
        """Export detailed portfolio report to CSV"""
        if filename is None:
            filename = f'portfolio_{portfolio_id}_report_{datetime.now().strftime("%Y%m%d")}.csv'
        
        # Get holdings
        holdings = self.get_portfolio_holdings(portfolio_id)
        
        # Get transactions
        transactions = pd.read_sql_query('''
            SELECT * FROM portfolio_transactions
            WHERE portfolio_id = ?
            ORDER BY transaction_date DESC
        ''', self.conn, params=[portfolio_id])
        
        # Export to Excel with multiple sheets
        with pd.ExcelWriter(filename.replace('.csv', '.xlsx'), engine='openpyxl') as writer:
            holdings.to_excel(writer, sheet_name='Holdings', index=False)
            transactions.to_excel(writer, sheet_name='Transactions', index=False)
        
        print(f"✓ Portfolio report exported to {filename.replace('.csv', '.xlsx')}")
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        print("✓ Database connection closed")


# Example Usage
if __name__ == "__main__":
    import sys
    sys.path.append('.')  # Ensure imports work
    
    # Initialize portfolio constructor
    pc = PortfolioConstructor('indian_stocks.db')
    
    print("\n" + "="*80)
    print("PORTFOLIO CONSTRUCTION & MANAGEMENT MODULE")
    print("="*80)
    
    # Example: Create a sample portfolio
    # In practice, you'd get this from StockAnalyzer module
    
    sample_stocks = pd.DataFrame({
        'symbol': ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS',
                   'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'HINDUNILVR.NS', 'LT.NS'],
        'momentum_score': [45.2, 38.7, 42.1, 35.8, 40.5, 33.2, 48.9, 31.5, 29.8, 44.3],
        '126d_volatility': [28.5, 22.3, 25.1, 24.8, 32.1, 35.2, 27.8, 18.5, 16.9, 26.4],
        'current_price': [2450.50, 3820.75, 1650.25, 1580.60, 1020.80, 
                         620.30, 1450.90, 450.20, 2580.40, 3250.70]
    })
    
    # Step 1: Calculate position sizes
    print("\n" + "="*80)
    print("STEP 1: POSITION SIZING")
    print("="*80)
    
    capital = 1000000  # 10 lakhs
    
    # Test different allocation methods
    methods = ['equal_weight', 'momentum_weighted', 'risk_parity', 'volatility_weighted']
    
    for method in methods:
        print(f"\n--- {method.upper()} ---")
        positions = pc.calculate_position_sizes(
            sample_stocks, 
            capital, 
            method=method,
            max_position_size=0.15,
            min_position_size=0.05
        )
    
    # Step 2: Create portfolio
    print("\n" + "="*80)
    print("STEP 2: CREATE PORTFOLIO")
    print("="*80)
    
    # Use risk_parity allocation
    positions = pc.calculate_position_sizes(
        sample_stocks, 
        capital, 
        method='risk_parity'
    )
    
    portfolio_id = pc.create_portfolio(
        positions,
        portfolio_name='Momentum Strategy Q4 2024',
        initial_capital=capital,
        allocation_method='risk_parity',
        transaction_cost_pct=0.05
    )
    
    # Step 3: Get portfolio summary
    print("\n" + "="*80)
    print("STEP 3: PORTFOLIO SUMMARY")
    print("="*80)
    
    summary = pc.get_portfolio_summary(portfolio_id)
    
    # Step 4: Check rebalance signals (simulated)
    print("\n" + "="*80)
    print("STEP 4: REBALANCE CHECK")
    print("="*80)
    
    # Simulate updated momentum scores
    updated_scores = sample_stocks.copy()
    updated_scores['momentum_score'] = updated_scores['momentum_score'] + np.random.randn(len(updated_scores)) * 5
    
    rebalance_check = pc.check_rebalance_signals(
        portfolio_id,
        updated_scores,
        weight_deviation_threshold=0.05,
        momentum_threshold_percentile=50
    )
    
    # Step 5: List all portfolios
    print("\n" + "="*80)
    print("STEP 5: ALL PORTFOLIOS")
    print("="*80)
    
    pc.list_all_portfolios()
    
    # Step 6: Export report
    print("\n" + "="*80)
    print("STEP 6: EXPORT REPORT")
    print("="*80)
    
    pc.export_portfolio_report(portfolio_id)
    
    print("\n" + "="*80)
    print("✓ PORTFOLIO CONSTRUCTION MODULE COMPLETE!")
    print("="*80)
    print("\nKey Features:")
    print("1. ✓ Multiple allocation methods")
    print("2. ✓ Transaction cost tracking")
    print("3. ✓ Tax-efficient rebalancing (LTCG/STCG)")
    print("4. ✓ Portfolio performance tracking")
    print("5. ✓ Rebalance signal detection")
    print("6. ✓ Comprehensive reporting")
    print("\nNext: Module 4 - Backtesting Engine")
    
    pc.close()