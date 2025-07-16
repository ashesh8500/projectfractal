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

# Check if wasm-opt is installed
if ! command -v wasm-opt &> /dev/null; then
    echo "Installing binaryen for wasm-opt..."
    if [ "$(uname)" == "Darwin" ]; then
        # macOS
        brew install binaryen
    elif [ "$(uname)" == "Linux" ]; then
        # Linux
        apt-get update && apt-get install -y binaryen
    else
        echo "Warning: Could not install binaryen automatically. WASM optimization will be skipped."
    fi
fi

# Create dist directory if it doesn't exist
mkdir -p dist

# Build the WASM package using the target-specific configuration in Cargo.toml
echo "Building WASM package..."
cargo build --target wasm32-unknown-unknown --release

# Generate JavaScript bindings
echo "Generating JavaScript bindings..."
wasm-bindgen --target web --out-dir ./dist --no-typescript ./target/wasm32-unknown-unknown/release/portfolio_frontend.wasm

# Optimize the WASM binary if wasm-opt is available
if command -v wasm-opt &> /dev/null; then
    echo "Optimizing WASM binary..."
    wasm-opt -Oz -o ./dist/portfolio_frontend_bg.wasm.optimized ./dist/portfolio_frontend_bg.wasm
    mv ./dist/portfolio_frontend_bg.wasm.optimized ./dist/portfolio_frontend_bg.wasm
else
    echo "Skipping WASM optimization (wasm-opt not found)"
fi

# Copy the HTML file and other assets
echo "Copying HTML file and assets..."
cp index.html ./dist/

# Create a version.json file with build information
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

cat > ./dist/version.json << EOL
{
  "version": "$(grep '^version' Cargo.toml | cut -d '"' -f 2)",
  "buildDate": "${BUILD_DATE}",
  "gitCommit": "${GIT_COMMIT}",
  "gitBranch": "${GIT_BRANCH}"
}
EOL

# Create a simple configuration file that can be modified at deployment time
cat > ./dist/config.js << EOL
// Configuration for Portfolio Optimizer
window.PORTFOLIO_CONFIG = {
  // Backend API URL
  apiUrl: "https://portfolio-backend-abcdefghij-uc.a.run.app",
  
  // Feature flags
  features: {
    enableRiskAnalysis: true,
    enableBacktesting: true,
    enableAdvancedCharts: true,
    enableDataExport: true
  },
  
  // Default theme
  defaultTheme: "dark",
  
  // Demo mode settings
  demoMode: true,
  demoUserId: "demo_user"
};
EOL

echo "WASM build completed successfully! Output is in the ./dist directory."
echo "To deploy to GCP Cloud Storage:"
echo "gcloud storage cp -r dist/* gs://<your-bucket-name>"

# Print size information
WASM_SIZE=$(du -h ./dist/portfolio_frontend_bg.wasm | cut -f1)
JS_SIZE=$(du -h ./dist/portfolio_frontend.js | cut -f1)
echo "WASM size: ${WASM_SIZE}"
echo "JS size: ${JS_SIZE}"