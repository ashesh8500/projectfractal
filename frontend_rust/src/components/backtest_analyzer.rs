use super::{Component, WindowedComponent};
use super::charts::{AllocationChart, DrawdownChart, PerformanceChart, utils};
use crate::portfolio_pb::BacktestResult;
use egui::{Color32, Context, ScrollArea, Ui, Window};
use std::any::Any;
use std::collections::HashMap;

pub struct BacktestAnalyzer {
    window: WindowedComponent,
    selected_month: usize,
    performance_chart: PerformanceChart,
    allocation_chart: AllocationChart,
    drawdown_chart: DrawdownChart,
}

impl BacktestAnalyzer {
    pub fn new() -> Self {
        Self {
            window: WindowedComponent::new("📊 Backtest Analyzer").with_size(900.0, 700.0),
            selected_month: 0,
            performance_chart: PerformanceChart::new("performance_analysis"),
            allocation_chart: AllocationChart::new("monthly_allocation_plot"),
            drawdown_chart: DrawdownChart::new("drawdown_analysis"),
        }
    }
    
    pub fn with_backtest_result(&mut self, result: Option<&BacktestResult>) -> &mut Self {
        // This method would be called to update the component with new data
        self
    }
    
    fn render_summary_metrics(&self, ui: &mut Ui, backtest_result: &BacktestResult) {
        ui.group(|ui| {
            ui.heading("📊 Backtest Summary");
            
            if backtest_result.is_using_mock_data {
                ui.colored_label(Color32::YELLOW, "⚠️ Using mock data - Connect to real data source for accurate results");
            }
            
            ui.horizontal(|ui| {
                // Left column - Period Analysis
                ui.vertical(|ui| {
                    ui.label("🗓️ Period Analysis:");
                    ui.label(format!("Start: {}", backtest_result.start_date));
                    ui.label(format!("End: {}", backtest_result.end_date));
                    ui.label(format!("Period: {} days", backtest_result.period_days));
                    ui.separator();
                    ui.label("💰 Performance:");
                    ui.label(format!("Start Value: {}", utils::format_currency(backtest_result.start_value)));
                    ui.label(format!("End Value: {}", utils::format_currency(backtest_result.end_value)));
                    ui.colored_label(Color32::GREEN, format!("Total Return: {}", utils::format_percentage(backtest_result.total_return_pct)));
                    ui.label(format!("Benchmark Return: {}", utils::format_percentage(backtest_result.benchmark_return_pct)));
                });
                
                ui.separator();
                
                // Middle column - Risk Metrics
                ui.vertical(|ui| {
                    ui.label("⚠️ Risk Metrics:");
                    ui.colored_label(Color32::RED, format!("Max Drawdown: {}", utils::format_percentage(backtest_result.max_drawdown_pct)));
                    ui.label(format!("Max DD Duration: {} days", backtest_result.max_drawdown_duration_days));
                    ui.label(format!("Max Exposure: {:.1}%", backtest_result.max_gross_exposure_pct));
                    ui.separator();
                    ui.label("📈 Ratios:");
                    ui.colored_label(Color32::BLUE, format!("Sharpe Ratio: {}", utils::format_ratio(backtest_result.sharpe_ratio)));
                    ui.colored_label(Color32::BLUE, format!("Calmar Ratio: {}", utils::format_ratio(backtest_result.calmar_ratio)));
                    ui.colored_label(Color32::BLUE, format!("Sortino Ratio: {}", utils::format_ratio(backtest_result.sortino_ratio)));
                });
                
                ui.separator();
                
                // Right column - Trading Activity
                ui.vertical(|ui| {
                    ui.label("🔄 Trading Activity:");
                    ui.label(format!("Total Trades: {}", backtest_result.total_trades));
                    ui.label(format!("Closed Trades: {}", backtest_result.total_closed_trades));
                    ui.label(format!("Open Trades: {}", backtest_result.total_open_trades));
                    ui.separator();
                    ui.label("📊 Trade Performance:");
                    ui.colored_label(Color32::GREEN, format!("Win Rate: {:.1}%", backtest_result.win_rate_pct));
                    ui.colored_label(Color32::GREEN, format!("Best Trade: {}", utils::format_percentage(backtest_result.best_trade_pct)));
                    ui.colored_label(Color32::RED, format!("Worst Trade: {}", utils::format_percentage(backtest_result.worst_trade_pct)));
                    ui.label(format!("Profit Factor: {:.2}", backtest_result.profit_factor));
                });
            });
        });
    }
    
