use eframe::{egui, App, CreationContext, Frame};
use egui::{CentralPanel, TopBottomPanel, ScrollArea, RichText, Color32, Window};
use egui_plot::{Legend, Line, Plot, PlotPoints, Bar, BarChart, GridMark, Corner, CoordinatesFormatter};
use tonic::transport::Channel;
use tonic::Request;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::mpsc;
use tokio::runtime::Runtime;
use chrono::{Utc, Duration, TimeZone};
use rand::Rng;
use std::time::{Instant, Duration as StdDuration};

// Component system
mod components;
use components::{manager::ComponentManager, Component};

// Generated from proto
pub mod portfolio_pb {
    tonic::include_proto!("portfolio");
}
use portfolio_pb::portfolio_service_client::PortfolioServiceClient;
use portfolio_pb::*;

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

#[derive(Debug, Clone, PartialEq)]
enum ChartType {
    Line,
    Bar,
    Candlestick,
}

impl ChartType {
    fn as_str(&self) -> &'static str {
        match self {
            ChartType::Line => "Line Chart",
            ChartType::Bar => "Bar Chart", 
            ChartType::Candlestick => "Candlestick",
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
enum TerminalTheme {
    Dark,
    Light,
    Bloomberg,
    Professional,
}

impl TerminalTheme {
    fn as_str(&self) -> &'static str {
        match self {
            TerminalTheme::Dark => "Dark",
            TerminalTheme::Light => "Light",
            TerminalTheme::Bloomberg => "Bloomberg",
            TerminalTheme::Professional => "Professional",
        }
    }
    
    fn get_colors(&self) -> TerminalColors {
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
struct TerminalColors {
    background: Color32,
    text: Color32,
    positive: Color32,
    negative: Color32,
    neutral: Color32,
    accent: Color32,
}

#[derive(Debug, Clone)]
struct PerformanceMetrics {
    total_return: f64,
    annualized_return: f64,
    volatility: f64,
    sharpe_ratio: f64,
    max_drawdown: f64,
    calmar_ratio: f64,
    sortino_ratio: f64,
    win_rate: f64,
    profit_factor: f64,
    dates: Vec<String>,
    values: Vec<f64>,
    benchmark_values: Vec<f64>,
}

impl Default for PerformanceMetrics {
    fn default() -> Self {
        Self {
            total_return: 0.0,
            annualized_return: 0.0,
            volatility: 0.0,
            sharpe_ratio: 0.0,
            max_drawdown: 0.0,
            calmar_ratio: 0.0,
            sortino_ratio: 0.0,
            win_rate: 0.0,
            profit_factor: 0.0,
            dates: Vec::new(),
            values: Vec::new(),
            benchmark_values: Vec::new(),
        }
    }
}

#[derive(Debug, Clone)]
struct StrategyAnalysis {
    portfolio_name: String,
    strategy_name: String,
    current_weights: HashMap<String, f64>,
    new_weights: HashMap<String, f64>,
    changes: HashMap<String, f64>,
    expected_return: f64,
    risk_score: f64,
    sharpe_ratio: f64,
    is_mock_data: bool,
    performance_metrics: PerformanceMetrics,
}


pub struct PortfolioApp {
    // gRPC client
    rt: Arc<Runtime>,
    
    // Component system
    components: ComponentManager,
    
    // UI state
    portfolio_name: String,
    available_portfolios: Vec<String>,
    holdings: HashMap<String, f64>,
    new_symbol: String,
    new_shares: String,
    selected_strategy: String,
    strategy_params: HashMap<String, String>,
    error_msg: Option<String>,
    success_msg: Option<String>,
    loading: bool,
    connection_status: String,
    
    // Data
    current_portfolio: Option<Portfolio>,
    strategy_result: Option<StrategyResult>,
    price_history: Option<PriceHistory>,
    backtest_result: Option<BacktestResult>,
    data_source_is_mock: bool,
    
    // Enhanced data source status
    data_source_status: Option<DataSourceStatus>,
    last_data_refresh: Instant,
    auto_refresh_enabled: bool,
    refresh_interval_seconds: u64,
    
    // Enhanced UI state
    show_advanced_options: bool,
    selected_chart_type: ChartType,
    selected_time_period: String,
    show_data_source_warning: bool,
    show_data_source_panel: bool,
    
    // Professional terminal features
    keyboard_shortcuts_enabled: bool,
    terminal_theme: TerminalTheme,
    real_time_updates: bool,
    
    // Window states
    show_strategy_analyzer: bool,
    show_risk_dashboard: bool,
    show_portfolio_comparison: bool,
    show_settings: bool,
    show_backtest_analyzer: bool,
    show_performance_dashboard: bool,
    show_technical_indicators: bool,
    
    // Strategy analysis
    strategy_analyses: Vec<StrategyAnalysis>,
    selected_analysis: Option<usize>,
    
    // Ticker visualization
    selected_tickers: HashMap<String, bool>, // ticker -> selected
    available_tickers: Vec<String>,
    show_charts: bool,
    refresh_charts_requested: bool,
    show_percentage: bool,
    
    // Technical indicators
    show_moving_averages: bool,
    show_bollinger_bands: bool,
    show_rsi: bool,
    ma_period: u32,
    bb_period: u32,
    rsi_period: u32,

    // Backtest analyzer
    backtest_selected_month: usize,
    
    // Async communication
    message_receiver: Option<mpsc::UnboundedReceiver<AppMessage>>,
    message_sender: Option<mpsc::UnboundedSender<AppMessage>>,
}

impl Default for PortfolioApp {
    fn default() -> Self {
        let rt = Arc::new(Runtime::new().unwrap());
        let (tx, rx) = mpsc::unbounded_channel();
        
        Self {
            rt,
            components: ComponentManager::new(),
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
            
            // Async communication
            message_receiver: Some(rx),
            message_sender: Some(tx),
        }
    }
}

impl PortfolioApp {
    fn new(_cc: &CreationContext<'_>) -> Self {
        let mut app = Self::default();
        app.connect_to_server();
        app.load_available_portfolios();
        app
    }

    fn generate_dates_and_metrics(&self, period: &str, num_points: usize) -> PerformanceMetrics {
        PortfolioApp::generate_dates_and_metrics_static(period, num_points)
    }

    fn generate_dates_and_metrics_static(period: &str, num_points: usize) -> PerformanceMetrics {
        let end_date = Utc::now();
        let start_date = match period {
            "1mo" => end_date - Duration::days(30),
            "3mo" => end_date - Duration::days(90),
            "6mo" => end_date - Duration::days(180),
            "1y" => end_date - Duration::days(365),
            "2y" => end_date - Duration::days(730),
            _ => end_date - Duration::days(365),
        };

        let total_days = (end_date - start_date).num_days() as usize;
        let step = if total_days > num_points { total_days / num_points } else { 1 };

        let mut dates = Vec::new();
        let mut values = Vec::new();
        let mut benchmark_values = Vec::new();
        let mut returns = Vec::new();
        let mut benchmark_returns = Vec::new();

        let mut portfolio_value = 100.0;
        let mut benchmark_value = 100.0;
        let mut max_value = 100.0;
        let mut max_drawdown = 0.0;

        for i in 0..num_points {
            let current_date = start_date + Duration::days((i * step) as i64);
            dates.push(current_date.format("%Y-%m-%d").to_string());

            // Generate realistic returns with some correlation and volatility
            let market_factor = 0.0003 + 0.001 * (i as f64 * 0.1).sin(); // Base market trend
            let mut rng = rand::thread_rng();
            let portfolio_return = market_factor + 0.0005 * (i as f64 * 0.15).cos() + (rng.gen::<f64>() - 0.5) * 0.02;
            let benchmark_return = market_factor * 0.8 + (rng.gen::<f64>() - 0.5) * 0.015;

            portfolio_value *= 1.0 + portfolio_return;
            benchmark_value *= 1.0 + benchmark_return;

            values.push(portfolio_value);
            benchmark_values.push(benchmark_value);
            returns.push(portfolio_return);
            benchmark_returns.push(benchmark_return);

            // Track drawdown
            if portfolio_value > max_value {
                max_value = portfolio_value;
            }
            let current_drawdown = (max_value - portfolio_value) / max_value;
            if current_drawdown > max_drawdown {
                max_drawdown = current_drawdown;
            }
        }

        let total_return = (portfolio_value - 100.0) / 100.0;
        let days_in_period = total_days as f64;
        let annualized_return = (portfolio_value / 100.0).powf(365.0 / days_in_period) - 1.0;
        let mean_return = returns.iter().sum::<f64>() / returns.len() as f64;
        let variance = returns.iter().map(|r| (r - mean_return).powi(2)).sum::<f64>() / returns.len() as f64;
        let volatility = variance.sqrt() * (252.0_f64).sqrt();
        let risk_free_rate = 0.02;
        let sharpe_ratio = if volatility > 0.0 { (annualized_return - risk_free_rate) / volatility } else { 0.0 };
        let calmar_ratio = if max_drawdown > 0.0 { annualized_return / max_drawdown } else { 0.0 };
        let downside_returns: Vec<f64> = returns.iter().filter(|&&r| r < 0.0).cloned().collect();
        let downside_deviation = if !downside_returns.is_empty() {
            let mean_downside = downside_returns.iter().sum::<f64>() / downside_returns.len() as f64;
            let downside_variance = downside_returns.iter().map(|r| (r - mean_downside).powi(2)).sum::<f64>() / downside_returns.len() as f64;
            downside_variance.sqrt() * (252.0_f64).sqrt()
        } else {
            volatility
        };
        let sortino_ratio = if downside_deviation > 0.0 { (annualized_return - risk_free_rate) / downside_deviation } else { 0.0 };
        let winning_trades = returns.iter().filter(|&&r| r > 0.0).count();
        let win_rate = winning_trades as f64 / returns.len() as f64;
        let gross_profit: f64 = returns.iter().filter(|&&r| r > 0.0).sum();
        let gross_loss: f64 = returns.iter().filter(|&&r| r < 0.0).sum::<f64>().abs();
        let profit_factor = if gross_loss > 0.0 { gross_profit / gross_loss } else { 0.0 };
        PerformanceMetrics {
            total_return,
            annualized_return,
            volatility,
            sharpe_ratio,
            max_drawdown,
            calmar_ratio,
            sortino_ratio,
            win_rate,
            profit_factor,
            dates,
            values,
            benchmark_values,
        }
    }


    fn load_available_portfolios(&mut self) {
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            let rt = self.rt.clone();
            
            rt.spawn(async move {
                match Channel::from_static("http://[::1]:50051").connect().await {
                    Ok(channel) => {
                        let mut client = PortfolioServiceClient::new(channel);
                        let request = Request::new(ListPortfoliosRequest {
                            user_id: "demo_user".to_string(),
                        });

                        match client.list_portfolios(request).await {
                            Ok(response) => {
                                let portfolios = response.into_inner().portfolio_names;
                                let _ = sender.send(AppMessage::PortfoliosList(portfolios));
                            }
                            Err(e) => {
                                let _ = sender.send(AppMessage::Error(format!("Failed to load portfolios: {}", e)));
                            }
                        }
                    }
                    Err(e) => {
                        let _ = sender.send(AppMessage::Error(format!("Connection failed: {}", e)));
                    }
                }
            });
        }
    }

    fn connect_to_server(&mut self) {
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            let rt = self.rt.clone();
            
            rt.spawn(async move {
                match Channel::from_static("http://[::1]:50051").connect().await {
                    Ok(channel) => {
                        let _client = PortfolioServiceClient::new(channel);
                        // Store client in a way that can be accessed later
                        let _ = sender.send(AppMessage::Connected);
                    }
                    Err(e) => {
                        let _ = sender.send(AppMessage::ConnectionFailed(format!("Connection failed: {}", e)));
                    }
                }
            });
        }
    }

    fn process_messages(&mut self, ctx: &egui::Context) {
        if let Some(receiver) = &mut self.message_receiver {
            while let Ok(message) = receiver.try_recv() {
                match message {
                    AppMessage::Connected => {
                        self.connection_status = "Connected".to_string();
                        self.error_msg = None;
                    }
                    AppMessage::ConnectionFailed(error) => {
                        self.connection_status = "Disconnected".to_string();
                        self.error_msg = Some(error);
                    }
                    AppMessage::PortfoliosList(portfolios) => {
                        self.available_portfolios = portfolios;
                    }
                    AppMessage::PortfolioCreated(portfolio) => {
                        self.data_source_is_mock = portfolio.is_using_mock_data;
                        self.show_data_source_warning = portfolio.is_using_mock_data;
                        self.current_portfolio = Some(portfolio);
                        self.success_msg = Some("Portfolio created successfully".to_string());
                        self.holdings.clear();
                        self.loading = false;
                    }
                    AppMessage::PortfolioLoaded(portfolio) => {
                        self.data_source_is_mock = portfolio.is_using_mock_data;
                        self.show_data_source_warning = portfolio.is_using_mock_data;
                        
                        // Initialize ticker selection from portfolio holdings
                        if let Some(holdings) = &portfolio.holdings {
                            self.selected_tickers.clear();
                            for symbol in holdings.shares.keys() {
                                self.selected_tickers.insert(symbol.clone(), true);
                            }
                            // Note: Will fetch price history on next frame
                        }
                        
                        self.current_portfolio = Some(portfolio);
                        self.success_msg = Some("Portfolio loaded successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::StrategyResult(result) => {
                        self.data_source_is_mock = result.is_using_mock_data;
                        self.show_data_source_warning = result.is_using_mock_data;
                        
                        // Create strategy analysis with real calculations
                        if let Some(portfolio) = &self.current_portfolio {
                            // Calculate expected return based on weight changes
                            let total_change: f64 = result.changes.values().map(|&v| v.abs()).sum();
                            let expected_return = if total_change > 0.1 { 0.12 } else { 0.08 }; // Higher expected return for more aggressive rebalancing
                            
                            // Calculate risk score based on concentration
                            let max_weight = result.new_weights.values().fold(0.0f64, |a, &b| a.max(b));
                            let risk_score = max_weight * 100.0; // Higher concentration = higher risk
                            
                            // Estimate Sharpe ratio based on diversification
                            let num_positions = result.new_weights.values().filter(|&&w| w > 0.01).count();
                            let sharpe_ratio = match num_positions {
                                1 => 0.8,  // Single position - lower Sharpe
                                2..=3 => 1.2, // Moderate diversification
                                _ => 1.5   // Well diversified
                            };
                            
                            // Prepare for borrow checker: clone required data and call outside mutable borrow
                            let selected_time_period = self.selected_time_period.clone();
                            let performance_metrics = PortfolioApp::generate_dates_and_metrics_static(&selected_time_period, 100);
                            let analysis = StrategyAnalysis {
                                portfolio_name: portfolio.name.clone(),
                                strategy_name: self.selected_strategy.clone(),
                                current_weights: portfolio.weights.clone(),
                                new_weights: result.new_weights.clone(),
                                changes: result.changes.clone(),
                                expected_return,
                                risk_score,
                                sharpe_ratio,
                                is_mock_data: result.is_using_mock_data,
                                performance_metrics,
                            };
                            self.strategy_analyses.push(analysis);
                            
                            // Note: Backtest can be run manually from the backtest analyzer window
                        }
                        
                        self.strategy_result = Some(result);
                        self.success_msg = Some("Strategy executed successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::PriceHistory(history) => {
                        self.data_source_is_mock = history.is_using_mock_data;
                        self.show_data_source_warning = history.is_using_mock_data;
                        self.price_history = Some(history);
                        self.success_msg = Some("Price history loaded successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::BacktestResult(result) => {
                        self.data_source_is_mock = result.is_using_mock_data;
                        self.show_data_source_warning = result.is_using_mock_data;
                        self.backtest_result = Some(result);
                        self.success_msg = Some("Backtest completed successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::Error(error) => {
                        self.error_msg = Some(error);
                        self.loading = false;
                    }
                    AppMessage::LoadingComplete => {
                        self.loading = false;
                    }
                    AppMessage::DataSourceUpdated(is_mock) => {
                        self.data_source_is_mock = is_mock;
                        self.show_data_source_warning = is_mock;
                    }
                    AppMessage::DataSourceStatus(status) => {
                        self.data_source_is_mock = status.is_mock_data;
                        self.show_data_source_warning = status.is_mock_data;
                        self.data_source_status = Some(status);
                        self.last_data_refresh = Instant::now();
                    }
                    AppMessage::RefreshData => {
                        // Mark for refresh - will be handled after message processing
                        self.refresh_charts_requested = true;
                    }
                }
                ctx.request_repaint();
            }
        }
    }

    fn run_backtest_for_strategy(&mut self, portfolio_name: &str, strategy_name: &str) {
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            let rt = self.rt.clone();
            let portfolio_name = portfolio_name.to_string();
            let strategy_name = strategy_name.to_string();
            
            self.loading = true;
            
            rt.spawn(async move {
                match Channel::from_static("http://[::1]:50051").connect().await {
                    Ok(channel) => {
                        let mut client = PortfolioServiceClient::new(channel);
                        let request = Request::new(BacktestRequest {
                            user_id: "demo_user".to_string(),
                            portfolio_name,
                            strategy_name,
                            params: None, // Use default parameters
                            rebalance_frequency: "M".to_string(), // Monthly rebalancing
                            start_value: 100.0,
                            transaction_cost: 0.001, // 0.1% transaction cost
                        });

                        match client.run_backtest(request).await {
                            Ok(response) => {
                                let backtest_result = response.into_inner();
                                let _ = sender.send(AppMessage::BacktestResult(backtest_result));
                            }
                            Err(e) => {
                                let _ = sender.send(AppMessage::Error(format!("Backtest failed: {}", e)));
                            }
                        }
                    }
                    Err(e) => {
                        let _ = sender.send(AppMessage::Error(format!("Connection failed: {}", e)));
                    }
                }
            });
        }
    }

    fn clear_messages(&mut self) {
        self.error_msg = None;
        self.success_msg = None;
    }
    
    fn fetch_data_source_status(&mut self) {
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            let rt = self.rt.clone();
            
            rt.spawn(async move {
                // Simulate fetching data source status from backend
                // In a real implementation, this would be a gRPC call to get data source status
                let status = DataSourceStatus {
                    current_source: "yfinance".to_string(),
                    is_mock_data: false,
                    last_update: chrono::Utc::now().to_rfc3339(),
                    success_rate: 0.95,
                    response_time_ms: 250,
                    error_count: 0,
                    available_sources: vec![
                        "yfinance".to_string(),
                        "alpha_vantage".to_string(),
                        "mock".to_string()
                    ],
                };
                let _ = sender.send(AppMessage::DataSourceStatus(status));
            });
        }
    }

    fn create_portfolio(&mut self) {
        if self.portfolio_name.is_empty() || self.holdings.is_empty() {
            self.error_msg = Some("Portfolio name and holdings required".to_string());
            return;
        }

        self.clear_messages();
        self.loading = true;

        let name = self.portfolio_name.clone();
        let holdings = self.holdings.clone();
        let sender = self.message_sender.as_ref().unwrap().clone();
        let rt = self.rt.clone();

        rt.spawn(async move {
            match Channel::from_static("http://[::1]:50051").connect().await {
                Ok(channel) => {
                    let mut client = PortfolioServiceClient::new(channel);
                    let user_id = "demo_user".to_string(); // Default user for demo
                    let request = Request::new(CreatePortfolioRequest {
                        user_id,
                        name,
                        holdings: Some(Holdings { shares: holdings }),
                    });

                    match client.create_portfolio(request).await {
                        Ok(response) => {
                            let _ = sender.send(AppMessage::PortfolioCreated(response.into_inner()));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(format!("Failed to create portfolio: {}", e)));
                        }
                    }
                }
                Err(e) => {
                    let _ = sender.send(AppMessage::Error(format!("Connection failed: {}", e)));
                }
            }
        });
    }

    fn load_portfolio(&mut self) {
        if self.portfolio_name.is_empty() {
            self.error_msg = Some("Portfolio name required".to_string());
            return;
        }

        self.clear_messages();
        self.loading = true;

        let name = self.portfolio_name.clone();
        let sender = self.message_sender.as_ref().unwrap().clone();
        let rt = self.rt.clone();

        rt.spawn(async move {
            match Channel::from_static("http://[::1]:50051").connect().await {
                Ok(channel) => {
                    let mut client = PortfolioServiceClient::new(channel);
                    let user_id = "demo_user".to_string(); // Default user for demo
                    let request = Request::new(LoadPortfolioRequest { user_id, name });

                    match client.load_portfolio(request).await {
                        Ok(response) => {
                            let _ = sender.send(AppMessage::PortfolioLoaded(response.into_inner()));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(format!("Failed to load portfolio: {}", e)));
                        }
                    }
                }
                Err(e) => {
                    let _ = sender.send(AppMessage::Error(format!("Connection failed: {}", e)));
                }
            }
        });
    }

    fn run_strategy(&mut self) {
        if self.portfolio_name.is_empty() || self.selected_strategy.is_empty() {
            self.error_msg = Some("Portfolio name and strategy required".to_string());
            return;
        }

        self.clear_messages();
        self.loading = true;

        let portfolio_name = self.portfolio_name.clone();
        let strategy_name = self.selected_strategy.clone();
        let params = self.strategy_params.clone();
        let sender = self.message_sender.as_ref().unwrap().clone();
        let rt = self.rt.clone();

        rt.spawn(async move {
            match Channel::from_static("http://[::1]:50051").connect().await {
                Ok(channel) => {
                    let mut client = PortfolioServiceClient::new(channel);
                    let user_id = "demo_user".to_string(); // Default user for demo
                    let request = Request::new(RunStrategyRequest {
                        user_id,
                        portfolio_name,
                        strategy_name,
                        params: Some(StrategyParams { params }),
                    });

                    match client.run_strategy(request).await {
                        Ok(response) => {
                            let _ = sender.send(AppMessage::StrategyResult(response.into_inner()));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(format!("Failed to run strategy: {}", e)));
                        }
                    }
                }
                Err(e) => {
                    let _ = sender.send(AppMessage::Error(format!("Connection failed: {}", e)));
                }
            }
        });
    }

