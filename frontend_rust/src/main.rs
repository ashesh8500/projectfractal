mod api;
mod models;
mod ui;
mod components;
mod utils;

#[macro_use]
extern crate lazy_static;

use ui::app::PortfolioApp;

#[cfg(not(target_arch = "wasm32"))]
fn main() -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1000.0, 700.0])
            .with_title("Portfolio Optimizer Pro - Advanced"),
        ..Default::default()
    };
    eframe::run_native(
        "Portfolio Optimizer Pro - Advanced",
        native_options,
        Box::new(|cc| Box::new(PortfolioApp::new(cc))),
    )
}

#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub fn start_app() -> Result<(), eframe::wasm_bindgen::JsValue> {
    // Set up panic hook for better error messages
    console_error_panic_hook::set_once();
    
    // Log to console
    tracing_wasm::set_as_global_default();
    
    let web_options = eframe::WebOptions::default();
    
    wasm_bindgen_futures::spawn_local(async {
        eframe::WebRunner::new()
            .start(
                "portfolio_app_canvas", // ID of the canvas element to use
                web_options,
                Box::new(|cc| Box::new(PortfolioApp::new(cc))),
            )
            .await
            .expect("Failed to start eframe");
    });
    
    Ok(())
}