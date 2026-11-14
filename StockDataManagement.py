"""
Indian Stock Data Management System
Module 1: Data Collection, Storage & Management

This module handles:
1. Fetching list of all NSE stocks
2. Downloading historical adjusted price data
3. Storing in SQLite database
4. Daily data updates
5. Data quality checks
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
import time
import requests
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

class StockDataManager:
    def __init__(self, db_path='indian_stocks.db'):
        """Initialize the data manager with SQLite database"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        print(f"✓ Database initialized: {db_path}")
    
    def create_tables(self):
        """Create necessary database tables"""
        cursor = self.conn.cursor()
        
        # Table for stock metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                industry TEXT,
                sector TEXT,
                market_cap REAL,
                isin TEXT,
                series TEXT,
                listing_date TEXT,
                last_updated TIMESTAMP
            )
        ''')
        
        # Table for daily price data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_data (
                symbol TEXT,
                date TEXT,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                adj_close REAL,
                volume INTEGER,
                PRIMARY KEY (symbol, date),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol)
            )
        ''')
        
        # Table for data quality tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_quality (
                symbol TEXT PRIMARY KEY,
                total_records INTEGER,
                first_date TEXT,
                last_date TEXT,
                missing_dates INTEGER,
                last_check TIMESTAMP,
                status TEXT
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_date ON price_data(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol ON price_data(symbol)')
        
        self.conn.commit()
        print("✓ Database tables created/verified")
    
    def get_all_nse_stocks(self, method='csv'):
        """
        Get list of all NSE-listed stocks
        
        Methods:
        1. 'csv' - Download from NSE website (most reliable)
        2. 'scrape' - Scrape from NSE website
        3. 'manual' - Use predefined comprehensive list
        """
        
        if method == 'csv':
            return self._get_nse_stocks_csv()
        elif method == 'scrape':
            return self._get_nse_stocks_scrape()
        else:
            return self._get_nse_stocks_manual()
    
    def _get_nse_stocks_csv(self):
        """
        Download equity list from NSE
        NSE provides CSV files with all listed stocks
        """
        print("Fetching NSE stock list from CSV...")
        
        try:
            # NSE Equity List URL (this is the bhavcopy structure)
            # Alternative: Use NSE website's equity list
            url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
            
            # NSE requires headers to prevent blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Save to temporary file
                with open('nse_equity_list.csv', 'wb', encoding="utf-8") as f:
                    f.write(response.content)
                
                # Read the CSV
                df = pd.read_csv('nse_equity_list.csv')
                print(df.columns)
                # Clean and standardize
                stocks = []
                for _, row in df.iterrows():
                    symbol = str(row['SYMBOL']).strip() + '.NS'
                    stocks.append({
                        'symbol': symbol,
                        'company_name': row.get('NAME OF COMPANY', ''),
                        'series': row.get(' SERIES', 'EQ'),
                        'isin': row.get(' ISIN NUMBER', '')
                    })
                
                print(f"✓ Found {len(stocks)} NSE stocks")
                return stocks
            else:
                print(f"✗ Failed to download NSE list (Status: {response.status_code})")
                print("Falling back to manual list...")
                return self._get_nse_stocks_manual()
                
        except Exception as e:
            print(f"✗ Error fetching NSE CSV: {e}")
            print("Falling back to manual list...")
            return self._get_nse_stocks_manual()
    
    def _get_nse_stocks_scrape(self):
        """Scrape stock list from NSE website"""
        print("Scraping NSE website for stock list...")
        # Implementation would go here
        # This is complex due to NSE's anti-bot measures
        print("Note: NSE scraping requires handling JavaScript and cookies")
        return self._get_nse_stocks_manual()
    
    def _get_nse_stocks_manual(self):
        """
        Comprehensive manual list of major NSE stocks
        This includes Nifty 500 + actively traded stocks
        """
        print("Using comprehensive manual stock list...")
        
        # Major indices coverage
        stocks = [
            # Nifty 50
            'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
            'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS',
            'LT.NS', 'AXISBANK.NS', 'ASIANPAINT.NS', 'MARUTI.NS', 'HCLTECH.NS',
            'BAJFINANCE.NS', 'TITAN.NS', 'WIPRO.NS', 'ULTRACEMCO.NS', 'NESTLEIND.NS',
            'SUNPHARMA.NS', 'ADANIENT.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS',
            'TATAMOTORS.NS', 'TATASTEEL.NS', 'BAJAJFINSV.NS', 'M&M.NS', 'HDFCLIFE.NS',
            'TECHM.NS', 'COALINDIA.NS', 'INDUSINDBK.NS', 'ADANIPORTS.NS', 'CIPLA.NS',
            'DIVISLAB.NS', 'JSWSTEEL.NS', 'APOLLOHOSP.NS', 'DRREDDY.NS', 'BRITANNIA.NS',
            'EICHERMOT.NS', 'HEROMOTOCO.NS', 'HINDALCO.NS', 'GRASIM.NS', 'TATACONSUM.NS',
            'BAJAJ-AUTO.NS', 'SBILIFE.NS', 'BPCL.NS', 'UPL.NS', 'VEDL.NS',
            
            # Nifty Next 50
            'ADANIGREEN.NS', 'ADANITRANS.NS', 'AMBUJACEM.NS', 'BANDHANBNK.NS', 'BERGEPAINT.NS',
            'BEL.NS', 'BOSCHLTD.NS', 'CHOLAFIN.NS', 'COLPAL.NS', 'DABUR.NS',
            'DLF.NS', 'GODREJCP.NS', 'GAIL.NS', 'HAVELLS.NS', 'ICICIPRULI.NS',
            'JINDALSTEL.NS', 'LTIM.NS', 'MARICO.NS', 'MUTHOOTFIN.NS', 'NMDC.NS',
            'NYKAA.NS', 'OBEROIRLTY.NS', 'OFSS.NS', 'PIIND.NS', 'PAGEIND.NS',
            'PERSISTENT.NS', 'PETRONET.NS', 'PIDILITIND.NS', 'PFC.NS', 'RECLTD.NS',
            'SHREECEM.NS', 'SIEMENS.NS', 'SRF.NS', 'TORNTPHARM.NS', 'TRENT.NS',
            'TVSMOTOR.NS', 'ZYDUSLIFE.NS', 'INDIGO.NS', 'BANKBARODA.NS', 'PNB.NS',
            
            # Midcap selections
            'ABBOTINDIA.NS', 'ACC.NS', 'AFFLE.NS', 'ALKEM.NS', 'ASHOKLEY.NS',
            'ASTRAL.NS', 'AUBANK.NS', 'AUROPHARMA.NS', 'BALKRISIND.NS', 'BATAINDIA.NS',
            'BHARATFORG.NS', 'BIOCON.NS', 'CANBK.NS', 'CHAMBLFERT.NS', 'COFORGE.NS',
            'CONCOR.NS', 'CUMMINSIND.NS', 'DEEPAKNTR.NS', 'DELTACORP.NS', 'DIXON.NS',
            'ESCORTS.NS', 'EXIDEIND.NS', 'FEDERALBNK.NS', 'GMRINFRA.NS', 'GNFC.NS',
            'GODREJPROP.NS', 'HATSUN.NS', 'ICICIGI.NS', 'IDFCFIRSTB.NS', 'IEX.NS',
            'IGL.NS', 'INDHOTEL.NS', 'IRCTC.NS', 'IRFC.NS', 'JUBLFOOD.NS',
            'KPITTECH.NS', 'L&TFH.NS', 'LICI.NS', 'LICHSGFIN.NS', 'LUPIN.NS',
            'MANAPPURAM.NS', 'MFSL.NS', 'MGL.NS', 'MOTHERSON.NS', 'MPHASIS.NS',
            'MRF.NS', 'NATIONALUM.NS', 'NAVINFLUOR.NS', 'NHPC.NS', 'NLCINDIA.NS',
            'PAYTM.NS', 'PGHH.NS', 'POLYCAB.NS', 'PVR.NS', 'RAIN.NS',
            'RBLBANK.NS', 'SAIL.NS', 'SBICARD.NS', 'SCHAEFFLER.NS', 'SONACOMS.NS',
            'SUNTV.NS', 'SUPREMEIND.NS', 'SYNGENE.NS', 'TATACHEM.NS', 'TATACOMM.NS',
            'TATAELXSI.NS', 'TATAPOWER.NS', 'TIINDIA.NS', 'TORNTPOWER.NS', 'UNIONBANK.NS',
            'VOLTAS.NS', 'YESBANK.NS', 'ZEEL.NS', 'ZOMATO.NS', 'ZYDUSWELL.NS',
            
            # Add more as needed - this list covers ~200 major stocks
        ]
        
        stock_list = [{'symbol': s, 'company_name': '', 'series': 'EQ', 'isin': ''} 
                     for s in stocks]
        
        print(f"✓ Loaded {len(stock_list)} stocks from manual list")
        return stock_list
    
    def save_stock_list(self, stock_list):
        """Save stock metadata to database"""
        cursor = self.conn.cursor()
        
        for stock in stock_list:
            cursor.execute('''
                INSERT OR REPLACE INTO stocks (symbol, company_name, series, isin, last_updated)
                VALUES (?, ?, ?, ?, ?)
            ''', (stock['symbol'], stock.get('company_name', ''), 
                  stock.get('series', 'EQ'), stock.get('isin', ''),
                  datetime.now()))
        
        self.conn.commit()
        print(f"✓ Saved {len(stock_list)} stocks to database")
    
    def download_historical_data(self, symbols, start_date, end_date=None, 
                                 batch_size=10, delay=1):
        """
        Download historical data for given symbols
        
        Parameters:
        - symbols: List of stock symbols
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (default: today)
        - batch_size: Number of stocks to download before delay
        - delay: Seconds to wait between batches (avoid rate limiting)
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        print(f"\n{'='*70}")
        print(f"DOWNLOADING HISTORICAL DATA")
        print(f"Period: {start_date} to {end_date}")
        print(f"Stocks: {len(symbols)}")
        print(f"{'='*70}\n")
        
        success_count = 0
        fail_count = 0
        cursor = self.conn.cursor()
        
        # for i, symbol in enumerate(symbols[1:], 1):
        for i, symbol in enumerate(symbols, 1):
            try:
                print(f"[{i}/{len(symbols)}] {symbol}...", end=' ', flush=True)
                
                # Download data
                data = yf.download(symbol, start=start_date, end=end_date, 
                                 progress=False, auto_adjust=False)
                
                if data.empty:
                    print("✗ No data")
                    fail_count += 1
                    continue
                
                # Insert data into database
                for date, row in data.iterrows():
                    cursor.execute('''
                        INSERT OR REPLACE INTO price_data 
                        (symbol, date, open, high, low, close, adj_close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (symbol, date.strftime('%Y-%m-%d'), 
                          float(row['Open']), float(row['High']), 
                          float(row['Low']), float(row['Close']),
                          float(row['Adj Close']), int(row['Volume'])))
                
                # Update quality tracking
                cursor.execute('''
                    INSERT OR REPLACE INTO data_quality
                    (symbol, total_records, first_date, last_date, last_check, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (symbol, len(data), data.index[0].strftime('%Y-%m-%d'),
                      data.index[-1].strftime('%Y-%m-%d'), datetime.now(), 'OK'))
                
                self.conn.commit()
                print(f"✓ {len(data)} records")
                success_count += 1
                
                # Rate limiting
                if i % batch_size == 0:
                    print(f"\n⏸  Pausing {delay}s to avoid rate limits...")
                    time.sleep(delay)
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
                fail_count += 1
                continue
        
        print(f"\n{'='*70}")
        print(f"DOWNLOAD COMPLETE")
        print(f"Success: {success_count} | Failed: {fail_count}")
        print(f"{'='*70}\n")
    
    def update_daily_data(self, lookback_days=30):
        """
        Update data for all stocks in database
        Gets last N days of data to ensure we don't miss anything
        """
        cursor = self.conn.cursor()
        
        # Get all symbols
        cursor.execute('SELECT symbol FROM stocks')
        symbols = [row[0] for row in cursor.fetchall()]
        
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        print(f"\n{'='*70}")
        print(f"DAILY UPDATE - Getting last {lookback_days} days")
        print(f"{'='*70}\n")
        
        self.download_historical_data(symbols, start_date, end_date, 
                                     batch_size=20, delay=0.5)
    
    def check_data_quality(self):
        """
        Check data quality for all stocks
        Identifies missing data, gaps, etc.
        """
        cursor = self.conn.cursor()
        
        print(f"\n{'='*70}")
        print(f"DATA QUALITY REPORT")
        print(f"{'='*70}\n")
        
        # Get quality stats
        cursor.execute('''
            SELECT symbol, total_records, first_date, last_date, status
            FROM data_quality
            ORDER BY total_records DESC
        ''')
        
        quality_data = cursor.fetchall()
        
        if not quality_data:
            print("No data quality information available")
            return
        
        # Summary statistics
        total_stocks = len(quality_data)
        avg_records = sum(row[1] for row in quality_data) / total_stocks
        
        print(f"Total Stocks: {total_stocks}")
        print(f"Average Records per Stock: {avg_records:.0f}")
        print(f"\nTop 20 Stocks by Data Points:\n")
        print(f"{'Symbol':<15} {'Records':>10} {'First Date':<12} {'Last Date':<12} {'Status':<8}")
        print(f"{'-'*70}")
        
        for row in quality_data[:20]:
            print(f"{row[0]:<15} {row[1]:>10} {row[2]:<12} {row[3]:<12} {row[4]:<8}")
        
        # Check for recent data gaps
        recent_cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM data_quality 
            WHERE last_date < ?
        ''', (recent_cutoff,))
        stale_count = cursor.fetchone()[0]
        
        if stale_count > 0:
            print(f"\n⚠  Warning: {stale_count} stocks have data older than 7 days")
        
        print(f"\n{'='*70}\n")
    
    def get_stock_data(self, symbol, start_date=None, end_date=None):
        """
        Retrieve stock data from database
        Returns pandas DataFrame
        """
        query = 'SELECT date, open, high, low, close, adj_close, volume FROM price_data WHERE symbol = ?'
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
        
        return df
    
    def export_to_csv(self, symbol, output_file=None):
        """Export stock data to CSV"""
        df = self.get_stock_data(symbol)
        
        if df.empty:
            print(f"No data found for {symbol}")
            return
        
        if output_file is None:
            output_file = f"{symbol.replace('.NS', '')}_data.csv"
        
        df.to_csv(output_file)
        print(f"✓ Exported {len(df)} records to {output_file}")
    
    def get_all_symbols(self):
        """Get list of all symbols in database"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT symbol FROM stocks ORDER BY symbol')
        return [row[0] for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection"""
        self.conn.close()
        print("✓ Database connection closed")


# Example Usage
if __name__ == "__main__":
    # Initialize data manager
    dm = StockDataManager('indian_stocks.db')
    
    # print("\n" + "="*70)
    # print("STEP 1: GET ALL NSE STOCKS")
    # print("="*70)
    
    # # Get stock list (tries CSV first, falls back to manual)
    # stock_list = dm.get_all_nse_stocks(method='csv')
    
    # # Save to database
    # dm.save_stock_list(stock_list)
    
    # print("\n" + "="*70)
    # print("STEP 2: DOWNLOAD HISTORICAL DATA")
    # print("="*70)
    # print("\nChoose your option:")
    # print("1. Download ALL stocks (will take hours)")
    # print("2. Download sample of 50 stocks (quick test)")
    # print("3. Skip download (use existing data)")
    
    # # For demo, let's download a sample
    # choice = int(input())  # Change this or make it interactive
    
    # if choice == 1:
    #     symbols = dm.get_all_symbols()
    #     dm.download_historical_data(symbols, start_date='2014-01-01')
    # elif choice == 2:
    #     # Download first 50 stocks as sample
    #     symbols = dm.get_all_symbols()[:50]
    #     print(f"\nDownloading sample of {len(symbols)} stocks...")
    #     dm.download_historical_data(symbols, start_date='2014-01-01')
    
    # print("\n" + "="*70)
    # print("STEP 3: DATA QUALITY CHECK")
    # print("="*70)
    
    # dm.check_data_quality()
    
    # print("\n" + "="*70)
    # print("STEP 4: EXAMPLE QUERIES")
    # print("="*70)
    
    # # Example: Get data for a specific stock
    # if dm.get_all_symbols():
    #     sample_symbol = dm.get_all_symbols()[0]
    #     df = dm.get_stock_data(sample_symbol, start_date='2023-01-01')
    #     print(f"\nSample data for {sample_symbol}:")
    #     print(df.head())
    #     print(f"\nTotal records: {len(df)}")
    

    dm.update_daily_data()


    print("\n" + "="*70)
    print("✓ DATA MANAGEMENT MODULE READY!")
    print("="*70)
    print("\nNext steps:")
    print("1. Run dm.update_daily_data() to get latest prices")
    print("2. Set up daily cron job for automatic updates")
    print("3. Use dm.get_stock_data(symbol) to fetch data for analysis")
    
    # Close connection
    dm.close()