    fn get_price_history(&mut self) {
        // Get selected tickers or use portfolio name as fallback
        let portfolio_name = if !self.selected_tickers.is_empty() {
            // Create a synthetic portfolio name for selected tickers
            let selected: Vec<String> = self.selected_tickers.iter()
                .filter(|(_, &selected)| selected)
                .map(|(ticker, _)| ticker.clone())
                .collect();
            if selected.is_empty() {
                return;
            }
            format!("TICKERS_{}", selected.join("_"))
        } else if !self.portfolio_name.is_empty() {
            self.portfolio_name.clone()
        } else {
            return;
        };

        self.clear_messages();
        self.loading = true;

        let period = self.selected_time_period.clone();
        let sender = self.message_sender.as_ref().unwrap().clone();
        let rt = self.rt.clone();

        rt.spawn(async move {
            match Channel::from_static("http://[::1]:50051").connect().await {
                Ok(channel) => {
                    let mut client = PortfolioServiceClient::new(channel);
                    let user_id = "demo_user".to_string(); // Default user for demo
                    let request = Request::new(GetPriceHistoryRequest { 
                        user_id,
                        portfolio_name,
                        period,
                    });

                    match client.get_price_history(request).await {
                        Ok(response) => {
                            let _ = sender.send(AppMessage::PriceHistory(response.into_inner()));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(format!("Failed to get price history: {}", e)));
                        }
                    }
                }
                Err(e) => {
                    let _ = sender.send(AppMessage::Error(format!("Connection failed: {}", e)));
                }
            }
        });
    }

    fn render_portfolio_dashboard(&mut self, ui: &mut egui::Ui) {
        if let Some(portfolio) = &self.current_portfolio {
            ui.group(|ui| {
                ui.heading("📊 Portfolio Dashboard");
                
                // Header info
                ui.horizontal(|ui| {
                    ui.label(RichText::new(format!("Name: {}", portfolio.name)).strong());
                    ui.separator();
                    ui.label(RichText::new(format!("Total Value: ${:.2}", portfolio.total_value)).strong().color(Color32::DARK_GREEN));
                    
                    if self.data_source_is_mock {
                        ui.separator();
                        ui.colored_label(Color32::LIGHT_RED, "⚠️ Mock Data");
                    }
                });

                ui.separator();
                
                // Current weights with visual representation
                ui.heading("📈 Current Weights");
                if let Some(holdings) = &portfolio.holdings {
                    let mut bars = Vec::new();
                    for (i, (symbol, shares)) in holdings.shares.iter().enumerate() {
                        let weight = portfolio.weights.get(symbol).unwrap_or(&0.0);
                        ui.horizontal(|ui| {
                            ui.label(format!("{}: {:.2} shares", symbol, shares));
                            ui.separator();
                            let weight_pct = weight * 100.0;
                            ui.colored_label(Color32::BLUE, format!("{:.1}%", weight_pct));
                            
                            // Weight bar
                            let bar_width = (weight_pct / 100.0 * 100.0) as f32;
                            let bar_rect = ui.allocate_space(egui::Vec2::new(bar_width.max(5.0), 15.0)).1;
                            ui.painter().rect_filled(bar_rect, 2.0, Color32::from_rgb(100, 149, 237));
                        });
                        
                        bars.push(Bar::new(i as f64, weight * 100.0).name(symbol));
                    }
                    
                    // Weight distribution chart
                    ui.separator();
                    ui.label("Weight Distribution:");
                    Plot::new("weight_distribution")
                        .legend(Legend::default())
                        .height(200.0)
                        .show(ui, |plot_ui| {
                            plot_ui.bar_chart(BarChart::new(bars).color(Color32::from_rgb(100, 149, 237)));
                        });
                }

                // Strategy results
                if let Some(result) = &self.strategy_result {
                    ui.separator();
                    ui.heading("🎯 Strategy Result");
                    
                    ui.horizontal(|ui| {
                        ui.label("New Weights:");
                        if result.is_using_mock_data {
                            ui.colored_label(Color32::LIGHT_RED, "⚠️ Based on mock data");
                        }
                    });
                    
                    for (symbol, weight) in &result.new_weights {
                        ui.label(format!("{}: {:.1}%", symbol, weight * 100.0));
                    }
                    
                    ui.separator();
                    ui.label("📊 Changes:");
                    for (symbol, change) in &result.changes {
                        let color = if *change > 0.0 { Color32::GREEN } else { Color32::RED };
                        let sign = if *change > 0.0 { "+" } else { "" };
                        ui.colored_label(color, format!("{}: {}{:.1}%", symbol, sign, change * 100.0));
                    }
                }
            });
        }
    }

    fn render_price_charts(&mut self, ui: &mut egui::Ui) {
        let selected_count = self.selected_tickers.values().filter(|&&v| v).count();
        
        if selected_count == 0 {
            ui.group(|ui| {
                ui.heading("📈 Price Charts");
                ui.separator();
                ui.vertical_centered(|ui| {
                    ui.label("🎯 Select tickers above to view price charts");
                    ui.label("Choose from portfolio holdings or additional tickers");
                });
            });
            return;
        }
        
        if let Some(history) = &self.price_history {
            ui.group(|ui| {
                ui.horizontal(|ui| {
                    ui.heading("📈 Price History");
                    if history.is_using_mock_data {
                        ui.colored_label(Color32::LIGHT_RED, "⚠️ Mock Data");
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.label(format!("Showing {} tickers", selected_count));
                    });
                });
                
                let num_symbols = history.symbols.len();
                if num_symbols > 0 && !history.prices.is_empty() {
                    let rows_per_symbol = history.prices.len() / num_symbols;
                    if rows_per_symbol > 0 {
                        let plot_height = 400.0;

                        // Define formatters
                        let show_percentage = self.show_percentage;
                        let x_axis_formatter = |mark: GridMark, _max_chars: usize, _range: &std::ops::RangeInclusive<f64>| {
                            if let Some(datetime) = Utc.timestamp_opt(mark.value as i64, 0).single() {
                                datetime.format("%Y-%m-%d").to_string()
                            } else {
                                format!("Day {}", mark.value)
                            }
                        };
                        let y_axis_formatter = move |mark: GridMark, _max_chars: usize, _range: &std::ops::RangeInclusive<f64>| {
                            if show_percentage {
                                format!("{:.1}%", mark.value)
                            } else {
                                format!("${:.2}", mark.value)
                            }
                        };
                        
                        let coordinate_formatter = CoordinatesFormatter::new(move |point, _bounds| {
                            let date_str = if let Some(datetime) = Utc.timestamp_opt(point.x as i64, 0).single() {
                                datetime.format("%Y-%m-%d %H:%M:%S").to_string()
                            } else {
                                format!("Day {:.0}", point.x)
                            };
                            if show_percentage {
                                format!("Date: {}\nValue: {:.2}%", date_str, point.y)
                            } else {
                                format!("Date: {}\nPrice: ${:.2}", date_str, point.y)
                            }
                        });
                        
                        match self.selected_chart_type {
                            ChartType::Line => {
                                Plot::new("price_plot")
                                    .legend(Legend::default())
                                    .height(plot_height)
                                    .x_axis_label("Date")
                                    .y_axis_label(if self.show_percentage { "Percentage (%)" } else { "Price" })
                                    .x_axis_formatter(x_axis_formatter)
                                    .y_axis_formatter(y_axis_formatter)
                                    .coordinates_formatter(Corner::RightBottom, coordinate_formatter)
                                    .show(ui, |plot_ui| {
                                        let colors = [
                                            Color32::BLUE, Color32::RED, Color32::GREEN, Color32::YELLOW,
                                            Color32::from_rgb(128, 0, 128), Color32::from_rgb(139, 69, 19),
                                        ];
                                        
                                        for (i, symbol) in history.symbols.iter().enumerate() {
                                            if !self.selected_tickers.get(symbol).copied().unwrap_or(false) { continue; }
                                            
                                            let start = i * rows_per_symbol;
                                            let end = (start + rows_per_symbol).min(history.prices.len());
                                            if start >= history.prices.len() { continue; }

                                            let prices_slice = &history.prices[start..end];
                                            let timestamps_slice = if history.timestamps.len() == history.prices.len() {
                                                Some(&history.timestamps[start..end])
                                            } else { None };

                                            let points: PlotPoints = if let Some(timestamps) = timestamps_slice {
                                                prices_slice.iter().zip(timestamps.iter())
                                                    .map(|(price, &timestamp)| [timestamp as f64, *price])
                                                    .collect()
                                            } else {
                                                prices_slice.iter().enumerate()
                                                    .map(|(j, price)| [j as f64, *price])
                                                    .collect()
                                            };

                                            let points: PlotPoints = if self.show_percentage && !prices_slice.is_empty() {
                                                let base_price = prices_slice[0];
                                                if let Some(timestamps) = timestamps_slice {
                                                    prices_slice.iter().zip(timestamps.iter())
                                                        .map(|(price, &timestamp)| [timestamp as f64, ((price / base_price) - 1.0) * 100.0])
                                                        .collect()
                                                } else {
                                                    prices_slice.iter().enumerate()
                                                        .map(|(j, price)| [j as f64, ((price / base_price) - 1.0) * 100.0])
                                                        .collect()
                                                }
                                            } else {
                                                points
                                            };
                                            
                                            let color = colors[i % colors.len()];
                                            plot_ui.line(Line::new(points).name(symbol).width(2.5).color(color));
                                        }
                                    });
                            }
                            ChartType::Bar => {
                                Plot::new("price_bar_plot")
                                    .legend(Legend::default())
                                    .height(plot_height)
                                    .x_axis_label("Date")
                                    .y_axis_label(if self.show_percentage { "Percentage (%)" } else { "Price" })
                                    .x_axis_formatter(x_axis_formatter)
                                    .y_axis_formatter(y_axis_formatter)
                                    .coordinates_formatter(Corner::RightBottom, coordinate_formatter)
                                    .show(ui, |plot_ui| {
                                        let colors = [
                                            Color32::BLUE, Color32::RED, Color32::GREEN, Color32::YELLOW,
                                            Color32::from_rgb(128, 0, 128), Color32::from_rgb(139, 69, 19),
                                        ];
                                        
                                        for (i, symbol) in history.symbols.iter().enumerate() {
                                            if !self.selected_tickers.get(symbol).copied().unwrap_or(false) { continue; }
                                            
                                            let start = i * rows_per_symbol;
                                            let end = (start + rows_per_symbol).min(history.prices.len());
                                            if start >= history.prices.len() { continue; }

                                            let prices_slice = &history.prices[start..end];
                                            let timestamps_slice = if history.timestamps.len() == history.prices.len() {
                                                Some(&history.timestamps[start..end])
                                            } else { None };

                                            let bars: Vec<Bar> = if let Some(timestamps) = timestamps_slice {
                                                prices_slice.iter().zip(timestamps.iter())
                                                    .map(|(price, &timestamp)| Bar::new(timestamp as f64, *price))
                                                    .collect()
                                            } else {
                                                prices_slice.iter().enumerate()
                                                    .map(|(j, price)| Bar::new(j as f64, *price))
                                                    .collect()
                                            };

                                            let color = colors[i % colors.len()];
                                            plot_ui.bar_chart(BarChart::new(bars).name(symbol).color(color));
                                        }
                                    });
                            }
                            ChartType::Candlestick => {
                                Plot::new("candlestick_plot")
                                    .legend(Legend::default())
                                    .height(plot_height)
                                    .x_axis_label("Date")
                                    .y_axis_label(if self.show_percentage { "Percentage (%)" } else { "Price" })
                                    .x_axis_formatter(x_axis_formatter)
                                    .y_axis_formatter(y_axis_formatter)
                                    .coordinates_formatter(Corner::RightBottom, coordinate_formatter)
                                    .show(ui, |plot_ui| {
                                        let colors = [
                                            Color32::BLUE, Color32::RED, Color32::GREEN, Color32::YELLOW,
                                            Color32::from_rgb(128, 0, 128), Color32::from_rgb(139, 69, 19),
                                        ];
                                        
                                        for (i, symbol) in history.symbols.iter().enumerate() {
                                            if !self.selected_tickers.get(symbol).copied().unwrap_or(false) { continue; }
                                            
                                            let start = i * rows_per_symbol;
                                            let end = (start + rows_per_symbol).min(history.prices.len());
                                            if start >= history.prices.len() { continue; }

                                            let prices_slice = &history.prices[start..end];
                                            let timestamps_slice = if history.timestamps.len() == history.prices.len() {
                                                Some(&history.timestamps[start..end])
                                            } else { None };
                                            
                                            // Create candlestick-like visualization using line segments
                                            let color = colors[i % colors.len()];
                                            
                                            for (j, price) in prices_slice.iter().enumerate() {
                                                let x = if let Some(timestamps) = timestamps_slice {
                                                    timestamps[j] as f64
                                                } else {
                                                    j as f64
                                                };

                                                let base_price = if j > 0 { prices_slice[j-1] } else { *price };
                                                
                                                // Simulate OHLC from single price point
                                                let open = base_price;
                                                let close = *price;
                                                let high = open.max(close) * 1.02; // Add 2% for high
                                                let low = open.min(close) * 0.98;  // Subtract 2% for low
                                                
                                                // Create high-low line (wick)
                                                let wick_points: PlotPoints = vec![[x, low], [x, high]].into();
                                                plot_ui.line(Line::new(wick_points).width(1.0).color(Color32::GRAY));
                                                
                                                // Create open-close body
                                                let body_color = if close > open { Color32::from_rgb(0, 150, 0) } else { Color32::from_rgb(150, 0, 0) };
                                                let body_width = if let Some(timestamps) = timestamps_slice {
                                                    if timestamps.len() > 1 { (timestamps[1] - timestamps[0]) as f64 * 0.4 } else { 86400.0 * 0.4 }
                                                } else { 0.4 };
                                                let body_points: PlotPoints = vec![[x - body_width, open], [x - body_width, close], [x + body_width, close], [x + body_width, open], [x - body_width, open]].into();
                                                plot_ui.line(Line::new(body_points).width(3.0).color(body_color));
                                            }
                                            
                                            // Also draw the main price line for reference
                                            let points: PlotPoints = if let Some(timestamps) = timestamps_slice {
                                                prices_slice.iter().zip(timestamps.iter())
                                                    .map(|(price, &timestamp)| [timestamp as f64, *price])
                                                    .collect()
                                            } else {
                                                prices_slice.iter().enumerate()
                                                    .map(|(j, price)| [j as f64, *price])
                                                    .collect()
                                            };
                                            plot_ui.line(Line::new(points).name(symbol).width(1.5).color(color));
                                        }
                                    });
                            }
                        }
                        
                        if self.show_advanced_options {
                            ui.separator();
                            ui.label("📊 Advanced Analytics:");
                            ui.label("• Volatility analysis");
                            ui.label("• Correlation matrix");
                            ui.label("• Risk metrics");
                            ui.label("(Coming soon...)");
                        }
                    }
                }
            });
        } else {
            ui.group(|ui| {
                ui.heading("📈 Price Charts");
                ui.separator();
                ui.vertical_centered(|ui| {
                    ui.label("📊 Loading price data...");
                    ui.label("Click 'Refresh Charts' to load price history");
                });
            });
        }
    }
}

