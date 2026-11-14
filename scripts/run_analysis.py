"""
Run your first momentum analysis
"""
from src.analysis.dynamic_analyzer import (
    DynamicStockAnalyzer, 
    StrategyConfig,
    PresetStrategies
)

def main():
    print("="*80)
    print("RUNNING MOMENTUM ANALYSIS")
    print("="*80)
    
    # Initialize analyzer
    analyzer = DynamicStockAnalyzer()
    
    # Use preset strategy
    config = PresetStrategies.balanced_momentum()
    config.display()
    
    # Set configuration
    analyzer.set_config(config)
    
    # Run analysis
    print("\nAnalyzing stocks...")
    results = analyzer.analyze_universe()
    
    # Apply filters
    filtered = analyzer.apply_filters(results)
    
    # Get top 20
    top_20 = analyzer.select_top_stocks(filtered, n=20)
    
    # Display results
    print("\n" + "="*80)
    print("TOP 20 MOMENTUM STOCKS")
    print("="*80)
    print(top_20[['symbol', 'momentum_score', 'current_price']].to_string(index=False))
    
    # Save results
    analyzer.save_analysis(top_20)
    print("\n✓ Results saved to results/ directory")
    
    analyzer.close()

if __name__ == "__main__":
    main()