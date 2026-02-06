from dataclasses import dataclass
from typing import Optional
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt

@dataclass
class VolatilityDragConfig:
    ticker: str
    leverage_k: float = 1.0
    lookback_window: int = 10
    risk_free_rate: float = 0.0

class StructuralDecayMonitor:
    """
    Calculates a ratio of expected trend to expected drag (Trend / VolatilityCost) 
    to determine if holding a levered ETF (in this case, NVDD) is favourable
    given market implied volatility (from options_chain.py)
    """
    def __init__(self, config: VolatilityDragConfig):
        self.config = config
        self.data: Optional[pd.DataFrame] = None

    def load_simulated_returns(self, simulated_log_returns: np.ndarray):
        """
        Store full simulation matrix (paths x days)
        """
        self.sim_paths = simulated_log_returns

    def compute_structural_greeks(self):
        """
        Compute decay metrics per simulated path, then average.
        """
        if not hasattr(self, "sim_paths"):
            raise RuntimeError("No simulated paths loaded.")

        k = self.config.leverage_k
        w = self.config.lookback_window

        trends = []
        drags = []
        effs = []

        for path in self.sim_paths:
            if len(path) < w:
                continue

            window = path[-w:]
            trend = abs(window.sum())
            var_sum = (window**2).sum()
            drag = (k**2 / 2) * var_sum
            eff = trend / (drag + 1e-8)

            trends.append(trend)
            drags.append(drag)
            effs.append(eff)

        return {
            "avg_trend": np.mean(trends),
            "avg_drag": np.mean(drags),
            "avg_efficiency": np.mean(effs)
        }

    def run_diagnosis(self):
        metrics = self.compute_structural_greeks()

        print(f"--- [ {self.config.ticker} FORWARD STRUCTURAL DIAGNOSTIC ] ---")
        print(f"Leverage Factor  : {self.config.leverage_k}x")
        print(f"Lookback Window  : {self.config.lookback_window} days")
        print(f"Expected Efficiency : {metrics['avg_efficiency']:.4f}")

        if metrics["avg_efficiency"] > 1.0:
            print(f"STATUS: FAVORABLE. Trend ({metrics['avg_trend']:.2%}) > Drag ({metrics['avg_drag']:.2%})")
        else:
            print(f"STATUS: DECAY REGIME. Volatility tax dominates.")

# Usage
if __name__ == "__main__":
    from price_distribution import simulate_log_return_paths

    # Inputs from your options model
    spot = 177.59
    forward_variance = 0.204605
    days_to_expiry = 12

    paths = simulate_log_return_paths(spot, forward_variance, days_to_expiry)

    config = VolatilityDragConfig(ticker="NVDD", leverage_k=1.0)
    monitor = StructuralDecayMonitor(config)
    monitor.load_simulated_returns(paths)
    monitor.run_diagnosis()