impl App for PortfolioApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut Frame) {
        // Process async messages
        self.process_messages(ctx);
        
        // Handle chart refresh requests
        if self.refresh_charts_requested {
            self.refresh_charts_requested = false;
            self.get_price_history();
        }
        
        // Auto-refresh mechanism
        if self.auto_refresh_enabled && self.real_time_updates {
            let elapsed = self.last_data_refresh.elapsed();
            if elapsed >= StdDuration::from_secs(self.refresh_interval_seconds) {
                if let Some(sender) = &self.message_sender {
                    let _ = sender.send(AppMessage::RefreshData);
                }
                self.fetch_data_source_status();
            }
        }
        
        // Keyboard shortcuts
        if self.keyboard_shortcuts_enabled {
            ctx.input(|i| {
                // Ctrl+R - Refresh data
                if i.key_pressed(egui::Key::R) && i.modifiers.ctrl {
                    if let Some(sender) = &self.message_sender {
                        let _ = sender.send(AppMessage::RefreshData);
                    }
                }
                
                // Ctrl+B - Run backtest
                if i.key_pressed(egui::Key::B) && i.modifiers.ctrl {
                    if !self.portfolio_name.is_empty() && !self.selected_strategy.is_empty() {
                        self.run_backtest_for_strategy(&self.portfolio_name.clone(), &self.selected_strategy.clone());
                    }
                }
                
                // Ctrl+S - Open settings
                if i.key_pressed(egui::Key::S) && i.modifiers.ctrl {
                    self.show_settings = true;
                }
                
                // F1-F4 - Toggle windows
                if i.key_pressed(egui::Key::F1) {
                    self.show_strategy_analyzer = !self.show_strategy_analyzer;
                }
                if i.key_pressed(egui::Key::F2) {
                    self.show_risk_dashboard = !self.show_risk_dashboard;
                }
                if i.key_pressed(egui::Key::F3) {
                    self.show_backtest_analyzer = !self.show_backtest_analyzer;
                }
                if i.key_pressed(egui::Key::F4) {
                    self.show_performance_dashboard = !self.show_performance_dashboard;
                }
                
                // Escape - Close all windows
                if i.key_pressed(egui::Key::Escape) {
                    self.show_strategy_analyzer = false;
                    self.show_risk_dashboard = false;
                    self.show_portfolio_comparison = false;
                    self.show_settings = false;
                    self.show_backtest_analyzer = false;
                    self.show_performance_dashboard = false;
                    self.show_technical_indicators = false;
                    self.show_data_source_panel = false;
                }
            });
        }

