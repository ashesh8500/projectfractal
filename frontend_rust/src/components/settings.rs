use super::{Component, WindowedComponent};
use egui::{Color32, Context, ScrollArea, Ui, Window};
use std::any::Any;

pub struct Settings {
    window: WindowedComponent,
    // Settings state
    dark_mode: bool,
    auto_refresh: bool,
    refresh_interval: f32,
    risk_tolerance: f32,
}

impl Settings {
    pub fn new() -> Self {
        Self {
            window: WindowedComponent::new("⚙️ Settings").with_size(600.0, 500.0),
            dark_mode: false,
            auto_refresh: true,
            refresh_interval: 30.0,
            risk_tolerance: 0.5,
        }
    }
    
    fn render_appearance_settings(&mut self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("🎨 Appearance");
            
            ui.checkbox(&mut self.dark_mode, "Dark Mode");
            ui.label("Switch between light and dark themes");
            
            ui.separator();
            
            ui.label("Chart Colors:");
            ui.horizontal(|ui| {
                ui.color_edit_button_srgba(&mut Color32::from_rgb(31, 119, 180).into());
                ui.label("Primary");
                ui.color_edit_button_srgba(&mut Color32::from_rgb(255, 127, 14).into());
                ui.label("Secondary");
            });
        });
    }
    
    fn render_data_settings(&mut self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📡 Data Settings");
            
            ui.checkbox(&mut self.auto_refresh, "Auto Refresh");
            ui.label("Automatically refresh market data");
            
            ui.horizontal(|ui| {
                ui.label("Refresh Interval:");
                ui.add(egui::Slider::new(&mut self.refresh_interval, 5.0..=300.0).suffix(" seconds"));
            });
            
            ui.separator();
            
            ui.label("Data Sources:");
            ui.horizontal(|ui| {
                if ui.button("Configure API Keys").clicked() {
                    // Handle API key configuration
                }
                if ui.button("Test Connection").clicked() {
                    // Handle connection test
                }
            });
        });
    }
    
    fn render_trading_settings(&mut self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("💼 Trading Settings");
            
            ui.horizontal(|ui| {
                ui.label("Risk Tolerance:");
                ui.add(egui::Slider::new(&mut self.risk_tolerance, 0.0..=1.0).text("Conservative ← → Aggressive"));
            });
            
            ui.separator();
            
            ui.label("Default Strategy Parameters:");
            ui.horizontal(|ui| {
                ui.label("Rebalance Frequency:");
                egui::ComboBox::from_label("")
                    .selected_text("Monthly")
                    .show_ui(ui, |ui| {
                        ui.selectable_value(&mut "daily", "daily", "Daily");
                        ui.selectable_value(&mut "weekly", "weekly", "Weekly");
                        ui.selectable_value(&mut "monthly", "monthly", "Monthly");
                        ui.selectable_value(&mut "quarterly", "quarterly", "Quarterly");
                    });
            });
            
            ui.checkbox(&mut true, "Enable Stop Loss");
            ui.checkbox(&mut false, "Enable Take Profit");
        });
    }
    
    fn render_notification_settings(&mut self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("🔔 Notifications");
            
            ui.checkbox(&mut true, "Portfolio Alerts");
            ui.checkbox(&mut true, "Strategy Signals");
            ui.checkbox(&mut false, "Market News");
            ui.checkbox(&mut true, "System Updates");
            
            ui.separator();
            
            ui.label("Alert Thresholds:");
            ui.horizontal(|ui| {
                ui.label("Drawdown Alert:");
                ui.add(egui::Slider::new(&mut 5.0, 1.0..=20.0).suffix("%"));
            });
            
            ui.horizontal(|ui| {
                ui.label("Profit Alert:");
                ui.add(egui::Slider::new(&mut 10.0, 1.0..=50.0).suffix("%"));
            });
        });
    }
    
    fn render_actions(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("⚡ Actions");
            
            ui.horizontal(|ui| {
                if ui.button("💾 Save Settings").clicked() {
                    // Handle save settings
                }
                if ui.button("🔄 Reset to Defaults").clicked() {
                    // Handle reset to defaults
                }
                if ui.button("📤 Export Settings").clicked() {
                    // Handle export settings
                }
                if ui.button("📥 Import Settings").clicked() {
                    // Handle import settings
                }
            });
        });
    }
}

impl Component for Settings {
    fn render_window(&mut self, ctx: &Context) {
        let mut is_open = self.window.is_open;
        Window::new(&self.window.title)
            .open(&mut is_open)
            .default_size(self.window.default_size)
            .resizable(self.window.resizable)
            .show(ctx, |ui| {
                self.render_ui(ui);
            });
        self.window.is_open = is_open;
    }
    
    fn render_ui(&mut self, ui: &mut Ui) {
        ScrollArea::vertical().show(ui, |ui| {
            ui.heading("⚙️ Application Settings");
            
            self.render_appearance_settings(ui);
            ui.separator();
            self.render_data_settings(ui);
            ui.separator();
            self.render_trading_settings(ui);
            ui.separator();
            self.render_notification_settings(ui);
            ui.separator();
            self.render_actions(ui);
        });
    }
    
    fn name(&self) -> &str {
        &self.window.title
    }
    
    fn is_open(&self) -> bool {
        self.window.is_open
    }
    
    fn set_open(&mut self, open: bool) {
        self.window.is_open = open;
    }
    
    fn as_any(&self) -> &dyn Any {
        self
    }
    
    fn as_any_mut(&mut self) -> &mut dyn Any {
        self
    }
}