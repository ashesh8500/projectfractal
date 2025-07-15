use eframe::{egui, App, CreationContext, Frame};
use egui::{CentralPanel, SidePanel, TopBottomPanel, ScrollArea, RichText, Color32, Stroke};
use egui_plot::{Legend, Line, Plot, PlotPoints, PlotPoint, Bar, BarChart, Text as PlotText};
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
    StrategyResult(StrategyResult),
    PriceHistory(PriceHistory),
    DataSourceUpdated(bool), // is_mock_data
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

pub struct PortfolioApp {
    // gRPC client
    client: Option<PortfolioServiceClient<Channel>>,
    rt: Arc<Runtime>,
    
    // UI state
    portfolio_name: String,
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
    
    // UI state
    show_advanced_options: bool,
    selected_chart_type: ChartType,
    selected_time_period: String,
    show_data_source_warning: bool,
    
    // Async communication
    message_receiver: Option<mpsc::UnboundedReceiver<AppMessage>>,
    message_sender: Option<mpsc::UnboundedSender<AppMessage>>,
}

impl Default for PortfolioApp {
    fn default() -> Self {
        let rt = Arc::new(Runtime::new().unwrap());
        let (tx, rx) = mpsc::unbounded_channel();
        
        Self {
            client: None,
            rt,
            portfolio_name: String::new(),
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
            message_receiver: Some(rx),
            message_sender: Some(tx),
        }
    }
}