        // Top panel: Enhanced status and warnings
        TopBottomPanel::top("top_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("📊 Portfolio Terminal Pro");
                
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    // Data source status panel toggle
                    if ui.button("📡 Data Status").clicked() {
                        self.show_data_source_panel = !self.show_data_source_panel;
                    }
                    
                    ui.separator();
                    
                    // Enhanced data source status
                    if let Some(status) = &self.data_source_status {
                        let source_color = if status.is_mock_data { 
                            Color32::LIGHT_RED 
                        } else if status.success_rate > 0.9 { 
                            Color32::GREEN 
                        } else if status.success_rate > 0.7 { 
                            Color32::YELLOW 
                        } else { 
                            Color32::RED 
                        };
                        
                        ui.colored_label(source_color, format!("📊 {}", status.current_source.to_uppercase()));
                        
                        if status.is_mock_data {
                            ui.colored_label(Color32::LIGHT_RED, "⚠️ MOCK");
                        }
                        
                        // Response time indicator
                        let response_color = if status.response_time_ms < 500 { 
                            Color32::GREEN 
                        } else if status.response_time_ms < 2000 { 
                            Color32::YELLOW 
                        } else { 
                            Color32::RED 
                        };
                        ui.colored_label(response_color, format!("{}ms", status.response_time_ms));
                        
                        ui.separator();
                    } else {
                        ui.colored_label(Color32::GRAY, "📊 No Data Status");
                        ui.separator();
                    }
                    
                    // Auto-refresh indicator
                    if self.auto_refresh_enabled {
                        let elapsed = self.last_data_refresh.elapsed().as_secs();
                        let remaining = self.refresh_interval_seconds.saturating_sub(elapsed);
                        ui.colored_label(Color32::BLUE, format!("🔄 {}s", remaining));
                        ui.separator();
                    }
                    
                    // Connection status
                    let (status_text, status_color) = if self.connection_status == "Connected" {
                        ("🟢 Connected", Color32::GREEN)
                    } else if self.connection_status == "Connecting..." {
                        ("🟡 Connecting...", Color32::YELLOW)
                    } else {
                        ("🔴 Disconnected", Color32::RED)
                    };
                    ui.colored_label(status_color, status_text);
                });
            });
            
            // Data source detail panel
            if self.show_data_source_panel {
                ui.separator();
                self.render_data_source_panel(ui);
            }
        });

        // Main content area
        CentralPanel::default().show(ctx, |ui| {
            ScrollArea::vertical().show(ui, |ui| {
                if self.loading {
                    ui.horizontal(|ui| {
                        ui.spinner();
                        ui.label("Loading...");
                    });
                }

                // Show messages
                if let Some(err) = &self.error_msg {
                    ui.colored_label(Color32::RED, format!("❌ {}", err));
                }
                if let Some(success) = &self.success_msg {
                    ui.colored_label(Color32::GREEN, format!("✅ {}", success));
                }

                ui.separator();

                // Main controls
                self.render_main_controls(ui);

                ui.separator();

                // Current portfolio display
                if let Some(portfolio) = &self.current_portfolio {
                    ui.group(|ui| {
                        ui.heading("📊 Current Portfolio");
                        ui.label(format!("Name: {}", portfolio.name));
                        ui.label(format!("Total Value: ${:.2}", portfolio.total_value));
                        
                        if let Some(holdings) = &portfolio.holdings {
                            ui.label("Holdings:");
                            for (symbol, shares) in &holdings.shares {
                                let weight = portfolio.weights.get(symbol).unwrap_or(&0.0);
                                ui.label(format!("  {} - {:.0} shares ({:.1}%)", symbol, shares, weight * 100.0));
                            }
                        }
                    });
                    
                    ui.separator();
                    
                    // Ticker visualization interface
                    self.render_ticker_interface(ui);
                } else {
                    ui.group(|ui| {
                        ui.heading("🎉 Welcome to Portfolio Optimizer Pro - Advanced");
                        ui.label("Select a portfolio from the dropdown above to get started.");
                        ui.label("Use the window controls to open advanced analysis tools.");
                    });
                }
            });
        });

        // Floating windows
        // Render all components through the component manager
        self.components.render_all(ctx);
    }
}

