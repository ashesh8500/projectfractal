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
        min_weight = min_weight or config.strategy.min_weight
        max_weight = max_weight or config.strategy.max_weight
        
        if min_weight >= max_weight:
            raise ValidationError(f"min_weight ({min_weight}) must be less than max_weight ({max_weight})")
        
        weights_series = pd.Series(weights)
        
        # Remove any zero or negative weights
        weights_series = weights_series[weights_series > 0]
        
        if weights_series.empty:
            raise StrategyError("All weights are zero or negative")
        
        # Initial clipping
        clipped = weights_series.clip(min_weight, max_weight)
        
        # Iterative normalization to handle max_weight constraints
        max_iterations = 10
        for iteration in range(max_iterations):
            # Normalize
            normalized = clipped / clipped.sum()
            
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
            adjustment = excess * (normalized[under_max] / normalized[under_max].sum())
            normalized[under_max] += adjustment
            
            # Clip again
            clipped = normalized.clip(min_weight, max_weight)
        
        # Final validation
        final_sum = normalized.sum()
        if abs(final_sum - 1.0) > 0.01:
            logger.warning(f"Final weights sum to {final_sum:.4f}, normalizing")
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
        adjustment_factor = 0.2  # How aggressively to rebalance
        
        new_weights = {}
        for symbol in current_weights:
            current_weight = current_weights[symbol]
            score = scores.get(symbol, 0.0)
            
            # Adjust weight based on score
            adjustment = score * adjustment_factor * current_weight
            new_weight = current_weight + adjustment
            
            # Ensure positive weights
            new_weights[symbol] = max(new_weight, 0.01)
        
        return new_weights


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
            
            if len(prices) < self.lookback_days:
                logger.warning(f"Insufficient data for ML strategy (need {self.lookback_days}, have {len(prices)})")
                return current_weights
            
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
        # Rank predictions
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)
        
        new_weights = {}
        total_symbols = len(current_weights)
        
        for i, (symbol, prediction) in enumerate(sorted_predictions):
            # Higher predicted returns get higher weights
            rank_weight = (total_symbols - i) / total_symbols
            base_weight = 1.0 / total_symbols
            
            # Combine rank-based weight with prediction strength
            prediction_factor = 1.0 + np.tanh(prediction * 10)  # Scale and bound
            new_weight = base_weight * rank_weight * prediction_factor
            
            new_weights[symbol] = new_weight
        
        return new_weights


# Strategy registry
STRATEGIES = {
    'bollinger': BollingerStrategy,
    'ml': MLStrategy
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