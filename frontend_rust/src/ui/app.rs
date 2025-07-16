use eframe::{egui, App, CreationContext, Frame};
use egui::{CentralPanel, TopBottomPanel, ScrollArea, RichText, Color32, Window};
use std::sync::Arc;
use tokio::sync::mpsc;
use std::time::Instant;

use crate::components::manager::ComponentManager;
use crate::models::app_state::AppState;
use crate::models::messages::{AppMessage, DataSourceStatus};

#[cfg(not(target_arch = "wasm32"))]
use tokio::runtime::Runtime;

#[cfg(target_arch = "wasm32")]
use wasm_bindgen_futures::spawn_local;

use crate::api::client;

pub struct PortfolioApp {
    // gRPC client
    #[cfg(not(target_arch = "wasm32"))]
    rt: Arc<Runtime>,
    
    // Component system
    components: ComponentManager,
    
    // Application state
    state: AppState,
    
    // Async communication
    message_receiver: Option<mpsc::UnboundedReceiver<AppMessage>>,
    message_sender: Option<mpsc::UnboundedSender<AppMessage>>,
}

impl Default for PortfolioApp {
    fn default() -> Self {
        let (tx, rx) = mpsc::unbounded_channel();
        
        #[cfg(not(target_arch = "wasm32"))]
        let rt = Arc::new(Runtime::new().unwrap());
        
        Self {
            #[cfg(not(target_arch = "wasm32"))]
            rt,
            components: ComponentManager::new(),
            state: AppState::default(),
            message_receiver: Some(rx),
            message_sender: Some(tx),
        }
    }
}

impl PortfolioApp {
    pub fn new(_cc: &CreationContext<'_>) -> Self {
        let mut app = Self::default();
        app.connect_to_server();
        app.load_available_portfolios();
        app
    }

    fn connect_to_server(&mut self) {
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            
            #[cfg(not(target_arch = "wasm32"))]
            {
                let rt = self.rt.clone();
                rt.spawn(async move {
                    match client::get_grpc_client().await {
                        Ok(_client) => {
                            // Store client in a way that can be accessed later
                            let _ = sender.send(AppMessage::Connected);
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::ConnectionFailed(format!("Connection failed: {}", e)));
                        }
                    }
                });
            }
            
