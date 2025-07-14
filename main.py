"""
Production-grade Streamlit application for portfolio management.
"""
import logging
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Optional

# Import our production modules
from config import setup_logging, config
from portfolio_manager import PortfolioManager
from strategies import get_strategy, STRATEGIES
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
            st.title("📊 Portfolio Optimizer Pro")
            st.markdown("---")
            
            # Sidebar for navigation and portfolio management
            self.render_sidebar()
            
            # Main content area
            if st.session_state.portfolio_manager is None:
                self.render_welcome_page()
            else:
                self.render_main_dashboard()
                
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
        
        # Strategy selection
        st.sidebar.subheader("Strategy")
        strategy_name = st.sidebar.selectbox(
            "Select Strategy",
            options=list(STRATEGIES.keys()),
            key="strategy_selector"
        )
        
        if st.sidebar.button("Run Strategy"):
            self.run_strategy(strategy_name)
    
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
    
    def run_strategy(self, strategy_name: str):
        """Run a rebalancing strategy."""
        try:
            if st.session_state.portfolio_manager is None:
                st.sidebar.error("No portfolio loaded")
                return
            
            # Get current data
            prices = st.session_state.portfolio_manager.get_price_history()
            current_weights = st.session_state.portfolio_manager.get_current_weights()
            
            # Create and run strategy
            strategy = get_strategy(strategy_name)
            new_weights = strategy.calculate_new_weights(prices, current_weights)
            
            # Display results
            st.subheader(f"🤖 {strategy.name} Results")
            
            # Create comparison dataframe
            comparison_df = pd.DataFrame({
                'Symbol': list(current_weights.keys()),
                'Current Weight': [f"{w:.2%}" for w in current_weights.values()],
                'New Weight': [f"{new_weights.get(s, 0):.2%}" for s in current_weights.keys()],
                'Change': [f"{new_weights.get(s, 0) - current_weights[s]:+.2%}" for s in current_weights.keys()]
            })
            
            st.dataframe(comparison_df, use_container_width=True)
            
            # Show implementation suggestions
            total_value = st.session_state.portfolio_manager.get_current_value()
            
            st.subheader("💡 Implementation Suggestions")
            
            for symbol in current_weights.keys():
                current_value = current_weights[symbol] * total_value
                target_value = new_weights.get(symbol, 0) * total_value
                difference = target_value - current_value
                
                current_price = st.session_state.portfolio_manager.current_prices[symbol]
                shares_change = difference / current_price
                
                if abs(shares_change) > 0.1:  # Only show significant changes
                    action = "BUY" if shares_change > 0 else "SELL"
                    st.write(f"**{symbol}**: {action} {abs(shares_change):.0f} shares (${difference:+,.2f})")
            
            logger.info(f"Ran {strategy_name} strategy successfully")
            
        except StrategyError as e:
            st.error(f"Strategy error: {e}")
        except Exception as e:
            logger.error(f"Error running strategy: {e}")
            st.error(f"Failed to run strategy: {e}")


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