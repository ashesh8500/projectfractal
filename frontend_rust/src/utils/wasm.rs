#[cfg(target_arch = "wasm32")]
use wasm_bindgen::prelude::*;
use std::sync::Once;

#[cfg(target_arch = "wasm32")]
#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = console)]
    pub fn log(s: &str);
    
    #[wasm_bindgen(js_namespace = console, js_name = log)]
    pub fn log_obj(obj: &JsValue);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn error(s: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn warn(s: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn info(s: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn debug(s: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn time(label: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn time_end(label: &str);
    
    #[wasm_bindgen(js_namespace = console)]
    pub fn time_log(label: &str);
}

// Initialize panic hook only once
static INIT_PANIC_HOOK: Once = Once::new();

#[cfg(target_arch = "wasm32")]
pub fn init_wasm_hooks() {
    INIT_PANIC_HOOK.call_once(|| {
        console_error_panic_hook::set_once();
        log("WASM panic hook initialized");
    });
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

// Local storage utilities
#[cfg(target_arch = "wasm32")]
pub fn store_local_data(key: &str, value: &str) -> Result<(), JsValue> {
    let window = web_sys::window().ok_or_else(|| JsValue::from_str("No window found"))?;
    let storage = window.local_storage()?.ok_or_else(|| JsValue::from_str("No local storage found"))?;
    storage.set_item(key, value)?;
    Ok(())
}

#[cfg(target_arch = "wasm32")]
pub fn get_local_data(key: &str) -> Result<Option<String>, JsValue> {
    let window = web_sys::window().ok_or_else(|| JsValue::from_str("No window found"))?;
    let storage = window.local_storage()?.ok_or_else(|| JsValue::from_str("No local storage found"))?;
    Ok(storage.get_item(key)?)
}

#[cfg(target_arch = "wasm32")]
pub fn remove_local_data(key: &str) -> Result<(), JsValue> {
    let window = web_sys::window().ok_or_else(|| JsValue::from_str("No window found"))?;
    let storage = window.local_storage()?.ok_or_else(|| JsValue::from_str("No local storage found"))?;
    storage.remove_item(key)?;
    Ok(())
}

#[cfg(not(target_arch = "wasm32"))]
pub fn store_local_data(_key: &str, _value: &str) -> Result<(), String> {
    // For native, we could implement file-based storage here
    Ok(())
}

#[cfg(not(target_arch = "wasm32"))]
pub fn get_local_data(_key: &str) -> Result<Option<String>, String> {
    // For native, we could implement file-based storage here
    Ok(None)
}

#[cfg(not(target_arch = "wasm32"))]
pub fn remove_local_data(_key: &str) -> Result<(), String> {
    // For native, we could implement file-based storage here
    Ok(())
}

// Fetch API wrapper for WASM
#[cfg(target_arch = "wasm32")]
pub async fn fetch_json<T>(url: &str) -> Result<T, JsValue> 
where 
    T: serde::de::DeserializeOwned,
{
    use wasm_bindgen::JsCast;
    use wasm_bindgen_futures::JsFuture;
    use web_sys::{Request, RequestInit, RequestMode, Response};

    let mut opts = RequestInit::new();
    opts.method("GET");
    opts.mode(RequestMode::Cors);

    let request = Request::new_with_str_and_init(url, &opts)?;
    request.headers().set("Accept", "application/json")?;

    let window = web_sys::window().ok_or_else(|| JsValue::from_str("No window found"))?;
    let resp_value = JsFuture::from(window.fetch_with_request(&request)).await?;
    let resp: Response = resp_value.dyn_into().unwrap();

    if !resp.ok() {
        return Err(JsValue::from_str(&format!(
            "HTTP error: {} {}",
            resp.status(),
            resp.status_text()
        )));
    }

    let json = JsFuture::from(resp.json()?).await?;
    let result: T = json.into_serde().map_err(|e| {
        JsValue::from_str(&format!("JSON parse error: {}", e))
    })?;

    Ok(result)
}

// For native, we would use reqwest or another HTTP client
#[cfg(not(target_arch = "wasm32"))]
pub async fn fetch_json<T>(_url: &str) -> Result<T, String> 
where 
    T: serde::de::DeserializeOwned,
{
    Err("fetch_json not implemented for native target".to_string())
}