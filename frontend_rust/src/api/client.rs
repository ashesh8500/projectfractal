use tonic::Request;

// Generated from proto
pub mod portfolio_pb {
    tonic::include_proto!("portfolio");
}
use portfolio_pb::portfolio_service_client::PortfolioServiceClient;
use portfolio_pb::*;

#[cfg(not(target_arch = "wasm32"))]
use tonic::transport::Channel;

#[cfg(target_arch = "wasm32")]
use tonic_web_wasm_client::Client;

// Helper function to get the appropriate gRPC client based on target architecture
#[cfg(not(target_arch = "wasm32"))]
pub async fn get_grpc_client() -> Result<PortfolioServiceClient<Channel>, tonic::transport::Error> {
    let channel = Channel::from_static("http://[::1]:50051").connect().await?;
    Ok(PortfolioServiceClient::new(channel))
}

#[cfg(target_arch = "wasm32")]
pub async fn get_grpc_client() -> Result<PortfolioServiceClient<Client>, tonic::transport::Error> {
    use crate::utils::wasm::get_url_param;
    
    // Try to get backend URL from URL parameters
    let backend_url = get_url_param("backend")
        .unwrap_or_else(|| {
            // Default backend URL for GCP deployment
            "https://portfolio-backend-abcdefghij-uc.a.run.app".to_string()
        });
    
    crate::console_log!("Connecting to backend at: {}", backend_url);
    let client = Client::new(&backend_url);
    Ok(PortfolioServiceClient::new(client))
}

// API functions for portfolio operations
pub async fn list_portfolios(user_id: &str) -> Result<Vec<String>, String> {
    match get_grpc_client().await {
        Ok(mut client) => {
            let request = Request::new(ListPortfoliosRequest {
                user_id: user_id.to_string(),
            });

            match client.list_portfolios(request).await {
                Ok(response) => Ok(response.into_inner().portfolio_names),
                Err(e) => Err(format!("Failed to load portfolios: {}", e)),
            }
        }
        Err(e) => Err(format!("Connection failed: {}", e)),
    }
}

pub async fn load_portfolio(user_id: &str, name: &str) -> Result<Portfolio, String> {
    match get_grpc_client().await {
        Ok(mut client) => {
            let request = Request::new(LoadPortfolioRequest {
                user_id: user_id.to_string(),
                name: name.to_string(),
            });

            match client.load_portfolio(request).await {
                Ok(response) => Ok(response.into_inner()),
                Err(e) => Err(format!("Failed to load portfolio: {}", e)),
            }
        }
        Err(e) => Err(format!("Connection failed: {}", e)),
    }
}

pub async fn create_portfolio(user_id: &str, name: &str, holdings: Holdings) -> Result<Portfolio, String> {
    match get_grpc_client().await {
        Ok(mut client) => {
            let request = Request::new(CreatePortfolioRequest {
                user_id: user_id.to_string(),
                name: name.to_string(),
                holdings: Some(holdings),
            });

            match client.create_portfolio(request).await {
                Ok(response) => Ok(response.into_inner()),
                Err(e) => Err(format!("Failed to create portfolio: {}", e)),
            }
        }
        Err(e) => Err(format!("Connection failed: {}", e)),
    }
}

pub async fn run_strategy(
    user_id: &str,
    portfolio_name: &str,
    strategy_name: &str,
    params: StrategyParams,
) -> Result<StrategyResult, String> {
    match get_grpc_client().await {
        Ok(mut client) => {
            let request = Request::new(RunStrategyRequest {
                user_id: user_id.to_string(),
                portfolio_name: portfolio_name.to_string(),
                strategy_name: strategy_name.to_string(),
                params: Some(params),
            });

            match client.run_strategy(request).await {
                Ok(response) => Ok(response.into_inner()),
                Err(e) => Err(format!("Failed to run strategy: {}", e)),
            }
        }
        Err(e) => Err(format!("Connection failed: {}", e)),
    }
}

pub async fn get_price_history(
    user_id: &str,
    portfolio_name: &str,
    period: &str,
) -> Result<PriceHistory, String> {
    match get_grpc_client().await {
        Ok(mut client) => {
            let request = Request::new(GetPriceHistoryRequest {
                user_id: user_id.to_string(),
                portfolio_name: portfolio_name.to_string(),
                period: period.to_string(),
            });

            match client.get_price_history(request).await {
                Ok(response) => Ok(response.into_inner()),
                Err(e) => Err(format!("Failed to get price history: {}", e)),
            }
        }
        Err(e) => Err(format!("Connection failed: {}", e)),
    }
}

pub async fn run_backtest(
    user_id: &str,
    portfolio_name: &str,
    strategy_name: &str,
    params: StrategyParams,
    rebalance_frequency: &str,
    start_value: f64,
    transaction_cost: f64,
) -> Result<BacktestResult, String> {
    match get_grpc_client().await {
        Ok(mut client) => {
            let request = Request::new(BacktestRequest {
                user_id: user_id.to_string(),
                portfolio_name: portfolio_name.to_string(),
                strategy_name: strategy_name.to_string(),
                params: Some(params),
                rebalance_frequency: rebalance_frequency.to_string(),
                start_value,
                transaction_cost,
            });

            match client.run_backtest(request).await {
                Ok(response) => Ok(response.into_inner()),
                Err(e) => Err(format!("Failed to run backtest: {}", e)),
            }
        }
        Err(e) => Err(format!("Connection failed: {}", e)),
    }
}