"""
Run your first backtest
"""
from src.backtest.backtest_engine import EnterpriseBacktestEngine
from src.analysis.dynamic_analyzer import PresetStrategies

def main():
    print("="*80)
    print("RUNNING BACKTEST")
    print("="*80)
    
    # Initialize engine
    engine = EnterpriseBacktestEngine()
    
    # Create strategy
    strategy = PresetStrategies.balanced_momentum()
    
    print("\nBacktesting strategy...")
    print("This may take a few minutes...\n")
    
    # Run backtest
    results = engine.run_backtest(
        strategy_config=strategy,
        start_date='2018-01-01',
        end_date='2023-12-31',
        initial_capital=1000000,
        rebalance_frequency='6M',
        n_stocks=15,
        allocation_method='risk_parity'
    )
    
    # Calculate metrics
    metrics = engine.calculate_metrics()
    
    # Display results
    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)
    for key, value in metrics.items():
        print(f"{key:<30}: {value}")
    print("="*80)
    
    # Export results
    engine.export_results()
    print("\n✓ Results exported to results/ directory")
    
    engine.close()

if __name__ == "__main__":
    main()