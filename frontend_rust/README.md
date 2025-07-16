# Portfolio Optimizer Frontend

This is the Rust-based frontend for the Portfolio Optimizer application, built with egui and WebAssembly (WASM) support for deployment on Google Cloud Platform.

## Features

- **Cross-platform**: Runs natively on desktop and in browsers via WebAssembly
- **Responsive UI**: Adapts to different screen sizes and devices
- **Professional Financial Terminal**: Industry-standard features for portfolio analysis
- **Real-time Data**: Connects to the backend for real-time portfolio data
- **Advanced Visualization**: Interactive charts and graphs for portfolio analysis

## Architecture

The frontend is built with a modular architecture:

- **API Module**: Handles communication with the backend server
- **Models Module**: Contains data structures and state management
- **UI Module**: Contains all UI-related code
- **Components Module**: Contains reusable UI components
- **Utils Module**: Contains utility functions

## Building and Running

### Prerequisites

- Rust toolchain (install via [rustup](https://rustup.rs/))
- wasm32-unknown-unknown target (`rustup target add wasm32-unknown-unknown`)
- wasm-bindgen-cli (`cargo install wasm-bindgen-cli`)
- For optimization: binaryen (`apt-get install binaryen` or `brew install binaryen`)

### Native Build

```bash
# Build and run the native application
cargo run --release
```

### WASM Build

```bash
# Build the WASM version
./build_wasm.sh

# The output will be in the ./dist directory
```

### Deployment to GCP

```bash
# Deploy to Google Cloud Platform
./deploy_to_gcp.sh
```

## Development

### Project Structure

```
frontend_rust/
├── src/
│   ├── api/                  # API communication layer
│   │   ├── client.rs         # gRPC client implementation
│   │   └── mod.rs
│   ├── components/           # Reusable UI components
│   │   ├── manager.rs        # Component management system
│   │   ├── mod.rs
│   │   └── ...               # Individual components
│   ├── models/               # Data models and state
│   │   ├── app_state.rs      # Application state
│   │   ├── messages.rs       # Message types for async communication
│   │   ├── performance.rs    # Performance metrics models
│   │   └── mod.rs
│   ├── ui/                   # UI implementation
│   │   ├── app.rs            # Main application UI
│   │   ├── portfolio.rs      # Portfolio management UI
│   │   ├── strategy.rs       # Strategy analysis UI
│   │   ├── charts.rs         # Chart rendering
│   │   ├── settings.rs       # Settings UI
│   │   └── mod.rs
│   ├── utils/                # Utility functions
│   │   ├── wasm.rs           # WASM-specific utilities
│   │   └── mod.rs
│   ├── lib.rs                # WASM entry point
│   └── main.rs               # Native entry point
├── build.rs                  # Build script for proto compilation
├── Cargo.toml                # Project dependencies
├── index.html                # HTML entry point for WASM
├── build_wasm.sh             # Script to build WASM version
└── deploy_to_gcp.sh          # Script to deploy to GCP
```

### Adding New Features

When adding new features:

1. Determine which module the feature belongs to
2. Create or modify the appropriate files
3. Update the main application state in `models/app_state.rs` if needed
4. Add UI components in the `ui` module
5. Add any necessary API calls in the `api` module
6. Ensure cross-platform compatibility with appropriate `#[cfg]` attributes

## WASM Compatibility

The application is designed to work on both native platforms and as a WebAssembly (WASM) application:

- Platform-specific code is isolated using `#[cfg(target_arch = "wasm32")]` attributes
- The `api` module handles different gRPC client implementations for native and WASM targets
- Async operations are handled differently based on the platform (tokio Runtime for native, wasm_bindgen_futures for WASM)

## Deployment

The application can be deployed to Google Cloud Platform using the provided scripts:

1. `build_wasm.sh`: Builds the WASM version of the application
2. `deploy_to_gcp.sh`: Deploys the built application to Google Cloud Storage and sets up a Load Balancer

## Configuration

The application can be configured at deployment time by modifying the `config.js` file in the `dist` directory. This file contains settings for:

- Backend API URL
- Feature flags
- Default theme
- Demo mode settings

## License

This project is licensed under the MIT License - see the LICENSE file for details.