use eframe::{egui, App, CreationContext, Frame};
use egui::{CentralPanel, SidePanel, TopBottomPanel, ScrollArea, RichText, Color32, Window};
use egui_plot::{Legend, Line, Plot, PlotPoints, Bar, BarChart};
use tonic::transport::Channel;
use tonic::Request;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::mpsc;
use tokio::runtime::Runtime;

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
    DataSourceUpdated(bool),
    Error(String),
    LoadingComplete,
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
}

pub struct PortfolioApp {
    // gRPC client
    rt: Arc<Runtime>,
    
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
    data_source_is_mock: bool,
    
    // Enhanced UI state
    show_advanced_options: bool,
    selected_chart_type: ChartType,
    selected_time_period: String,
    show_data_source_warning: bool,
    
    // Window states
    show_strategy_analyzer: bool,
    show_risk_dashboard: bool,
    show_portfolio_comparison: bool,
    show_settings: bool,
    
    // Strategy analysis
    strategy_analyses: Vec<StrategyAnalysis>,
    selected_analysis: Option<usize>,
    
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
            data_source_is_mock: false,
            show_advanced_options: false,
            selected_chart_type: ChartType::Line,
            selected_time_period: "1y".to_string(),
            show_data_source_warning: false,
            show_strategy_analyzer: false,
            show_risk_dashboard: false,
            show_portfolio_comparison: false,
            show_settings: false,
            strategy_analyses: Vec::new(),
            selected_analysis: None,
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

