use egui::{Context, Ui};
use std::any::Any;

/// Base trait for all UI components in the financial terminal
pub trait Component {
    /// Render the component in a window context
    fn render_window(&mut self, ctx: &Context);
    
    /// Render the component in a UI context (for embedded components)
    fn render_ui(&mut self, ui: &mut Ui);
    
    /// Get the component's name/title
    fn name(&self) -> &str;
    
    /// Check if the component window is open
    fn is_open(&self) -> bool;
    
    /// Set the component window open/closed state
    fn set_open(&mut self, open: bool);
    
    /// Get component as Any for downcasting
    fn as_any(&self) -> &dyn Any;
    
    /// Get mutable component as Any for downcasting
    fn as_any_mut(&mut self) -> &mut dyn Any;
}

/// Base struct for windowed components
pub struct WindowedComponent {
    pub title: String,
    pub is_open: bool,
    pub default_size: [f32; 2],
    pub resizable: bool,
}

impl WindowedComponent {
    pub fn new(title: impl Into<String>) -> Self {
        Self {
            title: title.into(),
            is_open: false,
            default_size: [800.0, 600.0],
            resizable: true,
        }
    }
    
    pub fn with_size(mut self, width: f32, height: f32) -> Self {
        self.default_size = [width, height];
        self
    }
    
    pub fn with_resizable(mut self, resizable: bool) -> Self {
        self.resizable = resizable;
        self
    }
}

pub mod backtest_analyzer;
pub mod strategy_analyzer;
pub mod risk_dashboard;
pub mod portfolio_comparison;
pub mod performance_dashboard;
pub mod technical_indicators;
pub mod settings;
pub mod charts;
pub mod manager;