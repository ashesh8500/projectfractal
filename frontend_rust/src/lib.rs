use wasm_bindgen::prelude::*;

// When the `wee_alloc` feature is enabled, use `wee_alloc` as the global allocator.
#[cfg(feature = "wee_alloc")]
#[global_allocator]
static ALLOC: wee_alloc::WeeAlloc = wee_alloc::WeeAlloc::INIT;

// Import the main module
mod api;
mod components;
mod models;
mod ui;
mod utils;

// Re-export the main function for WASM
#[wasm_bindgen]
pub fn start_app() -> Result<(), JsValue> {
    // Set up panic hook for better error messages
    console_error_panic_hook::set_once();
    
    // Initialize tracing for WASM
    tracing_wasm::set_as_global_default();
    
    // Start the eframe app
    let web_options = eframe::WebOptions::default();
    
    wasm_bindgen_futures::spawn_local(async {
        eframe::WebRunner::new()
            .start(
                "portfolio_app_canvas", // The HTML canvas ID
                web_options,
                Box::new(|cc| Box::new(ui::app::PortfolioApp::new(cc))),
            )
            .await
            .expect("Failed to start eframe app");
    });
    
    Ok(())
}