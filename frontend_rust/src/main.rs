use eframe::{egui, App, CreationContext, Frame};
use egui::{CentralPanel, SidePanel, Ui};
use egui_plot::{Legend, Line, Plot, PlotPoints};
use tonic::transport::Channel;
use tonic::Request;
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
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
    Error(String),
    LoadingComplete,
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
                        let client = PortfolioServiceClient::new(channel);
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
                        self.current_portfolio = Some(portfolio);
                        self.success_msg = Some("Portfolio created successfully".to_string());
                        self.holdings.clear();
                        self.loading = false;
                    }
                    AppMessage::PortfolioLoaded(portfolio) => {
                        self.current_portfolio = Some(portfolio);
                        self.success_msg = Some("Portfolio loaded successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::StrategyResult(result) => {
                        self.strategy_result = Some(result);
                        self.success_msg = Some("Strategy executed successfully".to_string());
                        self.loading = false;
                    }
                    AppMessage::PriceHistory(history) => {
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
        let sender = self.message_sender.as_ref().unwrap().clone();
        let rt = self.rt.clone();

        rt.spawn(async move {
            match Channel::from_static("http://[::1]:50051").connect().await {
                Ok(channel) => {
                    let mut client = PortfolioServiceClient::new(channel);
                    let request = Request::new(GetPriceHistoryRequest { 
                        portfolio_name,
                        period: "1y".to_string(),
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
}

impl App for PortfolioApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut Frame) {
        // Process async messages
        self.process_messages(ctx);

        // Sidebar: Portfolio management
        SidePanel::left("sidebar").show(ctx, |ui| {
            ui.heading("Portfolio Optimizer Pro");
            ui.separator();
            
            // Connection status
            ui.horizontal(|ui| {
                ui.label("Status:");
                let color = if self.connection_status == "Connected" {
                    egui::Color32::GREEN
                } else if self.connection_status == "Connecting..." {
                    egui::Color32::YELLOW
                } else {
                    egui::Color32::RED
                };
                ui.colored_label(color, &self.connection_status);
            });
            
            if self.connection_status != "Connected" {
                if ui.button("Reconnect").clicked() {
                    self.connect_to_server();
                }
            }
            
            ui.separator();

            // Portfolio Management
            ui.heading("Portfolio Management");
            ui.label("Portfolio Name:");
            ui.text_edit_singleline(&mut self.portfolio_name);

            if ui.button("Load Portfolio").clicked() {
                self.load_portfolio();
            }

            ui.separator();
            
            // Holdings management
            ui.heading("Create New Portfolio");
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

            if ui.button("Create Portfolio").clicked() {
                self.create_portfolio();
            }

            ui.separator();
            
            // Strategy section
            ui.heading("Strategy");
            egui::ComboBox::from_label("Select Strategy")
                .selected_text(&self.selected_strategy)
                .show_ui(ui, |ui| {
                    ui.selectable_value(&mut self.selected_strategy, "bollinger".to_string(), "Bollinger Bands");
                    ui.selectable_value(&mut self.selected_strategy, "ml".to_string(), "ML Strategy");
                    ui.selectable_value(&mut self.selected_strategy, "momentum".to_string(), "Momentum Strategy");
                });

            // Strategy parameters
            if !self.selected_strategy.is_empty() {
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

            if ui.button("Run Strategy").clicked() {
                self.run_strategy();
            }

            if ui.button("Get Price History").clicked() {
                self.get_price_history();
            }
        });

        // Central panel: Dashboard
        CentralPanel::default().show(ctx, |ui| {
            if self.loading {
                ui.horizontal(|ui| {
                    ui.spinner();
                    ui.label("Loading...");
                });
            }

            // Show messages
            if let Some(err) = &self.error_msg {
                ui.colored_label(egui::Color32::RED, err);
            }
            if let Some(success) = &self.success_msg {
                ui.colored_label(egui::Color32::GREEN, success);
            }

            if let Some(portfolio) = &self.current_portfolio {
                ui.heading("Portfolio Dashboard");
                ui.label(format!("Name: {}", portfolio.name));
                ui.label(format!("Total Value: ${:.2}", portfolio.total_value));

                ui.separator();
                ui.heading("Current Weights");
                if let Some(holdings) = &portfolio.holdings {
                    for (symbol, shares) in &holdings.shares {
                        let weight = portfolio.weights.get(symbol).unwrap_or(&0.0);
                        ui.label(format!("{}: {:.2} shares ({:.2}%)", symbol, shares, weight * 100.0));
                    }
                }

                if let Some(result) = &self.strategy_result {
                    ui.separator();
                    ui.heading("Strategy Result");
                    ui.label("New Weights:");
                    for (symbol, weight) in &result.new_weights {
                        ui.label(format!("{}: {:.2}%", symbol, weight * 100.0));
                    }
                    
                    ui.separator();
                    ui.label("Changes:");
                    for (symbol, change) in &result.changes {
                        let color = if *change > 0.0 { egui::Color32::GREEN } else { egui::Color32::RED };
                        ui.colored_label(color, format!("{}: {:+.2}%", symbol, change * 100.0));
                    }
                }

                if let Some(history) = &self.price_history {
                    ui.separator();
                    ui.heading("Price History");
                    let num_symbols = history.symbols.len();
                    if num_symbols > 0 && !history.prices.is_empty() {
                        let rows_per_symbol = history.prices.len() / num_symbols;
                        if rows_per_symbol > 0 {
                            Plot::new("price_plot")
                                .legend(Legend::default())
                                .height(300.0)
                                .show(ui, |plot_ui| {
                                    for (i, symbol) in history.symbols.iter().enumerate() {
                                        let start = i * rows_per_symbol;
                                        let end = (start + rows_per_symbol).min(history.prices.len());
                                        if start < history.prices.len() {
                                            let prices_slice = &history.prices[start..end];
                                            let points: PlotPoints = prices_slice.iter().enumerate()
                                                .map(|(j, price)| [j as f64, *price])
                                                .collect();
                                            plot_ui.line(Line::new(points).name(symbol));
                                        }
                                    }
                                });
                        }
                    }
                }
            } else {
                ui.heading("Welcome to Portfolio Optimizer Pro");
                ui.label("Create a new portfolio or load an existing one from the sidebar.");
                ui.separator();
                ui.label("This frontend connects to the Python gRPC server.");
                ui.label("Make sure the server is running on port 50051.");
            }
        });
    }
}

fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([1200.0, 800.0]),
        ..Default::default()
    };
    eframe::run_native(
        "Portfolio Optimizer Pro",
        native_options,
        Box::new(|cc| Box::new(PortfolioApp::new(cc))),
    )
}