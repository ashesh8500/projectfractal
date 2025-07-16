# WebAssembly (WASM) Compatibility Guide

This guide provides instructions for making the Portfolio Optimizer frontend compatible with WebAssembly (WASM) for deployment on Google Cloud Platform.

## Key Challenges and Solutions

### 1. Tokio and Mio Compatibility

The main challenge with WASM compatibility is that the `tokio` runtime and `mio` library do not fully support the WASM target. The error message "This wasm target is unsupported by mio. If using Tokio, disable the net feature" indicates this limitation.

**Solution:**

1. Create a WASM-specific build configuration that:
   - Removes the `tokio` dependency completely or limits it to features that work with WASM
   - Uses browser APIs for async operations instead of tokio
   - Uses `wasm-bindgen-futures` for handling futures

2. Use conditional compilation to provide different implementations for native and WASM targets:

```rust
#[cfg(not(target_arch = "wasm32"))]
// Native-specific code using tokio

#[cfg(target_arch = "wasm32")]
// WASM-specific code using web APIs
```

### 2. gRPC Communication

For gRPC communication in WASM, we need to use `tonic-web-wasm-client` instead of the standard Tonic transport.

**Solution:**

```rust
#[cfg(not(target_arch = "wasm32"))]
pub async fn get_grpc_client() -> Result<PortfolioServiceClient<Channel>, tonic::transport::Error> {
    let channel = Channel::from_static("http://[::1]:50051").connect().await?;
    Ok(PortfolioServiceClient::new(channel))
}

#[cfg(target_arch = "wasm32")]
pub async fn get_grpc_client() -> Result<PortfolioServiceClient<Client>, tonic::transport::Error> {
    let client = Client::new("https://portfolio-backend-abcdefghij-uc.a.run.app");
    Ok(PortfolioServiceClient::new(client))
}
```

### 3. Build Process

We've created a custom build process that:

1. Creates a WASM-specific Cargo.toml with compatible dependencies
2. Builds the WASM package
3. Generates JavaScript bindings
4. Creates a distribution package ready for deployment

## Testing WASM Compatibility

To verify WASM compatibility, we've created a simple test project that:

1. Implements basic WASM functionality
2. Can be built and tested in a browser
3. Demonstrates the core concepts needed for the full application

The test project is located in `frontend_rust/wasm_test/` and can be built with:

```bash
cd frontend_rust/wasm_test
wasm-pack build --target web
```

You can test it by serving the directory with a web server and opening the index.html file.

## Next Steps for Full Application

To make the full application WASM-compatible:

1. Update the `api/client.rs` module to use `tonic-web-wasm-client` for WASM targets
2. Modify async code to use `wasm_bindgen_futures::spawn_local` instead of tokio runtime
3. Create a WASM-specific entry point in `lib.rs`
4. Use the custom build script to create a WASM-compatible build
5. Test the application thoroughly in a browser environment

## Deployment to GCP

Once the WASM build is working:

1. Build the WASM version using the build script
2. Deploy to Google Cloud Storage using the deploy script
3. Configure the Load Balancer to route traffic between the frontend and backend
4. Set up DNS and SSL for the application

## Resources

- [wasm-bindgen documentation](https://rustwasm.github.io/docs/wasm-bindgen/)
- [tonic-web-wasm-client](https://github.com/bxlentpartners/tonic-web-wasm-client)
- [Rust and WebAssembly](https://rustwasm.github.io/docs/book/)
- [egui_web example](https://github.com/emilk/egui/tree/master/examples/web_example)