impl PortfolioApp {
    fn new(_cc: &CreationContext<'_>) -> Self {
        let mut app = Self::default();
        app.connect_to_server();
        app
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
                        // We need to recreate the client here since we can't easily pass it through messages
                        self.rt.spawn(async move {
                            // This is a workaround - in a real app you'd handle this differently
                        });
                    }
                    AppMessage::ConnectionFailed(error) => {
                        self.connection_status = "Disconnected".to_string();
                        self.error_msg = Some(error);
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
                        self.current_portfolio = Some(portfolio);
                        self.success_msg = Some("Portfolio loaded successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::StrategyResult(result) => {
                        self.data_source_is_mock = result.is_using_mock_data;
                        self.show_data_source_warning = result.is_using_mock_data;
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

    fn clear_messages(&mut self) {
        self.error_msg = None;
        self.success_msg = None;
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
                    let request = Request::new(CreatePortfolioRequest {
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
                    let request = Request::new(LoadPortfolioRequest { name });

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
                    let request = Request::new(RunStrategyRequest {
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
                    let request = Request::new(GetPriceHistoryRequest { 
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
        if let Some(history) = &self.price_history {
            ui.group(|ui| {
                ui.horizontal(|ui| {
                    ui.heading("📈 Price History");
                    if history.is_using_mock_data {
                        ui.colored_label(Color32::LIGHT_RED, "⚠️ Mock Data");
                    }
                });
                
                let num_symbols = history.symbols.len();
                if num_symbols > 0 && !history.prices.is_empty() {
                    let rows_per_symbol = history.prices.len() / num_symbols;
                    if rows_per_symbol > 0 {
                        let plot_height = if self.show_advanced_options { 400.0 } else { 300.0 };
                        
                        match self.selected_chart_type {
                            ChartType::Line => {
                                Plot::new("price_plot")
                                    .legend(Legend::default())
                                    .height(plot_height)
                                    .show(ui, |plot_ui| {
                                        for (i, symbol) in history.symbols.iter().enumerate() {
                                            let start = i * rows_per_symbol;
                                            let end = (start + rows_per_symbol).min(history.prices.len());
                                            if start < history.prices.len() {
                                                let prices_slice = &history.prices[start..end];
                                                let points: PlotPoints = prices_slice.iter().enumerate()
                                                    .map(|(j, price)| [j as f64, *price])
                                                    .collect();
                                                plot_ui.line(Line::new(points).name(symbol).width(2.0));
                                            }
                                        }
                                    });
                            }
                            ChartType::Bar => {
                                Plot::new("price_bar_plot")
                                    .legend(Legend::default())
                                    .height(plot_height)
                                    .show(ui, |plot_ui| {
                                        for (i, symbol) in history.symbols.iter().enumerate() {
                                            let start = i * rows_per_symbol;
                                            let end = (start + rows_per_symbol).min(history.prices.len());
                                            if start < history.prices.len() {
                                                let prices_slice = &history.prices[start..end];
                                                let bars: Vec<Bar> = prices_slice.iter().enumerate()
                                                    .map(|(j, price)| Bar::new(j as f64, *price))
                                                    .collect();
                                                plot_ui.bar_chart(BarChart::new(bars).name(symbol));
                                            }
                                        }
                                    });
                            }
                            ChartType::Candlestick => {
                                ui.label("Candlestick chart coming soon...");
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
        }
    }
}

impl App for PortfolioApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut Frame) {
        // Process async messages
        self.process_messages(ctx);

        // Top panel: Status and warnings
        TopBottomPanel::top("top_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("📊 Portfolio Optimizer Pro");
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
                        if ui.small_button("?").on_hover_text("Real market data unavailable. Using simulated data for demonstration.").clicked() {
                            self.show_data_source_warning = !self.show_data_source_warning;
                        }
                    }
                });
            });
            
            // Data source warning banner
            if self.show_data_source_warning && self.data_source_is_mock {
                ui.separator();
                ui.horizontal(|ui| {
                    ui.colored_label(Color32::LIGHT_RED, "⚠️ WARNING:");
                    ui.label("This application is using simulated market data. Real market data is currently unavailable.");
                    if ui.button("Dismiss").clicked() {
                        self.show_data_source_warning = false;
                    }
                });
            }
        });

        // Sidebar: Portfolio management
        SidePanel::left("sidebar").resizable(true).default_width(350.0).show(ctx, |ui| {
            ScrollArea::vertical().show(ui, |ui| {
                ui.heading("📂 Portfolio Management");
                ui.separator();
                
                if self.connection_status != "Connected" {
                    ui.horizontal(|ui| {
                        ui.label("🔌 Connection:");
                        if ui.button("Reconnect").clicked() {
                            self.connect_to_server();
                        }
                    });
                    ui.separator();
                }

                // Portfolio Management
                ui.group(|ui| {
                    ui.heading("📁 Load Portfolio");
                    ui.horizontal(|ui| {
                        ui.label("Name:");
                        ui.text_edit_singleline(&mut self.portfolio_name);
                    });
                    if ui.button("🔄 Load Portfolio").clicked() {
                        self.load_portfolio();
                    }
                });
                
                ui.separator();
                
                // Holdings management
                ui.group(|ui| {
                    ui.heading("➕ Create New Portfolio");
                    ui.label("Add Holdings:");
                    
                    ui.horizontal(|ui| {
                        ui.label("Symbol:");
                        ui.text_edit_singleline(&mut self.new_symbol);
                    });
                    
                    ui.horizontal(|ui| {
                        ui.label("Shares:");
                        ui.text_edit_singleline(&mut self.new_shares);
                    });
                    
                    if ui.button("Add Holding").clicked() {
                        if !self.new_symbol.is_empty() && !self.new_shares.is_empty() {
                            if let Ok(shares) = self.new_shares.parse::<f64>() {
                                if shares > 0.0 {
                                    self.holdings.insert(self.new_symbol.clone(), shares);
                                    self.new_symbol.clear();
                                    self.new_shares.clear();
                                    self.success_msg = Some("Holding added".to_string());
                                } else {
                                    self.error_msg = Some("Shares must be positive".to_string());
                                }
                            } else {
                                self.error_msg = Some("Invalid shares value".to_string());
                            }
                        }
                    }
                    
                    // Show current holdings
                    if !self.holdings.is_empty() {
                        ui.separator();
                        ui.label("Current Holdings:");
                        let mut to_remove = None;
                        for (symbol, shares) in &self.holdings {
                            ui.horizontal(|ui| {
                                ui.label(format!("{}: {:.2}", symbol, shares));
                                if ui.small_button("✖").clicked() {
                                    to_remove = Some(symbol.clone());
                                }
                            });
                        }
                        if let Some(symbol) = to_remove {
                            self.holdings.remove(&symbol);
                        }
                    }

                    if ui.button("🚀 Create Portfolio").clicked() {
                        self.create_portfolio();
                    }
                });
                
                ui.separator();
                
                // Strategy section
                ui.group(|ui| {
                    ui.heading("🎯 Strategy");
                    egui::ComboBox::from_label("Select Strategy")
                        .selected_text(&self.selected_strategy)
                        .show_ui(ui, |ui| {
                            ui.selectable_value(&mut self.selected_strategy, "bollinger".to_string(), "📈 Bollinger Bands");
                            ui.selectable_value(&mut self.selected_strategy, "ml".to_string(), "🤖 ML Strategy");
                            ui.selectable_value(&mut self.selected_strategy, "momentum".to_string(), "🚀 Momentum Strategy");
                        });

                    // Strategy parameters
                    if !self.selected_strategy.is_empty() {
                        ui.separator();
                        ui.label("Parameters:");
                        let params_keys = match self.selected_strategy.as_str() {
                            "bollinger" => vec![("window", "20"), ("std_dev", "2.0")],
                            "ml" => vec![("lookback_days", "60")],
                            "momentum" => vec![("lookback_period", "20"), ("momentum_threshold", "0.02")],
                            _ => vec![],
                        };
                        
                        for (key, default_value) in params_keys {
                            let mut value = self.strategy_params.get(key).cloned().unwrap_or_else(|| default_value.to_string());
                            ui.horizontal(|ui| {
                                ui.label(key);
                                ui.text_edit_singleline(&mut value);
                            });
                            self.strategy_params.insert(key.to_string(), value);
                        }
                    }

                    if ui.button("🎯 Run Strategy").clicked() {
                        self.run_strategy();
                    }
                });
                
                ui.separator();
                
                // Charts section
                ui.group(|ui| {
                    ui.heading("📊 Charts & Analysis");
                    
                    ui.horizontal(|ui| {
                        ui.label("Period:");
                        egui::ComboBox::from_id_source("time_period")
                            .selected_text(&self.selected_time_period)
                            .show_ui(ui, |ui| {
                                ui.selectable_value(&mut self.selected_time_period, "1mo".to_string(), "1 Month");
                                ui.selectable_value(&mut self.selected_time_period, "3mo".to_string(), "3 Months");
                                ui.selectable_value(&mut self.selected_time_period, "6mo".to_string(), "6 Months");
                                ui.selectable_value(&mut self.selected_time_period, "1y".to_string(), "1 Year");
                                ui.selectable_value(&mut self.selected_time_period, "2y".to_string(), "2 Years");
                                ui.selectable_value(&mut self.selected_time_period, "5y".to_string(), "5 Years");
                            });
                    });
                    
                    ui.horizontal(|ui| {
                        ui.label("Chart Type:");
                        egui::ComboBox::from_id_source("chart_type")
                            .selected_text(self.selected_chart_type.as_str())
                            .show_ui(ui, |ui| {
                                ui.selectable_value(&mut self.selected_chart_type, ChartType::Line, "📈 Line Chart");
                                ui.selectable_value(&mut self.selected_chart_type, ChartType::Bar, "📊 Bar Chart");
                                ui.selectable_value(&mut self.selected_chart_type, ChartType::Candlestick, "🕯️ Candlestick");
                            });
                    });
                    
                    if ui.button("📈 Get Price History").clicked() {
                        self.get_price_history();
                    }
                });
                
                ui.separator();
                
                // Advanced options
                ui.collapsing("🔧 Advanced Options", |ui| {
                    ui.checkbox(&mut self.show_advanced_options, "Show detailed metrics");
                    ui.label("• Risk analysis");
                    ui.label("• Performance metrics");
                    ui.label("• Optimization settings");
                    ui.label("(Coming soon...)");
                });
            });
        });

        // Central panel: Dashboard
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

                if self.current_portfolio.is_some() {
                    self.render_portfolio_dashboard(ui);
                    ui.separator();
                    self.render_price_charts(ui);
                } else {
                    ui.vertical_centered(|ui| {
                        ui.heading("🎉 Welcome to Portfolio Optimizer Pro");
                        ui.separator();
                        ui.label("📝 Create a new portfolio or load an existing one from the sidebar.");
                        ui.separator();
                        ui.label("🔗 This frontend connects to the Python gRPC server.");
                        ui.label("⚙️ Make sure the server is running on port 50051.");
                        
                        if self.connection_status != "Connected" {
                            ui.separator();
                            ui.colored_label(Color32::RED, "🔴 Server not connected. Please start the server and click Reconnect.");
                        }
                    });
                }
            });
        });
    }
}

fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1400.0, 900.0])
            .with_title("Portfolio Optimizer Pro"),
        ..Default::default()
    };
    eframe::run_native(
        "Portfolio Optimizer Pro",
        native_options,
        Box::new(|cc| Box::new(PortfolioApp::new(cc))),
    )
}