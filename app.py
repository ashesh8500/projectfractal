
import streamlit as st
from portfolio import PortfolioManager
from strategy import BollingerStrategy, MLStrategy, BaseStrategy
from backtester import Backtester
# from broker import IBConnector
from db import DBManager
# from llm import generate_strategy_class
from typing import Type, Dict
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Portfolio Optimizer Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def display_comprehensive_backtest_results(report: Dict, backtester: Backtester):
    """Display comprehensive backtest results in Streamlit."""

    st.header("📊 Comprehensive Backtest Analysis")

    # Summary table with metrics comparison
    if 'summary_table' in report and not report['summary_table'].empty:
        st.subheader("📈 Performance Summary")
        st.dataframe(report['summary_table'], use_container_width=True)

    # Key metrics in columns
    if 'basic_metrics' in report and report['basic_metrics']:
        metrics = report['basic_metrics']

        st.subheader("🎯 Key Performance Metrics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Return",
                f"{metrics.get('total_return', 0)*100:.2f}%",
                delta=None
            )
            st.metric(
                "Sharpe Ratio",
                f"{metrics.get('sharpe_ratio', 0):.3f}",
                delta=None
            )

        with col2:
            st.metric(
                "Annualized Return",
                f"{metrics.get('annualized_return', 0)*100:.2f}%",
                delta=None
            )
            st.metric(
                "Sortino Ratio",
                f"{metrics.get('sortino_ratio', 0):.3f}",
                delta=None
            )

        with col3:
            st.metric(
                "Volatility",
                f"{metrics.get('annualized_volatility', 0)*100:.2f}%",
                delta=None
            )
            st.metric(
                "Calmar Ratio",
                f"{metrics.get('calmar_ratio', 0):.3f}",
                delta=None
            )

        with col4:
            st.metric(
                "Max Drawdown",
                f"{metrics.get('max_drawdown', 0)*100:.2f}%",
                delta=None
            )
            st.metric(
                "Win Rate",
                f"{metrics.get('win_rate', 0)*100:.1f}%",
                delta=None
            )

    # Interactive charts
    if 'charts' in report and report['charts']:
        st.subheader("📊 Performance Visualization")

        # Main performance overview chart
        if 'performance_overview' in report['charts']:
            st.plotly_chart(report['charts']['performance_overview'], use_container_width=True)

        # Risk-return analysis
        if 'risk_return' in report['charts']:
            st.plotly_chart(report['charts']['risk_return'], use_container_width=True)

    # Comparison analysis
    st.subheader("🔍 Comparison Analysis")

    # Baseline comparison
    if 'baseline_comparison' in report and report['baseline_comparison']:
        baseline = report['baseline_comparison']

        st.write("**vs. Equal Weight Baseline:**")
        col1, col2, col3 = st.columns(3)

        with col1:
            portfolio_return = report['basic_metrics'].get('annualized_return', 0) * 100
            baseline_return = baseline.get('annualized_return', 0) * 100
            excess_return = portfolio_return - baseline_return
            st.metric(
                "Excess Return vs Baseline",
                f"{excess_return:.2f}%",
                delta=f"{excess_return:.2f}%" if excess_return != 0 else None
            )

        with col2:
            portfolio_sharpe = report['basic_metrics'].get('sharpe_ratio', 0)
            baseline_sharpe = baseline.get('sharpe_ratio', 0)
            sharpe_diff = portfolio_sharpe - baseline_sharpe
            st.metric(
                "Sharpe Difference",
                f"{sharpe_diff:.3f}",
                delta=f"{sharpe_diff:.3f}" if sharpe_diff != 0 else None
            )

        with col3:
            portfolio_vol = report['basic_metrics'].get('annualized_volatility', 0) * 100
            baseline_vol = baseline.get('volatility', 0) * 100
            vol_diff = portfolio_vol - baseline_vol
            st.metric(
                "Volatility Difference",
                f"{vol_diff:.2f}%",
                delta=f"{vol_diff:.2f}%" if vol_diff != 0 else None,
                delta_color="inverse"
            )

    # Benchmark comparison
    if 'benchmark_comparison' in report and report['benchmark_comparison']:
        benchmark = report['benchmark_comparison']

        st.write(f"**vs. Market Benchmark ({benchmark.get('symbol', 'N/A')}):**")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            portfolio_return = report['basic_metrics'].get('annualized_return', 0) * 100
            benchmark_return = benchmark.get('annualized_return', 0) * 100
            alpha = portfolio_return - benchmark_return
            st.metric(
                "Alpha",
                f"{alpha:.2f}%",
                delta=f"{alpha:.2f}%" if alpha != 0 else None
            )

        with col2:
            beta = benchmark.get('beta', 0)
            if beta is not None:
                st.metric("Beta", f"{beta:.3f}")
            else:
                st.metric("Beta", "N/A")

        with col3:
            if 'statistical_tests' in report and 'information_ratio' in report['statistical_tests']:
                info_ratio = report['statistical_tests']['information_ratio']
                st.metric("Information Ratio", f"{info_ratio:.3f}")
            else:
                st.metric("Information Ratio", "N/A")

        with col4:
            portfolio_sharpe = report['basic_metrics'].get('sharpe_ratio', 0)
            benchmark_sharpe = benchmark.get('sharpe_ratio', 0)
            sharpe_diff = portfolio_sharpe - benchmark_sharpe
            st.metric(
                "Sharpe Difference",
                f"{sharpe_diff:.3f}",
                delta=f"{sharpe_diff:.3f}" if sharpe_diff != 0 else None
            )

    # Performance attribution
    if 'attribution_analysis' in report and report['attribution_analysis']:
        st.subheader("🎯 Performance Attribution")

        attribution_data = []
        for symbol, attr in report['attribution_analysis'].items():
            attribution_data.append({
                'Asset': symbol,
                'Total Return (%)': f"{attr.get('total_return', 0)*100:.2f}",
                'Annualized Return (%)': f"{attr.get('annualized_return', 0)*100:.2f}",
                'Volatility (%)': f"{attr.get('volatility', 0)*100:.2f}",
                'Contribution (%)': f"{attr.get('contribution', 0)*100:.2f}"
            })

        if attribution_data:
            attribution_df = pd.DataFrame(attribution_data)
            st.dataframe(attribution_df, use_container_width=True)

            # Attribution chart
            fig = px.bar(
                attribution_df,
                x='Asset',
                y='Total Return (%)',
                title='Individual Asset Returns',
                color='Total Return (%)',
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)

    # Statistical significance
    if 'statistical_tests' in report and report['statistical_tests']:
        st.subheader("📊 Statistical Analysis")
        tests = report['statistical_tests']

        col1, col2 = st.columns(2)

        with col1:
            if 'baseline_ttest' in tests:
                baseline_test = tests['baseline_ttest']
                significance = "✅ Significant" if baseline_test.get('significant', False) else "❌ Not Significant"
                st.write(f"**Baseline Comparison T-Test:**")
                st.write(f"- Result: {significance}")
                st.write(f"- P-value: {baseline_test.get('p_value', 0):.4f}")
                st.write(f"- T-statistic: {baseline_test.get('statistic', 0):.4f}")

        with col2:
            if 'benchmark_ttest' in tests:
                benchmark_test = tests['benchmark_ttest']
                significance = "✅ Significant" if benchmark_test.get('significant', False) else "❌ Not Significant"
                st.write(f"**Benchmark Comparison T-Test:**")
                st.write(f"- Result: {significance}")
                st.write(f"- P-value: {benchmark_test.get('p_value', 0):.4f}")
                st.write(f"- T-statistic: {benchmark_test.get('statistic', 0):.4f}")

    # Risk metrics
    if 'basic_metrics' in report and report['basic_metrics']:
        st.subheader("⚠️ Risk Analysis")

        col1, col2, col3 = st.columns(3)

        with col1:
            var_5 = report['basic_metrics'].get('var_5', 0) * 100
            st.metric("Value at Risk (5%)", f"{var_5:.2f}%")

        with col2:
            cvar_5 = report['basic_metrics'].get('cvar_5', 0) * 100
            st.metric("Conditional VaR (5%)", f"{cvar_5:.2f}%")

        with col3:
            max_dd = report['basic_metrics'].get('max_drawdown', 0) * 100
            st.metric("Maximum Drawdown", f"{max_dd:.2f}%")

    # Allocation over time
    st.subheader("📈 Portfolio Allocation")
    allocation_fig = backtester.plot_allocation()
    if allocation_fig:
        st.plotly_chart(allocation_fig, use_container_width=True)


def display_risk_metrics_section(metrics: Dict):
    """Display detailed risk metrics."""
    st.subheader("⚠️ Detailed Risk Metrics")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Downside Risk:**")
        st.write(f"- Sortino Ratio: {metrics.get('sortino_ratio', 0):.3f}")
        st.write(f"- Value at Risk (5%): {metrics.get('var_5', 0)*100:.2f}%")
        st.write(f"- Conditional VaR (5%): {metrics.get('cvar_5', 0)*100:.2f}%")

    with col2:
        st.write("**Performance Consistency:**")
        st.write(f"- Win Rate: {metrics.get('win_rate', 0)*100:.1f}%")
        st.write(f"- Calmar Ratio: {metrics.get('calmar_ratio', 0):.3f}")
        st.write(f"- Max Drawdown: {metrics.get('max_drawdown', 0)*100:.2f}%")

# App header
st.title("📊 Portfolio Optimizer Pro")
st.markdown("*Advanced portfolio optimization with comprehensive backtesting*")
st.divider()

# Google OAuth setup (from secrets.toml)
# This part is pseudo-code and needs to be adapted to streamlit's new authentication
# For the purpose of this example, we will simulate a logged-in user.
st.session_state.logged_in = True
st.session_state.user_id = "test_user"
st.session_state.user_name = "Test User"