    fn render_allocation_analysis(&mut self, ui: &mut Ui, backtest_result: &BacktestResult) {
        ui.group(|ui| {
            ui.heading("📅 Monthly Allocation Analysis");
            
            if !backtest_result.allocations.is_empty() {
                ui.label("Historical portfolio allocation weights by month:");
                
                // Month navigation
                ui.horizontal(|ui| {
                    ui.label("Select Month:");
                    let num_months = backtest_result.allocations.len();
                    
                    // Ensure selected month is within bounds
                    if self.selected_month >= num_months {
                        self.selected_month = 0;
                    }
                    
                    // Previous button
                    if ui.button("◀ Previous").clicked() && self.selected_month > 0 {
                        self.selected_month -= 1;
                    }
                    
                    // Current month display
                    ui.label(format!("Month {}/{}", self.selected_month + 1, num_months));
                    if let Some(current_alloc) = backtest_result.allocations.get(self.selected_month) {
                        ui.label(format!("Date: {}", current_alloc.date));
                    }
                    
                    // Next button
                    if ui.button("Next ▶").clicked() && self.selected_month < num_months - 1 {
                        self.selected_month += 1;
                    }
                });
                
                ui.separator();
                
                // Display allocation chart for selected month
                if let Some(selected_allocation) = backtest_result.allocations.get(self.selected_month) {
                    ui.label(format!("Allocation for {}", selected_allocation.date));
                    
                    // Render the allocation chart
                    self.allocation_chart.render(ui, &selected_allocation.weights);
                }
                
                ui.separator();
                
                // Allocation details table
                self.render_allocation_table(ui, backtest_result);
            } else {
                ui.label("No allocation data available");
            }
        });
    }
    
    fn render_allocation_table(&self, ui: &mut Ui, backtest_result: &BacktestResult) {
        ui.group(|ui| {
            ui.heading("📋 Allocation Details");
            
            if let Some(selected_allocation) = backtest_result.allocations.get(self.selected_month) {
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
                                
                                let color = utils::allocation_color(*weight);
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
    }
    
    fn render_performance_analysis(&self, ui: &mut Ui, backtest_result: &BacktestResult) {
        ui.group(|ui| {
            ui.heading("📈 Performance Analysis");
            
            ui.label("Portfolio vs Benchmark Performance (Sample Data):");
            
            // Generate sample performance data based on backtest metrics
            let days = backtest_result.period_days as usize;
            let mut portfolio_values = Vec::new();
            let mut benchmark_values = Vec::new();
            
            let daily_portfolio_return = (1.0_f64 + backtest_result.total_return_pct / 100.0).powf(1.0 / days as f64) - 1.0;
            let daily_benchmark_return = (1.0_f64 + backtest_result.benchmark_return_pct / 100.0).powf(1.0 / days as f64) - 1.0;
            
            let mut portfolio_val = backtest_result.start_value;
            let mut benchmark_val = backtest_result.start_value;
            
            for i in 0..days.min(252) {
                // Add some volatility to make it realistic
                let portfolio_daily_return = daily_portfolio_return + 0.02 * (i as f64 * 0.1).sin() * 0.01;
                let benchmark_daily_return = daily_benchmark_return + 0.01 * (i as f64 * 0.05).sin() * 0.005;
                
                portfolio_val *= 1.0 + portfolio_daily_return;
                benchmark_val *= 1.0 + benchmark_daily_return;
                
                portfolio_values.push((i as f64, portfolio_val));
                benchmark_values.push((i as f64, benchmark_val));
            }
            
            self.performance_chart.render(ui, &portfolio_values, &benchmark_values);
        });
    }
    
    fn render_no_data_message(&self, ui: &mut Ui) {
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
    }
}

impl Component for BacktestAnalyzer {
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
            ui.heading("🔬 Portfolio Backtesting Analysis");
            
            // This would typically get the backtest result from the main app state
            // For now, we'll check if we have data through a method call
            // In the refactored version, this would be passed as a parameter
            
            // Placeholder for no data - in real implementation, this would be passed from main app
            self.render_no_data_message(ui);
            
            // When backtest_result is available, call:
            // self.render_summary_metrics(ui, backtest_result);
            // ui.separator();
            // self.render_allocation_analysis(ui, backtest_result);
            // ui.separator();
            // self.render_performance_analysis(ui, backtest_result);
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

impl BacktestAnalyzer {
    /// Render with backtest result data
    pub fn render_with_data(&mut self, ui: &mut Ui, backtest_result: Option<&BacktestResult>) {
        ui.heading("🔬 Portfolio Backtesting Analysis");
        
        let Some(backtest_result) = backtest_result else {
            self.render_no_data_message(ui);
            return;
        };
        
        self.render_summary_metrics(ui, backtest_result);
        ui.separator();
        self.render_allocation_analysis(ui, backtest_result);
        ui.separator();
        self.render_performance_analysis(ui, backtest_result);
    }
}