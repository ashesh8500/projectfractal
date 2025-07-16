use std::collections::HashMap;
use chrono::{Utc, Duration, TimeZone};
use rand::Rng;

#[derive(Debug, Clone)]
pub struct PerformanceMetrics {
    pub total_return: f64,
    pub annualized_return: f64,
    pub volatility: f64,
    pub sharpe_ratio: f64,
    pub max_drawdown: f64,
    pub calmar_ratio: f64,
    pub sortino_ratio: f64,
    pub win_rate: f64,
    pub profit_factor: f64,
    pub dates: Vec<String>,
    pub values: Vec<f64>,
    pub benchmark_values: Vec<f64>,
}

impl Default for PerformanceMetrics {
    fn default() -> Self {
        Self {
            total_return: 0.0,
            annualized_return: 0.0,
            volatility: 0.0,
            sharpe_ratio: 0.0,
            max_drawdown: 0.0,
            calmar_ratio: 0.0,
            sortino_ratio: 0.0,
            win_rate: 0.0,
            profit_factor: 0.0,
            dates: Vec::new(),
            values: Vec::new(),
            benchmark_values: Vec::new(),
        }
    }
}

#[derive(Debug, Clone)]
pub struct StrategyAnalysis {
    pub portfolio_name: String,
    pub strategy_name: String,
    pub current_weights: HashMap<String, f64>,
    pub new_weights: HashMap<String, f64>,
    pub changes: HashMap<String, f64>,
    pub expected_return: f64,
    pub risk_score: f64,
    pub sharpe_ratio: f64,
    pub is_mock_data: bool,
    pub performance_metrics: PerformanceMetrics,
}

impl PerformanceMetrics {
    pub fn generate(period: &str, num_points: usize) -> Self {
        let end_date = Utc::now();
        let start_date = match period {
            "1mo" => end_date - Duration::days(30),
            "3mo" => end_date - Duration::days(90),
            "6mo" => end_date - Duration::days(180),
            "1y" => end_date - Duration::days(365),
            "2y" => end_date - Duration::days(730),
            _ => end_date - Duration::days(365),
        };

        let total_days = (end_date - start_date).num_days() as usize;
        let step = if total_days > num_points { total_days / num_points } else { 1 };

        let mut dates = Vec::new();
        let mut values = Vec::new();
        let mut benchmark_values = Vec::new();
        let mut returns = Vec::new();
        let mut benchmark_returns = Vec::new();

        let mut portfolio_value = 100.0;
        let mut benchmark_value = 100.0;
        let mut max_value = 100.0;
        let mut max_drawdown = 0.0;

        for i in 0..num_points {
            let current_date = start_date + Duration::days((i * step) as i64);
            dates.push(current_date.format("%Y-%m-%d").to_string());

            // Generate realistic returns with some correlation and volatility
            let market_factor = 0.0003 + 0.001 * (i as f64 * 0.1).sin(); // Base market trend
            let mut rng = rand::thread_rng();
            let portfolio_return = market_factor + 0.0005 * (i as f64 * 0.15).cos() + (rng.gen::<f64>() - 0.5) * 0.02;
            let benchmark_return = market_factor * 0.8 + (rng.gen::<f64>() - 0.5) * 0.015;

            portfolio_value *= 1.0 + portfolio_return;
            benchmark_value *= 1.0 + benchmark_return;

            values.push(portfolio_value);
            benchmark_values.push(benchmark_value);
            returns.push(portfolio_return);
            benchmark_returns.push(benchmark_return);

            // Track drawdown
            if portfolio_value > max_value {
                max_value = portfolio_value;
            }
            let current_drawdown = (max_value - portfolio_value) / max_value;
            if current_drawdown > max_drawdown {
                max_drawdown = current_drawdown;
            }
        }

        let total_return = (portfolio_value - 100.0) / 100.0;
        let days_in_period = total_days as f64;
        let annualized_return = (portfolio_value / 100.0).powf(365.0 / days_in_period) - 1.0;
        let mean_return = returns.iter().sum::<f64>() / returns.len() as f64;
        let variance = returns.iter().map(|r| (r - mean_return).powi(2)).sum::<f64>() / returns.len() as f64;
        let volatility = variance.sqrt() * (252.0_f64).sqrt();
        let risk_free_rate = 0.02;
        let sharpe_ratio = if volatility > 0.0 { (annualized_return - risk_free_rate) / volatility } else { 0.0 };
        let calmar_ratio = if max_drawdown > 0.0 { annualized_return / max_drawdown } else { 0.0 };
        let downside_returns: Vec<f64> = returns.iter().filter(|&&r| r < 0.0).cloned().collect();
        let downside_deviation = if !downside_returns.is_empty() {
            let mean_downside = downside_returns.iter().sum::<f64>() / downside_returns.len() as f64;
            let downside_variance = downside_returns.iter().map(|r| (r - mean_downside).powi(2)).sum::<f64>() / downside_returns.len() as f64;
            downside_variance.sqrt() * (252.0_f64).sqrt()
        } else {
            volatility
        };
        let sortino_ratio = if downside_deviation > 0.0 { (annualized_return - risk_free_rate) / downside_deviation } else { 0.0 };
        let winning_trades = returns.iter().filter(|&&r| r > 0.0).count();
        let win_rate = winning_trades as f64 / returns.len() as f64;
        let gross_profit: f64 = returns.iter().filter(|&&r| r > 0.0).sum();
        let gross_loss: f64 = returns.iter().filter(|&&r| r < 0.0).sum::<f64>().abs();
        let profit_factor = if gross_loss > 0.0 { gross_profit / gross_loss } else { 0.0 };
        
        PerformanceMetrics {
            total_return,
            annualized_return,
            volatility,
            sharpe_ratio,
            max_drawdown,
            calmar_ratio,
            sortino_ratio,
            win_rate,
            profit_factor,
            dates,
            values,
            benchmark_values,
        }
    }
}