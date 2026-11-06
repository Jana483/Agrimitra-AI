"""Optional SageMaker entry point for mandi price bands.

The API uses this same function for a local forecast. Deploy it as a
SageMaker scikit-learn script only after a trained artifact exists.
"""

import random


def forecast_band(last_price, days=14, trend_bias=0.4):
    """Project a mid price and a widening low/high band."""
    mid = []
    upper = []
    lower = []
    value = last_price
    for day in range(days):
        value = round(value * (1 + (trend_bias + random.uniform(-0.8, 1.2)) / 100))
        band = value * (0.02 + (day * 0.003))
        mid.append(value)
        upper.append(round(value + band))
        lower.append(round(value - band))
    return {"prices": mid, "upper_bound": upper, "lower_bound": lower}
