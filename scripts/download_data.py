"""
Download historical data for NSE stocks
"""
from src.data.unified_data_manager import UnifiedDataManager
from datetime import datetime

def main():
    print("="*80)
    print("DOWNLOADING NSE STOCK DATA")
    print("="*80)
    
    # Initialize
    dm = UnifiedDataManager()
    
    # Option 1: Download sample (fast, for testing)
    print("\nOption 1: Download 50 stocks for testing")
    print("Option 2: Download NIFTY 500 (~500 stocks)")
    print("Option 3: Download ALL stocks (~2213 stocks)")
    
    choice = input("\nEnter your choice (1/2/3): ")
    
    if choice == "1":
        # Get first 50 stocks
        stocks = dm.get_stock_list('NIFTY50')
        stocks = stocks[:50]
    elif choice == "2":
        stocks = dm.get_stock_list('NIFTY500')
    else:
        stocks = dm.get_stock_list('ALL')
    
    symbols = [s['symbol'] for s in stocks]
    
    print(f"\nDownloading data for {len(symbols)} stocks...")
    print("This may take a while. Go grab a coffee! ☕")
    
    # Download
    dm.bulk_download(
        symbols,
        start_date='2014-01-01'  # 10+ years of data
    )
    
    # Show health report
    print("\n" + "="*80)
    print("DATA DOWNLOAD COMPLETE!")
    print("="*80)
    
    health = dm.get_system_health()
    print(f"Total stocks: {health['stocks']}")
    print(f"Total records: {health['records']}")
    print(f"Data quality: {health.get('quality_distribution', {})}")
    
    dm.close()
    print("\n✓ Ready to run analysis!")

if __name__ == "__main__":
    main()