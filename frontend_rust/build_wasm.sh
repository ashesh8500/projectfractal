#!/bin/bash
set -e

# Build the WASM version of the Portfolio Optimizer frontend
echo "Building WASM version of Portfolio Optimizer..."

# Check if wasm32 target is installed
if ! rustup target list | grep -q "wasm32-unknown-unknown"; then
    echo "Adding wasm32-unknown-unknown target..."
    rustup target add wasm32-unknown-unknown
fi

# Check if wasm-bindgen-cli is installed
if ! command -v wasm-bindgen &> /dev/null; then
    echo "Installing wasm-bindgen-cli..."
    cargo install wasm-bindgen-cli
fi

# Create a temporary Cargo.toml for WASM build
echo "Creating WASM-compatible Cargo.toml..."
cp Cargo.toml Cargo.toml.backup

# Create a WASM-specific Cargo.toml
cat > Cargo.toml.wasm << EOL
[package]
name = "portfolio_frontend"
version = "0.1.0"
edition = "2021"

[lib]
crate-type = ["cdylib"]

[dependencies]
egui = "0.27.2"
eframe = { version = "0.27.2", features = ["default_fonts", "persistence"] }
egui_plot = "0.27.2"
prost = "0.10.4"
serde = { version = "1.0", features = ["derive"] }
lazy_static = "1.4"
futures = "0.3"
futures-util = "0.3"
rand = "0.8"
chrono = { version = "0.4", features = ["serde"] }
# No tokio for WASM - using web APIs instead
tonic = { version = "0.7.2", features = ["codegen"] }
tonic-web-wasm-client = "0.7.1"
wasm-bindgen = "0.2"
wasm-bindgen-futures = "0.4"
console_error_panic_hook = "0.1.7"
tracing-wasm = "0.2.1"
web-sys = { version = "0.3", features = [
    "Document",
    "Window",
    "Element",
    "HtmlCanvasElement",
    "Performance",
    "PerformanceTiming",
    "console"
]}

[build-dependencies]
tonic-build = "0.7.2"
EOL

# Replace the original Cargo.toml with the WASM-specific one
mv Cargo.toml.wasm Cargo.toml

# Create dist directory if it doesn't exist
mkdir -p dist

# Build the WASM package
echo "Building WASM package..."
cargo build --target wasm32-unknown-unknown --release

# Generate JavaScript bindings
echo "Generating JavaScript bindings..."
wasm-bindgen --target web --out-dir ./dist --no-typescript ./target/wasm32-unknown-unknown/release/portfolio_frontend.wasm

# Copy the HTML file
echo "Copying HTML file..."
cp index.html ./dist/

# Restore the original Cargo.toml
echo "Restoring original Cargo.toml..."
mv Cargo.toml.backup Cargo.toml

echo "WASM build completed successfully! Output is in the ./dist directory."
echo "To deploy to GCP Cloud Storage:"
echo "gcloud storage cp -r dist/* gs://<your-bucket-name>"