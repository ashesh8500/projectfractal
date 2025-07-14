"""
Production-grade strategy implementations with proper error handling.
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler

from config import config
from exceptions import StrategyError, ValidationError

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """Base class for portfolio rebalancing strategies."""
    
    def __init__(self, name: str):
        self.name = name
        logger.info(f"Initialized strategy: {name}")
    
    @abstractmethod
    def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate new portfolio weights.
        
        Args:
            prices: Historical price data
            current_weights: Current portfolio weights
            
        Returns:
            Dict mapping symbols to new weights (0-1)
            
        Raises:
            StrategyError: If calculation fails
        """
        pass
    
    def _validate_inputs(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> None:
        """Validate strategy inputs."""
        if prices.empty:
            raise ValidationError("Price data is empty")
        
        if not current_weights:
            raise ValidationError("Current weights are empty")
        
        # Check if all symbols in weights have price data
        missing_symbols = set(current_weights.keys()) - set(prices.columns)
        if missing_symbols:
            raise ValidationError(f"Missing price data for symbols: {missing_symbols}")
        
        # Validate weights sum approximately to 1
        total_weight = sum(current_weights.values())
        if abs(total_weight - 1.0) > 0.1:
            logger.warning(f"Current weights sum to {total_weight:.4f}, not 1.0")
    
    @staticmethod
    def clip_and_normalize_weights(
        weights: Dict[str, float], 
        min_weight: float = None, 
        max_weight: float = None
    ) -> Dict[str, float]:
        """
        Clip weights to bounds and normalize to sum to 1.
        
        Args:
            weights: Raw weights
            min_weight: Minimum weight per asset
            max_weight: Maximum weight per asset
            
        Returns:
            Normalized weights
        """
        # Use more flexible constraints - allow strategies to express their preferences
        min_weight = min_weight or 0.01  # Reduced from 0.05 to allow more flexibility
        max_weight = max_weight or 0.80  # Increased from 0.4 to allow more concentration
        
        if min_weight >= max_weight:
            raise ValidationError(f"min_weight ({min_weight}) must be less than max_weight ({max_weight})")
        
        weights_series = pd.Series(weights)
        
        # Remove any zero or negative weights
        weights_series = weights_series[weights_series > 0]
        
        if weights_series.empty:
            raise StrategyError("All weights are zero or negative")
        
        # First normalize to sum to 1
        normalized = weights_series / weights_series.sum()
        
        # Apply minimum weight constraint
        normalized = normalized.clip(lower=min_weight)
        
        # Apply maximum weight constraint with redistribution
        max_iterations = 10
        for iteration in range(max_iterations):
            # Normalize after min constraint
            normalized = normalized / normalized.sum()
            
            # Check if any weight exceeds max_weight
            over_max = normalized > max_weight
            if not over_max.any():
                break
            
            # Set over-max weights to max_weight
            normalized[over_max] = max_weight
            
            # Redistribute excess among remaining weights
            excess = 1.0 - normalized.sum()
            under_max = ~over_max
            
            if under_max.sum() == 0:
                # All weights are at max, distribute equally
                normalized = pd.Series(max_weight, index=normalized.index)
                normalized = normalized / normalized.sum()
                break
            
            # Add excess proportionally to under-max weights
            if normalized[under_max].sum() > 0:
                adjustment = excess * (normalized[under_max] / normalized[under_max].sum())
                normalized[under_max] += adjustment
            else:
                # Equal distribution if all under-max weights are zero
                normalized[under_max] = excess / under_max.sum()
            
            # Clip again to maintain bounds
            normalized = normalized.clip(min_weight, max_weight)
        
        # Final normalization
        final_sum = normalized.sum()
        if abs(final_sum - 1.0) > 0.001:
            logger.debug(f"Final weights sum to {final_sum:.4f}, normalizing")
            normalized = normalized / final_sum
        
        return normalized.to_dict()


class BollingerStrategy(BaseStrategy):
    """Bollinger Bands based rebalancing strategy."""
    
    def __init__(self, window: int = None, std_dev: float = None):
        super().__init__("Bollinger Bands")
        self.window = window or config.strategy.bollinger_window
        self.std_dev = std_dev or config.strategy.bollinger_std
        
        logger.info(f"Bollinger strategy: window={self.window}, std_dev={self.std_dev}")
    
    def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate weights based on Bollinger Band signals."""
        try:
            self._validate_inputs(prices, current_weights)
            
            if len(prices) < self.window:
                logger.warning(f"Insufficient data for Bollinger Bands (need {self.window}, have {len(prices)})")
                return current_weights
            
            symbols = list(current_weights.keys())
            scores = {}
            
            for symbol in symbols:
                if symbol not in prices.columns:
                    logger.warning(f"No price data for {symbol}, keeping current weight")
                    scores[symbol] = 0.0
                    continue
                
                price_series = prices[symbol].dropna()
                if len(price_series) < self.window:
                    logger.warning(f"Insufficient data for {symbol}")
                    scores[symbol] = 0.0
                    continue
                
                # Calculate Bollinger Bands
                rolling_mean = price_series.rolling(window=self.window).mean()
                rolling_std = price_series.rolling(window=self.window).std()
                
                upper_band = rolling_mean + (self.std_dev * rolling_std)
                lower_band = rolling_mean - (self.std_dev * rolling_std)
                
                # Get latest values
                current_price = price_series.iloc[-1]
                latest_upper = upper_band.iloc[-1]
                latest_lower = lower_band.iloc[-1]
                latest_mean = rolling_mean.iloc[-1]
                
                # Calculate position within bands (-1 to 1)
                band_width = latest_upper - latest_lower
                if band_width > 0:
                    position = (current_price - latest_mean) / (band_width / 2)
                    # Invert signal: buy when price is low (negative score = underweight)
                    scores[symbol] = -position
                else:
                    scores[symbol] = 0.0
                
                logger.debug(f"{symbol}: price={current_price:.2f}, position={position:.3f}, score={scores[symbol]:.3f}")
            
            # Convert scores to weights
            new_weights = self._scores_to_weights(scores, current_weights)
            
            # Apply constraints
            final_weights = self.clip_and_normalize_weights(new_weights)
            
            logger.info(f"Bollinger strategy generated new weights: {final_weights}")
            return final_weights
            
        except Exception as e:
            logger.error(f"Bollinger strategy failed: {e}")
            raise StrategyError(f"Bollinger strategy calculation failed: {e}") from e
    
    def _scores_to_weights(self, scores: Dict[str, float], current_weights: Dict[str, float]) -> Dict[str, float]:
        """Convert scores to portfolio weights."""
        # Use a more sophisticated approach to convert scores to weights
        
        # Calculate score statistics
        score_values = list(scores.values())
        if len(score_values) <= 1:
            return current_weights
        
        score_mean = np.mean(score_values)
        score_std = np.std(score_values)
        
        # If no variation in scores, return current weights
        if score_std < 1e-6:
            logger.debug("No variation in Bollinger scores, returning current weights")
            return current_weights
        
        # Convert scores to z-scores for standardization
        z_scores = {k: (v - score_mean) / score_std for k, v in scores.items()}
        
        # Apply sigmoid function to create more pronounced differences
        # Higher scores (undervalued) get higher weights
        sigmoid_scores = {k: 1 / (1 + np.exp(-2 * z)) for k, z in z_scores.items()}
        
        # Normalize sigmoid scores to create weights
        total_sigmoid = sum(sigmoid_scores.values())
        if total_sigmoid > 0:
            raw_weights = {k: v / total_sigmoid for k, v in sigmoid_scores.items()}
        else:
            raw_weights = {k: 1.0 / len(scores) for k in scores}
        
        # Blend with current weights for stability (80% new, 20% current)
        blended_weights = {}
        for symbol in current_weights:
            new_weight = 0.8 * raw_weights.get(symbol, 1.0/len(current_weights)) + 0.2 * current_weights[symbol]
            blended_weights[symbol] = new_weight
        
        logger.debug(f"Bollinger scores: {scores}")
        logger.debug(f"Z-scores: {z_scores}")
        logger.debug(f"Sigmoid scores: {sigmoid_scores}")
        logger.debug(f"Raw weights: {raw_weights}")
        logger.debug(f"Blended weights: {blended_weights}")
        
        return blended_weights


class MLStrategy(BaseStrategy):
    """Machine Learning based rebalancing strategy."""
    
    def __init__(self, lookback_days: int = None):
        super().__init__("ML Strategy")
        self.lookback_days = lookback_days or config.strategy.ml_lookback_days
        self.model = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        
        logger.info(f"ML strategy: lookback_days={self.lookback_days}")
    
    def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate weights using ML predictions."""
        try:
            self._validate_inputs(prices, current_weights)
            
            # Use available data if less than requested lookback, but require minimum 60 days
            min_required = min(self.lookback_days, 60)
            if len(prices) < min_required:
                logger.warning(f"Insufficient data for ML strategy (need {min_required}, have {len(prices)})")
                return current_weights
            
            effective_lookback = min(self.lookback_days, len(prices))
            
            symbols = list(current_weights.keys())
            predictions = {}
            
            for symbol in symbols:
                if symbol not in prices.columns:
                    logger.warning(f"No price data for {symbol}")
                    predictions[symbol] = 0.0
                    continue
                
                try:
                    prediction = self._predict_return(prices[symbol])
                    predictions[symbol] = prediction
                    logger.debug(f"{symbol}: predicted return = {prediction:.4f}")
                except Exception as e:
                    logger.warning(f"ML prediction failed for {symbol}: {e}")
                    predictions[symbol] = 0.0
            
            # Convert predictions to weights
            new_weights = self._predictions_to_weights(predictions, current_weights)
            
            # Apply constraints
            final_weights = self.clip_and_normalize_weights(new_weights)
            
            logger.info(f"ML strategy generated new weights: {final_weights}")
            return final_weights
            
        except Exception as e:
            logger.error(f"ML strategy failed: {e}")
            raise StrategyError(f"ML strategy calculation failed: {e}") from e
    
    def _predict_return(self, price_series: pd.Series) -> float:
        """Predict future return for a single asset."""
        price_series = price_series.dropna()
        
        if len(price_series) < 50:  # Minimum data for ML
            return 0.0
        
        # Create features
        returns = price_series.pct_change().dropna()
        
        # Technical indicators as features
        features = []
        for i in range(5, len(returns)):
            # Use last 5 returns as features
            feature_vector = returns.iloc[i-5:i].values
            features.append(feature_vector)
        
        if len(features) < 20:  # Need minimum samples
            return 0.0
        
        features = np.array(features)
        
        # Target: next period return
        targets = returns.iloc[5:].values
        
        # Use last 80% for training, predict on last observation
        train_size = int(len(features) * 0.8)
        
        X_train = features[:train_size]
        y_train = targets[:train_size]
        X_predict = features[-1:] # Last observation
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_predict_scaled = self.scaler.transform(X_predict)
        
        # Train and predict
        self.model.fit(X_train_scaled, y_train)
        prediction = self.model.predict(X_predict_scaled)[0]
        
        # Clip extreme predictions
        return np.clip(prediction, -0.1, 0.1)
    
    def _predictions_to_weights(self, predictions: Dict[str, float], current_weights: Dict[str, float]) -> Dict[str, float]:
        """Convert return predictions to portfolio weights."""
        pred_values = list(predictions.values())
        
        # Check if predictions have meaningful variation
        if len(pred_values) <= 1:
            return current_weights
        
        pred_std = np.std(pred_values)
        if pred_std < 1e-6:
            logger.debug("No variation in ML predictions, returning current weights")
            return current_weights
        
        # Normalize predictions to z-scores
        pred_mean = np.mean(pred_values)
        z_scores = {k: (v - pred_mean) / pred_std for k, v in predictions.items()}
        
        # Apply exponential weighting to amplify differences
        # Higher predictions get exponentially more weight
        exp_scores = {k: np.exp(2 * z) for k, z in z_scores.items()}
        
        # Normalize to create weights
        total_exp = sum(exp_scores.values())
        if total_exp > 0:
            raw_weights = {k: v / total_exp for k, v in exp_scores.items()}
        else:
            raw_weights = {k: 1.0 / len(predictions) for k in predictions}
        
        # Blend with current weights (70% new, 30% current)
        blended_weights = {}
        for symbol in current_weights:
            new_weight = 0.7 * raw_weights.get(symbol, 1.0/len(current_weights)) + 0.3 * current_weights[symbol]
            blended_weights[symbol] = new_weight
        
        logger.debug(f"ML predictions: {predictions}")
        logger.debug(f"Z-scores: {z_scores}")
        logger.debug(f"Exponential scores: {exp_scores}")
        logger.debug(f"Raw weights: {raw_weights}")
        logger.debug(f"Blended weights: {blended_weights}")
        
        return blended_weights


class MomentumStrategy(BaseStrategy):
    """Momentum-based rebalancing strategy for testing parameter sensitivity."""
    
    def __init__(self, lookback_period: int = None, momentum_threshold: float = None):
        super().__init__("Momentum Strategy")
        self.lookback_period = lookback_period or 20
        self.momentum_threshold = momentum_threshold or 0.02
        
        logger.info(f"Momentum strategy: lookback_period={self.lookback_period}, threshold={self.momentum_threshold}")
    
    def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate weights based on price momentum."""
        try:
            self._validate_inputs(prices, current_weights)
            
            if len(prices) < self.lookback_period:
                logger.warning(f"Insufficient data for Momentum strategy (need {self.lookback_period}, have {len(prices)})")
                return current_weights
            
            symbols = list(current_weights.keys())
            momentum_scores = {}
            
            for symbol in symbols:
                if symbol not in prices.columns:
                    logger.warning(f"No price data for {symbol}")
                    momentum_scores[symbol] = 0.0
                    continue
                
                price_series = prices[symbol].dropna()
                if len(price_series) < self.lookback_period:
                    momentum_scores[symbol] = 0.0
                    continue
                
                # Calculate momentum as percentage change over lookback period
                current_price = price_series.iloc[-1]
                past_price = price_series.iloc[-self.lookback_period]
                momentum = (current_price - past_price) / past_price
                
                # Apply threshold - only consider significant momentum
                if abs(momentum) > self.momentum_threshold:
                    momentum_scores[symbol] = momentum
                else:
                    momentum_scores[symbol] = 0.0
                
                logger.debug(f"{symbol}: momentum={momentum:.4f}, score={momentum_scores[symbol]:.4f}")
            
            # Convert momentum scores to weights
            new_weights = self._momentum_to_weights(momentum_scores, current_weights)
            
            # Apply constraints
            final_weights = self.clip_and_normalize_weights(new_weights)
            
            logger.info(f"Momentum strategy generated new weights: {final_weights}")
            return final_weights
            
        except Exception as e:
            logger.error(f"Momentum strategy failed: {e}")
            raise StrategyError(f"Momentum strategy calculation failed: {e}") from e
    
    def _momentum_to_weights(self, momentum_scores: Dict[str, float], current_weights: Dict[str, float]) -> Dict[str, float]:
        """Convert momentum scores to portfolio weights."""
        momentum_values = list(momentum_scores.values())
        
        # Check if momentum scores have meaningful variation
        if len(momentum_values) <= 1:
            return current_weights
        
        momentum_std = np.std(momentum_values)
        if momentum_std < 1e-6:
            logger.debug("No variation in momentum scores, returning current weights")
            return current_weights
        
        # Normalize momentum scores to z-scores
        momentum_mean = np.mean(momentum_values)
        z_scores = {k: (v - momentum_mean) / momentum_std for k, v in momentum_scores.items()}
        
        # Apply tanh transformation to create bounded weights
        # Higher momentum gets higher weight but with diminishing returns
        tanh_scores = {k: np.tanh(z) for k, z in z_scores.items()}
        
        # Shift to positive range and normalize
        min_tanh = min(tanh_scores.values())
        shifted_scores = {k: v - min_tanh + 0.1 for k, v in tanh_scores.items()}
        
        total_shifted = sum(shifted_scores.values())
        if total_shifted > 0:
            raw_weights = {k: v / total_shifted for k, v in shifted_scores.items()}
        else:
            raw_weights = {k: 1.0 / len(momentum_scores) for k in momentum_scores}
        
        # Blend with current weights (75% new, 25% current)
        blended_weights = {}
        for symbol in current_weights:
            new_weight = 0.75 * raw_weights.get(symbol, 1.0/len(current_weights)) + 0.25 * current_weights[symbol]
            blended_weights[symbol] = new_weight
        
        logger.debug(f"Momentum scores: {momentum_scores}")
        logger.debug(f"Z-scores: {z_scores}")
        logger.debug(f"Tanh scores: {tanh_scores}")
        logger.debug(f"Raw weights: {raw_weights}")
        logger.debug(f"Blended weights: {blended_weights}")
        
        return blended_weights


# Strategy registry
STRATEGIES = {
    'bollinger': BollingerStrategy,
    'ml': MLStrategy,
    'momentum': MomentumStrategy
}


def get_strategy(strategy_name: str, **kwargs) -> BaseStrategy:
    """
    Get strategy instance by name.
    
    Args:
        strategy_name: Name of the strategy
        **kwargs: Strategy-specific parameters
        
    Returns:
        Strategy instance
        
    Raises:
        ValidationError: If strategy name is invalid
    """
    if strategy_name not in STRATEGIES:
        raise ValidationError(f"Unknown strategy: {strategy_name}. Available: {list(STRATEGIES.keys())}")
    
    return STRATEGIES[strategy_name](**kwargs)