from src.data.unified_data_manager import UnifiedDataManager

def main():
    # Initialize
    manager = UnifiedDataManager()

    # Get stocks
    stocks = manager.get_stock_list('ALL')
    print(f"Loaded {len(stocks)} stocks")

    # Download historical data (with rate limiting)
    symbols = [s['symbol'] for s in stocks[1780:]]  # All stocks
    manager.download_historical_data(
        symbols,
        start_date='2025-10-01',
        batch_size=5,   # Pause after every 5 stocks
        delay=2.0       # Wait 2 seconds between batches
    )

    # Or use bulk download with parallel processing
    # manager.bulk_download(
    #     symbols,
    #     start_date='2024-01-01',
    #     max_workers=2  # Reduce workers to avoid rate limits
    # )

    # Or update daily (last 30 days)
    # manager.update_daily_data(lookback_days=30)

    # Check system health
    health = manager.get_system_health()
    print(health)

    # Retry failed downloads
    manager.retry_failed_updates()

    manager.close()

if __name__ == "__main__":
    main()