#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    pub fn log(s: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn error(s: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn warn(s: &str);
}

#[cfg(target_arch = "wasm32")]
#[macro_export]
macro_rules! console_log {
    ($($t:tt)*) => (crate::utils::wasm::log(&format!($($t)*)))
}

#[cfg(not(target_arch = "wasm32"))]
#[macro_export]
macro_rules! console_log {
    ($($t:tt)*) => (println!($($t)*))
}

#[cfg(target_arch = "wasm32")]
#[macro_export]
macro_rules! console_error {
    ($($t:tt)*) => (crate::utils::wasm::error(&format!($($t)*)))
}

#[cfg(not(target_arch = "wasm32"))]
#[macro_export]
macro_rules! console_error {
    ($($t:tt)*) => (eprintln!("ERROR: {}", format!($($t)*)))
}

#[cfg(target_arch = "wasm32")]
#[macro_export]
macro_rules! console_warn {
    ($($t:tt)*) => (crate::utils::wasm::warn(&format!($($t)*)))
}

#[cfg(not(target_arch = "wasm32"))]
#[macro_export]
macro_rules! console_warn {
    ($($t:tt)*) => (eprintln!("WARNING: {}", format!($($t)*)))
}

// Get the current performance timestamp
#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
pub fn get_performance_now() -> f64 {
    let window = web_sys::window().expect("should have a window in this context");
    let performance = window
        .performance()
        .expect("performance should be available");
    performance.now()
}

#[cfg(not(target_arch = "wasm32"))]
pub fn get_performance_now() -> f64 {
    use std::time::{SystemTime, UNIX_EPOCH};
    let start = SystemTime::now();
    let since_the_epoch = start
        .duration_since(UNIX_EPOCH)
        .expect("Time went backwards");
    since_the_epoch.as_secs_f64() * 1000.0
}

// Helper function to get URL parameters
#[cfg(target_arch = "wasm32")]
pub fn get_url_param(name: &str) -> Option<String> {
    let window = web_sys::window()?;
    let location = window.location();
    let search = location.search().ok()?;
    
    if search.is_empty() {
        return None;
    }
    
    // Remove the leading '?'
    let search = &search[1..];
    
    // Split by '&' to get key-value pairs
    for pair in search.split('&') {
        let mut parts = pair.split('=');
        if let Some(key) = parts.next() {
            if key == name {
                return parts.next().map(|value| {
                    // URL decode the value
                    js_sys::decode_uri_component(value)
                        .ok()
                        .and_then(|s| s.as_string())
                        .unwrap_or_else(|| value.to_string())
                });
            }
        }
    }
    
    None
}

#[cfg(not(target_arch = "wasm32"))]
pub fn get_url_param(_name: &str) -> Option<String> {
    None
}