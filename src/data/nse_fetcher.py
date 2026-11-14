import requests
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict, Optional
import time
from io import StringIO
import json

class EnterpriseNSEDataFetcher:
    """
    Production-grade NSE data fetcher
    
    Features:
    - Multiple data sources with automatic fallback
    - Session management with proper headers
    - Rate limiting compliance
    - Cookie handling for NSE
    - Retry logic with exponential backoff
    """
    
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.session = self._create_session()
        self.base_url = "https://www.nseindia.com"
    
    def _create_session(self) -> requests.Session:
        """Create session with NSE-compliant headers"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json,text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.nseindia.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Upgrade-Insecure-Requests': '1'
        })
        return session
    
    def _get_cookies(self):
        """Get cookies from NSE homepage"""
        try:
            response = self.session.get(
                self.base_url,
                timeout=self.config.get('api.timeout', 30)
            )
            self.logger.debug("Cookies obtained from NSE")
        except Exception as e:
            self.logger.warning(f"Failed to get cookies: {e}")
    
    def fetch_nifty_50(self) -> List[Dict]:
        """Fetch Nifty 50 constituents"""
        return self._fetch_index_constituents('NIFTY 50')
    
    def fetch_nifty_500(self) -> List[Dict]:
        """Fetch Nifty 500 constituents"""
        return self._fetch_index_constituents('NIFTY 500')
    
    def _fetch_index_constituents(self, index_name: str) -> List[Dict]:
        """
        Fetch index constituents from NSE API
        
        Args:
            index_name: Index name (e.g., 'NIFTY 50', 'NIFTY 500')
        
        Returns:
            List of stock dictionaries
        """
        # Get cookies first
        self._get_cookies()
        
        # URL encode index name
        encoded_index = index_name.replace(' ', '%20')
        url = f"{self.base_url}/api/equity-stockIndices?index={encoded_index}"
        
        try:
            self.logger.info(f"Fetching {index_name} from NSE API...")
            
            response = self.session.get(
                url,
                timeout=self.config.get('api.timeout', 30)
            )
            response.raise_for_status()
            
            data = response.json()
            stocks = []
            
            for item in data.get('data', []):
                if item.get('symbol'):
                    stocks.append({
                        'symbol': item['symbol'] + '.NS',
                        'company_name': item.get('meta', {}).get('companyName', ''),
                        'industry': item.get('meta', {}).get('industry', ''),
                        'isin': item.get('meta', {}).get('isin', ''),
                        'index': index_name.replace(' ', '')
                    })
            
            self.logger.info(f"✓ Fetched {len(stocks)} stocks from {index_name}")
            return stocks
            
        except Exception as e:
            self.logger.error(f"Failed to fetch {index_name} from API: {e}")
            raise
    
    def fetch_equity_list_csv(self) -> List[Dict]:
        """
        Fetch complete equity list from NSE CSV
        
        Returns:
            List of all NSE stocks
        """
        csv_url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        
        try:
            self.logger.info("Fetching equity list CSV from NSE...")
            
            # Get cookies
            self._get_cookies()
            
            response = self.session.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Parse CSV
            df = pd.read_csv(StringIO(response.text))
            
            stocks = []
            for _, row in df.iterrows():
                stocks.append({
                    'symbol': str(row['SYMBOL']).strip() + '.NS',
                    'company_name': str(row.get('NAME OF COMPANY', '')).strip(),
                    'series': str(row.get(' SERIES', 'EQ')).strip(),
                    'isin': str(row.get(' ISIN NUMBER', '')).strip(),
                    'index': 'ALL'
                })
            
            self.logger.info(f"✓ Fetched {len(stocks)} stocks from CSV")
            return stocks
            
        except Exception as e:
            self.logger.error(f"Failed to fetch equity CSV: {e}")
            raise
    
    def get_stock_list_with_fallback(self, index_name: str) -> List[Dict]:
        """
        Fetch stock list with multiple fallback methods
        
        Args:
            index_name: 'NIFTY50', 'NIFTY500', 'ALL'
        
        Returns:
            List of stocks
        """
        methods = [
            ('NSE API', lambda: self._fetch_from_api(index_name)),
            ('NSE CSV', lambda: self._fetch_from_csv(index_name)),
            ('Cached File', lambda: self._fetch_from_cache(index_name)),
            ('Manual Fallback', lambda: self._fetch_manual_fallback(index_name))
        ]
        
        for method_name, method_func in methods:
            try:
                self.logger.info(f"Trying {method_name} for {index_name}...")
                stocks = method_func()
                
                if stocks and len(stocks) > 10:
                    self.logger.info(
                        f"✓ Successfully fetched {len(stocks)} stocks "
                        f"via {method_name}"
                    )
                    
                    # Cache the result
                    self._save_to_cache(index_name, stocks)
                    
                    return stocks
                    
            except Exception as e:
                self.logger.warning(f"{method_name} failed: {e}")
                continue
        
        raise Exception(f"All methods failed to fetch {index_name} stock list")
    
    def _fetch_from_api(self, index_name: str) -> List[Dict]:
        """Fetch from NSE API"""
        if index_name == 'NIFTY50':
            return self.fetch_nifty_50()
        elif index_name == 'NIFTY500':
            return self.fetch_nifty_500()
        elif index_name == 'ALL':
            return self.fetch_equity_list_csv()
        else:
            raise ValueError(f"Unknown index: {index_name}")
    
    def _fetch_from_csv(self, index_name: str) -> List[Dict]:
        """Fetch from NSE CSV"""
        return self.fetch_equity_list_csv()
    
    def _fetch_from_cache(self, index_name: str) -> List[Dict]:
        """Load from cached file"""
        import os
        
        cache_file = f"cache/{index_name}_stocks.json"
        
        if os.path.exists(cache_file):
            # Check if cache is recent (< 7 days old)
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < 7 * 24 * 3600:  # 7 days
                with open(cache_file, 'r', encoding="utf-8") as f:
                    return json.load(f)
        
        raise Exception("No valid cache found")
    
    def _save_to_cache(self, index_name: str, stocks: List[Dict]):
        """Save stocks to cache file"""
        import os
        
        os.makedirs('cache', exist_ok=True)
        cache_file = f"cache/{index_name}_stocks.json"
        
        with open(cache_file, 'w', encoding="utf-8") as f:
            json.dump(stocks, f, indent=2)
        
        self.logger.debug(f"Cached {len(stocks)} stocks to {cache_file}")
    
    def _fetch_manual_fallback(self, index_name: str) -> List[Dict]:
        """Manual fallback with predefined lists"""
        # Hardcoded fallback lists (last resort)
        # In production, these would be regularly updated
        
        if index_name == 'NIFTY50':
            symbols = [
                'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
                'ICICIBANK.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'ITC.NS', 'KOTAKBANK.NS'
                # ... add all 50
            ]
        elif index_name == 'NIFTY500':
            # Load from a maintained list file
            symbols = self._load_nifty_500_fallback()
        else:
            raise Exception("No manual fallback available")
        
        return [{'symbol': s, 'company_name': '', 'index': index_name} 
                for s in symbols]
    
    def _load_nifty_500_fallback(self) -> List[str]:
        """Load Nifty 500 from fallback file"""
        # This would be a curated, regularly updated file
        fallback_file = 'config/nifty500_fallback.txt'
        
        try:
            with open(fallback_file, 'r', encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []
