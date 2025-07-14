"""
Production-grade Streamlit application for portfolio management with rich strategy analysis.
"""
import logging
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
import itertools

# Import our production modules
from config import setup_logging, config
from portfolio_manager import PortfolioManager
from strategies import get_strategy, STRATEGIES, BaseStrategy
from database import db_manager
from exceptions import PortfolioError, DataFetchError, StrategyError, ValidationError

# Setup logging
logger = setup_logging()

# Page configuration
st.set_page_config(
    page_title="Portfolio Optimizer Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .error-message {
        color: #ff4b4b;
        background-color: #ffe6e6;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
    }
    .success-message {
        color: #00c851;
        background-color: #e6ffe6;
        padding: 0.5rem;
        border-radius: 0.25rem;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)


class PortfolioApp:
    """Main application class."""
    
    def __init__(self):
        self.initialize_session_state()
        logger.info("Portfolio application initialized")
    
    def initialize_session_state(self):
        """Initialize Streamlit session state."""
        if 'user_id' not in st.session_state:
            st.session_state.user_id = "default_user"
        
        if 'portfolio_manager' not in st.session_state:
            st.session_state.portfolio_manager = None
        
        if 'current_portfolio_name' not in st.session_state:
            st.session_state.current_portfolio_name = None
    
    def run(self):
        """Main application entry point."""
        try:
            st.title("📊 Portfolio Optimizer Pro - Strategy Analysis Suite")
            st.markdown("---")
            
            # Navigation tabs
            tab1, tab2, tab3, tab4 = st.tabs([
                "📈 Portfolio Dashboard", 
                "🔬 Strategy Analysis", 
                "📊 Backtesting", 
                "⚙️ Strategy Optimization"
            ])
            
            # Sidebar for navigation and portfolio management
            self.render_sidebar()
            
            # Main content based on selected tab
            with tab1:
                if st.session_state.portfolio_manager is None:
                    self.render_welcome_page()
                else:
                    self.render_main_dashboard()
            
            with tab2:
                if st.session_state.portfolio_manager is None:
                    st.info("Please load or create a portfolio first.")
                else:
                    self.render_strategy_analysis()
            
            with tab3:
                if st.session_state.portfolio_manager is None:
                    st.info("Please load or create a portfolio first.")
                else:
                    self.render_backtesting()
            
            with tab4:
                if st.session_state.portfolio_manager is None:
                    st.info("Please load or create a portfolio first.")
                else:
                    self.render_strategy_optimization()
                
        except Exception as e:
            logger.error(f"Application error: {e}")
            st.error(f"An unexpected error occurred: {e}")
    
    def render_sidebar(self):
        """Render the sidebar with portfolio management."""
        st.sidebar.title("Portfolio Management")
        
        # Portfolio selection/creation
        self.render_portfolio_selector()
        
        # Portfolio actions
        if st.session_state.portfolio_manager is not None:
            st.sidebar.markdown("---")
            self.render_portfolio_actions()
    
    def render_portfolio_selector(self):
        """Render portfolio selection and creation interface."""
        st.sidebar.subheader("Select Portfolio")
        
        # List existing portfolios
        try:
            portfolios = db_manager.list_portfolios(st.session_state.user_id)
            portfolio_names = [p['name'] for p in portfolios]
            
            if portfolio_names:
                selected_portfolio = st.sidebar.selectbox(
                    "Existing Portfolios",
                    options=[""] + portfolio_names,
                    key="portfolio_selector"
                )
                
                if selected_portfolio and selected_portfolio != st.session_state.current_portfolio_name:
                    self.load_portfolio(selected_portfolio)
            
        except Exception as e:
            logger.error(f"Error listing portfolios: {e}")
            st.sidebar.error("Failed to load portfolios")
        
        # Create new portfolio
        st.sidebar.markdown("**Or Create New Portfolio**")
        
        with st.sidebar.form("create_portfolio"):
            new_portfolio_name = st.text_input("Portfolio Name")
            
            # Holdings input
            st.markdown("**Initial Holdings**")
            col1, col2 = st.columns(2)
            
            with col1:
                symbols_input = st.text_area(
                    "Symbols (one per line)",
                    placeholder="AAPL\nMSFT\nGOOGL",
                    height=100
                )
            
            with col2:
                shares_input = st.text_area(
                    "Shares (one per line)",
                    placeholder="100\n50\n25",
                    height=100
                )
            
            if st.form_submit_button("Create Portfolio"):
                self.create_portfolio(new_portfolio_name, symbols_input, shares_input)
    
    def render_portfolio_actions(self):
        """Render portfolio action buttons."""
        col1, col2 = st.sidebar.columns(2)
        
        with col1:
            if st.button("Refresh Data"):
                self.refresh_portfolio_data()
        
        with col2:
            if st.button("Save Portfolio"):
                self.save_current_portfolio()
        
        # Strategy selection and configuration
        st.sidebar.subheader("Strategy Configuration")
        strategy_name = st.sidebar.selectbox(
            "Select Strategy",
            options=list(STRATEGIES.keys()),
            key="strategy_selector"
        )
        
        # Strategy-specific parameters
        strategy_params = self.render_strategy_parameters(strategy_name)
        
        if st.sidebar.button("Run Strategy"):
            self.run_strategy(strategy_name, strategy_params)
    
    def render_welcome_page(self):
        """Render welcome page when no portfolio is loaded."""
        st.markdown("""
        ## Welcome to Portfolio Optimizer Pro
        
        This application helps you manage and optimize your investment portfolio using advanced strategies.
        
        ### Features:
        - 📈 Real-time portfolio tracking
        - 🤖 AI-powered rebalancing strategies
        - 📊 Comprehensive performance analytics
        - 💾 Portfolio persistence and history
        
        ### Getting Started:
        1. Create a new portfolio or load an existing one from the sidebar
        2. Add your holdings (symbols and shares)
        3. Select a rebalancing strategy
        4. Analyze performance and optimize your portfolio
        
        **Select or create a portfolio from the sidebar to begin.**
        """)
    
    def render_main_dashboard(self):
        """Render the main dashboard with portfolio information."""
        try:
            # Portfolio summary
            self.render_portfolio_summary()
            
            # Portfolio composition
            col1, col2 = st.columns(2)
            
            with col1:
                self.render_portfolio_composition()
            
            with col2:
                self.render_performance_metrics()
            
            # Price charts
            self.render_price_charts()
            
        except Exception as e:
            logger.error(f"Dashboard rendering error: {e}")
            st.error(f"Failed to render dashboard: {e}")
    
    def render_portfolio_summary(self):
        """Render portfolio summary metrics."""
        try:
            summary = st.session_state.portfolio_manager.get_summary()
            
            st.subheader("📊 Portfolio Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Value",
                    f"${summary['total_value']:,.2f}"
                )
            
            with col2:
                st.metric(
                    "Positions",
                    summary['num_positions']
                )
            
            with col3:
                if summary['largest_position']:
                    symbol, weight = summary['largest_position']
                    st.metric(
                        "Largest Position",
                        f"{symbol} ({weight:.1%})"
                    )
            
            with col4:
                st.metric(
                    "Last Updated",
                    summary['data_last_updated'][:10]  # Just the date
                )
            
        except Exception as e:
            logger.error(f"Error rendering portfolio summary: {e}")
            st.error("Failed to load portfolio summary")
    
    def render_portfolio_composition(self):
        """Render portfolio composition chart."""
        try:
            st.subheader("🥧 Portfolio Composition")
            
            weights = st.session_state.portfolio_manager.get_current_weights()
            position_values = st.session_state.portfolio_manager.get_position_values()
            
            # Create pie chart
            fig = px.pie(
                values=list(position_values.values()),
                names=list(position_values.keys()),
                title="Portfolio Allocation"
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
            
            # Weights table
            weights_df = pd.DataFrame([
                {"Symbol": symbol, "Weight": f"{weight:.2%}", "Value": f"${position_values[symbol]:,.2f}"}
                for symbol, weight in weights.items()
            ])
            
            st.dataframe(weights_df, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error rendering portfolio composition: {e}")
            st.error("Failed to load portfolio composition")
    
    def render_performance_metrics(self):
        """Render performance metrics."""
        try:
            st.subheader("📈 Performance Metrics")
            
            prices = st.session_state.portfolio_manager.get_price_history()
            weights = st.session_state.portfolio_manager.get_current_weights()
            
            # Calculate portfolio returns
            returns = prices.pct_change().dropna()
            
            # Weight returns by current portfolio weights
            portfolio_returns = (returns * pd.Series(weights)).sum(axis=1)
            
            # Calculate metrics
            total_return = (1 + portfolio_returns).prod() - 1
            annualized_return = (1 + portfolio_returns.mean()) ** 252 - 1
            volatility = portfolio_returns.std() * (252 ** 0.5)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            # Display metrics
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Return", f"{total_return:.2%}")
                st.metric("Volatility", f"{volatility:.2%}")
            
            with col2:
                st.metric("Annualized Return", f"{annualized_return:.2%}")
                st.metric("Sharpe Ratio", f"{sharpe_ratio:.3f}")
            
            # Portfolio value over time
            portfolio_value = (1 + portfolio_returns).cumprod()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=portfolio_value.index,
                y=portfolio_value.values,
                mode='lines',
                name='Portfolio Value',
                line=dict(color='blue', width=2)
            ))
            
            fig.update_layout(
                title="Portfolio Performance",
                xaxis_title="Date",
                yaxis_title="Cumulative Return",
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error rendering performance metrics: {e}")
            st.error("Failed to calculate performance metrics")
    
    def render_price_charts(self):
        """Render individual stock price charts."""
        try:
            st.subheader("📊 Price Charts")
            
            prices = st.session_state.portfolio_manager.get_price_history()
            
            # Normalize prices to show relative performance
            normalized_prices = prices / prices.iloc[0]
            
            fig = go.Figure()
            
            for symbol in normalized_prices.columns:
                fig.add_trace(go.Scatter(
                    x=normalized_prices.index,
                    y=normalized_prices[symbol],
                    mode='lines',
                    name=symbol,
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                title="Normalized Price Performance",
                xaxis_title="Date",
                yaxis_title="Normalized Price (Base = 1.0)",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            logger.error(f"Error rendering price charts: {e}")
            st.error("Failed to render price charts")
    
    def create_portfolio(self, name: str, symbols_input: str, shares_input: str):
        """Create a new portfolio."""
        try:
            if not name or not name.strip():
                st.sidebar.error("Portfolio name is required")
                return
            
            # Parse inputs
            symbols = [s.strip().upper() for s in symbols_input.split('\n') if s.strip()]
            shares_str = [s.strip() for s in shares_input.split('\n') if s.strip()]
            
            if len(symbols) != len(shares_str):
                st.sidebar.error("Number of symbols must match number of shares")
                return
            
            # Convert shares to float
            holdings = {}
            for symbol, shares_str in zip(symbols, shares_str):
                try:
                    shares = float(shares_str)
                    if shares <= 0:
                        st.sidebar.error(f"Shares for {symbol} must be positive")
                        return
                    holdings[symbol] = shares
                except ValueError:
                    st.sidebar.error(f"Invalid shares value for {symbol}: {shares_str}")
                    return
            
            # Create portfolio manager
            portfolio_manager = PortfolioManager(holdings)
            
            # Save to database
            db_manager.save_portfolio(st.session_state.user_id, name, holdings)
            
            # Update session state
            st.session_state.portfolio_manager = portfolio_manager
            st.session_state.current_portfolio_name = name
            
            st.sidebar.success(f"Portfolio '{name}' created successfully!")
            logger.info(f"Created portfolio '{name}' with {len(holdings)} positions")
            
            # Rerun to update the display
            st.rerun()
            
        except ValidationError as e:
            st.sidebar.error(f"Validation error: {e}")
        except Exception as e:
            logger.error(f"Error creating portfolio: {e}")
            st.sidebar.error(f"Failed to create portfolio: {e}")
    
    def load_portfolio(self, name: str):
        """Load an existing portfolio."""
        try:
            holdings = db_manager.load_portfolio(st.session_state.user_id, name)
            
            if holdings is None:
                st.sidebar.error(f"Portfolio '{name}' not found")
                return
            
            # Create portfolio manager
            portfolio_manager = PortfolioManager(holdings)
            
            # Update session state
            st.session_state.portfolio_manager = portfolio_manager
            st.session_state.current_portfolio_name = name
            
            st.sidebar.success(f"Portfolio '{name}' loaded successfully!")
            logger.info(f"Loaded portfolio '{name}' with {len(holdings)} positions")
            
            # Rerun to update the display
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error loading portfolio: {e}")
            st.sidebar.error(f"Failed to load portfolio: {e}")
    
    def save_current_portfolio(self):
        """Save the current portfolio to database."""
        try:
            if st.session_state.portfolio_manager is None:
                st.sidebar.error("No portfolio to save")
                return
            
            if st.session_state.current_portfolio_name is None:
                st.sidebar.error("No portfolio name set")
                return
            
            holdings = st.session_state.portfolio_manager.holdings
            
            db_manager.save_portfolio(
                st.session_state.user_id,
                st.session_state.current_portfolio_name,
                holdings
            )
            
            st.sidebar.success("Portfolio saved successfully!")
            logger.info(f"Saved portfolio '{st.session_state.current_portfolio_name}'")
            
        except Exception as e:
            logger.error(f"Error saving portfolio: {e}")
            st.sidebar.error(f"Failed to save portfolio: {e}")
    
    def refresh_portfolio_data(self):
        """Refresh portfolio data."""
        try:
            if st.session_state.portfolio_manager is None:
                st.sidebar.error("No portfolio loaded")
                return
            
            st.session_state.portfolio_manager.refresh_data()
            st.sidebar.success("Data refreshed successfully!")
            logger.info("Portfolio data refreshed")
            
            # Rerun to update the display
            st.rerun()
            
        except Exception as e:
            logger.error(f"Error refreshing data: {e}")
            st.sidebar.error(f"Failed to refresh data: {e}")
    
    def run_strategy(self, strategy_name: str, strategy_params: Dict = None):
        """Run a rebalancing strategy."""
        try:
            if st.session_state.portfolio_manager is None:
                st.sidebar.error("No portfolio loaded")
                return
            
            # Get current data
            prices = st.session_state.portfolio_manager.get_price_history()
            current_weights = st.session_state.portfolio_manager.get_current_weights()
            
            # Show data source information
            data_info = self.get_data_source_info(prices)
            if data_info['is_mock']:
                st.warning(f"⚠️ Using mock data: {data_info['reason']}")
            else:
                st.success(f"✅ Using real market data (last updated: {data_info['last_date']})")
            
            # Create and run strategy with parameters
            strategy_params = strategy_params or {}
            st.info(f"Running {strategy_name} strategy with parameters: {strategy_params}")
            
            strategy = get_strategy(strategy_name, **strategy_params)
            
            # Log strategy execution details
            logger.info(f"Executing {strategy_name} with params: {strategy_params}")
            logger.info(f"Input data shape: {prices.shape}, date range: {prices.index[0]} to {prices.index[-1]}")
            logger.info(f"Current weights: {current_weights}")
            
            new_weights = strategy.calculate_new_weights(prices, current_weights)
            
            # Display results with more detail
            st.subheader(f"🤖 {strategy.name} Results")
            
            # Show parameter impact
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Strategy Parameters:**")
                for param, value in strategy_params.items():
                    st.write(f"- {param}: {value}")
            
            with col2:
                st.markdown("**Data Summary:**")
                st.write(f"- Data points: {len(prices)}")
                st.write(f"- Date range: {prices.index[0].strftime('%Y-%m-%d')} to {prices.index[-1].strftime('%Y-%m-%d')}")
                st.write(f"- Symbols: {list(prices.columns)}")
            
            # Calculate and show weight changes
            weight_changes = {}
            total_change = 0
            for symbol in current_weights:
                change = new_weights.get(symbol, 0) - current_weights[symbol]
                weight_changes[symbol] = change
                total_change += abs(change)
            
            st.metric("Total Portfolio Rebalancing", f"{total_change:.2%}")
            
            # Create comparison dataframe with more details
            comparison_df = pd.DataFrame({
                'Symbol': list(current_weights.keys()),
                'Current Weight': [f"{w:.2%}" for w in current_weights.values()],
                'New Weight': [f"{new_weights.get(s, 0):.2%}" for s in current_weights.keys()],
                'Absolute Change': [f"{weight_changes[s]:+.2%}" for s in current_weights.keys()],
                'Relative Change': [f"{weight_changes[s]/current_weights[s]:+.1%}" if current_weights[s] > 0 else "N/A" for s in current_weights.keys()]
            })
            
            st.dataframe(comparison_df, use_container_width=True)
            
            # Show implementation suggestions
            total_value = st.session_state.portfolio_manager.get_current_value()
            
            st.subheader("💡 Implementation Suggestions")
            
            implementation_needed = False
            for symbol in current_weights.keys():
                current_value = current_weights[symbol] * total_value
                target_value = new_weights.get(symbol, 0) * total_value
                difference = target_value - current_value
                
                current_price = st.session_state.portfolio_manager.current_prices[symbol]
                shares_change = difference / current_price
                
                if abs(shares_change) > 0.1:  # Only show significant changes
                    implementation_needed = True
                    action = "BUY" if shares_change > 0 else "SELL"
                    st.write(f"**{symbol}**: {action} {abs(shares_change):.0f} shares (${difference:+,.2f})")
            
            if not implementation_needed:
                st.info("No significant rebalancing needed based on current strategy parameters.")
            
            logger.info(f"Strategy {strategy_name} completed. Total rebalancing: {total_change:.2%}")
            
        except StrategyError as e:
            st.error(f"Strategy error: {e}")
            logger.error(f"Strategy error in {strategy_name}: {e}")
        except Exception as e:
            logger.error(f"Error running strategy {strategy_name}: {e}")
            st.error(f"Failed to run strategy: {e}")
    
    def get_data_source_info(self, prices: pd.DataFrame) -> Dict:
        """Determine if data is real or mock and provide context."""
        # Check if data looks like mock data
        is_mock = False
        reason = ""
        
        # Simple heuristics to detect mock data
        for symbol in prices.columns:
            price_series = prices[symbol].dropna()
            if len(price_series) > 0:
                # Check if prices are too regular (mock data tends to be more regular)
                returns = price_series.pct_change().dropna()
                if len(returns) > 10:
                    # Real data should have more varied volatility
                    volatility_of_volatility = returns.rolling(20).std().std()
                    if volatility_of_volatility < 0.001:  # Very low variation in volatility
                        is_mock = True
                        reason = "Data appears to be generated (low volatility variation)"
                        break
        
        # Check for weekend data (real stock data shouldn't have weekend dates)
        weekend_dates = prices.index[prices.index.weekday >= 5]
        if len(weekend_dates) > 0:
            is_mock = True
            reason = "Data contains weekend dates"
        
        return {
            'is_mock': is_mock,
            'reason': reason,
            'last_date': prices.index[-1].strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(prices)
        }
    
    def render_strategy_parameters(self, strategy_name: str) -> Dict:
        """Render strategy-specific parameter controls."""
        params = {}
        
        if strategy_name == 'bollinger':
            st.sidebar.markdown("**Bollinger Bands Parameters**")
            params['window'] = st.sidebar.slider(
                "Window Size", 
                min_value=5, 
                max_value=50, 
                value=20, 
                help="Number of periods for moving average"
            )
            params['std_dev'] = st.sidebar.slider(
                "Standard Deviations", 
                min_value=1.0, 
                max_value=3.0, 
                value=2.0, 
                step=0.1,
                help="Number of standard deviations for bands"
            )
        
        elif strategy_name == 'ml':
            st.sidebar.markdown("**ML Strategy Parameters**")
            params['lookback_days'] = st.sidebar.slider(
                "Lookback Days", 
                min_value=30, 
                max_value=252, 
                value=60,
                help="Number of days to look back for training"
            )
        
        elif strategy_name == 'momentum':
            st.sidebar.markdown("**Momentum Strategy Parameters**")
            params['lookback_period'] = st.sidebar.slider(
                "Lookback Period", 
                min_value=5, 
                max_value=60, 
                value=20,
                help="Number of days to calculate momentum"
            )
            params['momentum_threshold'] = st.sidebar.slider(
                "Momentum Threshold", 
                min_value=0.01, 
                max_value=0.10, 
                value=0.02,
                step=0.01,
                format="%.2f",
                help="Minimum momentum to trigger rebalancing"
            )
        
        return params
    
    def render_strategy_analysis(self):
        """Render comprehensive strategy analysis interface."""
        st.header("🔬 Strategy Analysis Suite")
        
        # Strategy comparison section
        st.subheader("📊 Strategy Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            strategies_to_compare = st.multiselect(
                "Select Strategies to Compare",
                options=list(STRATEGIES.keys()),
                default=list(STRATEGIES.keys())[:2] if len(STRATEGIES) >= 2 else list(STRATEGIES.keys())
            )
        
        with col2:
            comparison_period = st.selectbox(
                "Analysis Period",
                options=['1mo', '3mo', '6mo', '1y', '2y'],
                index=2
            )
        
        # Strategy parameters for comparison
        strategy_params_map = {}
        if strategies_to_compare:
            st.markdown("**Strategy Parameters for Comparison:**")
            for strategy in strategies_to_compare:
                with st.expander(f"⚙️ {strategy.title()} Parameters"):
                    strategy_params_map[strategy] = self.render_strategy_parameters_detailed(strategy)
        
        if strategies_to_compare and st.button("Run Strategy Comparison"):
            self.run_strategy_comparison(strategies_to_compare, comparison_period, strategy_params_map)
        
        # Individual strategy deep dive
        st.markdown("---")
        st.subheader("🔍 Strategy Deep Dive")
        
        selected_strategy = st.selectbox(
            "Select Strategy for Detailed Analysis",
            options=list(STRATEGIES.keys())
        )
        
        # Strategy-specific parameters for deep dive
        strategy_params = self.render_strategy_parameters_detailed(selected_strategy)
        
        if st.button("Analyze Strategy"):
            self.analyze_single_strategy(selected_strategy, strategy_params)
    
    def render_strategy_parameters_detailed(self, strategy_name: str) -> Dict:
        """Render detailed strategy parameters for analysis."""
        params = {}
        
        col1, col2, col3 = st.columns(3)
        
        if strategy_name == 'bollinger':
            with col1:
                params['window'] = st.slider(
                    "Window Size", 
                    min_value=5, 
                    max_value=50, 
                    value=20
                )
            with col2:
                params['std_dev'] = st.slider(
                    "Standard Deviations", 
                    min_value=1.0, 
                    max_value=3.0, 
                    value=2.0, 
                    step=0.1
                )
            with col3:
                st.metric("Default Window", "20")
                st.metric("Default Std Dev", "2.0")
        
        elif strategy_name == 'ml':
            with col1:
                params['lookback_days'] = st.slider(
                    "Lookback Days", 
                    min_value=30, 
                    max_value=252, 
                    value=60
                )
            with col2:
                st.metric("Default Lookback", "60 days")
        
        elif strategy_name == 'momentum':
            with col1:
                params['lookback_period'] = st.slider(
                    "Lookback Period", 
                    min_value=5, 
                    max_value=60, 
                    value=20
                )
            with col2:
                params['momentum_threshold'] = st.slider(
                    "Momentum Threshold", 
                    min_value=0.01, 
                    max_value=0.10, 
                    value=0.02,
                    step=0.01,
                    format="%.2f"
                )
            with col3:
                st.metric("Default Period", "20 days")
                st.metric("Default Threshold", "2%")
        
        return params
    
    def run_strategy_comparison(self, strategies: List[str], period: str, strategy_params_map: Dict = None):
        """Run comparison analysis between multiple strategies."""
        try:
            st.subheader("📈 Strategy Performance Comparison")
            
            # Get portfolio data
            portfolio_manager = st.session_state.portfolio_manager
            prices = portfolio_manager.get_price_history()
            current_weights = portfolio_manager.get_current_weights()
            
            # Run each strategy
            strategy_results = {}
            strategy_weights = {}
            
            for strategy_name in strategies:
                try:
                    # Get strategy parameters for this strategy
                    params = strategy_params_map.get(strategy_name, {}) if strategy_params_map else {}
                    strategy = get_strategy(strategy_name, **params)
                    new_weights = strategy.calculate_new_weights(prices, current_weights)
                    
                    # Calculate performance metrics
                    performance = self.calculate_strategy_performance(prices, new_weights)
                    strategy_results[strategy_name] = performance
                    strategy_weights[strategy_name] = new_weights
                    
                    # Log strategy execution details
                    logger.info(f"Strategy comparison - {strategy_name} with params {params}: weights={new_weights}")
                    logger.info(f"Strategy {strategy_name} performance: {performance}")
                    
                except Exception as e:
                    st.error(f"Error running {strategy_name}: {e}")
                    logger.error(f"Error in strategy comparison for {strategy_name}: {e}")
                    continue
            
            if not strategy_results:
                st.error("No strategies ran successfully")
                return
            
            # Display comparison table
            self.display_strategy_comparison_table(strategy_results)
            
            # Display weight allocation comparison
            self.display_weight_comparison(strategy_weights, current_weights)
            
            # Display performance charts
            self.display_performance_comparison_charts(strategy_results)
            
        except Exception as e:
            logger.error(f"Error in strategy comparison: {e}")
            st.error(f"Strategy comparison failed: {e}")
    
    def calculate_strategy_performance(self, prices: pd.DataFrame, weights: Dict[str, float]) -> Dict:
        """Calculate comprehensive performance metrics for a strategy."""
        try:
            # Calculate returns
            returns = prices.pct_change().dropna()
            
            # Weight returns by strategy weights
            portfolio_returns = (returns * pd.Series(weights)).sum(axis=1)
            
            # Performance metrics
            total_return = (1 + portfolio_returns).prod() - 1
            annualized_return = (1 + portfolio_returns.mean()) ** 252 - 1
            volatility = portfolio_returns.std() * (252 ** 0.5)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            rolling_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Win rate
            win_rate = (portfolio_returns > 0).mean()
            
            # Value at Risk (95%)
            var_95 = np.percentile(portfolio_returns, 5)
            
            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'var_95': var_95,
                'portfolio_returns': portfolio_returns
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            return {}
    
    def display_strategy_comparison_table(self, strategy_results: Dict):
        """Display strategy comparison metrics in a table."""
        comparison_data = []
        
        for strategy_name, results in strategy_results.items():
            comparison_data.append({
                'Strategy': strategy_name.title(),
                'Total Return': f"{results.get('total_return', 0):.2%}",
                'Annualized Return': f"{results.get('annualized_return', 0):.2%}",
                'Volatility': f"{results.get('volatility', 0):.2%}",
                'Sharpe Ratio': f"{results.get('sharpe_ratio', 0):.3f}",
                'Max Drawdown': f"{results.get('max_drawdown', 0):.2%}",
                'Win Rate': f"{results.get('win_rate', 0):.2%}",
                'VaR (95%)': f"{results.get('var_95', 0):.2%}"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)
        
        # Add debug info to help identify issues
        if st.checkbox("Show Debug Info", key="debug_comparison"):
            st.subheader("Debug: Raw Performance Data")
            for strategy_name, results in strategy_results.items():
                st.write(f"**{strategy_name}**: {results}")
    
    def display_weight_comparison(self, strategy_weights: Dict, current_weights: Dict):
        """Display weight allocation comparison."""
        st.subheader("🥧 Weight Allocation Comparison")
        
        # Prepare data for visualization
        symbols = list(current_weights.keys())
        weight_data = {'Symbol': symbols, 'Current': [current_weights[s] for s in symbols]}
        
        for strategy_name, weights in strategy_weights.items():
            weight_data[strategy_name.title()] = [weights.get(s, 0) for s in symbols]
        
        weight_df = pd.DataFrame(weight_data)
        
        # Create grouped bar chart
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set3
        for i, column in enumerate(weight_df.columns[1:]):
            fig.add_trace(go.Bar(
                name=column,
                x=weight_df['Symbol'],
                y=weight_df[column],
                marker_color=colors[i % len(colors)]
            ))
        
        fig.update_layout(
            title="Portfolio Weight Allocation by Strategy",
            xaxis_title="Symbol",
            yaxis_title="Weight",
            barmode='group',
            yaxis=dict(tickformat='.1%')
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def display_performance_comparison_charts(self, strategy_results: Dict):
        """Display performance comparison charts."""
        st.subheader("📊 Performance Comparison Charts")
        
        # Cumulative returns chart
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        for i, (strategy_name, results) in enumerate(strategy_results.items()):
            if 'portfolio_returns' in results:
                cumulative_returns = (1 + results['portfolio_returns']).cumprod()
                fig.add_trace(go.Scatter(
                    x=cumulative_returns.index,
                    y=cumulative_returns.values,
                    mode='lines',
                    name=strategy_name.title(),
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
        
        fig.update_layout(
            title="Cumulative Returns Comparison",
            xaxis_title="Date",
            yaxis_title="Cumulative Return",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk-Return scatter plot
        fig_scatter = go.Figure()
        
        for i, (strategy_name, results) in enumerate(strategy_results.items()):
            fig_scatter.add_trace(go.Scatter(
                x=[results.get('volatility', 0)],
                y=[results.get('annualized_return', 0)],
                mode='markers+text',
                name=strategy_name.title(),
                text=[strategy_name.title()],
                textposition="top center",
                marker=dict(
                    size=15,
                    color=colors[i % len(colors)]
                )
            ))
        
        fig_scatter.update_layout(
            title="Risk-Return Profile",
            xaxis_title="Volatility (Risk)",
            yaxis_title="Annualized Return",
            xaxis=dict(tickformat='.1%'),
            yaxis=dict(tickformat='.1%')
        )
        
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    def analyze_single_strategy(self, strategy_name: str, params: Dict):
        """Perform detailed analysis of a single strategy."""
        try:
            st.subheader(f"🔍 Deep Dive: {strategy_name.title()} Strategy")
            
            # Get portfolio data
            portfolio_manager = st.session_state.portfolio_manager
            prices = portfolio_manager.get_price_history()
            current_weights = portfolio_manager.get_current_weights()
            
            # Create strategy with parameters
            strategy = get_strategy(strategy_name, **params)
            new_weights = strategy.calculate_new_weights(prices, current_weights)
            
            # Calculate detailed performance
            performance = self.calculate_strategy_performance(prices, new_weights)
            
            # Display key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Annualized Return",
                    f"{performance.get('annualized_return', 0):.2%}"
                )
                st.metric(
                    "Sharpe Ratio",
                    f"{performance.get('sharpe_ratio', 0):.3f}"
                )
            
            with col2:
                st.metric(
                    "Volatility",
                    f"{performance.get('volatility', 0):.2%}"
                )
                st.metric(
                    "Max Drawdown",
                    f"{performance.get('max_drawdown', 0):.2%}"
                )
            
            with col3:
                st.metric(
                    "Win Rate",
                    f"{performance.get('win_rate', 0):.2%}"
                )
                st.metric(
                    "VaR (95%)",
                    f"{performance.get('var_95', 0):.2%}"
                )
            
            with col4:
                st.metric(
                    "Total Return",
                    f"{performance.get('total_return', 0):.2%}"
                )
            
            # Strategy-specific analysis
            if strategy_name == 'bollinger':
                self.analyze_bollinger_strategy(prices, params)
            elif strategy_name == 'ml':
                self.analyze_ml_strategy(prices, params)
            
            # Weight changes analysis
            self.display_weight_changes_analysis(current_weights, new_weights)
            
        except Exception as e:
            logger.error(f"Error in single strategy analysis: {e}")
            st.error(f"Strategy analysis failed: {e}")
    
    def analyze_bollinger_strategy(self, prices: pd.DataFrame, params: Dict):
        """Analyze Bollinger Bands strategy specifics."""
        st.subheader("📈 Bollinger Bands Analysis")
        
        window = params.get('window', 20)
        std_dev = params.get('std_dev', 2.0)
        
        # Select a symbol for detailed analysis
        symbol = st.selectbox("Select Symbol for Bollinger Analysis", prices.columns)
        
        if symbol:
            price_series = prices[symbol].dropna()
            
            # Calculate Bollinger Bands
            rolling_mean = price_series.rolling(window=window).mean()
            rolling_std = price_series.rolling(window=window).std()
            upper_band = rolling_mean + (std_dev * rolling_std)
            lower_band = rolling_mean - (std_dev * rolling_std)
            
            # Create Bollinger Bands chart
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=price_series.index,
                y=price_series.values,
                mode='lines',
                name='Price',
                line=dict(color='blue', width=2)
            ))
            
            fig.add_trace(go.Scatter(
                x=rolling_mean.index,
                y=rolling_mean.values,
                mode='lines',
                name='Moving Average',
                line=dict(color='orange', width=1)
            ))
            
            fig.add_trace(go.Scatter(
                x=upper_band.index,
                y=upper_band.values,
                mode='lines',
                name='Upper Band',
                line=dict(color='red', width=1, dash='dash')
            ))
            
            fig.add_trace(go.Scatter(
                x=lower_band.index,
                y=lower_band.values,
                mode='lines',
                name='Lower Band',
                line=dict(color='red', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(255,0,0,0.1)'
            ))
            
            fig.update_layout(
                title=f"Bollinger Bands for {symbol}",
                xaxis_title="Date",
                yaxis_title="Price",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Band statistics
            current_price = price_series.iloc[-1]
            current_upper = upper_band.iloc[-1]
            current_lower = lower_band.iloc[-1]
            current_mean = rolling_mean.iloc[-1]
            
            band_position = (current_price - current_mean) / ((current_upper - current_lower) / 2)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Current Price", f"${current_price:.2f}")
            with col2:
                st.metric("Band Position", f"{band_position:.2f}")
            with col3:
                signal = "SELL" if band_position > 0.5 else "BUY" if band_position < -0.5 else "HOLD"
                st.metric("Signal", signal)
    
    def analyze_ml_strategy(self, prices: pd.DataFrame, params: Dict):
        """Analyze ML strategy specifics."""
        st.subheader("🤖 ML Strategy Analysis")
        
        lookback_days = params.get('lookback_days', 60)
        
        st.info(f"ML Strategy uses {lookback_days} days of historical data to predict future returns.")
        
        # Feature importance analysis (simplified)
        st.markdown("**Key Features:**")
        st.write("- Historical returns (5-day lookback)")
        st.write("- Price momentum indicators")
        st.write("- Volatility measures")
        st.write("- Technical indicators")
        
        # Model performance metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Training Window", f"{int(lookback_days * 0.8)} days")
        with col2:
            st.metric("Prediction Horizon", "1 day")
    
    def display_weight_changes_analysis(self, current_weights: Dict, new_weights: Dict):
        """Display detailed weight changes analysis."""
        st.subheader("⚖️ Weight Changes Analysis")
        
        # Calculate changes
        changes = {}
        for symbol in current_weights:
            current = current_weights[symbol]
            new = new_weights.get(symbol, 0)
            change = new - current
            changes[symbol] = {
                'current': current,
                'new': new,
                'change': change,
                'change_pct': change / current if current > 0 else 0
            }
        
        # Create visualization
        symbols = list(changes.keys())
        current_vals = [changes[s]['current'] for s in symbols]
        new_vals = [changes[s]['new'] for s in symbols]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name='Current',
            x=symbols,
            y=current_vals,
            marker_color='lightblue'
        ))
        
        fig.add_trace(go.Bar(
            name='New',
            x=symbols,
            y=new_vals,
            marker_color='darkblue'
        ))
        
        fig.update_layout(
            title="Current vs New Weight Allocation",
            xaxis_title="Symbol",
            yaxis_title="Weight",
            barmode='group',
            yaxis=dict(tickformat='.1%')
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Changes table
        changes_data = []
        for symbol, data in changes.items():
            changes_data.append({
                'Symbol': symbol,
                'Current Weight': f"{data['current']:.2%}",
                'New Weight': f"{data['new']:.2%}",
                'Absolute Change': f"{data['change']:+.2%}",
                'Relative Change': f"{data['change_pct']:+.1%}"
            })
        
        changes_df = pd.DataFrame(changes_data)
        st.dataframe(changes_df, use_container_width=True)
    
    def render_backtesting(self):
        """Render backtesting interface."""
        st.header("📊 Strategy Backtesting")
        
        # Backtesting parameters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            backtest_period = st.selectbox(
                "Backtesting Period",
                options=['3mo', '6mo', '1y', '2y', '5y'],
                index=2
            )
        
        with col2:
            rebalance_frequency = st.selectbox(
                "Rebalancing Frequency",
                options=['Daily', 'Weekly', 'Monthly', 'Quarterly'],
                index=2
            )
        
        with col3:
            transaction_cost = st.slider(
                "Transaction Cost (%)",
                min_value=0.0,
                max_value=1.0,
                value=0.1,
                step=0.01,
                format="%.2f%%"
            )
        
        # Strategy selection for backtesting
        strategies_to_backtest = st.multiselect(
            "Select Strategies to Backtest",
            options=list(STRATEGIES.keys()),
            default=list(STRATEGIES.keys())
        )
        
        # Strategy parameters for backtesting
        backtest_params_map = {}
        if strategies_to_backtest:
            st.markdown("**Strategy Parameters for Backtesting:**")
            for strategy in strategies_to_backtest:
                with st.expander(f"⚙️ {strategy.title()} Parameters"):
                    backtest_params_map[strategy] = self.render_strategy_parameters_detailed(strategy)
        
        if strategies_to_backtest and st.button("Run Backtest"):
            self.run_backtest(strategies_to_backtest, backtest_period, rebalance_frequency, transaction_cost, backtest_params_map)
    
    def run_backtest(self, strategies: List[str], period: str, frequency: str, transaction_cost: float, backtest_params_map: Dict = None):
        """Run comprehensive backtesting analysis."""
        try:
            st.subheader("🔄 Backtesting Results")
            
            # Get extended historical data
            portfolio_manager = st.session_state.portfolio_manager
            
            # Simulate backtesting (simplified version)
            st.info("Running backtesting simulation...")
            
            # For demonstration, we'll use the existing price data
            prices = portfolio_manager.get_price_history()
            initial_weights = portfolio_manager.get_current_weights()
            
            backtest_results = {}
            
            for strategy_name in strategies:
                try:
                    # Get strategy parameters for this strategy
                    params = backtest_params_map.get(strategy_name, {}) if backtest_params_map else {}
                    strategy = get_strategy(strategy_name, **params)
                    new_weights = strategy.calculate_new_weights(prices, initial_weights)
                    
                    # Calculate backtested performance (simplified)
                    performance = self.simulate_backtest_performance(
                        prices, new_weights, frequency, transaction_cost
                    )
                    
                    backtest_results[strategy_name] = performance
                    
                    # Log backtest execution details
                    logger.info(f"Backtest - {strategy_name} with params {params}: weights={new_weights}")
                    
                except Exception as e:
                    st.error(f"Backtesting failed for {strategy_name}: {e}")
                    logger.error(f"Error in backtest for {strategy_name}: {e}")
                    continue
            
            if backtest_results:
                self.display_backtest_results(backtest_results)
            
        except Exception as e:
            logger.error(f"Backtesting error: {e}")
            st.error(f"Backtesting failed: {e}")
    
    def simulate_backtest_performance(self, prices: pd.DataFrame, weights: Dict[str, float], 
                                    frequency: str, transaction_cost: float) -> Dict:
        """Simulate backtesting performance (simplified)."""
        # This is a simplified simulation
        # In a real implementation, you would:
        # 1. Split data into training/testing periods
        # 2. Rebalance at specified frequency
        # 3. Account for transaction costs
        # 4. Handle corporate actions, dividends, etc.
        
        returns = prices.pct_change().dropna()
        portfolio_returns = (returns * pd.Series(weights)).sum(axis=1)
        
        # Apply transaction costs (simplified)
        # Assume rebalancing happens monthly and costs are applied
        monthly_cost = transaction_cost / 100 / 12  # Convert to monthly
        adjusted_returns = portfolio_returns - monthly_cost
        
        # Calculate metrics
        total_return = (1 + adjusted_returns).prod() - 1
        annualized_return = (1 + adjusted_returns.mean()) ** 252 - 1
        volatility = adjusted_returns.std() * (252 ** 0.5)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        cumulative_returns = (1 + adjusted_returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'cumulative_returns': cumulative_returns
        }
    
    def display_backtest_results(self, backtest_results: Dict):
        """Display backtesting results."""
        st.subheader("📈 Backtesting Performance Summary")
        
        # Performance table
        performance_data = []
        for strategy_name, results in backtest_results.items():
            performance_data.append({
                'Strategy': strategy_name.title(),
                'Total Return': f"{results.get('total_return', 0):.2%}",
                'Annualized Return': f"{results.get('annualized_return', 0):.2%}",
                'Volatility': f"{results.get('volatility', 0):.2%}",
                'Sharpe Ratio': f"{results.get('sharpe_ratio', 0):.3f}",
                'Max Drawdown': f"{results.get('max_drawdown', 0):.2%}"
            })
        
        performance_df = pd.DataFrame(performance_data)
        st.dataframe(performance_df, use_container_width=True)
        
        # Cumulative returns chart
        fig = go.Figure()
        
        colors = px.colors.qualitative.Set1
        for i, (strategy_name, results) in enumerate(backtest_results.items()):
            if 'cumulative_returns' in results:
                cumulative_returns = results['cumulative_returns']
                fig.add_trace(go.Scatter(
                    x=cumulative_returns.index,
                    y=cumulative_returns.values,
                    mode='lines',
                    name=strategy_name.title(),
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
        
        fig.update_layout(
            title="Backtested Cumulative Returns",
            xaxis_title="Date",
            yaxis_title="Cumulative Return",
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    def render_strategy_optimization(self):
        """Render strategy optimization interface."""
        st.header("⚙️ Strategy Parameter Optimization")
        
        # Strategy selection
        strategy_to_optimize = st.selectbox(
            "Select Strategy to Optimize",
            options=list(STRATEGIES.keys())
        )
        
        # Optimization objective
        optimization_objective = st.selectbox(
            "Optimization Objective",
            options=['Sharpe Ratio', 'Total Return', 'Minimize Volatility', 'Minimize Drawdown']
        )
        
        # Parameter ranges for optimization
        st.subheader("Parameter Ranges")
        
        param_ranges = self.render_optimization_parameters(strategy_to_optimize)
        
        if param_ranges and st.button("Run Optimization"):
            self.run_parameter_optimization(strategy_to_optimize, param_ranges, optimization_objective)
    
    def render_optimization_parameters(self, strategy_name: str) -> Dict:
        """Render parameter ranges for optimization."""
        param_ranges = {}
        
        if strategy_name == 'bollinger':
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Window Size Range**")
                window_min = st.number_input("Min Window", value=10, min_value=5, max_value=50)
                window_max = st.number_input("Max Window", value=30, min_value=5, max_value=50)
                param_ranges['window'] = (window_min, window_max)
            
            with col2:
                st.markdown("**Standard Deviation Range**")
                std_min = st.number_input("Min Std Dev", value=1.5, min_value=1.0, max_value=3.0, step=0.1)
                std_max = st.number_input("Max Std Dev", value=2.5, min_value=1.0, max_value=3.0, step=0.1)
                param_ranges['std_dev'] = (std_min, std_max)
        
        elif strategy_name == 'ml':
            st.markdown("**Lookback Days Range**")
            lookback_min = st.number_input("Min Lookback", value=30, min_value=20, max_value=200)
            lookback_max = st.number_input("Max Lookback", value=90, min_value=20, max_value=200)
            param_ranges['lookback_days'] = (lookback_min, lookback_max)
        
        elif strategy_name == 'momentum':
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Lookback Period Range**")
                period_min = st.number_input("Min Period", value=10, min_value=5, max_value=60)
                period_max = st.number_input("Max Period", value=40, min_value=5, max_value=60)
                param_ranges['lookback_period'] = (period_min, period_max)
            
            with col2:
                st.markdown("**Momentum Threshold Range**")
                threshold_min = st.number_input("Min Threshold", value=0.01, min_value=0.005, max_value=0.10, step=0.005, format="%.3f")
                threshold_max = st.number_input("Max Threshold", value=0.05, min_value=0.005, max_value=0.10, step=0.005, format="%.3f")
                param_ranges['momentum_threshold'] = (threshold_min, threshold_max)
        
        return param_ranges
    
    def run_parameter_optimization(self, strategy_name: str, param_ranges: Dict, objective: str):
        """Run parameter optimization for a strategy."""
        try:
            st.subheader("🔍 Parameter Optimization Results")
            
            # Get portfolio data
            portfolio_manager = st.session_state.portfolio_manager
            prices = portfolio_manager.get_price_history()
            current_weights = portfolio_manager.get_current_weights()
            
            # Generate parameter combinations
            param_combinations = self.generate_parameter_combinations(param_ranges)
            
            st.info(f"Testing {len(param_combinations)} parameter combinations...")
            
            # Progress bar
            progress_bar = st.progress(0)
            results = []
            
            for i, params in enumerate(param_combinations):
                try:
                    # Run strategy with these parameters
                    strategy = get_strategy(strategy_name, **params)
                    new_weights = strategy.calculate_new_weights(prices, current_weights)
                    
                    # Calculate performance
                    performance = self.calculate_strategy_performance(prices, new_weights)
                    
                    # Store results
                    result = {
                        'params': params,
                        'performance': performance
                    }
                    results.append(result)
                    
                except Exception as e:
                    logger.warning(f"Parameter combination failed: {params}, error: {e}")
                    continue
                
                # Update progress
                progress_bar.progress((i + 1) / len(param_combinations))
            
            if results:
                self.display_optimization_results(results, objective, strategy_name)
            else:
                st.error("No successful parameter combinations found")
            
        except Exception as e:
            logger.error(f"Optimization error: {e}")
            st.error(f"Parameter optimization failed: {e}")
    
    def generate_parameter_combinations(self, param_ranges: Dict) -> List[Dict]:
        """Generate all combinations of parameters within ranges."""
        param_grids = {}
        
        for param_name, (min_val, max_val) in param_ranges.items():
            if param_name in ['window', 'lookback_days', 'lookback_period']:
                # Integer parameters
                param_grids[param_name] = list(range(int(min_val), int(max_val) + 1, 5))
            else:
                # Float parameters
                param_grids[param_name] = [min_val + i * (max_val - min_val) / 10 for i in range(11)]
        
        # Generate all combinations
        param_names = list(param_grids.keys())
        param_values = list(param_grids.values())
        
        combinations = []
        for combination in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combination))
            combinations.append(param_dict)
        
        return combinations[:50]  # Limit to 50 combinations for performance
    
    def display_optimization_results(self, results: List[Dict], objective: str, strategy_name: str):
        """Display parameter optimization results."""
        # Sort results by objective
        objective_mapping = {
            'Sharpe Ratio': 'sharpe_ratio',
            'Total Return': 'total_return',
            'Minimize Volatility': 'volatility',
            'Minimize Drawdown': 'max_drawdown'
        }
        
        objective_key = objective_mapping[objective]
        reverse_sort = objective not in ['Minimize Volatility', 'Minimize Drawdown']
        
        sorted_results = sorted(
            results, 
            key=lambda x: x['performance'].get(objective_key, 0), 
            reverse=reverse_sort
        )
        
        # Display top results
        st.subheader(f"🏆 Top Parameter Combinations (by {objective})")
        
        top_results = sorted_results[:10]
        optimization_data = []
        
        for i, result in enumerate(top_results):
            params = result['params']
            performance = result['performance']
            
            row = {
                'Rank': i + 1,
                'Sharpe Ratio': f"{performance.get('sharpe_ratio', 0):.3f}",
                'Total Return': f"{performance.get('total_return', 0):.2%}",
                'Volatility': f"{performance.get('volatility', 0):.2%}",
                'Max Drawdown': f"{performance.get('max_drawdown', 0):.2%}"
            }
            
            # Add parameter columns
            for param_name, param_value in params.items():
                if isinstance(param_value, float):
                    row[param_name.title()] = f"{param_value:.2f}"
                else:
                    row[param_name.title()] = str(param_value)
            
            optimization_data.append(row)
        
        optimization_df = pd.DataFrame(optimization_data)
        st.dataframe(optimization_df, use_container_width=True)
        
        # Best parameters summary
        best_result = sorted_results[0]
        best_params = best_result['params']
        best_performance = best_result['performance']
        
        st.subheader("🎯 Optimal Parameters")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Best Parameters:**")
            for param_name, param_value in best_params.items():
                if isinstance(param_value, float):
                    st.write(f"- {param_name.title()}: {param_value:.2f}")
                else:
                    st.write(f"- {param_name.title()}: {param_value}")
        
        with col2:
            st.markdown("**Performance with Optimal Parameters:**")
            st.metric("Sharpe Ratio", f"{best_performance.get('sharpe_ratio', 0):.3f}")
            st.metric("Total Return", f"{best_performance.get('total_return', 0):.2%}")
            st.metric("Volatility", f"{best_performance.get('volatility', 0):.2%}")
            st.metric("Max Drawdown", f"{best_performance.get('max_drawdown', 0):.2%}")
        
        # Parameter sensitivity analysis
        if len(results) > 10:
            self.display_parameter_sensitivity(results, objective_key)
    
    def display_parameter_sensitivity(self, results: List[Dict], objective_key: str):
        """Display parameter sensitivity analysis."""
        st.subheader("📊 Parameter Sensitivity Analysis")
        
        # Extract parameter values and objective values
        param_names = list(results[0]['params'].keys())
        
        for param_name in param_names:
            param_values = [r['params'][param_name] for r in results]
            objective_values = [r['performance'].get(objective_key, 0) for r in results]
            
            # Create scatter plot
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=param_values,
                y=objective_values,
                mode='markers',
                name=param_name.title(),
                marker=dict(
                    size=8,
                    color=objective_values,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title=objective_key.replace('_', ' ').title())
                )
            ))
            
            fig.update_layout(
                title=f"{objective_key.replace('_', ' ').title()} vs {param_name.title()}",
                xaxis_title=param_name.title(),
                yaxis_title=objective_key.replace('_', ' ').title()
            )
            
            st.plotly_chart(fig, use_container_width=True)


def main():
    """Main application entry point."""
    try:
        app = PortfolioApp()
        app.run()
    except Exception as e:
        logger.error(f"Critical application error: {e}")
        st.error("A critical error occurred. Please check the logs.")


if __name__ == "__main__":
    main()