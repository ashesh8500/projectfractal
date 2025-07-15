use super::{Component, WindowedComponent};
use super::charts::{DrawdownChart, PerformanceChart, utils};
use egui::{Color32, Context, ScrollArea, Ui, Window};
use std::any::Any;

pub struct RiskDashboard {
    window: WindowedComponent,
    drawdown_chart: DrawdownChart,
    volatility_chart: PerformanceChart,
}

impl RiskDashboard {
    pub fn new() -> Self {
        Self {
            window: WindowedComponent::new("⚠️ Risk Dashboard").with_size(800.0, 600.0),
            drawdown_chart: DrawdownChart::new("risk_drawdown"),
            volatility_chart: PerformanceChart::new("volatility_analysis"),
        }
    }
    
    fn render_risk_metrics(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("⚠️ Risk Metrics");
            
            ui.horizontal(|ui| {
                ui.vertical(|ui| {
                    ui.label("📊 Portfolio Risk:");
                    ui.colored_label(Color32::RED, "VaR (95%): -5.2%");
                    ui.colored_label(Color32::RED, "Max Drawdown: -12.5%");
                    ui.label("Beta: 1.15");
                    ui.label("Alpha: 2.3%");
                });
                
                ui.separator();
                
                ui.vertical(|ui| {
                    ui.label("📈 Volatility:");
                    ui.label("Daily Vol: 1.8%");
                    ui.label("Monthly Vol: 6.2%");
                    ui.label("Annual Vol: 21.5%");
                    ui.colored_label(Color32::BLUE, "Sharpe Ratio: 1.25");
                });
                
                ui.separator();
                
                ui.vertical(|ui| {
                    ui.label("🔄 Correlation:");
                    ui.label("vs S&P 500: 0.85");
                    ui.label("vs Bonds: -0.12");
                    ui.label("vs Gold: 0.23");
                    ui.label("Diversification: 0.73");
                });
            });
        });
    }
    
    fn render_risk_visualization(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📊 Risk Visualization");
            
            // Sample drawdown data
            let drawdown_data: Vec<f64> = (0..100)
                .map(|i| (i as f64 * 0.05).sin() * 0.1)
                .collect();
            
            self.drawdown_chart.render(ui, &drawdown_data);
        });
    }
    
    fn render_no_data_message(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.vertical_centered(|ui| {
                ui.label("⚠️ No risk analysis available");
                ui.label("Load a portfolio to see risk metrics");
                ui.separator();
                ui.label("Available risk metrics:");
                ui.label("• Value at Risk (VaR)");
                ui.label("• Maximum Drawdown");
                ui.label("• Beta and Alpha");
                ui.label("• Volatility Analysis");
            });
        });
    }
}

impl Component for RiskDashboard {
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
            ui.heading("⚠️ Risk Analysis Dashboard");
            
            // For now, show sample data
            self.render_risk_metrics(ui);
            ui.separator();
            self.render_risk_visualization(ui);
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