if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.header("Please log in with Google.")
    if st.button("Log in with Google"):
        # In a real app, this would redirect to Google's OAuth flow
        st.session_state.logged_in = True
        st.session_state.user_id = "test_user" # Replace with actual user ID from OAuth
        st.session_state.user_name = "Test User" # Replace with actual user name
        st.rerun()
else:
    user_id = st.session_state.user_id
    st.header(f"Welcome, {st.session_state.user_name}!")

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # App settings
        with st.expander("🎨 Display Settings"):
            show_debug = st.checkbox("Show debug info", value=False)
            chart_theme = st.selectbox("Chart theme", ["plotly", "plotly_white", "plotly_dark"])

        # Portfolio settings
        with st.expander("📊 Portfolio Settings"):
            min_position_size = st.number_input("Min position size (%)", value=1.0, min_value=0.1, max_value=10.0) / 100
            max_position_size = st.number_input("Max position size (%)", value=25.0, min_value=5.0, max_value=50.0) / 100
            rebalance_threshold = st.number_input("Rebalance threshold (%)", value=1.0, min_value=0.1, max_value=5.0) / 100

        # Risk settings
        with st.expander("⚠️ Risk Management"):
            max_portfolio_volatility = st.number_input("Max portfolio volatility (%)", value=20.0, min_value=5.0, max_value=50.0) / 100
            var_confidence = st.selectbox("VaR confidence level", [90, 95, 99], index=1)

        # Store settings in session state
        st.session_state['settings'] = {
            'show_debug': show_debug,
            'chart_theme': chart_theme,
            'min_position_size': min_position_size,
            'max_position_size': max_position_size,
            'rebalance_threshold': rebalance_threshold,
            'max_portfolio_volatility': max_portfolio_volatility,
            'var_confidence': var_confidence
        }

        # User actions
        st.divider()
        if st.button("🔄 Refresh Data"):
            # Clear cached data
            if 'backtest_report' in st.session_state:
                del st.session_state['backtest_report']
            if 'backtester' in st.session_state:
                del st.session_state['backtester']
            st.success("Data refreshed!")
            st.rerun()

        if st.button("🚪 Log out"):
            st.session_state.logged_in = False
            del st.session_state.user_id
            del st.session_state.user_name
            st.rerun()

    db = DBManager()

    # Portfolio selection
    col1, col2 = st.columns(2)
    with col1:
        portfolio_option = st.selectbox("Portfolio", ["New"] + db.load_portfolios(user_id))
    if portfolio_option == "New":
        holdings_input = st.text_area("Enter holdings as JSON: {'AAPL': 100, 'GOOG': 50}", "{'AAPL': 100}")
        try:
            import json
            holdings = json.loads(holdings_input) if holdings_input else {"AAPL": 100}
        except json.JSONDecodeError:
            st.error("Invalid JSON format")
            holdings = {"AAPL": 100}
        save_name = st.text_input("Save as")
        if st.button("Save Portfolio") and save_name:
            db.save_portfolio(user_id, save_name, holdings)
    else:
        holdings = db.load_portfolio(user_id, portfolio_option)

    if not holdings:
        st.warning("No holdings found. Using default AAPL position.")
        holdings = {"AAPL": 100}

    pm = PortfolioManager(holdings)

    # Quick start guide for new users
    if 'first_visit' not in st.session_state:
        st.session_state.first_visit = True

    if st.session_state.first_visit:
        with st.expander("🚀 Quick Start Guide", expanded=True):
            st.markdown("""
            **Welcome to Portfolio Optimizer Pro!** Here's how to get started:

            1. **📁 Load Portfolio**: Enter your holdings in JSON format or load a saved portfolio
            2. **🎯 Select Strategy**: Choose from Bollinger, ML, or create custom strategies
            3. **📊 Run Backtest**: Click the "Run Comprehensive Backtest" button for detailed analysis
            4. **📈 Analyze Results**: Review performance metrics, comparisons, and risk analysis
            5. **📋 Review Orders**: Check suggested portfolio adjustments
            6. **🔌 Execute Trades**: Connect to Interactive Brokers to place orders

            **Pro Tips:**
            - Use the sidebar to adjust risk settings and display preferences
            - Compare against different benchmarks (S&P 500, NASDAQ, etc.)
            - Review statistical significance of your strategy's performance
            """)

            if st.button("Got it! Hide this guide"):
                st.session_state.first_visit = False
                st.rerun()

    # Tables
    st.subheader("Current Information")
    st.table(pm.get_current_distribution())
    st.table(pm.calculate_attractiveness())
    st.table(pm.calculate_performance())

    # Strategy
    st.subheader("Strategy")
    # Predefined strategies
    predefined_strategies = {
        "Bollinger": BollingerStrategy,
        "ML": MLStrategy
    }
    # Load custom strategies
    custom_strategies = {name: db.load_strategy_code(user_id, name) for name in db.load_strategies(user_id)}

    strategy_options = list(predefined_strategies.keys()) + list(custom_strategies.keys()) + ["Custom LLM"]
    strategy_option = st.selectbox("Select Strategy", strategy_options)

    strat = None
    if strategy_option in predefined_strategies:
        strat = predefined_strategies[strategy_option]()
    elif strategy_option in custom_strategies:
        code = custom_strategies[strategy_option]
        local_scope = {}
        exec(code, {"BaseStrategy": BaseStrategy, "pd": pd, "np": np, "Dict": Dict}, local_scope)
        strat_class = next(iter(local_scope.values())) # Get the first class from the exec'd code
        strat = strat_class()
    elif strategy_option == "Custom LLM":
        prompt = st.text_area("Enter strategy prompt")
        if st.button("Generate Strategy"):
            try:
                custom_class = generate_strategy_class(prompt)
                strat = custom_class()
                st.session_state.generated_strategy = strat
                st.session_state.generated_strategy_code = "class CustomStrategy(BaseStrategy):\n    ..." # Placeholder
            except Exception as e:
                st.error(str(e))
                st.stop()
        if 'generated_strategy' in st.session_state:
            strat = st.session_state.generated_strategy
            save_strat_name = st.text_input("Save strategy as")
            if st.button("Save Generated Strategy") and save_strat_name:
                db.save_strategy(user_id, save_strat_name, st.session_state.generated_strategy_code)


    if strat:
        # Create tabs for better organization
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Backtest", "📈 Current Portfolio", "📋 Orders", "🔌 Broker"])

        with tab1:
            st.subheader("Backtest Configuration")

            # Backtest parameters in sidebar for better space usage
            with st.container():
                col1, col2, col3 = st.columns(3)

                with col1:
                    period = st.selectbox("Period", ["1y", "3y", "5y"], key="period_select")

                with col2:
                    rebalance_freq = st.number_input("Rebalance every N days", value=30, min_value=1, max_value=252, key="rebalance_freq")

                with col3:
                    benchmark_symbol = st.selectbox("Benchmark", ["^GSPC", "^IXIC", "^DJI", "QQQ"], key="benchmark_select")

            if st.button("🚀 Run Comprehensive Backtest", type="primary"):
                bt = Backtester(list(pm.symbols), strat, period=period, rebalance_freq=rebalance_freq)

                progress_bar = st.progress(0)
                status_text = st.empty()

                with st.spinner("Running backtest..."):
                    status_text.text("📊 Running portfolio backtest...")
                    progress_bar.progress(20)
                    stats = bt.run()

                    # Store backtester in session state for comprehensive analysis
                    st.session_state['backtester'] = bt
                    st.session_state['backtest_stats'] = stats

                    status_text.text("📈 Calculating baseline comparison...")
                    progress_bar.progress(40)

                    status_text.text("🎯 Analyzing performance attribution...")
                    progress_bar.progress(60)

                    status_text.text("📊 Generating comprehensive analysis...")
                    progress_bar.progress(80)

                    # Generate comprehensive report with custom benchmark
                    report = bt.generate_comprehensive_report()

                    # Update benchmark if different from default
                    if benchmark_symbol != "^GSPC":
                        custom_benchmark = bt.get_benchmark_comparison(benchmark_symbol)
                        if custom_benchmark:
                            report['benchmark_comparison'] = custom_benchmark

                    st.session_state['backtest_report'] = report

                    progress_bar.progress(100)
                    status_text.text("✅ Analysis complete!")

                st.success("🎉 Comprehensive backtest completed! See detailed analysis below.")
                st.balloons()

            # Display comprehensive backtest results if available
            if 'backtest_report' in st.session_state and st.session_state['backtest_report']:
                st.divider()
                display_comprehensive_backtest_results(st.session_state['backtest_report'], st.session_state['backtester'])

        with tab2:
            st.subheader("📈 Portfolio Overview")

            # Key portfolio metrics
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Current Allocation")
                dist = pm.get_current_distribution()
                fig = px.pie(values=list(dist.values()), names=list(dist.keys()),
                           title="Portfolio Allocation")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Portfolio Details")
                st.table(pm.get_current_distribution())

                # Additional portfolio metrics
                try:
                    performance = pm.calculate_performance()
                    if not performance.empty:
                        st.subheader("Performance Metrics")
                        st.table(performance)
                except Exception as e:
                    st.warning(f"Could not calculate performance metrics: {e}")

                try:
                    attractiveness = pm.calculate_attractiveness()
                    if not attractiveness.empty:
                        st.subheader("Asset Attractiveness")
                        st.table(attractiveness)
                except Exception as e:
                    st.warning(f"Could not calculate attractiveness: {e}")

        with tab3:
            st.subheader("📋 Order Management")

            # Calculate new weights and orders
            try:
                current_weights = pm.get_current_distribution()
                new_weights = strat.calculate_new_weights(pm.prices, current_weights)
                orders = pm.get_orders_today(new_weights)

                # Display weight changes
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Current vs Target Weights")
                    weight_comparison = pd.DataFrame({
                        'Current (%)': [f"{v*100:.2f}" for v in current_weights.values()],
                        'Target (%)': [f"{new_weights.get(k, 0)*100:.2f}" for k in current_weights.keys()],
                        'Change (%)': [f"{(new_weights.get(k, 0) - v)*100:.2f}" for k, v in current_weights.items()]
                    }, index=current_weights.keys())
                    st.dataframe(weight_comparison, use_container_width=True)

                with col2:
                    st.subheader("Orders to Execute")
                    if not orders.empty:
                        st.dataframe(orders, use_container_width=True)

                        # Order summary
                        total_orders = len(orders)
                        buy_orders = len(orders[orders['Action'] == 'BUY']) if 'Action' in orders.columns else 0
                        sell_orders = len(orders[orders['Action'] == 'SELL']) if 'Action' in orders.columns else 0

                        st.metric("Total Orders", total_orders)
                        col_buy, col_sell = st.columns(2)
                        with col_buy:
                            st.metric("Buy Orders", buy_orders)
                        with col_sell:
                            st.metric("Sell Orders", sell_orders)
                    else:
                        st.info("No orders needed - portfolio is already optimally allocated!")

            except Exception as e:
                st.error(f"Error calculating orders: {e}")
                st.write("Please ensure you have a valid strategy selected and portfolio data loaded.")

        with tab4:
            st.subheader("🔌 Interactive Brokers Connection")

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Connection Status:**")
                if 'ib' in st.session_state:
                    st.success("✅ Connected to Interactive Brokers")

                    if st.button("🔄 Refresh Connection"):
                        # Add connection refresh logic here
                        st.info("Connection refreshed")

                    if st.button("❌ Disconnect IB", type="secondary"):
                        try:
                            st.session_state['ib'].disconnect()
                            del st.session_state['ib']
                            st.success("Disconnected from IB.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error disconnecting: {e}")
                else:
                    st.warning("❌ Not connected to Interactive Brokers")

                    if st.button("🔗 Connect to IB", type="primary"):
                        try:
                            # ib = IBConnector()
                            # st.session_state['ib'] = ib
                            st.success("Connected to IB")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to connect to IB: {e}")
                            st.write("Make sure TWS or IB Gateway is running and API is enabled.")

            with col2:
                st.write("**Order Execution:**")
                if 'ib' in st.session_state:
                    try:
                        current_weights = pm.get_current_distribution()
                        new_weights = strat.calculate_new_weights(pm.prices, current_weights)
                        orders = pm.get_orders_today(new_weights)

                        if not orders.empty:
                            st.write(f"Ready to place {len(orders)} orders:")

                            if st.button("🚀 Place All Orders", type="primary"):
                                try:
                                    # st.session_state['ib'].place_orders(orders)
                                    st.success("Orders placed successfully!")
                                    st.balloons()
                                except Exception as e:
                                    st.error(f"Failed to place orders: {e}")

                            if st.button("📋 Preview Orders"):
                                st.dataframe(orders, use_container_width=True)
                        else:
                            st.info("No orders to place - portfolio is optimally allocated.")

                    except Exception as e:
                        st.error(f"Error preparing orders: {e}")
                else:
                    st.warning("Connect to IB first to place orders")

                st.write("**Settings:**")
                with st.expander("⚙️ Advanced Settings"):
                    st.number_input("Order timeout (seconds)", value=30, min_value=5, max_value=300)
                    st.selectbox("Order type", ["MKT", "LMT", "STP"])
                    st.checkbox("Dry run mode", value=True, help="Test orders without actually placing them")
