import numpy as np
import pandas as pd

def simulate_log_return_paths(spot: float, forward_variance: float, days_to_expiry: int, n_paths: int = 5000, seed: int = 42):
    """
    Takes spot + (annualized) implied variance + days_to_expiry and generates Monte Carlo daily log-return paths.
    Assumes risk-neutral drift ~ 0 for short horizons.
    """
    rng = np.random.default_rng(seed)

    T = days_to_expiry / 252.0                 # year fraction
    sigma_annual = np.sqrt(forward_variance)   # annualized vol
    sigma_daily = sigma_annual / np.sqrt(252)  # daily vol

    # Simulate daily log returns: r_t ~ N(0, sigma_daily^2)
    log_rets = rng.normal(loc=0.0, scale=sigma_daily, size=(n_paths, days_to_expiry))

    # Optional: convert to price paths
    # price_paths = spot * np.exp(np.cumsum(log_rets, axis=1))

    return log_rets  # shape: (n_paths, days_to_expiry)

# Example using your output:
spot = 177.59
forward_variance = 0.204605      # from "Forward Implied Variance"
days_to_expiry = 12              # example: Feb 4 -> Feb 20 ~ 12 trading days

paths = simulate_log_return_paths(spot, forward_variance, days_to_expiry)
print(paths.shape)  # (5000, 12)
print(paths[0])     # first simulated daily log-return path
