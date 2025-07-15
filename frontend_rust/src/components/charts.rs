use egui::{Color32, Ui};
use egui_plot::{Bar, BarChart, Legend, Line, Plot, PlotPoints};
use std::collections::HashMap;

/// Financial chart styling and utilities
pub struct ChartStyle {
    pub primary_color: Color32,
    pub secondary_color: Color32,
    pub positive_color: Color32,
    pub negative_color: Color32,
    pub neutral_color: Color32,
    pub background_color: Color32,
}

impl Default for ChartStyle {
    fn default() -> Self {
        Self {
            primary_color: Color32::from_rgb(31, 119, 180),
            secondary_color: Color32::from_rgb(255, 127, 14),
            positive_color: Color32::from_rgb(44, 160, 44),
            negative_color: Color32::from_rgb(214, 39, 40),
            neutral_color: Color32::GRAY,
            background_color: Color32::from_rgb(248, 249, 250),
        }
    }
}

/// Performance chart for portfolio vs benchmark
pub struct PerformanceChart {
    pub name: String,
    pub height: f32,
    pub style: ChartStyle,
}

impl PerformanceChart {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            height: 300.0,
            style: ChartStyle::default(),
        }
    }
    
    pub fn with_height(mut self, height: f32) -> Self {
        self.height = height;
        self
    }
    
    pub fn render(&self, ui: &mut Ui, portfolio_data: &[(f64, f64)], benchmark_data: &[(f64, f64)]) {
        let portfolio_points: PlotPoints = portfolio_data.iter().map(|(x, y)| [*x, *y]).collect();
        let benchmark_points: PlotPoints = benchmark_data.iter().map(|(x, y)| [*x, *y]).collect();
        
        Plot::new(&self.name)
            .legend(Legend::default())
            .height(self.height)
            .show(ui, |plot_ui| {
                plot_ui.line(
                    Line::new(portfolio_points)
                        .name("Portfolio")
                        .width(2.5)
                        .color(self.style.primary_color)
                );
                plot_ui.line(
                    Line::new(benchmark_points)
                        .name("Benchmark")
                        .width(2.0)
                        .color(self.style.secondary_color)
                );
            });
    }
}

/// Allocation bar chart
pub struct AllocationChart {
    pub name: String,
    pub height: f32,
    pub style: ChartStyle,
}

impl AllocationChart {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            height: 250.0,
            style: ChartStyle::default(),
        }
    }
    
    pub fn with_height(mut self, height: f32) -> Self {
        self.height = height;
        self
    }
    
    pub fn render(&self, ui: &mut Ui, allocations: &HashMap<String, f64>) {
        let mut bars = Vec::new();
        let mut symbols: Vec<_> = allocations.keys().collect();
        symbols.sort();
        
        for (i, symbol) in symbols.iter().enumerate() {
            if let Some(weight) = allocations.get(*symbol) {
                if *weight > 0.0 {
                    bars.push(Bar::new(i as f64, *weight * 100.0).name(symbol));
                }
            }
        }
        
        if !bars.is_empty() {
            Plot::new(&self.name)
                .legend(Legend::default())
                .height(self.height)
                .show(ui, |plot_ui| {
                    plot_ui.bar_chart(BarChart::new(bars).color(self.style.primary_color));
                });
        }
    }
}

/// Drawdown chart
pub struct DrawdownChart {
    pub name: String,
    pub height: f32,
    pub style: ChartStyle,
}

impl DrawdownChart {
    pub fn new(name: impl Into<String>) -> Self {
        Self {
            name: name.into(),
            height: 200.0,
            style: ChartStyle::default(),
        }
    }
    
    pub fn with_height(mut self, height: f32) -> Self {
        self.height = height;
        self
    }
    
    pub fn render(&self, ui: &mut Ui, drawdown_data: &[f64]) {
        let drawdown_points: PlotPoints = drawdown_data
            .iter()
            .enumerate()
            .map(|(i, v)| [i as f64, *v * -100.0])
            .collect();
        
        Plot::new(&self.name)
            .legend(Legend::default())
            .height(self.height)
            .show(ui, |plot_ui| {
                plot_ui.line(
                    Line::new(drawdown_points)
                        .name("Drawdown (%)")
                        .width(2.0)
                        .color(self.style.negative_color)
                );
            });
    }
}

/// Utility functions for financial data visualization
pub mod utils {
    use super::*;
    
    /// Generate color for percentage values (green for positive, red for negative)
    pub fn percentage_color(value: f64) -> Color32 {
        if value > 0.0 {
            Color32::from_rgb(44, 160, 44) // Green
        } else if value < 0.0 {
            Color32::from_rgb(214, 39, 40) // Red
        } else {
            Color32::GRAY
        }
    }
    
    /// Generate color for allocation weights
    pub fn allocation_color(weight: f64) -> Color32 {
        if weight > 0.3 {
            Color32::DARK_GREEN
        } else if weight > 0.15 {
            Color32::BLUE
        } else {
            Color32::GRAY
        }
    }
    
    /// Format percentage for display
    pub fn format_percentage(value: f64) -> String {
        format!("{:.2}%", value)
    }
    
    /// Format currency for display
    pub fn format_currency(value: f64) -> String {
        format!("${:.2}", value)
    }
    
    /// Format ratio for display
    pub fn format_ratio(value: f64) -> String {
        format!("{:.4}", value)
    }
}