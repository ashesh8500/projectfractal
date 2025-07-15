use super::{Component, WindowedComponent};
use super::charts::{PerformanceChart, utils};
use egui::{Color32, Context, ScrollArea, Ui, Window};
use std::any::Any;

pub struct PortfolioComparison {
    window: WindowedComponent,
    comparison_chart: PerformanceChart,
}

impl PortfolioComparison {
    pub fn new() -> Self {
        Self {
            window: WindowedComponent::new("📊 Portfolio Comparison").with_size(800.0, 600.0),
            comparison_chart: PerformanceChart::new("portfolio_comparison"),
        }
    }
    
    fn render_comparison_metrics(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📊 Portfolio Comparison");
            
            egui::Grid::new("comparison_grid")
                .striped(true)
                .show(ui, |ui| {
                    ui.label("Metric");
                    ui.label("Portfolio A");
                    ui.label("Portfolio B");
                    ui.label("Difference");
                    ui.end_row();
                    
                    ui.label("Total Return");
                    ui.colored_label(Color32::GREEN, "12.5%");
                    ui.colored_label(Color32::GREEN, "8.3%");
                    ui.colored_label(Color32::GREEN, "+4.2%");
                    ui.end_row();
                    
                    ui.label("Volatility");
                    ui.label("15.2%");
                    ui.label("12.8%");
                    ui.colored_label(Color32::RED, "+2.4%");
                    ui.end_row();
                    
                    ui.label("Sharpe Ratio");
                    ui.colored_label(Color32::BLUE, "0.82");
                    ui.colored_label(Color32::BLUE, "0.65");
                    ui.colored_label(Color32::GREEN, "+0.17");
                    ui.end_row();
                    
                    ui.label("Max Drawdown");
                    ui.colored_label(Color32::RED, "-8.5%");
                    ui.colored_label(Color32::RED, "-6.2%");
                    ui.colored_label(Color32::RED, "-2.3%");
                    ui.end_row();
                });
        });
    }
    
    fn render_comparison_chart(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📈 Performance Comparison");
            
            // Sample data for comparison
            let portfolio_a: Vec<(f64, f64)> = (0..252)
                .map(|i| (i as f64, 100.0 * (1.0 + 0.0005 * i as f64 + 0.02 * (i as f64 * 0.1).sin())))
                .collect();
            
            let portfolio_b: Vec<(f64, f64)> = (0..252)
                .map(|i| (i as f64, 100.0 * (1.0 + 0.0003 * i as f64 + 0.015 * (i as f64 * 0.08).sin())))
                .collect();
            
            self.comparison_chart.render(ui, &portfolio_a, &portfolio_b);
        });
    }
    
    fn render_no_data_message(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.vertical_centered(|ui| {
                ui.label("📊 No portfolios to compare");
                ui.label("Load multiple portfolios to see comparison");
                ui.separator();
                ui.label("Comparison features:");
                ui.label("• Side-by-side performance metrics");
                ui.label("• Risk-adjusted returns");
                ui.label("• Allocation differences");
                ui.label("• Historical performance");
            });
        });
    }
}

impl Component for PortfolioComparison {
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
            ui.heading("📊 Portfolio Comparison");
            
            // For now, show sample comparison
            self.render_comparison_metrics(ui);
            ui.separator();
            self.render_comparison_chart(ui);
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