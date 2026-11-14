# ============================================================================
# FILE: dashboard/enhanced_app.py
# Enhanced Enterprise Dashboard with Full Integration
# ============================================================================

"""
Enhanced Momentum Investment Dashboard

NEW FEATURES:
- Integrated workflow (Analysis → Backtest → Portfolio)
- Strategy comparison tool
- Workflow history and tracking
- One-click portfolio creation
- Performance monitoring
- Smart recommendations
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
sys.path.append('..')

# Import all components
from src.core.config import ConfigManager
from src.core.logging import LoggerFactory
from src.analysis.dynamic_analyzer import (
    DynamicStockAnalyzer, 
    StrategyConfig, 
    PresetStrategies
)
from src.portfolio.portfolio_manager import EnterprisePortfolioManager
from src.backtest.backtest_engine import EnterpriseBacktestEngine
from src.workflow.integrated_manager import IntegratedWorkflowManager


def main():
    
    # Page configuration
    st.set_page_config(
        page_title="Momentum Investment System - Enhanced",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Custom CSS
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
        .success-box {
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .warning-box {
            background-color: #fff3cd;
            border: 1px solid #ffeeba;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
        }
        .info-box {
            background-color: #d1ecf1;
            border: 1px solid #bee5eb;
            border-radius: 5px;
            padding: 1rem;
            margin: 1rem 0;
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
        st.session_state.workflow_manager = IntegratedWorkflowManager()
        st.session_state.initialized = True
        
        # Workflow state
        st.session_state.current_strategy = None
        st.session_state.analysis_results = None
        st.session_state.backtest_results = None
        st.session_state.portfolio_id = None

    # Sidebar navigation
    st.sidebar.title("🚀 Navigation")
    page = st.sidebar.radio(
        "Go to",
        [
            "🏠 Dashboard",
            "⚡ Integrated Workflow",
            "📊 Strategy Comparison", 
            "🔍 Stock Analysis",
            "📈 Backtesting",
            "💼 Portfolio Management",
            "⚙️ Strategy Builder",
            "📜 Workflow History",
            "🔧 System Health"
        ]
    )

    wfm = st.session_state.workflow_manager

    # ============================================================================
    # PAGE 1: DASHBOARD (Enhanced)
    # ============================================================================

    if page == "🏠 Dashboard":
        st.markdown('<h1 class="main-header">Momentum Investment System</h1>', 
                    unsafe_allow_html=True)
        
        # Quick Stats
        col1, col2, col3, col4 = st.columns(4)
        
        history = wfm.get_workflow_history(limit=100)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">Total Workflows</div>
                <div style="font-size: 2.5rem; font-weight: 700;">{len(history)}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            completed = len(history[history['status'] == 'completed'])
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">Completed</div>
                <div style="font-size: 2.5rem; font-weight: 700;">{completed}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            portfolios = len(history[history['portfolio_created'] == 1])
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">Portfolios Created</div>
                <div style="font-size: 2.5rem; font-weight: 700;">{portfolios}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; opacity: 0.9;">Success Rate</div>
                <div style="font-size: 2.5rem; font-weight: 700;">{completed/max(1,len(history))*100:.0f}%</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick Actions
        st.subheader("⚡ Quick Actions")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🚀 New Workflow", use_container_width=True, type="primary"):
                st.switch_page = "⚡ Integrated Workflow"
                st.rerun()
        
        with col2:
            if st.button("📊 Compare Strategies", use_container_width=True):
                st.switch_page = "📊 Strategy Comparison"
                st.rerun()
        
        with col3:
            if st.button("💼 View Portfolios", use_container_width=True):
                st.switch_page = "💼 Portfolio Management"
                st.rerun()
        
        with col4:
            if st.button("📜 View History", use_container_width=True):
                st.switch_page = "📜 Workflow History"
                st.rerun()
        
        st.markdown("---")
        
        # Recent Workflows
        st.subheader("📜 Recent Workflows")
        
        if not history.empty:
            recent = history.head(10)
            
            # Format display
            display_df = recent[['workflow_name', 'strategy_name', 'created_date', 
                                'status', 'portfolio_created']].copy()
            display_df['created_date'] = pd.to_datetime(display_df['created_date']).dt.strftime('%Y-%m-%d %H:%M')
            display_df.columns = ['Workflow', 'Strategy', 'Created', 'Status', 'Portfolio']
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("No workflows yet. Create your first workflow!")

    # ============================================================================
    # PAGE 2: INTEGRATED WORKFLOW (NEW)
    # ============================================================================

    elif page == "⚡ Integrated Workflow":
        st.title("⚡ Integrated Workflow")
        st.markdown("**Complete workflow: Strategy → Analysis → Backtest → Portfolio**")
        
        # Workflow Configuration
        st.subheader("📋 Step 1: Configure Workflow")
        
        col1, col2 = st.columns(2)
        
        with col1:
            workflow_name = st.text_input(
                "Workflow Name",
                value=f"Workflow_{datetime.now().strftime('%Y%m%d_%H%M')}"
            )
        
        with col2:
            preset_strategy = st.selectbox(
                "Select Preset Strategy",
                [
                    "Balanced Momentum",
                    "Short Term Momentum",
                    "Classic Momentum",
                    "Six Month Momentum",
                    "Custom"
                ]
            )
        
        # Get strategy config
        strategy_map = {
            "Balanced Momentum": PresetStrategies.balanced_momentum(),
            "Short Term Momentum": PresetStrategies.short_term_momentum(),
            "Classic Momentum": PresetStrategies.classic_momentum(),
            "Six Month Momentum": PresetStrategies.six_month_momentum()
        }
        
        if preset_strategy != "Custom":
            strategy_config = strategy_map[preset_strategy]
            st.session_state.current_strategy = strategy_config
            
            with st.expander("📊 View Strategy Configuration"):
                st.json(strategy_config.to_dict())
        else:
            st.info("Custom strategy builder available in Strategy Builder page")
        
        st.markdown("---")
        
        # Backtest Parameters
        st.subheader("📈 Step 2: Backtest Parameters")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime(2020, 1, 1)
            )
        
        with col2:
            initial_capital = st.number_input(
                "Initial Capital (₹)",
                min_value=100000,
                value=1000000,
                step=100000
            )
        
        with col3:
            rebalance_freq = st.selectbox(
                "Rebalance Frequency",
                ["3M", "6M", "12M"]
            )
        
        col1, col2 = st.columns(2)
        
        with col1:
            n_stocks = st.slider("Portfolio Size", 5, 30, 15)
        
        with col2:
            allocation = st.selectbox(
                "Allocation Method",
                ["risk_parity", "equal_weight", "momentum_weighted"]
            )
        
        auto_create = st.checkbox(
            "Auto-create portfolio if backtest passes criteria",
            value=False,
            help="Portfolio will be created automatically if CAGR > 15%, Sharpe > 1.0, and MDD > -25%"
        )
        
        st.markdown("---")
        
        # Run Workflow Button
        if st.button("🚀 Run Complete Workflow", type="primary", use_container_width=True):
            if st.session_state.current_strategy is None:
                st.error("Please select a strategy first!")
            else:
                with st.spinner("Running complete workflow... This may take several minutes"):
                    
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("Stage 1/3: Running Analysis...")
                    progress_bar.progress(10)
                    
                    # Run workflow
                    results = wfm.run_complete_workflow(
                        strategy_config=st.session_state.current_strategy,
                        workflow_name=workflow_name,
                        backtest_params={
                            'start_date': start_date.strftime('%Y-%m-%d'),
                            'initial_capital': initial_capital,
                            'rebalance_frequency': rebalance_freq,
                            'n_stocks': n_stocks,
                            'allocation_method': allocation
                        },
                        auto_create_portfolio=auto_create
                    )
                    
                    progress_bar.progress(100)
                    status_text.text("✓ Workflow Complete!")
                    
                    st.success(f"✓ Workflow completed: {results['status']}")
                    
                    # Store results in session
                    st.session_state.workflow_results = results
                    
                    # Display Results
                    st.markdown("---")
                    st.subheader("📊 Workflow Results")
                    
                    # Analysis Results
                    if 'analysis' in results['stages']:
                        analysis = results['stages']['analysis']
                        
                        if analysis['success']:
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "Stocks Analyzed",
                                    analysis['total_analyzed']
                                )
                            
                            with col2:
                                st.metric(
                                    "After Filters",
                                    analysis['after_filters']
                                )
                            
                            with col3:
                                st.metric(
                                    "Top Stocks",
                                    analysis['top_stocks_count']
                                )
                            
                            # Show top stocks
                            with st.expander("📋 Top Stocks Details"):
                                top_df = pd.DataFrame(analysis['top_stocks'])
                                st.dataframe(top_df, use_container_width=True)
                    
                    # Backtest Results
                    if 'backtest' in results['stages']:
                        backtest = results['stages']['backtest']
                        
                        if backtest['success']:
                            st.markdown("---")
                            st.subheader("📈 Backtest Performance")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            
                            metrics = backtest['metrics']
                            
                            with col1:
                                st.metric("CAGR", f"{metrics['CAGR (%)']:.2f}%")
                            
                            with col2:
                                st.metric("Sharpe Ratio", f"{metrics['Sharpe Ratio']:.2f}")
                            
                            with col3:
                                st.metric("Max Drawdown", f"{metrics['Max Drawdown (%)']:.2f}%")
                            
                            with col4:
                                st.metric("Win Rate", f"{metrics['Win Rate (%)']:.1f}%")
                    
                    # Recommendation
                    if 'recommendation' in results:
                        st.markdown("---")
                        st.subheader("💡 Recommendation")
                        
                        rec = results['recommendation']
                        
                        if rec['create_portfolio']:
                            st.markdown(f"""
                            <div class="success-box">
                                <h4>✅ Recommended: Create Portfolio</h4>
                                <p><strong>Reason:</strong> {rec['reason']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if not auto_create:
                                if st.button("✅ Create Portfolio Now", type="primary"):
                                    st.info("Creating portfolio... (Implement portfolio creation)")
                        else:
                            st.markdown(f"""
                            <div class="warning-box">
                                <h4>⚠️ Not Recommended: Review Strategy</h4>
                                <p><strong>Reason:</strong> {rec['reason']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    
                    # Portfolio Results (if created)
                    if 'portfolio' in results['stages']:
                        portfolio = results['stages']['portfolio']
                        
                        if portfolio['success']:
                            st.markdown("---")
                            st.subheader("💼 Portfolio Created")
                            
                            st.success(f"Portfolio ID: {portfolio['portfolio_id']}")
                            
                            # Portfolio summary
                            summary = portfolio['summary']
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric(
                                    "Portfolio Value",
                                    f"₹{summary['total_current_value']:,.0f}"
                                )
                            
                            with col2:
                                st.metric(
                                    "Number of Holdings",
                                    summary['num_holdings']
                                )
                            
                            with col3:
                                st.metric(
                                    "P&L",
                                    f"{summary['unrealized_pnl_pct']:.2f}%"
                                )

    # ============================================================================
    # PAGE 3: STRATEGY COMPARISON (NEW)
    # ============================================================================

    elif page == "📊 Strategy Comparison":
        st.title("📊 Strategy Comparison")
        st.markdown("**Compare multiple strategies side-by-side**")
        
        # Comparison Configuration
        col1, col2 = st.columns([2, 1])
        
        with col1:
            comparison_name = st.text_input(
                "Comparison Name",
                value=f"Comparison_{datetime.now().strftime('%Y%m%d')}"
            )
        
        with col2:
            start_date = st.date_input(
                "Backtest Start Date",
                value=datetime(2020, 1, 1)
            )
        
        # Strategy Selection
        st.subheader("Select Strategies to Compare")
        
        col1, col2, col3 = st.columns(3)
        
        strategies_to_compare = []
        
        with col1:
            if st.checkbox("Balanced Momentum", value=True):
                strategies_to_compare.append(PresetStrategies.balanced_momentum())
        
        with col2:
            if st.checkbox("Short Term Momentum"):
                strategies_to_compare.append(PresetStrategies.short_term_momentum())
        
        with col3:
            if st.checkbox("Classic Momentum"):
                strategies_to_compare.append(PresetStrategies.classic_momentum())
        
        st.markdown("---")
        
        if st.button("▶️ Run Comparison", type="primary", use_container_width=True):
            if len(strategies_to_compare) < 2:
                st.error("Please select at least 2 strategies to compare")
            else:
                with st.spinner(f"Comparing {len(strategies_to_compare)} strategies..."):
                    
                    results = wfm.compare_strategies(
                        strategies=strategies_to_compare,
                        comparison_name=comparison_name,
                        backtest_params={'start_date': start_date.strftime('%Y-%m-%d')}
                    )
                    
                    st.success("✓ Comparison complete!")
                    
                    # Display Results
                    st.markdown("---")
                    st.subheader("📊 Comparison Results")
                    
                    # Winner
                    st.markdown(f"""
                    <div class="success-box">
                        <h3>🏆 Winner: {results['winner']}</h3>
                        <p>Sharpe Ratio: {results['winner_sharpe']:.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Detailed Comparison Table
                    st.subheader("📋 Detailed Metrics")
                    
                    comparison_df = pd.DataFrame(results['strategies'])
                    
                    # Reorder columns
                    metric_cols = ['strategy_name', 'cagr', 'sharpe', 'max_drawdown', 
                                  'total_return', 'volatility', 'win_rate']
                    comparison_df = comparison_df[metric_cols]
                    comparison_df.columns = ['Strategy', 'CAGR (%)', 'Sharpe', 'Max DD (%)', 
                                           'Total Return (%)', 'Volatility (%)', 'Win Rate (%)']
                    
                    st.dataframe(
                        comparison_df.style.highlight_max(
                            subset=['CAGR (%)', 'Sharpe', 'Total Return (%)', 'Win Rate (%)'],
                            color='lightgreen'
                        ).highlight_min(
                            subset=['Max DD (%)', 'Volatility (%)'],
                            color='lightcoral'
                        ),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                    # Visual Comparison
                    st.subheader("📊 Visual Comparison")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.bar(
                            comparison_df,
                            x='Strategy',
                            y='Sharpe',
                            title='Sharpe Ratio Comparison',
                            color='Sharpe',
                            color_continuous_scale='Viridis'
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        fig = px.scatter(
                            comparison_df,
                            x='Volatility (%)',
                            y='CAGR (%)',
                            size='Sharpe',
                            color='Strategy',
                            title='Risk vs Return',
                            hover_data=['Win Rate (%)']
                        )
                        st.plotly_chart(fig, use_container_width=True)

    # ============================================================================
    # PAGE 4: WORKFLOW HISTORY (NEW)
    # ============================================================================

    elif page == "📜 Workflow History":
        st.title("📜 Workflow History")
        
        # Get history
        history = wfm.get_workflow_history(limit=50)
        
        if not history.empty:
            # Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_filter = st.multiselect(
                    "Filter by Status",
                    options=history['status'].unique(),
                    default=history['status'].unique()
                )
            
            with col2:
                strategy_filter = st.multiselect(
                    "Filter by Strategy",
                    options=history['strategy_name'].unique(),
                    default=history['strategy_name'].unique()
                )
            
            # Apply filters
            filtered = history[
                (history['status'].isin(status_filter)) &
                (history['strategy_name'].isin(strategy_filter))
            ]
            
            # Display
            st.dataframe(
                filtered[[
                    'workflow_id', 'workflow_name', 'strategy_name', 
                    'created_date', 'status', 'portfolio_created'
                ]],
                use_container_width=True,
                hide_index=True
            )
            
            # Workflow Details
            st.markdown("---")
            st.subheader("🔍 View Workflow Details")
            
            selected_id = st.number_input(
                "Enter Workflow ID",
                min_value=1,
                step=1
            )
            
            if st.button("📄 Load Details"):
                details = wfm.get_workflow_details(selected_id)
                
                if details:
                    st.json(details)
                else:
                    st.error(f"Workflow {selected_id} not found")
        
        else:
            st.info("No workflow history yet")

    # Keep other existing pages (Stock Analysis, Backtesting, etc.)
    # Add them here with elif statements...

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem'>
        <p>Momentum Investment System v2.0 | Enterprise Edition with Integrated Workflows</p>
        <p>Built with ❤️ using Streamlit | © 2024</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()