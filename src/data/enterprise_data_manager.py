"""
Enterprise Data Manager
Integrates all Priority 1 features with existing Module 1
"""

import pandas as pd
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import yfinance as yf
import requests
import time

# Import Priority 1 components
from src.core.config import ConfigManager
from src.core.logging import LoggerFactory
from src.core.errors import (
    ErrorHandler, DataFetchError, ValidationError,
    with_retry, RecoveryAction
)
from src.core.validation import DataValidator, DataQualityLevel
from src.data.nse_fetcher import EnterpriseNSEDataFetcher
from src.utils.rate_limiter import RateLimiter
from src.utils.cache import CacheManager

class EnterpriseDataManager:
    """
    Production-ready data management system
    Replaces simplified StockDataManager from Module 1
    """
    
    def __init__(self):
        """Initialize with all enterprise features"""
        # Load configuration
        self.config = ConfigManager()
        
        # Setup logging
        self.logger = LoggerFactory.create_logger(
            'data_manager',
            self.config,
            context={'component': 'data_management'}
        )
        
        self.logger.info("Initializing Enterprise Data Manager...")
        
        # Initialize components
        self.error_handler = ErrorHandler(self.logger, self.config)
        self.validator = DataValidator(self.logger, self.config)
        self.nse_fetcher = EnterpriseNSEDataFetcher(self.config, self.logger)
        self.cache = CacheManager(self.config, self.logger)
        
        # Rate limiter
        rate_limit = self.config.get('api.rate_limit', 100)
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit)
        
        # Database connection
        db_path = self.config.get('database.path')
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        
        self.logger.info("✓ Enterprise Data Manager initialized successfully")
    
    def _create_tables(self):
        """Create database tables with proper schema"""
        cursor = self.conn.cursor()
        
        # Stocks table with additional metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                symbol TEXT PRIMARY KEY,
                company_name TEXT,
                industry TEXT,
                sector TEXT,
                market_cap REAL,
                isin TEXT,
                series TEXT,
                index_membership TEXT,
                listing_date TEXT,
                last_updated TIMESTAMP,
                data_quality_score REAL,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Price data with validation flags
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
                validated INTEGER DEFAULT 0,
                data_quality TEXT,
                PRIMARY KEY (symbol, date),
                FOREIGN KEY (symbol) REFERENCES stocks(symbol)
            )
        ''')
        
        # Data quality tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_quality (
                symbol TEXT PRIMARY KEY,
                total_records INTEGER,
                first_date TEXT,
                last_date TEXT,
                missing_dates INTEGER,
                outliers INTEGER,
                quality_level TEXT,
                last_check TIMESTAMP,
                issues TEXT,
                FOREIGN KEY (symbol) REFERENCES stocks(symbol)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_date ON price_data(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_symbol ON price_data(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stocks_index ON stocks(index_membership)')
        
        self.conn.commit()
        self.logger.info("✓ Database tables created/verified")
    
    def get_stock_list(self, index_name: str = 'NIFTY500') -> List[Dict]:
        """
        Get stock list with enterprise features
        
        Args:
            index_name: Index name (NIFTY50, NIFTY500, etc.)
        
        Returns:
            List of stock dictionaries
        """
        cache_key = f"stock_list_{index_name}"
        
        # Try cache first
        cached = self.cache.get(cache_key, max_age_seconds=86400)  # 24 hour cache
        if cached:
            self.logger.info(f"Using cached stock list for {index_name}")
            return cached
        
        try:
            self.logger.info(f"Fetching {index_name} stock list...")
            
            # Fetch with fallback mechanisms
            stocks = self.nse_fetcher.get_stock_list_with_fallback(index_name)
            
            # Validate
            if not stocks or len(stocks) < 10:
                raise ValidationError(
                    f"Invalid stock list: only {len(stocks)} stocks fetched"
                )
            
            # Cache for 24 hours
            self.cache.set(cache_key, stocks)
            
            self.logger.info(f"✓ Fetched {len(stocks)} stocks for {index_name}")
            return stocks
            
        except Exception as e:
            recovery = self.error_handler.handle(
                e,
                context={'index': index_name, 'function': 'get_stock_list'}
            )
            
            if recovery == RecoveryAction.FALLBACK:
                # Try to get stale cache
                stale_cache = self.cache.get(cache_key, max_age_seconds=604800)  # 7 days
                if stale_cache:
                    self.logger.warning("Using stale cache due to fetch failure")
                    return stale_cache
            
            raise
    
    @with_retry(max_attempts=3, backoff_factor=2.0)
    def download_stock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Download stock data with enterprise features
        
        Args:
            symbol: Stock symbol
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (default: today)
        
        Returns:
            DataFrame with price data
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Rate limiting
            self.rate_limiter.acquire()
            
            # Download
            self.logger.debug(f"Downloading {symbol} from {start_date} to {end_date}")
            print(f"Downloading {symbol} from {start_date} to {end_date}")
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=False
            )
            
            if data.empty:
                raise DataFetchError(f"No data returned for {symbol}")
            
            # Validate data quality
            quality_report = self.validator.validate_price_data(data, symbol)
            
            if not quality_report.is_usable():
                self.logger.warning(
                    f"Poor data quality for {symbol}: {quality_report.issues}"
                )
            
            # Store validation results
            self._save_quality_report(symbol, quality_report)
            
            return data
            
        except Exception as e:
            recovery = self.error_handler.handle(
                e,
                context={'symbol': symbol, 'start_date': start_date},
                retry_count=3
            )
            
            if recovery == RecoveryAction.SKIP:
                return pd.DataFrame()  # Return empty DataFrame
            else:
                raise

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
                with open('nse_equity_list.csv', 'wb') as f:
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
                        'isin': row.get(' ISIN NUMBER', ''),
                        'listing_date': row.get(' LISTING DATE', ''),
                        'index_membership': 'NSE',  # Placeholder
                        'market_cap': row.get(' MARKET LOT', 0) * row.get(' FACE VALUE', 0)
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
        
        self.bulk_download(symbols, start_date=start_date)

    def save_stock_list(self, stock_list):
        """Save stock metadata to database"""
        cursor = self.conn.cursor()
        for stock in stock_list:
            cursor.execute('''
                INSERT OR REPLACE INTO stocks (symbol, company_name, series, isin, listing_date, index_membership, market_cap, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (stock['symbol'], stock.get('company_name', ''), 
                  stock.get('series', 'EQ'), stock.get('isin', ''),
                  stock.get('listing_date', ''), stock.get('index_membership', ''),
                  stock.get('market_cap', 0),
                  datetime.now()))
        
        self.conn.commit()
        print(f"✓ Saved {len(stock_list)} stocks to database")
    
    def _save_quality_report(self, symbol: str, report):
        """Save data quality report to database"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO data_quality
            (symbol, total_records, first_date, last_date, missing_dates,
             outliers, quality_level, last_check, issues)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            symbol,
            report.total_records,
            report.first_date,
            report.last_date,
            report.date_gaps,
            report.outliers,
            report.quality_level.value,
            datetime.now().isoformat(),
            '|'.join(report.issues)
        ))
        
        self.conn.commit()
    
    def bulk_download(self, symbols: List[str], start_date: str):
        """
        Download data for multiple stocks with progress tracking
        
        Args:
            symbols: List of stock symbols
            start_date: Start date
        """
        from tqdm import tqdm
        
        self.logger.info(f"Bulk downloading {len(symbols)} stocks...")
        
        stats = {
            'success': 0,
            'failed': 0,
            'poor_quality': 0
        }
        #594
        # Progress bar
        for symbol in tqdm(symbols[1542:], desc="Downloading", initial=1542, total=len(symbols)):
            try:
                data = self.download_stock_data(symbol, start_date)
                
                if not data.empty:
                    # Save to database
                    self._save_price_data(symbol, data)
                    stats['success'] += 1
                else:
                    stats['failed'] += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to download {symbol}: {e}")
                stats['failed'] += 1
        
        # Log summary
        self.logger.info(
            f"Download complete: {stats['success']} success, "
            f"{stats['failed']} failed"
        )
        
        # Get error report
        error_report = self.error_handler.get_error_report()
        self.logger.info(f"Errors encountered: {error_report['total_errors']}")
    
    def _save_price_data(self, symbol: str, data: pd.DataFrame):
        """Save price data to database"""
        cursor = self.conn.cursor()
        
        for date, row in data.iterrows():
            cursor.execute('''
                INSERT OR REPLACE INTO price_data
                (symbol, date, open, high, low, close, adj_close, volume, validated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                symbol,
                date.strftime('%Y-%m-%d'),
                float(row['Open']),
                float(row['High']),
                float(row['Low']),
                float(row['Close']),
                float(row['Adj Close']),
                int(row['Volume'])
            ))
        
        self.conn.commit()
    
    def get_system_health(self) -> Dict:
        """Get comprehensive system health report"""
        cursor = self.conn.cursor()
        
        # Count stocks
        cursor.execute('SELECT COUNT(*) FROM stocks')
        total_stocks = cursor.fetchone()[0]
        
        # Count records
        cursor.execute('SELECT COUNT(*) FROM price_data')
        total_records = cursor.fetchone()[0]
        
        # Quality distribution
        cursor.execute('''
            SELECT quality_level, COUNT(*) 
            FROM data_quality 
            GROUP BY quality_level
        ''')
        quality_dist = dict(cursor.fetchall())
        
        # Cache stats
        cache_stats = self.cache.get_stats()
        
        # Rate limiter stats
        rate_stats = self.rate_limiter.get_stats()
        
        # Error stats
        error_stats = self.error_handler.get_error_report()
        
        return {
            'stocks': total_stocks,
            'records': total_records,
            'quality_distribution': quality_dist,
            'cache': cache_stats,
            'rate_limiter': rate_stats,
            'errors': error_stats,
            'timestamp': datetime.now().isoformat()
        }
    
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

    def close(self):
        """Close connections and cleanup"""
        self.conn.close()
        self.logger.info("Data Manager closed")

# # ============================================================================
# # USAGE EXAMPLE
# # ============================================================================

# if __name__ == "__main__":
#     # Initialize enterprise data manager
#     dm = EnterpriseDataManager()
    
#     # Get stock list
#     nifty_500 = dm.get_stock_list('NIFTY500')
#     print(f"Loaded {len(nifty_500)} Nifty 500 stocks")
    
#     # Download data with all enterprise features
#     symbols = [s['symbol'] for s in nifty_500[:10]]  # First 10 for demo
#     dm.bulk_download(symbols, start_date='2020-01-01')
    
#     # Get system health
#     health = dm.get_system_health()
#     print("\nSystem Health:")
#     print(f"  Total stocks: {health['stocks']}")
#     print(f"  Total records: {health['records']}")
#     print(f"  Cache hit rate: {health['cache']['hit_rate']}")
#     print(f"  Errors: {health['errors']['total_errors']}")
    
#     dm.close()