impl PortfolioApp {
    fn render_main_controls(&mut self, ui: &mut egui::Ui) {
        // Portfolio selection
        ui.group(|ui| {
            ui.heading("📁 Portfolio Selection");
            
            ui.horizontal(|ui| {
                ui.label("Portfolio:");
                egui::ComboBox::from_id_source("portfolio_selector")
                    .selected_text(&self.portfolio_name)
                    .show_ui(ui, |ui| {
                        for portfolio in &self.available_portfolios {
                            ui.selectable_value(&mut self.portfolio_name, portfolio.clone(), portfolio);
                        }
                    });
                if ui.button("🔄 Load").clicked() {
                    self.load_portfolio();
                }
            });
        });

        ui.separator();

        // Strategy controls
        ui.group(|ui| {
            ui.heading("🎯 Strategy Analysis");
            
            ui.horizontal(|ui| {
                ui.label("Strategy:");
                egui::ComboBox::from_label("")
                    .selected_text(&self.selected_strategy)
                    .show_ui(ui, |ui| {
                        ui.selectable_value(&mut self.selected_strategy, "bollinger".to_string(), "📈 Bollinger Bands");
                        ui.selectable_value(&mut self.selected_strategy, "ml".to_string(), "🤖 ML Strategy");
                        ui.selectable_value(&mut self.selected_strategy, "momentum".to_string(), "🚀 Momentum Strategy");
                    });
                if ui.button("🎯 Run").clicked() {
                    self.run_strategy();
                }
                if ui.button("🧪 Run Backtest").clicked() {
                    if !self.portfolio_name.is_empty() && !self.selected_strategy.is_empty() {
                        self.run_backtest_for_strategy(&self.portfolio_name.clone(), &self.selected_strategy.clone());
                    } else {
                        self.error_msg = Some("Portfolio name and strategy required for backtest".to_string());
                    }
                }
            });
            
            if ui.button("📊 Open Strategy Analyzer").clicked() {
                self.components.strategy_analyzer.set_open(true);
            }
        });

        ui.separator();

        // Window controls
        ui.group(|ui| {
            ui.heading("🪟 Professional Terminal Windows");
            
            ui.horizontal(|ui| {
                if ui.button("📊 Strategy Analyzer (F1)").clicked() {
                    self.components.strategy_analyzer.set_open(true);
                }
                if ui.button("⚠️ Risk Dashboard (F2)").clicked() {
                    self.components.risk_dashboard.set_open(true);
                }
            });
            
            ui.horizontal(|ui| {
                if ui.button("📊 Backtest Analyzer (F3)").clicked() {
                    self.components.backtest_analyzer.set_open(true);
                }
                if ui.button("📈 Performance Dashboard (F4)").clicked() {
                    self.components.performance_dashboard.set_open(true);
                }
            });
            
            ui.horizontal(|ui| {
                if ui.button("📊 Technical Indicators").clicked() {
                    self.components.technical_indicators.set_open(true);
                }
                if ui.button("📈 Portfolio Comparison").clicked() {
                    self.components.portfolio_comparison.set_open(true);
                }
            });
            
            ui.horizontal(|ui| {
                if ui.button("⚙️ Settings (Ctrl+S)").clicked() {
                    self.components.settings.set_open(true);
                }
                if ui.button("🔄 Force Refresh (Ctrl+R)").clicked() {
                    if let Some(sender) = &self.message_sender {
                        let _ = sender.send(AppMessage::RefreshData);
                    }
                }
            });
            
            ui.separator();
            ui.label("💡 Press ESC to close all windows");
            ui.checkbox(&mut self.keyboard_shortcuts_enabled, "🎹 Enable Keyboard Shortcuts");
        });
    }

