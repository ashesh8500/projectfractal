from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict
from sklearn.ensemble import GradientBoostingRegressor

class BaseStrategy(ABC):
    """Base class for strategies. Subclasses implement calculate_new_weights."""
    
    @abstractmethod
    def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
        pass

    @staticmethod
    def clip_weights(weights: Dict[str, float], min_weight: float = 0.05, max_weight: float = 0.4) -> Dict[str, float]:
        weights_series = pd.Series(weights)
        
        # First clip to bounds
        clipped = weights_series.clip(min_weight, max_weight)
        
        # Normalize so they sum to 1
        normalized = clipped / clipped.sum()
        
        # If normalization caused any weight to exceed max_weight, iteratively adjust
        while normalized.max() > max_weight:
            # Set any weights above max to max
            over_max = normalized > max_weight
            normalized[over_max] = max_weight
            
            # Redistribute the excess among remaining weights
            excess = 1.0 - normalized.sum()
            under_max = ~over_max
            if under_max.sum() > 0:
                adjustment = excess / under_max.sum()
                normalized[under_max] += adjustment
                # Clip again to prevent going over max
                normalized = normalized.clip(min_weight, max_weight)
                normalized = normalized / normalized.sum()  # Renormalize
            else:
                break
                
        return normalized.to_dict()

class BollingerStrategy(BaseStrategy):
    """Bollinger Bands based rebalancing."""
    
    def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
        adjustment_factor = 0.2
        symbols = list(current_weights.keys())
        scores = {}
        window = 20
        std_multiplier = 2
        price_df = prices[symbols].iloc[-window*2:]  # Enough data
        
        for ticker in symbols:
            series = price_df[ticker]
            if len(series) < window:
                scores[ticker] = 0.5
                continue
            sma = series.rolling(window=window).mean().iloc[-1]
            std = series.rolling(window=window).std().iloc[-1]
            lower = sma - std_multiplier * std
            upper = sma + std_multiplier * std
            current = series.iloc[-1]
            bw = upper - lower
            if bw == 0:
                pb = 0.5
            else:
                pb = (current - lower) / bw
            scores[ticker] = pb
        
        scores_series = pd.Series(scores)
        target_weights = (scores_series / scores_series.sum()).to_dict()
        blended = {k: (1 - adjustment_factor) * current_weights.get(k, 0) + adjustment_factor * target_weights.get(k, 0) for k in symbols}
        return self.clip_weights(blended)

class MLStrategy(BaseStrategy):
    """Gradient Boosting based prediction."""
    
    def calculate_new_weights(self, prices: pd.DataFrame, current_weights: Dict[str, float]) -> Dict[str, float]:
        symbols = list(current_weights.keys())
        features = self._prepare_features(prices[symbols])
        returns = prices[symbols].pct_change().shift(-1).dropna()
        
        common_index = features.index.intersection(returns.index)
        if len(common_index) < 10:
            return current_weights  # Fallback
        
        features = features.loc[common_index]
        returns = returns.loc[common_index]
        
        X_train = features.iloc[:-1]
        y_train = returns.iloc[:-1]
        X_predict = features.iloc[-1:].values
        
        model = GradientBoostingRegressor(n_estimators=100, learning_rate=0.1, max_depth=3)
        model.fit(X_train, y_train.mean(axis=1))  # Average returns for simplicity; adjust if multi-output
        
        predicted = model.predict(X_predict)[0]
        expected_returns = {s: predicted for s in symbols}  # Simplify; can improve
        
        # Dummy cov for now; use real
        cov_matrix = returns.cov()
        
        # Simple allocation based on predicted
        weights_series = pd.Series(expected_returns)
        weights_series = weights_series / weights_series.sum()
        return self.clip_weights(weights_series.to_dict())

    def _prepare_features(self, prices: pd.DataFrame) -> pd.DataFrame:
        features = pd.DataFrame(index=prices.index)
        for symbol in prices.columns:
            price = prices[symbol]
            returns = price.pct_change()
            features[f'{symbol}_returns'] = returns
            features[f'{symbol}_vol_5'] = returns.rolling(5).std()
            features[f'{symbol}_ma_5'] = price.rolling(5).mean()
            # Add more as in original
        return features.dropna()

# Add more predefined strategies as needed
