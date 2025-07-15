use super::{Component, WindowedComponent};
use super::charts::{AllocationChart, PerformanceChart, utils};
use crate::portfolio_pb::StrategyResult;
use egui::{Color32, Context, ScrollArea, Ui, Window};
use std::any::Any;

pub struct StrategyAnalyzer {
    window: WindowedComponent,
    performance_chart: PerformanceChart,
    allocation_chart: AllocationChart,
}

impl StrategyAnalyzer {
    pub fn new() -> Self {
        Self {
            window: WindowedComponent::new("🧠 Strategy Analyzer").with_size(800.0, 600.0),
            performance_chart: PerformanceChart::new("strategy_performance"),
            allocation_chart: AllocationChart::new("strategy_allocation"),
        }
    }
    
    fn render_strategy_results(&self, ui: &mut Ui, strategy_result: &StrategyResult) {
        ui.group(|ui| {
            ui.heading("📊 Strategy Analysis Results");
            
            if strategy_result.is_using_mock_data {
                ui.colored_label(Color32::YELLOW, "⚠️ Using mock data");
            }
            
            ui.separator();
            
            // Strategy recommendations
            ui.label("📈 New Allocation Recommendations:");
            
            let mut allocations: Vec<_> = strategy_result.new_weights.iter().collect();
            allocations.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());
            
            egui::Grid::new("strategy_allocations")
                .striped(true)
                .show(ui, |ui| {
                    ui.label("Symbol");
                    ui.label("New Weight");
                    ui.label("Change");
                    ui.end_row();
                    
                    for (symbol, weight) in allocations {
                        ui.label(symbol);
                        ui.colored_label(utils::allocation_color(*weight), format!("{:.1}%", weight * 100.0));
                        
                        if let Some(change) = strategy_result.changes.get(symbol) {
                            let color = utils::percentage_color(*change);
                            ui.colored_label(color, format!("{:+.1}%", change * 100.0));
                        } else {
                            ui.label("—");
                        }
                        ui.end_row();
                    }
                });
        });
    }
    
    fn render_no_data_message(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.vertical_centered(|ui| {
                ui.label("🧠 No strategy analysis available");
                ui.label("Run a strategy first to see analysis");
                ui.separator();
                ui.label("Available strategies:");
                ui.label("• Bollinger Bands Strategy");
                ui.label("• Machine Learning Strategy");
                ui.label("• Risk Parity Strategy");
            });
        });
    }
}

impl Component for StrategyAnalyzer {
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
            ui.heading("🧠 Strategy Analysis");
            
            // Placeholder for no data
            self.render_no_data_message(ui);
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

impl StrategyAnalyzer {
    /// Render with strategy result data
    pub fn render_with_data(&mut self, ui: &mut Ui, strategy_result: Option<&StrategyResult>) {
        ui.heading("🧠 Strategy Analysis");
        
        let Some(strategy_result) = strategy_result else {
            self.render_no_data_message(ui);
            return;
        };
        
        self.render_strategy_results(ui, strategy_result);
    }
}