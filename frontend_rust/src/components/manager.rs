use super::{Component, backtest_analyzer::BacktestAnalyzer, strategy_analyzer::StrategyAnalyzer, 
           risk_dashboard::RiskDashboard, portfolio_comparison::PortfolioComparison,
           performance_dashboard::PerformanceDashboard, technical_indicators::TechnicalIndicators,
           settings::Settings};
use egui::Context;

/// Component manager that handles all UI components
pub struct ComponentManager {
    pub backtest_analyzer: BacktestAnalyzer,
    pub strategy_analyzer: StrategyAnalyzer,
    pub risk_dashboard: RiskDashboard,
    pub portfolio_comparison: PortfolioComparison,
    pub performance_dashboard: PerformanceDashboard,
    pub technical_indicators: TechnicalIndicators,
    pub settings: Settings,
}

impl ComponentManager {
    pub fn new() -> Self {
        Self {
            backtest_analyzer: BacktestAnalyzer::new(),
            strategy_analyzer: StrategyAnalyzer::new(),
            risk_dashboard: RiskDashboard::new(),
            portfolio_comparison: PortfolioComparison::new(),
            performance_dashboard: PerformanceDashboard::new(),
            technical_indicators: TechnicalIndicators::new(),
            settings: Settings::new(),
        }
    }
    
    /// Render all open component windows
    pub fn render_all(&mut self, ctx: &Context) {
        if self.backtest_analyzer.is_open() {
            self.backtest_analyzer.render_window(ctx);
        }
        if self.strategy_analyzer.is_open() {
            self.strategy_analyzer.render_window(ctx);
        }
        if self.risk_dashboard.is_open() {
            self.risk_dashboard.render_window(ctx);
        }
        if self.portfolio_comparison.is_open() {
            self.portfolio_comparison.render_window(ctx);
        }
        if self.performance_dashboard.is_open() {
            self.performance_dashboard.render_window(ctx);
        }
        if self.technical_indicators.is_open() {
            self.technical_indicators.render_window(ctx);
        }
        if self.settings.is_open() {
            self.settings.render_window(ctx);
        }
    }
    
    /// Close all component windows
    pub fn close_all(&mut self) {
        self.backtest_analyzer.set_open(false);
        self.strategy_analyzer.set_open(false);
        self.risk_dashboard.set_open(false);
        self.portfolio_comparison.set_open(false);
        self.performance_dashboard.set_open(false);
        self.technical_indicators.set_open(false);
        self.settings.set_open(false);
    }
    
    /// Get a list of all components
    pub fn get_all_components(&mut self) -> Vec<&mut dyn Component> {
        vec![
            &mut self.backtest_analyzer,
            &mut self.strategy_analyzer,
            &mut self.risk_dashboard,
            &mut self.portfolio_comparison,
            &mut self.performance_dashboard,
            &mut self.technical_indicators,
            &mut self.settings,
        ]
    }
    
    /// Handle keyboard shortcuts for components
    pub fn handle_keyboard_shortcuts(&mut self, ctx: &Context) {
        ctx.input(|i| {
            if i.key_pressed(egui::Key::F1) {
                self.strategy_analyzer.set_open(!self.strategy_analyzer.is_open());
            }
            if i.key_pressed(egui::Key::F2) {
                self.risk_dashboard.set_open(!self.risk_dashboard.is_open());
            }
            if i.key_pressed(egui::Key::F3) {
                self.backtest_analyzer.set_open(!self.backtest_analyzer.is_open());
            }
            if i.key_pressed(egui::Key::F4) {
                self.performance_dashboard.set_open(!self.performance_dashboard.is_open());
            }
            if i.key_pressed(egui::Key::F5) {
                self.technical_indicators.set_open(!self.technical_indicators.is_open());
            }
            if i.key_pressed(egui::Key::F6) {
                self.portfolio_comparison.set_open(!self.portfolio_comparison.is_open());
            }
            if i.key_pressed(egui::Key::F12) {
                self.settings.set_open(!self.settings.is_open());
            }
            if i.key_pressed(egui::Key::Escape) {
                self.close_all();
            }
        });
    }
}