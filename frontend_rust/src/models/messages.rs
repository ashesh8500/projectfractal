use crate::api::client::portfolio_pb::*;

// Message types for async communication
#[derive(Debug, Clone)]
pub enum AppMessage {
    Connected,
    ConnectionFailed(String),
    PortfolioCreated(Portfolio),
    PortfolioLoaded(Portfolio),
    PortfoliosList(Vec<String>),
    StrategyResult(StrategyResult),
    PriceHistory(PriceHistory),
    BacktestResult(BacktestResult),
    DataSourceUpdated(bool), // is_mock_data
    DataSourceStatus(DataSourceStatus),
    Error(String),
    LoadingComplete,
    RefreshData,
}

// Enhanced data source status tracking
#[derive(Debug, Clone)]
pub struct DataSourceStatus {
    pub current_source: String,      // "yfinance", "alpha_vantage", "mock"
    pub is_mock_data: bool,
    pub last_update: String,         // ISO timestamp
    pub success_rate: f64,           // 0.0 to 1.0
    pub response_time_ms: u64,
    pub error_count: u32,
    pub available_sources: Vec<String>,
}