            #[cfg(target_arch = "wasm32")]
            {
                spawn_local(async move {
                    match client::get_grpc_client().await {
                        Ok(_client) => {
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
    }

    fn load_available_portfolios(&mut self) {
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            
            #[cfg(not(target_arch = "wasm32"))]
            {
                let rt = self.rt.clone();
                rt.spawn(async move {
                    let user_id = "demo_user".to_string();
                    match client::list_portfolios(&user_id).await {
                        Ok(portfolios) => {
                            let _ = sender.send(AppMessage::PortfoliosList(portfolios));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(e));
                        }
                    }
                });
            }
            
            #[cfg(target_arch = "wasm32")]
            {
                spawn_local(async move {
                    let user_id = "demo_user".to_string();
                    match client::list_portfolios(&user_id).await {
                        Ok(portfolios) => {
                            let _ = sender.send(AppMessage::PortfoliosList(portfolios));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(e));
                        }
                    }
                });
            }
        }
    }

    fn process_messages(&mut self, ctx: &egui::Context) {
        if let Some(receiver) = &mut self.message_receiver {
            while let Ok(message) = receiver.try_recv() {
                match message {
                    AppMessage::Connected => {
                        self.state.connection_status = "Connected".to_string();
                        self.state.error_msg = None;
                    }
                    AppMessage::ConnectionFailed(error) => {
                        self.state.connection_status = "Disconnected".to_string();
                        self.state.error_msg = Some(error);
                    }
                    AppMessage::PortfoliosList(portfolios) => {
                        self.state.available_portfolios = portfolios;
                    }
                    AppMessage::PortfolioLoaded(portfolio) => {
                        self.state.current_portfolio = Some(portfolio.clone());
                        self.state.portfolio_name = portfolio.name;
                        self.state.holdings = portfolio.holdings.unwrap_or_default().shares;
                        self.state.data_source_is_mock = portfolio.is_using_mock_data;
                        self.state.loading = false;
                        
                        if self.state.data_source_is_mock {
                            self.state.show_data_source_warning = true;
                        }
                    }
                    AppMessage::PortfolioCreated(portfolio) => {
                        self.state.current_portfolio = Some(portfolio.clone());
                        self.state.portfolio_name = portfolio.name;
                        self.state.holdings = portfolio.holdings.unwrap_or_default().shares;
                        self.state.data_source_is_mock = portfolio.is_using_mock_data;
                        self.state.loading = false;
                        self.state.success_msg = Some("Portfolio created successfully".to_string());
                        
                        // Refresh the list of available portfolios
                        self.load_available_portfolios();
                    }
                    AppMessage::StrategyResult(result) => {
                        self.state.strategy_result = Some(result.clone());
                        self.state.data_source_is_mock = result.is_using_mock_data;
                        self.state.loading = false;
                        
                        if self.state.data_source_is_mock {
                            self.state.show_data_source_warning = true;
                        }
                    }
                    AppMessage::PriceHistory(history) => {
                        self.state.price_history = Some(history.clone());
                        self.state.data_source_is_mock = history.is_using_mock_data;
                        self.state.loading = false;
                        
                        if self.state.data_source_is_mock {
                            self.state.show_data_source_warning = true;
                        }
                    }
                    AppMessage::BacktestResult(result) => {
                        self.state.backtest_result = Some(result.clone());
                        self.state.data_source_is_mock = result.is_using_mock_data;
                        self.state.loading = false;
                        
                        if self.state.data_source_is_mock {
                            self.state.show_data_source_warning = true;
                        }
                    }
                    AppMessage::DataSourceUpdated(is_mock) => {
                        self.state.data_source_is_mock = is_mock;
                        self.state.show_data_source_warning = is_mock;
                    }
                    AppMessage::DataSourceStatus(status) => {
                        self.state.data_source_status = Some(status);
                    }
                    AppMessage::Error(error) => {
                        self.state.error_msg = Some(error);
                        self.state.loading = false;
                    }
                    AppMessage::LoadingComplete => {
                        self.state.loading = false;
                    }
                    AppMessage::RefreshData => {
                        // Refresh data based on current state
                        if let Some(portfolio) = &self.state.current_portfolio {
                            // Reload portfolio data
                            self.load_portfolio(&portfolio.name);
                        }
                    }
                }
                
                // Request a repaint after processing messages
                ctx.request_repaint();
            }
        }
    }

    fn load_portfolio(&mut self, name: &str) {
        self.state.loading = true;
        self.state.error_msg = None;
        
        if let Some(sender) = &self.message_sender {
            let sender = sender.clone();
            let name = name.to_string();
            
            #[cfg(not(target_arch = "wasm32"))]
            {
                let rt = self.rt.clone();
                rt.spawn(async move {
                    let user_id = "demo_user".to_string();
                    match client::load_portfolio(&user_id, &name).await {
                        Ok(portfolio) => {
                            let _ = sender.send(AppMessage::PortfolioLoaded(portfolio));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(e));
                        }
                    }
                });
            }
            
            #[cfg(target_arch = "wasm32")]
            {
                spawn_local(async move {
                    let user_id = "demo_user".to_string();
                    match client::load_portfolio(&user_id, &name).await {
                        Ok(portfolio) => {
                            let _ = sender.send(AppMessage::PortfolioLoaded(portfolio));
                        }
                        Err(e) => {
                            let _ = sender.send(AppMessage::Error(e));
                        }
                    }
                });
            }
        }
    }

    // Add more methods for other API calls...
}

impl App for PortfolioApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut Frame) {
        // Process any pending messages
        self.process_messages(ctx);
        
        // Check if auto-refresh is needed
        if self.state.auto_refresh_enabled {
            let now = Instant::now();
            let elapsed = now.duration_since(self.state.last_data_refresh).as_secs();
            
            if elapsed >= self.state.refresh_interval_seconds {
                if let Some(sender) = &self.message_sender {
                    let _ = sender.send(AppMessage::RefreshData);
                }
                self.state.last_data_refresh = now;
            }
        }
        
        // Render UI components
        self.render_top_panel(ctx);
        self.render_bottom_panel(ctx);
        self.render_main_panel(ctx);
        