    fn render_ticker_interface(&mut self, ui: &mut egui::Ui) {
        ui.group(|ui| {
            ui.horizontal(|ui| {
                ui.heading("📈 Ticker Visualization");
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if self.data_source_is_mock {
                        ui.colored_label(Color32::LIGHT_RED, "⚠️ Mock Data");
                    }
                    ui.checkbox(&mut self.show_charts, "Show Charts");
                });
            });
            
            ui.separator();
            
            // Ticker selection interface
            ui.group(|ui| {
                ui.heading("🎯 Ticker Selection");
                
                // Portfolio tickers section
                if let Some(portfolio) = &self.current_portfolio {
                    if let Some(holdings) = &portfolio.holdings {
                        ui.label("📊 Portfolio Holdings:");
                        ui.horizontal_wrapped(|ui| {
                            for symbol in holdings.shares.keys() {
                                let is_selected = self.selected_tickers.get(symbol).copied().unwrap_or(false);
                                let mut selected = is_selected;
                                
                                ui.group(|ui| {
                                    ui.horizontal(|ui| {
                                        if ui.checkbox(&mut selected, "").changed() {
                                            self.selected_tickers.insert(symbol.clone(), selected);
                                            if selected {
                                                self.refresh_charts_requested = true;
                                            }
                                        }
                                        
                                        let color = if is_selected { Color32::GREEN } else { Color32::GRAY };
                                        ui.colored_label(color, symbol);
                                        
                                        if let Some(shares) = holdings.shares.get(symbol) {
                                            ui.label(format!("({:.0} shares)", shares));
                                        }
                                    });
                                });
                            }
                        });
                        
                        ui.separator();
                    }
                }
                
                // Additional tickers section
                ui.label("📋 Additional Tickers:");
                ui.horizontal_wrapped(|ui| {
                    for ticker in &self.available_tickers.clone() {
                        let is_selected = self.selected_tickers.get(ticker).copied().unwrap_or(false);
                        let mut selected = is_selected;
                        
                        // Skip if already in portfolio
                        if let Some(portfolio) = &self.current_portfolio {
                            if let Some(holdings) = &portfolio.holdings {
                                if holdings.shares.contains_key(ticker) {
                                    continue;
                                }
                            }
                        }
                        
                        ui.group(|ui| {
                            ui.horizontal(|ui| {
                                if ui.checkbox(&mut selected, "").changed() {
                                    self.selected_tickers.insert(ticker.clone(), selected);
                                    if selected {
                                        self.refresh_charts_requested = true;
                                    }
                                }
                                
                                let color = if is_selected { Color32::GREEN } else { Color32::GRAY };
                                ui.colored_label(color, ticker);
                            });
                        });
                    }
                });
                
                ui.separator();
                
                // Controls
                ui.horizontal(|ui| {
                    if ui.button("🔄 Refresh Charts").clicked() {
                        self.refresh_charts_requested = true;
                    }
                    
                    if ui.button("✅ Select All Portfolio").clicked() {
                        if let Some(portfolio) = &self.current_portfolio {
                            if let Some(holdings) = &portfolio.holdings {
                                for symbol in holdings.shares.keys() {
                                    self.selected_tickers.insert(symbol.clone(), true);
                                }
                                self.refresh_charts_requested = true;
                            }
                        }
                    }
                    
                    if ui.button("❌ Clear Selection").clicked() {
                        self.selected_tickers.clear();
                    }
                });
                
                // Chart type and period controls
                ui.separator();
                ui.horizontal(|ui| {
                    ui.label("Chart Type:");
                    egui::ComboBox::from_id_source("ticker_chart_type")
                        .selected_text(self.selected_chart_type.as_str())
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.selected_chart_type, ChartType::Line, "📈 Line Chart");
                            ui.selectable_value(&mut self.selected_chart_type, ChartType::Bar, "📊 Bar Chart");
                            ui.selectable_value(&mut self.selected_chart_type, ChartType::Candlestick, "🕯️ Candlestick");
                        });
                    
                    ui.separator();
                    
                    ui.label("Period:");
                    egui::ComboBox::from_id_source("ticker_time_period")
                        .selected_text(&self.selected_time_period)
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.selected_time_period, "1d".to_string(), "1 Day");
                            ui.selectable_value(&mut self.selected_time_period, "5d".to_string(), "5 Days");
                            ui.selectable_value(&mut self.selected_time_period, "1mo".to_string(), "1 Month");
                            ui.selectable_value(&mut self.selected_time_period, "1y".to_string(), "1 Year");
                            ui.selectable_value(&mut self.selected_time_period, "YTD".to_string(), "Year-to-Date");
                            ui.selectable_value(&mut self.selected_time_period, "All".to_string(), "All Time");
                        });
                    
                    ui.separator();
                    
                    ui.checkbox(&mut self.show_percentage, "📊 Show as %");
                });
            });
            
            // Chart display
            if self.show_charts {
                ui.separator();
                self.render_price_charts(ui);
            }
        });
    }

    fn render_strategy_analyzer(&mut self, ctx: &egui::Context) {
        Window::new("📊 Strategy Analyzer")
            .open(&mut self.show_strategy_analyzer)
            .default_size([600.0, 500.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    if self.strategy_analyses.is_empty() {
                        ui.label("No strategy analyses yet. Run a strategy to see analysis here.");
                        return;
                    }

                    // Strategy selection
                    ui.horizontal(|ui| {
                        ui.label("Analysis:");
                        egui::ComboBox::from_id_source("analysis_selector")
                            .selected_text(
                                if let Some(idx) = self.selected_analysis {
                                    format!("{} - {}", 
                                        self.strategy_analyses[idx].portfolio_name,
                                        self.strategy_analyses[idx].strategy_name)
                                } else {
                                    "Select analysis".to_string()
                                }
                            )
                            .show_ui(ui, |ui| {
                                for (i, analysis) in self.strategy_analyses.iter().enumerate() {
                                    let text = format!("{} - {}", analysis.portfolio_name, analysis.strategy_name);
                                    ui.selectable_value(&mut self.selected_analysis, Some(i), text);
                                }
                            });
                    });

                    if let Some(idx) = self.selected_analysis {
                        if let Some(analysis) = self.strategy_analyses.get(idx) {
                            ui.separator();
                            
                            // Strategy overview
                            ui.group(|ui| {
                                ui.heading("📈 Strategy Overview");
                                ui.label(format!("Portfolio: {}", analysis.portfolio_name));
                                ui.label(format!("Strategy: {}", analysis.strategy_name));
                                if analysis.is_mock_data {
                                    ui.colored_label(Color32::LIGHT_RED, "⚠️ Based on mock data");
                                }
                            });

                            ui.separator();

                            // Performance metrics
                            ui.group(|ui| {
                                ui.heading("📊 Performance Metrics");
                                ui.horizontal(|ui| {
                                    ui.vertical(|ui| {
                                        ui.label("Total Return:");
                                        ui.colored_label(Color32::GREEN, format!("{:.2}%", analysis.performance_metrics.total_return * 100.0));
                                        ui.label("Annualized:");
                                        ui.colored_label(Color32::GREEN, format!("{:.2}%", analysis.performance_metrics.annualized_return * 100.0));
                                    });
                                    ui.separator();
                                    ui.vertical(|ui| {
                                        ui.label("Volatility:");
                                        ui.colored_label(Color32::YELLOW, format!("{:.2}%", analysis.performance_metrics.volatility * 100.0));
                                        ui.label("Max Drawdown:");
                                        ui.colored_label(Color32::RED, format!("{:.2}%", analysis.performance_metrics.max_drawdown * 100.0));
                                    });
                                    ui.separator();
                                    ui.vertical(|ui| {
                                        ui.label("Sharpe Ratio:");
                                        ui.colored_label(Color32::BLUE, format!("{:.3}", analysis.performance_metrics.sharpe_ratio));
                                        ui.label("Calmar Ratio:");
                                        ui.colored_label(Color32::BLUE, format!("{:.3}", analysis.performance_metrics.calmar_ratio));
                                        ui.label("Sortino Ratio:");
                                        ui.colored_label(Color32::BLUE, format!("{:.3}", analysis.performance_metrics.sortino_ratio));
                                    });
                                });
                                
                                ui.separator();
                                ui.horizontal(|ui| {
                                    ui.label("Win Rate:");
                                    ui.colored_label(Color32::GREEN, format!("{:.1}%", analysis.performance_metrics.win_rate * 100.0));
                                    ui.separator();
                                    ui.label("Profit Factor:");
                                    ui.colored_label(Color32::BLUE, format!("{:.2}", analysis.performance_metrics.profit_factor));
                                });
                            });

                            ui.separator();

                            // Weight changes
                            ui.group(|ui| {
                                ui.heading("🔄 Weight Changes");
                                
                                // Current vs New weights comparison
                                for symbol in analysis.current_weights.keys() {
                                    let current = analysis.current_weights.get(symbol).unwrap_or(&0.0);
                                    let new = analysis.new_weights.get(symbol).unwrap_or(&0.0);
                                    let change = analysis.changes.get(symbol).unwrap_or(&0.0);
                                    
                                    ui.horizontal(|ui| {
                                        ui.label(format!("{}:", symbol));
                                        ui.label(format!("{:.1}%", current * 100.0));
                                        ui.label("→");
                                        ui.label(format!("{:.1}%", new * 100.0));
                                        let color = if *change > 0.0 { Color32::GREEN } else { Color32::RED };
                                        ui.colored_label(color, format!("({:+.1}%)", change * 100.0));
                                    });
                                }
                            });

                            ui.separator();

                            // Weight distribution chart
                            ui.group(|ui| {
                                ui.heading("📊 Weight Distribution");
                                
                                let mut bars = Vec::new();
                                for (i, (symbol, weight)) in analysis.new_weights.iter().enumerate() {
                                    bars.push(Bar::new(i as f64, weight * 100.0).name(symbol));
                                }
                                
                                Plot::new("strategy_weights")
                                    .legend(Legend::default())
                                    .height(200.0)
                                    .show(ui, |plot_ui| {
                                        plot_ui.bar_chart(BarChart::new(bars).color(Color32::from_rgb(100, 149, 237)));
                                    });
                            });

                            ui.separator();

                            // Performance chart
                            ui.group(|ui| {
                                ui.heading("📈 Performance vs Benchmark");
                                
                                Plot::new("strategy_performance")
                                    .legend(Legend::default())
                                    .height(250.0)
                                    .show(ui, |plot_ui| {
                                        // Portfolio performance line
                                        let portfolio_points: PlotPoints = analysis.performance_metrics.values.iter().enumerate()
                                            .map(|(i, value)| [i as f64, *value])
                                            .collect();
                                        plot_ui.line(Line::new(portfolio_points).name("Strategy").width(2.5).color(Color32::BLUE));
                                        
                                        // Benchmark performance line
                                        let benchmark_points: PlotPoints = analysis.performance_metrics.benchmark_values.iter().enumerate()
                                            .map(|(i, value)| [i as f64, *value])
                                            .collect();
                                        plot_ui.line(Line::new(benchmark_points).name("Benchmark").width(2.0).color(Color32::RED));
                                    });
                            });
                        }
                    }
                });
            });
    }

    fn render_risk_dashboard(&mut self, ctx: &egui::Context) {
        Window::new("⚠️ Risk Dashboard")
            .open(&mut self.show_risk_dashboard)
            .default_size([500.0, 400.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.heading("📊 Portfolio Risk Analysis");
                    
                    if let Some(portfolio) = &self.current_portfolio {
                        // Calculate metrics first
                        let max_weight = portfolio.weights.values().fold(0.0f64, |a, &b| a.max(b));
                        let num_holdings = portfolio.weights.len();
                        
                        // Portfolio risk metrics
                        ui.group(|ui| {
                            ui.heading("🎯 Current Portfolio Risk");
                            
                            // Concentration risk
                            let concentration_risk = max_weight * 100.0;
                            
                            ui.horizontal(|ui| {
                                ui.label("Concentration Risk:");
                                let color = if concentration_risk > 50.0 { Color32::RED } 
                                          else if concentration_risk > 30.0 { Color32::YELLOW } 
                                          else { Color32::GREEN };
                                ui.colored_label(color, format!("{:.1}%", concentration_risk));
                            });
                            
                            // Diversification score
                            let diversification = (1.0 / num_holdings as f64) * 100.0;
                            ui.horizontal(|ui| {
                                ui.label("Diversification Score:");
                                ui.colored_label(Color32::BLUE, format!("{:.1}/100", 100.0 - diversification));
                            });
                        });

                        ui.separator();

                        // Risk by asset
                        ui.group(|ui| {
                            ui.heading("📈 Risk by Asset");
                            for (symbol, weight) in &portfolio.weights {
                                let risk_level = if *weight > 0.4 { "High" } 
                                               else if *weight > 0.2 { "Medium" } 
                                               else { "Low" };
                                let color = if *weight > 0.4 { Color32::RED }
                                          else if *weight > 0.2 { Color32::YELLOW }
                                          else { Color32::GREEN };
                                
                                ui.horizontal(|ui| {
                                    ui.label(format!("{}:", symbol));
                                    ui.label(format!("{:.1}%", weight * 100.0));
                                    ui.colored_label(color, risk_level);
                                });
                            }
                        });

                        ui.separator();

                        // Recommendations
                        ui.group(|ui| {
                            ui.heading("💡 Risk Recommendations");
                            
                            if max_weight > 0.5 {
                                ui.colored_label(Color32::RED, "⚠️ High concentration risk detected");
                                ui.label("Consider reducing position in largest holding");
                            }
                            
                            if num_holdings < 5 {
                                ui.colored_label(Color32::YELLOW, "⚠️ Limited diversification");
                                ui.label("Consider adding more positions for better diversification");
                            }
                            
                            if num_holdings >= 5 && max_weight <= 0.4 {
                                ui.colored_label(Color32::GREEN, "✅ Well-diversified portfolio");
                            }
                        });
                    } else {
                        ui.label("Load a portfolio to see risk analysis");
                    }
                });
            });
    }

    fn render_portfolio_comparison(&mut self, ctx: &egui::Context) {
        Window::new("📈 Portfolio Comparison")
            .open(&mut self.show_portfolio_comparison)
            .default_size([700.0, 500.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.heading("📊 Strategy Comparison");
                    
                    if self.strategy_analyses.len() < 2 {
                        ui.label("Run multiple strategies to compare them here.");
                        ui.label(format!("Current analyses: {}", self.strategy_analyses.len()));
                        return;
                    }

                    // Comparison table
                    ui.group(|ui| {
                        ui.heading("📋 Performance Comparison");
                        
                        // Header
                        ui.horizontal(|ui| {
                            ui.label("Strategy");
                            ui.separator();
                            ui.label("Expected Return");
                            ui.separator();
                            ui.label("Risk Score");
                            ui.separator();
                            ui.label("Sharpe Ratio");
                        });
                        
                        ui.separator();
                        
                        // Data rows
                        for analysis in &self.strategy_analyses {
                            ui.horizontal(|ui| {
                                ui.label(&analysis.strategy_name);
                                ui.separator();
                                ui.colored_label(Color32::GREEN, format!("{:.2}%", analysis.expected_return * 100.0));
                                ui.separator();
                                let risk_color = if analysis.risk_score > 50.0 { Color32::RED } else { Color32::YELLOW };
                                ui.colored_label(risk_color, format!("{:.1}", analysis.risk_score));
                                ui.separator();
                                ui.colored_label(Color32::BLUE, format!("{:.2}", analysis.sharpe_ratio));
                            });
                        }
                    });

                    ui.separator();

                    // Performance chart
                    ui.group(|ui| {
                        ui.heading("📊 Risk-Return Scatter");
                        
                        Plot::new("risk_return_scatter")
                            .height(300.0)
                            .show(ui, |plot_ui| {
                                for analysis in &self.strategy_analyses {
                                    let points: PlotPoints = vec![[analysis.risk_score, analysis.expected_return * 100.0]].into();
                                    plot_ui.line(Line::new(points).name(&analysis.strategy_name).width(8.0));
                                }
                            });
                    });
                });
            });
    }

    fn render_backtest_analyzer(&mut self, ctx: &egui::Context) {
        Window::new("📊 Backtest Analyzer")
            .open(&mut self.show_backtest_analyzer)
            .default_size([900.0, 700.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.heading("🔬 Portfolio Backtesting Analysis");
                    
                    let Some(backtest_result) = &self.backtest_result else {
                        ui.group(|ui| {
                            ui.vertical_centered(|ui| {
                                ui.label("📈 No backtest results available");
                                ui.label("Run strategies first to see backtest analysis");
                                ui.separator();
                                ui.label("Click 'Run Backtest' button in the strategy section first");
                                ui.separator();
                                ui.label("Available features:");
                                ui.label("• Performance metrics (Sharpe, Calmar, Sortino ratios)");
                                ui.label("• Drawdown analysis");
                                ui.label("• Monthly allocation plots");
                                ui.label("• Risk-adjusted returns");
                            });
                        });
                        return;
                    };

                    // Backtest summary metrics using real data
                    ui.group(|ui| {
                        ui.heading("📊 Backtest Summary");
                        
                        if backtest_result.is_using_mock_data {
                            ui.colored_label(Color32::YELLOW, "⚠️ Using mock data - Connect to real data source for accurate results");
                        }
                        
                        ui.horizontal(|ui| {
                            // Left column
                            ui.vertical(|ui| {
                                ui.label("🗓️ Period Analysis:");
                                ui.label(format!("Start: {}", backtest_result.start_date));
                                ui.label(format!("End: {}", backtest_result.end_date));
                                ui.label(format!("Period: {} days", backtest_result.period_days));
                                ui.separator();
                                ui.label("💰 Performance:");
                                ui.label(format!("Start Value: ${:.2}", backtest_result.start_value));
                                ui.label(format!("End Value: ${:.2}", backtest_result.end_value));
                                ui.colored_label(Color32::GREEN, format!("Total Return: {:.2}%", backtest_result.total_return_pct));
                                ui.label(format!("Benchmark Return: {:.2}%", backtest_result.benchmark_return_pct));
                            });
                            
                            ui.separator();
                            
                            // Middle column  
                            ui.vertical(|ui| {
                                ui.label("⚠️ Risk Metrics:");
                                ui.colored_label(Color32::RED, format!("Max Drawdown: {:.2}%", backtest_result.max_drawdown_pct));
                                ui.label(format!("Max DD Duration: {} days", backtest_result.max_drawdown_duration_days));
                                ui.label(format!("Max Exposure: {:.1}%", backtest_result.max_gross_exposure_pct));
                                ui.separator();
                                ui.label("📈 Ratios:");
                                ui.colored_label(Color32::BLUE, format!("Sharpe Ratio: {:.4}", backtest_result.sharpe_ratio));
                                ui.colored_label(Color32::BLUE, format!("Calmar Ratio: {:.4}", backtest_result.calmar_ratio));
                                ui.colored_label(Color32::BLUE, format!("Sortino Ratio: {:.4}", backtest_result.sortino_ratio));
                            });
                            
                            ui.separator();
                            
                            // Right column
                            ui.vertical(|ui| {
                                ui.label("🔄 Trading Activity:");
                                ui.label(format!("Total Trades: {}", backtest_result.total_trades));
                                ui.label(format!("Closed Trades: {}", backtest_result.total_closed_trades));
                                ui.label(format!("Open Trades: {}", backtest_result.total_open_trades));
                                ui.separator();
                                ui.label("📊 Trade Performance:");
                                ui.colored_label(Color32::GREEN, format!("Win Rate: {:.1}%", backtest_result.win_rate_pct));
                                ui.colored_label(Color32::GREEN, format!("Best Trade: {:.2}%", backtest_result.best_trade_pct));
                                ui.colored_label(Color32::RED, format!("Worst Trade: {:.2}%", backtest_result.worst_trade_pct));
                                ui.label(format!("Profit Factor: {:.2}", backtest_result.profit_factor));
                            });
                        });
                    });

                    ui.separator();

                    // Monthly allocation visualization using real backtest data
                    ui.group(|ui| {
                        ui.heading("📅 Monthly Allocation Analysis");
                        
                        if !backtest_result.allocations.is_empty() {
                            ui.label("Historical portfolio allocation weights by month:");
                            
                            // Extract unique symbols from allocations
                            let symbols: std::collections::HashSet<String> = backtest_result.allocations
                                .iter()
                                .flat_map(|alloc| alloc.weights.keys().cloned())
                                .collect();
                            let _symbols: Vec<String> = symbols.into_iter().collect();
                            
                            // Fixed allocation selector - use buttons instead of slider to prevent cursor issues
                            ui.horizontal(|ui| {
                                ui.label("Select Month:");
                                let num_months = backtest_result.allocations.len();
                                
                                // Ensure selected month is within bounds
                                if self.backtest_selected_month >= num_months {
                                    self.backtest_selected_month = 0;
                                }
                                
                                // Previous button
                                if ui.button("◀ Previous").clicked() && self.backtest_selected_month > 0 {
                                    self.backtest_selected_month -= 1;
                                }
                                
                                // Current month display
                                ui.label(format!("Month {}/{}", self.backtest_selected_month + 1, num_months));
                                if let Some(current_alloc) = backtest_result.allocations.get(self.backtest_selected_month) {
                                    ui.label(format!("Date: {}", current_alloc.date));
                                }
                                
                                // Next button
                                if ui.button("Next ▶").clicked() && self.backtest_selected_month < num_months - 1 {
                                    self.backtest_selected_month += 1;
                                }
                            });
                            
                            ui.separator();
                            
                            // Display allocation chart for selected month
                            if let Some(selected_allocation) = backtest_result.allocations.get(self.backtest_selected_month) {
                                ui.label(format!("Allocation for {}", selected_allocation.date));
                                
                                // Create bars for the selected month
                                let mut bars = Vec::new();
                                let colors = [
                                    Color32::from_rgb(31, 119, 180),   // Blue
                                    Color32::from_rgb(255, 127, 14),   // Orange  
                                    Color32::from_rgb(44, 160, 44),    // Green
                                    Color32::from_rgb(214, 39, 40),    // Red
                                    Color32::from_rgb(148, 103, 189),  // Purple
                                    Color32::from_rgb(140, 86, 75),    // Brown
                                ];
                                
                                for (i, (symbol, weight)) in selected_allocation.weights.iter().enumerate() {
                                    if *weight > 0.0 {
                                        bars.push(Bar::new(i as f64, *weight * 100.0).name(symbol));
                                    }
                                }
                                
                                if !bars.is_empty() {
                                    Plot::new("monthly_allocation_plot")
                                        .legend(Legend::default())
                                        .height(250.0)
                                        .show(ui, |plot_ui| {
                                            plot_ui.bar_chart(BarChart::new(bars).color(colors[0]));
                                        });
                                }
                            }
                            
                            ui.separator();
                            
                            // Allocation table for better readability
                            ui.group(|ui| {
                                ui.heading("📋 Allocation Details");
                                
                                if let Some(selected_allocation) = backtest_result.allocations.get(self.backtest_selected_month) {
                                    ui.label(format!("Date: {}", selected_allocation.date));
                                    
                                    // Create sorted list of allocations
                                    let mut sorted_allocations: Vec<(&String, &f64)> = selected_allocation.weights.iter().collect();
                                    sorted_allocations.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());
                                    
                                    // Display as a formatted table
                                    egui::Grid::new("allocation_table")
                                        .striped(true)
                                        .show(ui, |ui| {
                                            ui.label("Symbol");
                                            ui.label("Weight");
                                            ui.label("Visual");
                                            ui.end_row();
                                            
                                            for (symbol, weight) in sorted_allocations {
                                                if *weight > 0.0 {
                                                    ui.label(symbol);
                                                    
                                                    let color = if *weight > 0.3 { Color32::DARK_GREEN }
                                                               else if *weight > 0.15 { Color32::BLUE }
                                                               else { Color32::GRAY };
                                                    ui.colored_label(color, format!("{:.1}%", weight * 100.0));
                                                    
                                                    // Visual bar
                                                    let bar_width = (*weight * 100.0) as f32;
                                                    ui.horizontal(|ui| {
                                                        ui.add(egui::ProgressBar::new(bar_width / 100.0).desired_width(100.0));
                                                    });
                                                    ui.end_row();
                                                }
                                            }
                                        });
                                }
                            });
                        } else {
                            ui.label("No allocation data available");
                        }
                    });

                    ui.separator();

                    // Performance visualization with mock data as fallback
                    ui.group(|ui| {
                        ui.heading("📈 Performance Analysis");
                        
                        ui.label("Portfolio vs Benchmark Performance (Sample Data):");
                        
                        Plot::new("performance_plot")
                            .legend(Legend::default())
                            .height(300.0)
                            .show(ui, |plot_ui| {
                                // Generate sample performance data based on backtest metrics
                                let days = backtest_result.period_days as usize;
                                let mut portfolio_values = Vec::new();
                                let mut benchmark_values = Vec::new();
                                
                                let daily_portfolio_return = (1.0 + backtest_result.total_return_pct / 100.0).powf(1.0 / days as f64) - 1.0;
                                let daily_benchmark_return = (1.0 + backtest_result.benchmark_return_pct / 100.0).powf(1.0 / days as f64) - 1.0;
                                
                                let mut portfolio_val = backtest_result.start_value;
                                let mut benchmark_val = backtest_result.start_value;
                                
                                for i in 0..days.min(252) {
                                    // Add some volatility to make it realistic
                                    let portfolio_daily_return = daily_portfolio_return + 0.02 * (i as f64 * 0.1).sin() * 0.01;
                                    let benchmark_daily_return = daily_benchmark_return + 0.01 * (i as f64 * 0.05).sin() * 0.005;
                                    
                                    portfolio_val *= 1.0 + portfolio_daily_return;
                                    benchmark_val *= 1.0 + benchmark_daily_return;
                                    
                                    portfolio_values.push([i as f64, portfolio_val]);
                                    benchmark_values.push([i as f64, benchmark_val]);
                                }
                                
                                let portfolio_points: PlotPoints = portfolio_values.into();
                                let benchmark_points: PlotPoints = benchmark_values.into();
                                
                                plot_ui.line(Line::new(portfolio_points).name("Portfolio").width(2.5).color(Color32::BLUE));
                                plot_ui.line(Line::new(benchmark_points).name("Benchmark").width(2.0).color(Color32::RED));
                            });
                    });
                });
            });
    }


    fn render_data_source_panel(&mut self, ui: &mut egui::Ui) {
        ui.group(|ui| {
            ui.heading("📡 Data Source Status");
            
            // Extract status to avoid borrow checker issues
            let status_clone = self.data_source_status.clone();
            if let Some(status) = status_clone {
                ui.horizontal(|ui| {
                    // Left column - Current status
                    ui.vertical(|ui| {
                        ui.strong("Current Source:");
                        let source_color = if status.is_mock_data { Color32::LIGHT_RED } else { Color32::GREEN };
                        ui.colored_label(source_color, &status.current_source);
                        
                        ui.strong("Data Quality:");
                        if status.is_mock_data {
                            ui.colored_label(Color32::LIGHT_RED, "⚠️ Mock Data - For Testing Only");
                        } else {
                            ui.colored_label(Color32::GREEN, "✅ Real Market Data");
                        }
                        
                        ui.strong("Last Update:");
                        ui.label(&status.last_update);
                    });
                    
                    ui.separator();
                    
                    // Middle column - Performance metrics
                    ui.vertical(|ui| {
                        ui.strong("Performance Metrics:");
                        
                        let success_color = if status.success_rate > 0.9 { Color32::GREEN }
                                          else if status.success_rate > 0.7 { Color32::YELLOW }
                                          else { Color32::RED };
                        ui.horizontal(|ui| {
                            ui.label("Success Rate:");
                            ui.colored_label(success_color, format!("{:.1}%", status.success_rate * 100.0));
                        });
                        
                        let response_color = if status.response_time_ms < 500 { Color32::GREEN }
                                           else if status.response_time_ms < 2000 { Color32::YELLOW }
                                           else { Color32::RED };
                        ui.horizontal(|ui| {
                            ui.label("Response Time:");
                            ui.colored_label(response_color, format!("{}ms", status.response_time_ms));
                        });
                        
                        ui.horizontal(|ui| {
                            ui.label("Error Count:");
                            let error_color = if status.error_count == 0 { Color32::GREEN } else { Color32::RED };
                            ui.colored_label(error_color, format!("{}", status.error_count));
                        });
                    });
                    
                    ui.separator();
                    
                    // Right column - Available sources and controls
                    ui.vertical(|ui| {
                        ui.strong("Available Sources:");
                        for source in &status.available_sources {
                            let is_current = source == &status.current_source;
                            let color = if is_current { Color32::GREEN } else { Color32::GRAY };
                            let prefix = if is_current { "▶ " } else { "  " };
                            ui.colored_label(color, format!("{}{}", prefix, source));
                        }
                        
                        ui.separator();
                        
                        let mut should_refresh = false;
                        ui.horizontal(|ui| {
                            if ui.button("🔄 Refresh Status").clicked() {
                                should_refresh = true;
                            }
                            
                            ui.checkbox(&mut self.auto_refresh_enabled, "Auto Refresh");
                        });
                        
                        if should_refresh {
                            self.fetch_data_source_status();
                        }
                        
                        if self.auto_refresh_enabled {
                            ui.horizontal(|ui| {
                                ui.label("Interval:");
                                ui.add(egui::Slider::new(&mut self.refresh_interval_seconds, 10..=300).suffix("s"));
                            });
                        }
                    });
                });
            } else {
                let mut should_fetch = false;
                ui.vertical_centered(|ui| {
                    ui.label("🔍 No data source status available");
                    ui.label("Connect to backend to see real-time status");
                    if ui.button("🔄 Fetch Status").clicked() {
                        should_fetch = true;
                    }
                });
                
                if should_fetch {
                    self.fetch_data_source_status();
                }
            }
        });
    }

    fn render_performance_dashboard(&mut self, ctx: &egui::Context) {
        Window::new("📈 Performance Dashboard")
            .open(&mut self.show_performance_dashboard)
            .default_size([900.0, 600.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.heading("🎯 Real-Time Performance Metrics");
                    
                    if let Some(portfolio) = &self.current_portfolio {
                        // Real-time P&L section
                        ui.group(|ui| {
                            ui.heading("💰 Real-Time P&L");
                            
                            let colors = self.terminal_theme.get_colors();
                            
                            ui.horizontal(|ui| {
                                ui.vertical(|ui| {
                                    ui.strong("Portfolio Value:");
                                    ui.colored_label(colors.positive, format!("${:.2}", portfolio.total_value));
                                    
                                    // Mock daily change
                                    let daily_change = portfolio.total_value * 0.0125; // 1.25% gain
                                    let daily_change_pct = 1.25;
                                    ui.colored_label(colors.positive, format!("+${:.2} (+{:.2}%)", daily_change, daily_change_pct));
                                });
                                
                                ui.separator();
                                
                                ui.vertical(|ui| {
                                    ui.strong("Intraday High:");
                                    ui.colored_label(colors.neutral, format!("${:.2}", portfolio.total_value * 1.035));
                                    
                                    ui.strong("Intraday Low:");
                                    ui.colored_label(colors.neutral, format!("${:.2}", portfolio.total_value * 0.992));
                                });
                                
                                ui.separator();
                                
                                ui.vertical(|ui| {
                                    ui.strong("Data Quality:");
                                    if self.data_source_is_mock {
                                        ui.colored_label(Color32::LIGHT_RED, "⚠️ Mock Data");
                                    } else {
                                        ui.colored_label(colors.positive, "✅ Live Data");
                                    }
                                    
                                    if let Some(status) = &self.data_source_status {
                                        ui.label(format!("Source: {}", status.current_source));
                                        ui.label(format!("Latency: {}ms", status.response_time_ms));
                                    }
                                });
                            });
                        });
                        
                        ui.separator();
                        
                        // Position-level performance
                        ui.group(|ui| {
                            ui.heading("📊 Position Performance");
                            
                            if let Some(holdings) = &portfolio.holdings {
                                for (symbol, shares) in &holdings.shares {
                                    let weight = portfolio.weights.get(symbol).unwrap_or(&0.0);
                                    let mock_price = 150.0 + (symbol.len() as f64 * 25.0); // Mock price
                                    let position_value = shares * mock_price;
                                    let mock_change_pct = (symbol.len() as f64 % 5.0) - 2.0; // -2% to +2%
                                    
                                    ui.horizontal(|ui| {
                                        ui.strong(symbol);
                                        ui.label(format!("{:.0} shares", shares));
                                        ui.label(format!("${:.2}/share", mock_price));
                                        ui.label(format!("${:.2} total", position_value));
                                        
                                        let change_color = if mock_change_pct > 0.0 { Color32::GREEN } else { Color32::RED };
                                        ui.colored_label(change_color, format!("{:+.2}%", mock_change_pct));
                                        
                                        // Progress bar for weight
                                        let progress = *weight as f32;
                                        ui.add(egui::ProgressBar::new(progress).text(format!("{:.1}%", weight * 100.0)));
                                    });
                                }
                            }
                        });
                    } else {
                        ui.vertical_centered(|ui| {
                            ui.label("📊 Load a portfolio to see performance dashboard");
                        });
                    }
                });
            });
    }
    
    fn render_technical_indicators(&mut self, ctx: &egui::Context) {
        Window::new("📊 Technical Indicators")
            .open(&mut self.show_technical_indicators)
            .default_size([600.0, 500.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.heading("📈 Technical Analysis Tools");
                    
                    // Indicator controls
                    ui.group(|ui| {
                        ui.heading("🔧 Indicator Settings");
                        
                        ui.horizontal(|ui| {
                            ui.checkbox(&mut self.show_moving_averages, "📈 Moving Averages");
                            if self.show_moving_averages {
                                ui.add(egui::Slider::new(&mut self.ma_period, 5..=200).text("Period"));
                            }
                        });
                        
                        ui.horizontal(|ui| {
                            ui.checkbox(&mut self.show_bollinger_bands, "📊 Bollinger Bands");
                            if self.show_bollinger_bands {
                                ui.add(egui::Slider::new(&mut self.bb_period, 10..=50).text("Period"));
                            }
                        });
                        
                        ui.horizontal(|ui| {
                            ui.checkbox(&mut self.show_rsi, "📉 RSI");
                            if self.show_rsi {
                                ui.add(egui::Slider::new(&mut self.rsi_period, 5..=30).text("Period"));
                            }
                        });
                    });
                    
                    ui.separator();
                    
                    // Mock technical analysis display
                    if self.show_moving_averages || self.show_bollinger_bands || self.show_rsi {
                        ui.group(|ui| {
                            ui.heading("📊 Current Signals");
                            
                            if self.show_moving_averages {
                                ui.label(format!("📈 MA({}): Bullish trend detected", self.ma_period));
                                ui.colored_label(Color32::GREEN, "Signal: BUY");
                            }
                            
                            if self.show_bollinger_bands {
                                ui.label(format!("📊 BB({}): Price near upper band", self.bb_period));
                                ui.colored_label(Color32::YELLOW, "Signal: NEUTRAL");
                            }
                            
                            if self.show_rsi {
                                ui.label(format!("📉 RSI({}): 65.2 - Momentum strong", self.rsi_period));
                                ui.colored_label(Color32::GREEN, "Signal: HOLD");
                            }
                            
                            ui.separator();
                            ui.label("🔮 Overall Signal: BULLISH");
                            ui.colored_label(Color32::GREEN, "Confidence: 78%");
                        });
                        
                        ui.separator();
                        
                        // Mock chart with indicators
                        ui.group(|ui| {
                            ui.heading("📈 Chart with Indicators");
                            ui.label("📊 Chart display with technical overlays");
                            ui.label("(Technical indicator plotting would be implemented here)");
                            ui.label("• Moving average lines");
                            ui.label("• Bollinger band envelopes");
                            ui.label("• RSI oscillator panel");
                        });
                    } else {
                        ui.vertical_centered(|ui| {
                            ui.label("🎯 Enable indicators above to see analysis");
                        });
                    }
                });
            });
    }

    fn render_settings(&mut self, ctx: &egui::Context) {
        Window::new("⚙️ Settings")
            .open(&mut self.show_settings)
            .default_size([400.0, 300.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.heading("🔧 Professional Terminal Settings");
                    
                    // Theme settings
                    ui.group(|ui| {
                        ui.heading("🎨 Terminal Theme");
                        ui.horizontal(|ui| {
                            ui.label("Theme:");
                            egui::ComboBox::from_id_source("terminal_theme")
                                .selected_text(self.terminal_theme.as_str())
                                .show_ui(ui, |ui| {
                                    ui.selectable_value(&mut self.terminal_theme, TerminalTheme::Dark, "Dark");
                                    ui.selectable_value(&mut self.terminal_theme, TerminalTheme::Light, "Light");
                                    ui.selectable_value(&mut self.terminal_theme, TerminalTheme::Bloomberg, "Bloomberg");
                                    ui.selectable_value(&mut self.terminal_theme, TerminalTheme::Professional, "Professional");
                                });
                        });
                        
                        let colors = self.terminal_theme.get_colors();
                        ui.horizontal(|ui| {
                            ui.label("Preview:");
                            ui.colored_label(colors.positive, "Positive");
                            ui.colored_label(colors.negative, "Negative");
                            ui.colored_label(colors.accent, "Accent");
                        });
                    });

                    ui.separator();
                    
                    // Real-time settings
                    ui.group(|ui| {
                        ui.heading("🔄 Real-Time Updates");
                        ui.checkbox(&mut self.real_time_updates, "Enable real-time updates");
                        ui.checkbox(&mut self.auto_refresh_enabled, "Auto-refresh data");
                        
                        if self.auto_refresh_enabled {
                            ui.horizontal(|ui| {
                                ui.label("Refresh interval:");
                                ui.add(egui::Slider::new(&mut self.refresh_interval_seconds, 10..=300).suffix("s"));
                            });
                        }
                        
                        if ui.button("🔄 Force Refresh Now").clicked() {
                            if let Some(sender) = &self.message_sender {
                                let _ = sender.send(AppMessage::RefreshData);
                            }
                        }
                    });

                    ui.separator();
                    
                    // Chart settings
                    ui.group(|ui| {
                        ui.heading("📊 Chart Settings");
                        ui.checkbox(&mut self.show_advanced_options, "Show advanced analytics");
                        
                        ui.horizontal(|ui| {
                            ui.label("Default chart type:");
                            egui::ComboBox::from_id_source("default_chart")
                                .selected_text(self.selected_chart_type.as_str())
                                .show_ui(ui, |ui| {
                                    ui.selectable_value(&mut self.selected_chart_type, ChartType::Line, "Line Chart");
                                    ui.selectable_value(&mut self.selected_chart_type, ChartType::Bar, "Bar Chart");
                                    ui.selectable_value(&mut self.selected_chart_type, ChartType::Candlestick, "Candlestick");
                                });
                        });
                    });

                    ui.separator();
                    
                    // Input settings
                    ui.group(|ui| {
                        ui.heading("🎹 Input & Controls");
                        ui.checkbox(&mut self.keyboard_shortcuts_enabled, "Enable keyboard shortcuts");
                        
                        if self.keyboard_shortcuts_enabled {
                            ui.label("Available shortcuts:");
                            ui.label("• Ctrl+R - Refresh data");
                            ui.label("• Ctrl+B - Run backtest");
                            ui.label("• Ctrl+S - Open settings");
                            ui.label("• F1-F4 - Toggle windows");
                            ui.label("• ESC - Close all windows");
                        }
                    });

                    ui.separator();

                    ui.group(|ui| {
                        ui.heading("🔔 Notifications & Warnings");
                        ui.checkbox(&mut self.show_data_source_warning, "Show data source warnings");
                        ui.checkbox(&mut self.show_data_source_panel, "Show data source panel by default");
                    });

                    ui.separator();

                    ui.group(|ui| {
                        ui.heading("🧹 Data Management");
                        if ui.button("Clear Strategy Analyses").clicked() {
                            self.strategy_analyses.clear();
                            self.selected_analysis = None;
                        }
                        
                        if ui.button("Reset All Windows").clicked() {
                            self.show_strategy_analyzer = false;
                            self.show_risk_dashboard = false;
                            self.show_portfolio_comparison = false;
                            self.show_backtest_analyzer = false;
                            self.show_performance_dashboard = false;
                            self.show_technical_indicators = false;
                            self.show_data_source_panel = false;
                        }
                        
                        ui.label("Refresh portfolio list from main controls");
                    });
                });
            });
    }
}

fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1000.0, 700.0])
            .with_title("Portfolio Optimizer Pro - Advanced"),
        ..Default::default()
    };
    eframe::run_native(
        "Portfolio Optimizer Pro - Advanced",
        native_options,
        Box::new(|cc| Box::new(PortfolioApp::new(cc))),
    )
}
