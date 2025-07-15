use super::{Component, WindowedComponent};
use super::charts::{AllocationChart, PerformanceChart, utils};
use egui::{Color32, Context, ScrollArea, Ui, Window};
use std::any::Any;
use std::collections::HashMap;

pub struct PerformanceDashboard {
    window: WindowedComponent,
    performance_chart: PerformanceChart,
    allocation_chart: AllocationChart,
}

impl PerformanceDashboard {
    pub fn new() -> Self {
        Self {
            window: WindowedComponent::new("📈 Performance Dashboard").with_size(900.0, 700.0),
            performance_chart: PerformanceChart::new("performance_overview"),
            allocation_chart: AllocationChart::new("current_allocation"),
        }
    }
    
    fn render_performance_summary(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📈 Performance Summary");
            
            ui.horizontal(|ui| {
                ui.vertical(|ui| {
                    ui.label("📊 Returns:");
                    ui.colored_label(Color32::GREEN, "YTD: +15.2%");
                    ui.colored_label(Color32::GREEN, "1Y: +22.8%");
                    ui.colored_label(Color32::GREEN, "3Y: +18.5%");
                    ui.colored_label(Color32::GREEN, "5Y: +12.3%");
                });
                
                ui.separator();
                
                ui.vertical(|ui| {
                    ui.label("⚠️ Risk Metrics:");
                    ui.label("Volatility: 16.8%");
                    ui.colored_label(Color32::BLUE, "Sharpe: 1.35");
                    ui.colored_label(Color32::BLUE, "Sortino: 1.85");
                    ui.colored_label(Color32::RED, "Max DD: -8.2%");
                });
                
                ui.separator();
                
                ui.vertical(|ui| {
                    ui.label("💰 Portfolio Value:");
                    ui.label("Current: $125,430");
                    ui.colored_label(Color32::GREEN, "P&L: +$23,430");
                    ui.label("Cash: $5,230");
                    ui.label("Invested: $120,200");
                });
            });
        });
    }
    
    fn render_performance_chart(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📊 Performance Over Time");
            
            // Sample performance data
            let portfolio_data: Vec<(f64, f64)> = (0..252)
                .map(|i| (i as f64, 100000.0 * (1.0 + 0.0008 * i as f64 + 0.03 * (i as f64 * 0.1).sin())))
                .collect();
            
            let benchmark_data: Vec<(f64, f64)> = (0..252)
                .map(|i| (i as f64, 100000.0 * (1.0 + 0.0006 * i as f64 + 0.02 * (i as f64 * 0.08).sin())))
                .collect();
            
            self.performance_chart.render(ui, &portfolio_data, &benchmark_data);
        });
    }
    
    fn render_allocation_breakdown(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📊 Current Allocation");
            
            let mut sample_allocations = HashMap::new();
            sample_allocations.insert("AAPL".to_string(), 0.25);
            sample_allocations.insert("GOOGL".to_string(), 0.20);
            sample_allocations.insert("MSFT".to_string(), 0.18);
            sample_allocations.insert("AMZN".to_string(), 0.15);
            sample_allocations.insert("TSLA".to_string(), 0.12);
            sample_allocations.insert("NVDA".to_string(), 0.10);
            
            self.allocation_chart.render(ui, &sample_allocations);
            
            ui.separator();
            
            // Allocation table
            egui::Grid::new("allocation_breakdown")
                .striped(true)
                .show(ui, |ui| {
                    ui.label("Symbol");
                    ui.label("Weight");
                    ui.label("Value");
                    ui.label("P&L");
                    ui.end_row();
                    
                    for (symbol, weight) in &sample_allocations {
                        ui.label(symbol);
                        ui.colored_label(utils::allocation_color(*weight), format!("{:.1}%", weight * 100.0));
                        ui.label(format!("{}", utils::format_currency(125430.0 * weight)));
                        ui.colored_label(Color32::GREEN, "+$1,250");
                        ui.end_row();
                    }
                });
        });
    }
    
    fn render_no_data_message(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.vertical_centered(|ui| {
                ui.label("📈 No performance data available");
                ui.label("Load a portfolio to see performance metrics");
                ui.separator();
                ui.label("Available metrics:");
                ui.label("• Portfolio returns and P&L");
                ui.label("• Risk-adjusted performance");
                ui.label("• Allocation breakdown");
                ui.label("• Historical performance");
            });
        });
    }
}

impl Component for PerformanceDashboard {
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
            ui.heading("📈 Performance Dashboard");
            
            // For now, show sample performance data
            self.render_performance_summary(ui);
            ui.separator();
            self.render_performance_chart(ui);
            ui.separator();
            self.render_allocation_breakdown(ui);
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