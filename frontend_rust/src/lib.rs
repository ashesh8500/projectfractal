// Common modules for all targets
pub mod api;
pub mod components;
pub mod models;
pub mod ui;
pub mod utils;

// WASM-specific code
#[cfg(target_arch = "wasm32")]
mod wasm {
    use wasm_bindgen::prelude::*;
    use web_sys::console;
    
    // Re-export the main function for WASM
    #[wasm_bindgen]
    pub fn start_app() -> Result<(), JsValue> {
        // Set up panic hook for better error messages
        console_error_panic_hook::set_once();
        
        // Initialize tracing for WASM
        tracing_wasm::set_as_global_default();
        
        // Log startup information
        console::log_1(&"Portfolio Optimizer starting...".into());
        
        // Configure web options
        let mut web_options = eframe::WebOptions::default();
        web_options.renderer = eframe::Renderer::Wgpu;
        
        // Start the eframe app
        wasm_bindgen_futures::spawn_local(async {
            eframe::WebRunner::new()
                .start(
                    "portfolio_app_canvas", // The HTML canvas ID
                    web_options,
                    Box::new(|cc| Box::new(crate::ui::app::PortfolioApp::new(cc))),
                )
                .await
                .expect("Failed to start eframe app");
        });
        
        Ok(())
    }
    
    // Additional WASM-specific utilities
    #[wasm_bindgen]
    pub fn get_version() -> String {
        format!("Portfolio Optimizer v{}", env!("CARGO_PKG_VERSION"))
    }
    
    #[wasm_bindgen]
    pub fn set_theme(theme_name: &str) -> Result<(), JsValue> {
        // Store theme preference in local storage
        let window = web_sys::window().ok_or_else(|| JsValue::from_str("No window found"))?;
        let storage = window.local_storage()?.ok_or_else(|| JsValue::from_str("No local storage found"))?;
        storage.set_item("portfolio_theme", theme_name)?;
        Ok(())
    }
}

// Re-export WASM functions
#[cfg(target_arch = "wasm32")]
pub use wasm::*;