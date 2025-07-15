use super::{Component, WindowedComponent};
use super::charts::{PerformanceChart, utils};
use egui::{Color32, Context, ScrollArea, Ui, Window};
use std::any::Any;

pub struct TechnicalIndicators {
    window: WindowedComponent,
    indicator_chart: PerformanceChart,
}

impl TechnicalIndicators {
    pub fn new() -> Self {
        Self {
            window: WindowedComponent::new("📊 Technical Indicators").with_size(800.0, 600.0),
            indicator_chart: PerformanceChart::new("technical_indicators"),
        }
    }
    
    fn render_indicator_summary(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📊 Technical Indicators");
            
            ui.horizontal(|ui| {
                ui.vertical(|ui| {
                    ui.label("📈 Moving Averages:");
                    ui.label("SMA 20: $145.23");
                    ui.label("SMA 50: $142.67");
                    ui.label("EMA 12: $146.89");
                    ui.label("EMA 26: $143.45");
                });
                
                ui.separator();
                
                ui.vertical(|ui| {
                    ui.label("📊 Oscillators:");
                    ui.colored_label(Color32::GREEN, "RSI: 58.3 (Neutral)");
                    ui.colored_label(Color32::BLUE, "MACD: 0.45 (Bullish)");
                    ui.label("Stoch: 65.2 (Overbought)");
                    ui.label("Williams %R: -23.4");
                });
                
                ui.separator();
                
                ui.vertical(|ui| {
                    ui.label("📈 Volatility:");
                    ui.label("ATR: 2.45");
                    ui.label("Bollinger Upper: $148.90");
                    ui.label("Bollinger Lower: $141.20");
                    ui.colored_label(Color32::YELLOW, "Volatility: High");
                });
            });
        });
    }
    
    fn render_indicator_chart(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("📊 Price & Indicators");
            
            // Sample price data with indicators
            let price_data: Vec<(f64, f64)> = (0..100)
                .map(|i| (i as f64, 145.0 + 10.0 * (i as f64 * 0.1).sin() + 2.0 * (i as f64 * 0.05).cos()))
                .collect();
            
            let sma_data: Vec<(f64, f64)> = (0..100)
                .map(|i| (i as f64, 145.0 + 8.0 * (i as f64 * 0.1).sin()))
                .collect();
            
            self.indicator_chart.render(ui, &price_data, &sma_data);
        });
    }
    
    fn render_signal_summary(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.heading("🚨 Trading Signals");
            
            egui::Grid::new("signals_grid")
                .striped(true)
                .show(ui, |ui| {
                    ui.label("Indicator");
                    ui.label("Signal");
                    ui.label("Strength");
                    ui.end_row();
                    
                    ui.label("RSI");
                    ui.colored_label(Color32::GREEN, "BUY");
                    ui.label("Medium");
                    ui.end_row();
                    
                    ui.label("MACD");
                    ui.colored_label(Color32::GREEN, "BUY");
                    ui.label("Strong");
                    ui.end_row();
                    
                    ui.label("Bollinger Bands");
                    ui.colored_label(Color32::YELLOW, "NEUTRAL");
                    ui.label("Weak");
                    ui.end_row();
                    
                    ui.label("Moving Average");
                    ui.colored_label(Color32::GREEN, "BUY");
                    ui.label("Strong");
                    ui.end_row();
                });
        });
    }
    
    fn render_no_data_message(&self, ui: &mut Ui) {
        ui.group(|ui| {
            ui.vertical_centered(|ui| {
                ui.label("📊 No technical indicators available");
                ui.label("Load price data to see indicators");
                ui.separator();
                ui.label("Available indicators:");
                ui.label("• Moving Averages (SMA, EMA)");
                ui.label("• RSI & MACD");
                ui.label("• Bollinger Bands");
                ui.label("• Stochastic Oscillator");
            });
        });
    }
}

impl Component for TechnicalIndicators {
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
            ui.heading("📊 Technical Analysis");
            
            // For now, show sample indicators
            self.render_indicator_summary(ui);
            ui.separator();
            self.render_indicator_chart(ui);
            ui.separator();
            self.render_signal_summary(ui);
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