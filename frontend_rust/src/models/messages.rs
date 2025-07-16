use crate::api::client::portfolio_pb::*;

/// Application messages for async communication
#[derive(Debug, Clone)]
pub enum AppMessage {
    // Connection status
    Connected,
    ConnectionFailed(String),
    
    // Portfolio operations
    PortfoliosList(Vec<String>),
    PortfolioLoaded(Portfolio),
    PortfolioCreated(Portfolio),
    PortfolioUpdated(Portfolio),
    PortfolioDeleted(String),
    
    // Strategy operations
    StrategyResult(StrategyResult),
    StrategyAnalysisComplete(StrategyAnalysis),
    
    // Data operations
    PriceHistory(PriceHistory),
    BacktestResult(BacktestResult),
    DataSourceUpdated(bool), // is_mock_data
    DataSourceStatus(DataSourceStatus),
    
    // UI operations
    RefreshData,
    RefreshCharts,
    
    // Status messages
    Error(String),
    Warning(String),
    Success(String),
    LoadingComplete,
}

/// Data source status information
#[derive(Debug, Clone)]
pub struct DataSourceStatus {
    pub current_source: String,      // "yfinance", "alpha_vantage", "mock"
    pub is_mock_data: bool,
    pub last_update: String,         // ISO timestamp
    pub success_rate: f64,           // 0.0 to 1.0
    pub response_time_ms: u64,
    pub error_count: u32,
    pub available_sources: Vec<String>,
    pub data_quality: DataQuality,
}

/// Data quality indicator
#[derive(Debug, Clone, PartialEq)]
pub enum DataQuality {
    High,
    Medium,
    Low,
    Unknown,
}

impl DataQuality {
    pub fn as_str(&self) -> &'static str {
        match self {
            DataQuality::High => "High",
            DataQuality::Medium => "Medium",
            DataQuality::Low => "Low",
            DataQuality::Unknown => "Unknown",
        }
    }
}

/// Strategy analysis result
#[derive(Debug, Clone)]
pub struct StrategyAnalysis {
    pub strategy_name: String,
    pub parameters: Vec<(String, String)>,
    pub performance_metrics: crate::models::performance::PerformanceMetrics,
    pub timestamp: String,
    pub portfolio_name: String,
}