        // Render modal windows
        if self.state.show_settings {
            self.render_settings_window(ctx);
        }
        
        if self.state.show_strategy_analyzer {
            self.render_strategy_analyzer_window(ctx);
        }
        
        if self.state.show_risk_dashboard {
            self.render_risk_dashboard_window(ctx);
        }
        
        // ... other windows
    }
}

// UI rendering methods
impl PortfolioApp {
    fn render_top_panel(&mut self, ctx: &egui::Context) {
        TopBottomPanel::top("top_panel").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                ui.menu_button("File", |ui| {
                    if ui.button("New Portfolio").clicked() {
                        // Handle new portfolio
                        ui.close_menu();
                    }
                    
                    if ui.button("Open Portfolio").clicked() {
                        // Handle open portfolio
                        ui.close_menu();
                    }
                    
                    if ui.button("Save").clicked() {
                        // Handle save
                        ui.close_menu();
                    }
                    
                    ui.separator();
                    
                    if ui.button("Settings").clicked() {
                        self.state.show_settings = true;
                        ui.close_menu();
                    }
                    
                    ui.separator();
                    
                    if ui.button("Exit").clicked() {
                        // Handle exit
                        ui.close_menu();
                    }
                });
                
                ui.menu_button("View", |ui| {
                    if ui.checkbox(&mut self.state.show_advanced_options, "Advanced Options").clicked() {
                        ui.close_menu();
                    }
                    
                    ui.separator();
                    
                    if ui.button("Performance Dashboard").clicked() {
                        self.state.show_performance_dashboard = true;
                        ui.close_menu();
                    }
                    
                    if ui.button("Risk Dashboard").clicked() {
                        self.state.show_risk_dashboard = true;
                        ui.close_menu();
                    }
                    
                    if ui.button("Technical Indicators").clicked() {
                        self.state.show_technical_indicators = true;
                        ui.close_menu();
                    }
                });
                
                ui.menu_button("Strategy", |ui| {
                    if ui.button("Strategy Analyzer").clicked() {
                        self.state.show_strategy_analyzer = true;
                        ui.close_menu();
                    }
                    
                    if ui.button("Backtest").clicked() {
                        self.state.show_backtest_analyzer = true;
                        ui.close_menu();
                    }
                    
                    ui.separator();
                    
                    if ui.button("Portfolio Comparison").clicked() {
                        self.state.show_portfolio_comparison = true;
                        ui.close_menu();
                    }
                });
                
                ui.menu_button("Data", |ui| {
                    if ui.button("Refresh Data").clicked() {
                        if let Some(sender) = &self.message_sender {
                            let _ = sender.send(AppMessage::RefreshData);
                        }
                        self.state.last_data_refresh = Instant::now();
                        ui.close_menu();
                    }
                    
                    ui.checkbox(&mut self.state.auto_refresh_enabled, "Auto Refresh");
                    
                    ui.separator();
                    
                    if ui.button("Data Source Settings").clicked() {
                        self.state.show_data_source_panel = true;
                        ui.close_menu();
                    }
                });
                
                ui.menu_button("Help", |ui| {
                    if ui.button("Documentation").clicked() {
                        // Open documentation
                        ui.close_menu();
                    }
                    
                    if ui.button("About").clicked() {
                        // Show about dialog
                        ui.close_menu();
                    }
                });
                
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    let status_text = format!("Status: {}", self.state.connection_status);
                    ui.label(status_text);
                    
                    if self.state.loading {
                        ui.spinner();
                    }
                });
            });
        });
    }
    
    fn render_bottom_panel(&mut self, ctx: &egui::Context) {
        TopBottomPanel::bottom("bottom_panel").show(ctx, |ui| {
            ui.horizontal(|ui| {
                if let Some(error) = &self.state.error_msg {
                    ui.label(RichText::new(format!("Error: {}", error)).color(Color32::RED));
                } else if let Some(success) = &self.state.success_msg {
                    ui.label(RichText::new(success).color(Color32::GREEN));
                } else {
                    ui.label("Ready");
                }
                
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if let Some(data_source) = &self.state.data_source_status {
                        let source_text = format!("Data: {} ({}ms)", data_source.current_source, data_source.response_time_ms);
                        ui.label(source_text);
                    }
                    
                    if self.state.data_source_is_mock {
                        ui.label(RichText::new("Using Mock Data").color(Color32::YELLOW));
                    }
                });
            });
        });
    }
    
    fn render_main_panel(&mut self, ctx: &egui::Context) {
        CentralPanel::default().show(ctx, |ui| {
            // Main content goes here
            ScrollArea::vertical().show(ui, |ui| {
                // Portfolio section
                ui.heading("Portfolio");
                
                ui.horizontal(|ui| {
                    ui.label("Select Portfolio:");
                    egui::ComboBox::from_id_source("portfolio_selector")
                        .selected_text(if self.state.portfolio_name.is_empty() { "Select..." } else { &self.state.portfolio_name })
                        .show_ui(ui, |ui| {
                            for name in &self.state.available_portfolios {
                                if ui.selectable_label(self.state.portfolio_name == *name, name).clicked() {
                                    self.state.portfolio_name = name.clone();
                                    self.load_portfolio(name);
                                }
                            }
                        });
                        
                    if ui.button("New").clicked() {
                        // Handle new portfolio
                    }
                });
                
                // Portfolio holdings
                if let Some(portfolio) = &self.state.current_portfolio {
                    ui.heading("Holdings");
                    
                    egui::Grid::new("holdings_grid")
                        .num_columns(3)
                        .spacing([40.0, 4.0])
                        .striped(true)
                        .show(ui, |ui| {
                            ui.label("Symbol");
                            ui.label("Shares");
                            ui.label("Weight");
                            ui.end_row();
                            
                            for (symbol, shares) in &self.state.holdings {
                                ui.label(symbol);
                                ui.label(format!("{:.2}", shares));
                                
                                let weight = portfolio.weights.get(symbol).unwrap_or(&0.0);
                                ui.label(format!("{:.2}%", weight * 100.0));
                                
                                ui.end_row();
                            }
                        });
                }
                
                // Add more UI sections as needed
            });
        });
    }
    
    fn render_settings_window(&mut self, ctx: &egui::Context) {
        Window::new("Settings")
            .open(&mut self.state.show_settings)
            .resizable(true)
            .show(ctx, |ui| {
                ui.heading("Application Settings");
                
                ui.collapsing("Theme", |ui| {
                    ui.horizontal(|ui| {
                        ui.label("Terminal Theme:");
                        
                        let themes = [
                            ("Dark", crate::models::app_state::TerminalTheme::Dark),
                            ("Light", crate::models::app_state::TerminalTheme::Light),
                            ("Bloomberg", crate::models::app_state::TerminalTheme::Bloomberg),
                            ("Professional", crate::models::app_state::TerminalTheme::Professional),
                        ];
                        
                        for (name, theme) in themes {
                            if ui.selectable_label(self.state.terminal_theme == theme, name).clicked() {
                                self.state.terminal_theme = theme;
                                // Apply theme
                            }
                        }
                    });
                });
                
                ui.collapsing("Data", |ui| {
                    ui.checkbox(&mut self.state.auto_refresh_enabled, "Auto Refresh Data");
                    
                    if self.state.auto_refresh_enabled {
                        ui.horizontal(|ui| {
                            ui.label("Refresh Interval (seconds):");
                            ui.add(egui::Slider::new(&mut self.state.refresh_interval_seconds, 5..=300));
                        });
                    }
                });
                
                ui.collapsing("Interface", |ui| {
                    ui.checkbox(&mut self.state.keyboard_shortcuts_enabled, "Enable Keyboard Shortcuts");
                    ui.checkbox(&mut self.state.real_time_updates, "Real-time Updates");
                });
            });
    }
    
    fn render_strategy_analyzer_window(&mut self, ctx: &egui::Context) {
        Window::new("Strategy Analyzer")
            .open(&mut self.state.show_strategy_analyzer)
            .resizable(true)
            .show(ctx, |ui| {
                ui.heading("Strategy Analysis");
                
                ui.horizontal(|ui| {
                    ui.label("Strategy:");
                    egui::ComboBox::from_id_source("strategy_selector")
                        .selected_text(&self.state.selected_strategy)
                        .show_ui(ui, |ui| {
                            for strategy in &["bollinger", "mean_reversion", "momentum", "equal_weight"] {
                                if ui.selectable_label(self.state.selected_strategy == *strategy, *strategy).clicked() {
                                    self.state.selected_strategy = strategy.to_string();
                                }
                            }
                        });
                        
                    if ui.button("Run Analysis").clicked() {
                        // Run strategy analysis
                    }
                });
                
                // Strategy parameters
                ui.collapsing("Strategy Parameters", |ui| {
                    match self.state.selected_strategy.as_str() {
                        "bollinger" => {
                            ui.horizontal(|ui| {
                                ui.label("Window:");
                                let mut window = self.state.strategy_params.get("window")
                                    .unwrap_or(&"20".to_string()).clone();
                                if ui.text_edit_singleline(&mut window).changed() {
                                    self.state.strategy_params.insert("window".to_string(), window);
                                }
                            });
                            
                            ui.horizontal(|ui| {
                                ui.label("Std Dev:");
                                let mut std_dev = self.state.strategy_params.get("std_dev")
                                    .unwrap_or(&"2.0".to_string()).clone();
                                if ui.text_edit_singleline(&mut std_dev).changed() {
                                    self.state.strategy_params.insert("std_dev".to_string(), std_dev);
                                }
                            });
                        },
                        // Add other strategies
                        _ => {
                            ui.label("No parameters for this strategy");
                        }
                    }
                });
                
                // Results display
                if let Some(result) = &self.state.strategy_result {
                    ui.heading("Results");
                    
                    egui::Grid::new("strategy_results_grid")
                        .num_columns(3)
                        .spacing([40.0, 4.0])
                        .striped(true)
                        .show(ui, |ui| {
                            ui.label("Symbol");
                            ui.label("New Weight");
                            ui.label("Change");
                            ui.end_row();
                            
                            for (symbol, weight) in &result.new_weights {
                                ui.label(symbol);
                                ui.label(format!("{:.2}%", weight * 100.0));
                                
                                let change = result.changes.get(symbol).unwrap_or(&0.0);
                                let change_text = format!("{:+.2}%", change * 100.0);
                                let change_color = if *change > 0.0 {
                                    self.state.terminal_theme.get_colors().positive
                                } else if *change < 0.0 {
                                    self.state.terminal_theme.get_colors().negative
                                } else {
                                    self.state.terminal_theme.get_colors().neutral
                                };
                                
                                ui.label(RichText::new(change_text).color(change_color));
                                
                                ui.end_row();
                            }
                        });
                }
            });
    }
    
    fn render_risk_dashboard_window(&mut self, ctx: &egui::Context) {
        Window::new("Risk Dashboard")
            .open(&mut self.state.show_risk_dashboard)
            .resizable(true)
            .show(ctx, |ui| {
                ui.heading("Portfolio Risk Analysis");
                
                // Risk metrics display
                if let Some(portfolio) = &self.state.current_portfolio {
                    // Display risk metrics
                    ui.label(format!("Portfolio: {}", portfolio.name));
                    
                    // Generate some sample metrics for demonstration
                    let metrics = crate::models::performance::PerformanceMetrics::generate(&self.state.selected_time_period, 100);
                    
                    egui::Grid::new("risk_metrics_grid")
                        .num_columns(2)
                        .spacing([40.0, 4.0])
                        .striped(true)
                        .show(ui, |ui| {
                            ui.label("Volatility:");
                            ui.label(format!("{:.2}%", metrics.volatility * 100.0));
                            ui.end_row();
                            
                            ui.label("Sharpe Ratio:");
                            ui.label(format!("{:.2}", metrics.sharpe_ratio));
                            ui.end_row();
                            
                            ui.label("Max Drawdown:");
                            ui.label(format!("{:.2}%", metrics.max_drawdown * 100.0));
                            ui.end_row();
                            
                            ui.label("Sortino Ratio:");
                            ui.label(format!("{:.2}", metrics.sortino_ratio));
                            ui.end_row();
                            
                            ui.label("Calmar Ratio:");
                            ui.label(format!("{:.2}", metrics.calmar_ratio));
                            ui.end_row();
                        });
                }
            });
    }
}