    fn connect_to_server(&mut self) {
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            let rt = self.rt.clone();
            
            rt.spawn(async move {
                match Channel::from_static("http://[::1]:50051").connect().await {
                    Ok(_channel) => {
                        let _ = sender.send(AppMessage::Connected);
                    }
                    Err(e) => {
                        let _ = sender.send(AppMessage::ConnectionFailed(format!("Connection failed: {}", e)));
                    }
                }
            });
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
                        self.load_available_portfolios();
                    }
                    AppMessage::PortfolioLoaded(portfolio) => {
                        self.data_source_is_mock = portfolio.is_using_mock_data;
                        self.show_data_source_warning = portfolio.is_using_mock_data;
                        self.current_portfolio = Some(portfolio);
                        self.success_msg = Some("Portfolio loaded successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::StrategyResult(result) => {
                        self.data_source_is_mock = result.is_using_mock_data;
                        self.show_data_source_warning = result.is_using_mock_data;
                        
                        // Create strategy analysis
                        if let Some(portfolio) = &self.current_portfolio {
                            let analysis = StrategyAnalysis {
                                portfolio_name: portfolio.name.clone(),
                                strategy_name: self.selected_strategy.clone(),
                                current_weights: portfolio.weights.clone(),
                                new_weights: result.new_weights.clone(),
                                changes: result.changes.clone(),
                                expected_return: self.calculate_expected_return(&result.new_weights),
                                risk_score: self.calculate_risk_score(&result.new_weights),
                                sharpe_ratio: self.calculate_sharpe_ratio(&result.new_weights),
                                is_mock_data: result.is_using_mock_data,
                            };
                            self.strategy_analyses.push(analysis);
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
                }
                ctx.request_repaint();
            }
        }
    }

    fn calculate_expected_return(&self, _weights: &HashMap<String, f64>) -> f64 {
        // Simplified calculation - in practice, use historical returns
        0.08 + (rand::random::<f64>() - 0.5) * 0.04
    }

    fn calculate_risk_score(&self, weights: &HashMap<String, f64>) -> f64 {
        // Simplified risk calculation based on concentration
        let mut max_weight = 0.0;
        for weight in weights.values() {
            if *weight > max_weight {
                max_weight = *weight;
            }
        }
        max_weight * 100.0 // Higher concentration = higher risk
    }

    fn calculate_sharpe_ratio(&self, _weights: &HashMap<String, f64>) -> f64 {
        // Simplified Sharpe ratio calculation
        1.2 + (rand::random::<f64>() - 0.5) * 0.8
    }

    fn clear_messages(&mut self) {
        self.error_msg = None;
        self.success_msg = None;
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
                    let user_id = "demo_user".to_string();
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
                    let user_id = "demo_user".to_string();
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
        if self.portfolio_name.is_empty() {
            self.error_msg = Some("Portfolio name required".to_string());
            return;
        }

        self.clear_messages();
        self.loading = true;

        let portfolio_name = self.portfolio_name.clone();
        let period = self.selected_time_period.clone();
        let sender = self.message_sender.as_ref().unwrap().clone();
        let rt = self.rt.clone();

        rt.spawn(async move {
            match Channel::from_static("http://[::1]:50051").connect().await {
                Ok(channel) => {
                    let mut client = PortfolioServiceClient::new(channel);
                    let user_id = "demo_user".to_string();
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
            });
            
            if ui.button("📊 Open Strategy Analyzer").clicked() {
                self.show_strategy_analyzer = true;
            }
        });

        ui.separator();

        // Window controls
        ui.group(|ui| {
            ui.heading("🪟 Analysis Windows");
            
            ui.horizontal(|ui| {
                if ui.button("📊 Strategy Analyzer").clicked() {
                    self.show_strategy_analyzer = true;
                }
                if ui.button("⚠️ Risk Dashboard").clicked() {
                    self.show_risk_dashboard = true;
                }
            });
            
            ui.horizontal(|ui| {
                if ui.button("📈 Portfolio Comparison").clicked() {
                    self.show_portfolio_comparison = true;
                }
                if ui.button("⚙️ Settings").clicked() {
                    self.show_settings = true;
                }
            });
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
                                        ui.label("Expected Return:");
                                        ui.colored_label(Color32::GREEN, format!("{:.2}%", analysis.expected_return * 100.0));
                                    });
                                    ui.separator();
                                    ui.vertical(|ui| {
                                        ui.label("Risk Score:");
                                        let color = if analysis.risk_score > 50.0 { Color32::RED } else { Color32::YELLOW };
                                        ui.colored_label(color, format!("{:.1}", analysis.risk_score));
                                    });
                                    ui.separator();
                                    ui.vertical(|ui| {
                                        ui.label("Sharpe Ratio:");
                                        ui.colored_label(Color32::BLUE, format!("{:.2}", analysis.sharpe_ratio));
                                    });
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
                        // Portfolio risk metrics
                        ui.group(|ui| {
                            ui.heading("🎯 Current Portfolio Risk");
                            
                            // Concentration risk
                            let max_weight = portfolio.weights.values().fold(0.0f64, |a, &b| a.max(b));
                            let concentration_risk = max_weight * 100.0;
                            
                            ui.horizontal(|ui| {
                                ui.label("Concentration Risk:");
                                let color = if concentration_risk > 50.0 { Color32::RED } 
                                          else if concentration_risk > 30.0 { Color32::YELLOW } 
                                          else { Color32::GREEN };
                                ui.colored_label(color, format!("{:.1}%", concentration_risk));
                            });
                            
                            // Diversification score
                            let num_holdings = portfolio.weights.len();
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

    fn render_settings(&mut self, ctx: &egui::Context) {
        Window::new("⚙️ Settings")
            .open(&mut self.show_settings)
            .default_size([400.0, 300.0])
            .resizable(true)
            .show(ctx, |ui| {
                ScrollArea::vertical().show(ui, |ui| {
                    ui.heading("🔧 Application Settings");
                    
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

                    ui.group(|ui| {
                        ui.heading("🔔 Notifications");
                        ui.checkbox(&mut self.show_data_source_warning, "Show data source warnings");
                    });

                    ui.separator();

                    ui.group(|ui| {
                        ui.heading("🧹 Data Management");
                        if ui.button("Clear Strategy Analyses").clicked() {
                            self.strategy_analyses.clear();
                            self.selected_analysis = None;
                        }
                        if ui.button("Refresh Portfolio List").clicked() {
                            self.load_available_portfolios();
                        }
                    });
                });
            });
    }
}

impl App for PortfolioApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut Frame) {
        // Process async messages
        self.process_messages(ctx);

        // Top panel: Status and warnings
        TopBottomPanel::top("top_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("📊 Portfolio Optimizer Pro - Advanced");
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    // Connection status
                    let (status_text, status_color) = if self.connection_status == "Connected" {
                        ("🟢 Connected", Color32::GREEN)
                    } else if self.connection_status == "Connecting..." {
                        ("🟡 Connecting...", Color32::YELLOW)
                    } else {
                        ("🔴 Disconnected", Color32::RED)
                    };
                    ui.colored_label(status_color, status_text);
                    
                    // Data source warning
                    if self.data_source_is_mock {
                        ui.separator();
                        ui.colored_label(Color32::LIGHT_RED, "⚠️ Using Mock Data");
                    }
                });
            });
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
        self.render_strategy_analyzer(ctx);
        self.render_risk_dashboard(ctx);
        self.render_portfolio_comparison(ctx);
        self.render_settings(ctx);
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