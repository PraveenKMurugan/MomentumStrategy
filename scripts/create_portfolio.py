"""
Create your first portfolio
"""
from src.portfolio.portfolio_manager import EnterprisePortfolioManager
import pandas as pd

def main():
    print("="*80)
    print("CREATING PORTFOLIO")
    print("="*80)
    
    # Initialize portfolio manager
    pm = EnterprisePortfolioManager()
    
    # Load top stocks from previous analysis
    # (In practice, you'd load from results/ directory)
    
    # For demo, create sample stocks
    sample_stocks = pd.DataFrame({
        'symbol': ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'],
        'momentum_score': [45.2, 38.7, 42.1, 35.8, 40.5],
        'volatility': [28.5, 22.3, 25.1, 24.8, 32.1],
        'current_price': [2450.50, 3820.75, 1650.25, 1580.60, 1020.80]
    })
    
    # Calculate positions
    print("\nCalculating position sizes...")
    positions = pm.calculate_position_sizes(
        sample_stocks,
        capital=1000000,  # 10 lakhs
        method='risk_parity'
    )
    
    # Create portfolio
    portfolio_id = pm.create_portfolio(
        positions,
        portfolio_name='My First Momentum Portfolio',
        initial_capital=1000000,
        allocation_method='risk_parity'
    )
    
    print(f"\n✓ Portfolio created! ID: {portfolio_id}")
    
    # Display summary
    pm.get_portfolio_summary(portfolio_id)
    
    pm.close()

if __name__ == "__main__":
    main()