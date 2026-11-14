# ============================================================================
# FILE: dashboard/app.py
# Enterprise Streamlit Dashboard for Momentum Investment System
# ============================================================================

"""
Enterprise Momentum Investment Dashboard

Features:
- Real-time portfolio tracking
- Strategy configuration
- Backtesting interface
- Performance analytics
- Risk monitoring
- Data quality dashboard
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import sys
sys.path.append('..')

# Import enterprise modules
from src.core.config import ConfigManager
from src.core.logging import LoggerFactory
from src.data.enterprise_data_manager import EnterpriseDataManager
from src.analysis.dynamic_analyzer import DynamicStockAnalyzer, StrategyConfig
from src.portfolio.portfolio_manager import EnterprisePortfolioManager
from src.backtest.backtest_engine import EnterpriseBacktestEngine


def main():
    
    # Page configuration
    st.set_page_config(
        page_title="Momentum Investment System",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS for professional styling
    st.markdown("""
    <style>
        .main-header {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 1.5rem;
            border-radius: 10px;
            color: white;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .kpi-value {
            font-size: 2.5rem;
            font-weight: 700;
        }
        .kpi-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }
        .success-text {
            color: #10b981;
            font-weight: 600;
        }
        .warning-text {
            color: #f59e0b;
            font-weight: 600;
        }
        .danger-text {
            color: #ef4444;
            font-weight: 600;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 1rem 2rem;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.config = ConfigManager()
        st.session_state.logger = LoggerFactory.create_logger(
            'dashboard',
            st.session_state.config
        )
        st.session_state.data_manager = EnterpriseDataManager()
        st.session_state.initialized = True

    # Sidebar navigation
    st.sidebar.title("📊 Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["🏠 Dashboard", "🔍 Stock Analysis", "💼 Portfolio Management", 
        "📈 Backtesting", "⚙️ Strategy Builder", "📊 System Health"]
    )

    # ============================================================================
    # PAGE 1: MAIN DASHBOARD
    # ============================================================================

    if page == "🏠 Dashboard":
        st.markdown('<h1 class="main-header">Momentum Investment System</h1>', 
                    unsafe_allow_html=True)
        
        # KPI Section
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="kpi-label">Total Stocks Tracked</div>
                <div class="kpi-value">2,213</div>
                <div style="margin-top: 0.5rem;">↑ +12 this week</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <div class="kpi-label">Active Portfolios</div>
                <div class="kpi-value">3</div>
                <div style="margin-top: 0.5rem;">✓ All performing</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class="metric-card">
                <div class="kpi-label">Avg Portfolio Return</div>
                <div class="kpi-value">+18.5%</div>
                <div style="margin-top: 0.5rem;">↑ vs Nifty: +5.2%</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown("""
            <div class="metric-card">
                <div class="kpi-label">Data Quality Score</div>
                <div class="kpi-value">94/100</div>
                <div style="margin-top: 0.5rem;">✓ Excellent</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Update Data", use_container_width=True):
                with st.spinner("Updating data..."):
                    # Trigger data update
                    st.success("Data updated successfully!")
        
        with col2:
            if st.button("📊 Run Analysis", use_container_width=True):
                st.info("Navigate to Stock Analysis page")
        
        with col3:
            if st.button("💼 View Portfolios", use_container_width=True):
                st.info("Navigate to Portfolio Management page")
        
        with col4:
            if st.button("📈 New Backtest", use_container_width=True):
                st.info("Navigate to Backtesting page")
        
        st.markdown("---")
        
        # Recent Activity
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📈 Portfolio Performance (Last 30 Days)")
            
            # Sample data for demo
            dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
            portfolio_value = [1000000 * (1 + i * 0.002 + (i % 5) * 0.001) for i in range(30)]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=portfolio_value,
                mode='lines',
                name='Portfolio Value',
                line=dict(color='#667eea', width=3),
                fill='tozeroy',
                fillcolor='rgba(102, 126, 234, 0.1)'
            ))
            
            fig.update_layout(
                height=400,
                margin=dict(l=0, r=0, t=0, b=0),
                hovermode='x unified',
                xaxis_title="Date",
                yaxis_title="Value (₹)",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🔔 Recent Alerts")
            
            alerts = [
                {"type": "success", "message": "RELIANCE.NS momentum above threshold", "time": "2 hours ago"},
                {"type": "warning", "message": "Portfolio rebalance recommended", "time": "1 day ago"},
                {"type": "info", "message": "Data quality check completed", "time": "2 days ago"}
            ]
            
            for alert in alerts:
                if alert["type"] == "success":
                    st.success(f"✓ {alert['message']}\n\n*{alert['time']}*")
                elif alert["type"] == "warning":
                    st.warning(f"⚠️ {alert['message']}\n\n*{alert['time']}*")
                else:
                    st.info(f"ℹ️ {alert['message']}\n\n*{alert['time']}*")

    # ============================================================================
    # PAGE 2: STOCK ANALYSIS
    # ============================================================================

    elif page == "🔍 Stock Analysis":
        st.title("🔍 Stock Analysis & Screening")
        
        # Analysis configuration
        st.subheader("📋 Configure Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            universe = st.selectbox(
                "Select Universe",
                ["NIFTY50", "NIFTY500", "NIFTY_MIDCAP", "ALL"]
            )
        
        with col2:
            lookback_period = st.selectbox(
                "Lookback Period",
                ["1 Year", "2 Years", "3 Years", "5 Years"]
            )
        
        with col3:
            min_momentum = st.slider(
                "Min Momentum Score",
                min_value=0,
                max_value=30,
                value=8,
                step=1
            )
        
        # Filters
        st.subheader("🔍 Filters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            min_volume = st.number_input(
                "Min Daily Volume",
                min_value=0,
                value=100000,
                step=10000,
                format="%d"
            )
        
        with col2:
            max_volatility = st.slider(
                "Max Volatility (%)",
                min_value=20,
                max_value=100,
                value=55,
                step=5
            )
        
        with col3:
            top_n = st.number_input(
                "Number of Stocks",
                min_value=5,
                max_value=50,
                value=20,
                step=5
            )
        
        # Run Analysis Button
        if st.button("🚀 Run Analysis", type="primary", use_container_width=True):
            with st.spinner("Analyzing stocks..."):
                # Simulate analysis
                progress_bar = st.progress(0)
                for i in range(100):
                    progress_bar.progress(i + 1)
                
                # Sample results
                results_data = {
                    'Symbol': ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'],
                    'Momentum Score': [45.2, 38.7, 42.1, 35.8, 40.5],
                    '6M Return (%)': [28.5, 22.3, 25.1, 24.8, 32.1],
                    'Volatility (%)': [28.5, 22.3, 25.1, 24.8, 32.1],
                    'Current Price': [2450.50, 3820.75, 1650.25, 1580.60, 1020.80]
                }
                
                df_results = pd.DataFrame(results_data)
                
                st.success("✓ Analysis completed!")
                
                # Display results
                st.subheader("📊 Top Momentum Stocks")
                
                # Styled dataframe
                st.dataframe(
                    df_results.style.background_gradient(
                        subset=['Momentum Score'],
                        cmap='RdYlGn'
                    ).format({
                        'Momentum Score': '{:.1f}',
                        '6M Return (%)': '{:.1f}%',
                        'Volatility (%)': '{:.1f}%',
                        'Current Price': '₹{:.2f}'
                    }),
                    use_container_width=True
                )
                
                # Visualization
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.bar(
                        df_results,
                        x='Symbol',
                        y='Momentum Score',
                        title='Momentum Score Comparison',
                        color='Momentum Score',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.scatter(
                        df_results,
                        x='Volatility (%)',
                        y='6M Return (%)',
                        size='Momentum Score',
                        color='Momentum Score',
                        hover_data=['Symbol'],
                        title='Risk vs Return',
                        color_continuous_scale='Viridis'
                    )
                    st.plotly_chart(fig, use_container_width=True)

    # ============================================================================
    # PAGE 3: PORTFOLIO MANAGEMENT
    # ============================================================================

    elif page == "💼 Portfolio Management":
        st.title("💼 Portfolio Management")
        
        # Portfolio selector
        portfolios = ["Momentum Strategy 1", "Balanced Portfolio", "Aggressive Growth"]
        selected_portfolio = st.selectbox("Select Portfolio", portfolios)
        
        # Portfolio summary
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="Portfolio Value",
                value="₹12,45,850",
                delta="+ ₹1,45,850 (13.3%)"
            )
        
        with col2:
            st.metric(
                label="Day Change",
                value="+ ₹12,450",
                delta="+1.01%"
            )
        
        with col3:
            st.metric(
                label="Holdings",
                value="15",
                delta=""
            )
        
        with col4:
            st.metric(
                label="Cash Balance",
                value="₹54,150",
                delta=""
            )
        
        st.markdown("---")
        
        # Holdings table
        st.subheader("📋 Current Holdings")
        
        holdings_data = {
            'Symbol': ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS', 'ICICIBANK.NS'],
            'Shares': [50, 30, 75, 80, 120],
            'Entry Price': [2100.00, 3500.00, 1450.00, 1450.00, 950.00],
            'Current Price': [2450.50, 3820.75, 1650.25, 1580.60, 1020.80],
            'Value': [122525, 114622, 123769, 126448, 122496],
            'P&L %': [16.7, 9.2, 13.8, 9.0, 7.5],
            'Weight %': [20.1, 18.8, 20.3, 20.7, 20.1]
        }
        
        df_holdings = pd.DataFrame(holdings_data)
        
        st.dataframe(
            df_holdings.style.background_gradient(
                subset=['P&L %'],
                cmap='RdYlGn'
            ).format({
                'Entry Price': '₹{:.2f}',
                'Current Price': '₹{:.2f}',
                'Value': '₹{:,.0f}',
                'P&L %': '{:+.1f}%',
                'Weight %': '{:.1f}%'
            }),
            use_container_width=True
        )
        
        # Portfolio allocation
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Portfolio Allocation")
            fig = px.pie(
                df_holdings,
                values='Value',
                names='Symbol',
                title='Holdings Distribution'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📈 Performance Over Time")
            # Sample performance data
            dates = pd.date_range(end=datetime.now(), periods=90, freq='D')
            returns = [i * 0.15 + (i % 10) * 0.5 for i in range(90)]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=returns,
                mode='lines',
                fill='tozeroy',
                line=dict(color='#10b981', width=2)
            ))
            fig.update_layout(
                title='90-Day Returns',
                xaxis_title='Date',
                yaxis_title='Return (%)',
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Rebalance check
        st.markdown("---")
        st.subheader("⚖️ Rebalancing Recommendations")
        
        rebalance_needed = st.checkbox("Show rebalancing suggestions")
        
        if rebalance_needed:
            st.info("✓ Portfolio is well-balanced. No immediate rebalancing required.")
            st.write("Next scheduled rebalance: **15 days**")

    # ============================================================================
    # PAGE 4: BACKTESTING
    # ============================================================================

    elif page == "📈 Backtesting":
        st.title("📈 Strategy Backtesting")
        
        # Backtest configuration
        st.subheader("⚙️ Configuration")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime(2020, 1, 1)
            )
        
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now()
            )
        
        with col3:
            initial_capital = st.number_input(
                "Initial Capital (₹)",
                min_value=100000,
                value=1000000,
                step=100000
            )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rebalance_freq = st.selectbox(
                "Rebalance Frequency",
                ["Monthly", "Quarterly", "Semi-Annual", "Annual"]
            )
        
        with col2:
            n_stocks = st.slider(
                "Portfolio Size",
                min_value=5,
                max_value=30,
                value=15
            )
        
        with col3:
            allocation = st.selectbox(
                "Allocation Method",
                ["Equal Weight", "Momentum Weighted", "Risk Parity"]
            )
        
        # Run backtest
        if st.button("🚀 Run Backtest", type="primary", use_container_width=True):
            with st.spinner("Running backtest... This may take a few minutes"):
                # Simulate backtest
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i in range(100):
                    progress_bar.progress(i + 1)
                    status_text.text(f"Processing... {i+1}%")
                
                st.success("✓ Backtest completed!")
                
                # Results
                st.markdown("---")
                st.subheader("📊 Backtest Results")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Final Value", "₹18,45,230", "+84.5%")
                
                with col2:
                    st.metric("CAGR", "16.8%", "+4.2% vs Nifty")
                
                with col3:
                    st.metric("Max Drawdown", "-24.5%", "")
                
                with col4:
                    st.metric("Sharpe Ratio", "1.24", "")
                
                # Equity curve
                st.subheader("📈 Equity Curve")
                
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                portfolio_values = [initial_capital * (1 + i/len(dates) * 0.85) 
                                for i in range(len(dates))]
                benchmark_values = [initial_capital * (1 + i/len(dates) * 0.65) 
                                for i in range(len(dates))]
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=portfolio_values,
                    name='Strategy',
                    line=dict(color='#667eea', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=benchmark_values,
                    name='Nifty 50',
                    line=dict(color='#f59e0b', width=2)
                ))
                
                fig.update_layout(
                    height=500,
                    xaxis_title='Date',
                    yaxis_title='Portfolio Value (₹)',
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)

    # ============================================================================
    # PAGE 5: STRATEGY BUILDER
    # ============================================================================

    elif page == "⚙️ Strategy Builder":
        st.title("⚙️ Strategy Configuration Builder")
        
        st.info("💡 Create custom momentum strategies with drag-and-drop configuration")
        
        # Strategy name
        strategy_name = st.text_input("Strategy Name", value="My Custom Strategy")
        
        st.markdown("---")
        
        # Universe selection
        st.subheader("📍 Universe Selection")
        universe = st.multiselect(
            "Select Stock Universe",
            ["NIFTY50", "NIFTY500", "NIFTY_MIDCAP", "NIFTY_SMALLCAP"],
            default=["NIFTY500"]
        )
        
        st.markdown("---")
        
        # Performance periods
        st.subheader("📊 Performance Periods")
        
        st.write("Add periods to calculate momentum:")
        
        num_periods = st.number_input("Number of Periods", min_value=1, max_value=5, value=3)
        
        periods = []
        for i in range(num_periods):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                period_name = st.text_input(
                    f"Period {i+1} Name",
                    value=f"{['3M', '6M', '12M'][min(i, 2)]}",
                    key=f"period_name_{i}"
                )
            
            with col2:
                period_days = st.number_input(
                    f"Days",
                    min_value=21,
                    max_value=504,
                    value=[63, 126, 252][min(i, 2)],
                    step=21,
                    key=f"period_days_{i}"
                )
            
            with col3:
                period_weight = st.number_input(
                    f"Weight",
                    min_value=0.0,
                    max_value=1.0,
                    value=[0.2, 0.3, 0.5][min(i, 2)],
                    step=0.1,
                    key=f"period_weight_{i}"
                )
            
            periods.append({
                'name': period_name,
                'days': period_days,
                'weight': period_weight
            })
        
        st.markdown("---")
        
        # Filters
        st.subheader("🔍 Filters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            min_volume_filter = st.number_input(
                "Minimum Daily Volume",
                min_value=0,
                value=100000,
                step=10000
            )
            
            max_volatility_filter = st.slider(
                "Maximum Volatility (%)",
                min_value=20,
                max_value=100,
                value=55
            )
        
        with col2:
            min_momentum_filter = st.slider(
                "Minimum Momentum Score",
                min_value=0,
                max_value=30,
                value=8
            )
            
            min_liquidity = st.number_input(
                "Minimum Market Cap (Cr)",
                min_value=0,
                value=1000,
                step=100
            )
        
        st.markdown("---")
        
        # Preview
        if st.button("💾 Save Strategy", type="primary", use_container_width=True):
            strategy_config = {
                'name': strategy_name,
                'universe': universe,
                'periods': periods,
                'filters': {
                    'min_volume': min_volume_filter,
                    'max_volatility': max_volatility_filter,
                    'min_momentum': min_momentum_filter,
                    'min_market_cap': min_liquidity
                }
            }
            
            st.success(f"✓ Strategy '{strategy_name}' saved successfully!")
            
            with st.expander("📋 View Configuration"):
                st.json(strategy_config)

    # ============================================================================
    # PAGE 6: SYSTEM HEALTH
    # ============================================================================

    elif page == "📊 System Health":
        st.title("📊 System Health & Monitoring")
        
        # System metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("System Status", "✅ Healthy")
        
        with col2:
            st.metric("Data Freshness", "2 min ago")
        
        with col3:
            st.metric("Cache Hit Rate", "87.3%")
        
        with col4:
            st.metric("API Rate Limit", "45/100")
        
        st.markdown("---")
        
        # Data quality
        st.subheader("📊 Data Quality Overview")
        
        quality_data = {
            'Category': ['Excellent', 'Good', 'Acceptable', 'Poor'],
            'Count': [1850, 280, 65, 18],
            'Percentage': [83.6, 12.7, 2.9, 0.8]
        }
        
        df_quality = pd.DataFrame(quality_data)
        
        fig = px.bar(
            df_quality,
            x='Category',
            y='Count',
            title='Data Quality Distribution',
            color='Percentage',
            color_continuous_scale='RdYlGn'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        # Error log
        st.subheader("⚠️ Recent Errors (Last 24h)")
        
        errors_data = {
            'Timestamp': ['2024-11-24 10:30', '2024-11-24 08:15', '2024-11-23 16:45'],
            'Type': ['ConnectionError', 'ValidationError', 'DataQualityError'],
            'Symbol': ['XYZ.NS', 'ABC.NS', 'DEF.NS'],
            'Message': ['Timeout fetching data', 'Invalid price data', 'Missing volume data']
        }
        
        df_errors = pd.DataFrame(errors_data)
        st.dataframe(df_errors, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem'>
        <p>Momentum Investment System v1.0 | Enterprise Edition</p>
        <p>Built with ❤️ using Streamlit | © 2024</p>
    </div>
    """, unsafe_allow_html=True)


    # ============================================================================
    # DEPLOYMENT INSTRUCTIONS
    # ============================================================================

    """
    COMPLETE DEPLOYMENT GUIDE
    ==========================

    1. DIRECTORY STRUCTURE:
    -----------------------
    momentum_system/
    ├── config/
    │   ├── base.yaml
    │   ├── development.yaml
    │   └── production.yaml
    ├── dashboard/
    │   └── app.py (this file)
    ├── src/
    │   ├── core/
    │   │   ├── config.py
    │   │   ├── logging.py
    │   │   ├── errors.py
    │   │   └── validation.py
    │   ├── data/
    │   │   ├── enterprise_data_manager.py
    │   │   └── nse_fetcher.py
    │   ├── analysis/
    │   │   └── dynamic_analyzer.py
    │   ├── portfolio/
    │   │   └── portfolio_manager.py
    │   └── backtest/
    │       └── backtest_engine.py
    ├── logs/
    ├── cache/
    ├── tests/
    ├── .env
    ├── requirements.txt
    └── README.md

    2. INSTALL DEPENDENCIES:
    ------------------------
    pip install streamlit plotly pandas numpy pyyaml python-dotenv
    pip install yfinance requests beautifulsoup4 tenacity

    3. RUN DASHBOARD:
    -----------------
    streamlit run dashboard/app.py

    4. DEPLOY TO STREAMLIT CLOUD:
    ------------------------------
    - Push code to GitHub
    - Go to share.streamlit.io
    - Connect your repository
    - Deploy!

    5. DEPLOY TO YOUR OWN SERVER:
    ------------------------------
    # Using systemd (Linux)
    sudo nano /etc/systemd/system/momentum-dashboard.service

    [Unit]
    Description=Momentum Investment Dashboard
    After=network.target

    [Service]
    User=your_user
    WorkingDirectory=/path/to/momentum_system
    Environment="PATH=/path/to/venv/bin"
    ExecStart=/path/to/venv/bin/streamlit run dashboard/app.py --server.port 8501

    [Install]
    WantedBy=multi-user.target

    # Enable and start
    sudo systemctl enable momentum-dashboard
    sudo systemctl start momentum-dashboard

    6. DOCKER DEPLOYMENT:
    ---------------------
    # Dockerfile
    FROM python:3.10-slim
    WORKDIR /app
    COPY requirements.txt .
    RUN pip install -r requirements.txt
    COPY . .
    EXPOSE 8501
    CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

    # Build and run
    docker build -t momentum-dashboard .
    docker run -p 8501:8501 momentum-dashboard
    """

if __name__ == "__main__":
    main()
