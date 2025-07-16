use std::collections::HashMap;
use std::time::Instant;
use egui::Color32;

use crate::api::client::portfolio_pb::*;
use crate::models::messages::DataSourceStatus;
use crate::models::performance::{PerformanceMetrics, StrategyAnalysis};

#[derive(Debug, Clone, PartialEq)]
pub enum ChartType {
    Line,
    Bar,
    Candlestick,
}

impl ChartType {
    pub fn as_str(&self) -> &'static str {
        match self {
            ChartType::Line => "Line Chart",
            ChartType::Bar => "Bar Chart", 
            ChartType::Candlestick => "Candlestick",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub enum TerminalTheme {
    Dark,
    Light,
    Bloomberg,
    Professional,
}

impl TerminalTheme {
    pub fn as_str(&self) -> &'static str {
        match self {
            TerminalTheme::Dark => "Dark",
            TerminalTheme::Light => "Light",
            TerminalTheme::Bloomberg => "Bloomberg",
            TerminalTheme::Professional => "Professional",
        }
    }
    
    pub fn get_colors(&self) -> TerminalColors {
        match self {
            TerminalTheme::Dark => TerminalColors {
                background: Color32::from_rgb(18, 18, 18),
                text: Color32::from_rgb(255, 255, 255),
                positive: Color32::from_rgb(0, 255, 0),
                negative: Color32::from_rgb(255, 0, 0),
                neutral: Color32::from_rgb(128, 128, 128),
                accent: Color32::from_rgb(0, 150, 255),
            },
            TerminalTheme::Light => TerminalColors {
                background: Color32::from_rgb(255, 255, 255),
                text: Color32::from_rgb(0, 0, 0),
                positive: Color32::from_rgb(0, 150, 0),
                negative: Color32::from_rgb(200, 0, 0),
                neutral: Color32::from_rgb(100, 100, 100),
                accent: Color32::from_rgb(0, 100, 200),
            },
            TerminalTheme::Bloomberg => TerminalColors {
                background: Color32::from_rgb(0, 0, 0),
                text: Color32::from_rgb(255, 165, 0),
                positive: Color32::from_rgb(0, 255, 0),
                negative: Color32::from_rgb(255, 0, 0),
                neutral: Color32::from_rgb(128, 128, 128),
                accent: Color32::from_rgb(255, 165, 0),
            },
            TerminalTheme::Professional => TerminalColors {
                background: Color32::from_rgb(30, 30, 40),
                text: Color32::from_rgb(220, 220, 220),
                positive: Color32::from_rgb(0, 200, 100),
                negative: Color32::from_rgb(255, 100, 100),
                neutral: Color32::from_rgb(150, 150, 150),
                accent: Color32::from_rgb(100, 150, 255),
            },
        }
    }
}

#[derive(Debug, Clone)]
pub struct TerminalColors {
    pub background: Color32,
    pub text: Color32,
    pub positive: Color32,
    pub negative: Color32,
    pub neutral: Color32,
    pub accent: Color32,
}

// Main application state
pub struct AppState {
    // UI state
    pub portfolio_name: String,
    pub available_portfolios: Vec<String>,
    pub holdings: HashMap<String, f64>,
    pub new_symbol: String,
    pub new_shares: String,
    pub selected_strategy: String,
    pub strategy_params: HashMap<String, String>,
    pub error_msg: Option<String>,
    pub success_msg: Option<String>,
    pub loading: bool,
    pub connection_status: String,
    
    // Data
    pub current_portfolio: Option<Portfolio>,
    pub strategy_result: Option<StrategyResult>,
    pub price_history: Option<PriceHistory>,
    pub backtest_result: Option<BacktestResult>,
    pub data_source_is_mock: bool,
    
    // Enhanced data source status
    pub data_source_status: Option<DataSourceStatus>,
    pub last_data_refresh: Instant,
    pub auto_refresh_enabled: bool,
    pub refresh_interval_seconds: u64,
    
    // Enhanced UI state
    pub show_advanced_options: bool,
    pub selected_chart_type: ChartType,
    pub selected_time_period: String,
    pub show_data_source_warning: bool,
    pub show_data_source_panel: bool,
    
    // Professional terminal features
    pub keyboard_shortcuts_enabled: bool,
    pub terminal_theme: TerminalTheme,
    pub real_time_updates: bool,
    
    // Window states
    pub show_strategy_analyzer: bool,
    pub show_risk_dashboard: bool,
    pub show_portfolio_comparison: bool,
    pub show_settings: bool,
    pub show_backtest_analyzer: bool,
    pub show_performance_dashboard: bool,
    pub show_technical_indicators: bool,
    
    // Strategy analysis
    pub strategy_analyses: Vec<StrategyAnalysis>,
    pub selected_analysis: Option<usize>,
    
    // Ticker visualization
    pub selected_tickers: HashMap<String, bool>, // ticker -> selected
    pub available_tickers: Vec<String>,
    pub show_charts: bool,
    pub refresh_charts_requested: bool,
    pub show_percentage: bool,
    
    // Technical indicators
    pub show_moving_averages: bool,
    pub show_bollinger_bands: bool,
    pub show_rsi: bool,
    pub ma_period: u32,
    pub bb_period: u32,
    pub rsi_period: u32,

    // Backtest analyzer
    pub backtest_selected_month: usize,
}

impl Default for AppState {
    fn default() -> Self {
        Self {
            portfolio_name: String::new(),
            available_portfolios: Vec::new(),
            holdings: HashMap::new(),
            new_symbol: String::new(),
            new_shares: String::new(),
            selected_strategy: "bollinger".to_string(),
            strategy_params: HashMap::new(),
            error_msg: None,
            success_msg: None,
            loading: false,
            connection_status: "Connecting...".to_string(),
            current_portfolio: None,
            strategy_result: None,
            price_history: None,
            backtest_result: None,
            data_source_is_mock: false,
            
            // Enhanced data source status
            data_source_status: None,
            last_data_refresh: Instant::now(),
            auto_refresh_enabled: true,
            refresh_interval_seconds: 30,
            
            // Enhanced UI state
            show_advanced_options: false,
            selected_chart_type: ChartType::Line,
            selected_time_period: "1y".to_string(),
            show_data_source_warning: false,
            show_data_source_panel: false,
            
            // Professional terminal features
            keyboard_shortcuts_enabled: true,
            terminal_theme: TerminalTheme::Professional,
            real_time_updates: true,
            
            // Window states
            show_strategy_analyzer: false,
            show_risk_dashboard: false,
            show_portfolio_comparison: false,
            show_settings: false,
            show_backtest_analyzer: false,
            show_performance_dashboard: false,
            show_technical_indicators: false,
            
            // Strategy analysis
            strategy_analyses: Vec::new(),
            selected_analysis: None,
            
            // Ticker visualization
            selected_tickers: HashMap::new(),
            available_tickers: vec!["AAPL".to_string(), "GOOGL".to_string(), "MSFT".to_string(), "NVDA".to_string(), "AMZN".to_string(), "TSLA".to_string()],
            show_charts: true,
            refresh_charts_requested: false,
            show_percentage: false,
            
            // Technical indicators
            show_moving_averages: false,
            show_bollinger_bands: false,
            show_rsi: false,
            ma_period: 20,
            bb_period: 20,
            rsi_period: 14,

            // Backtest analyzer
            backtest_selected_month: 0,
        }
    }
}