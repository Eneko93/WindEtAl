# Economics
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PriceVolumeSeries:
    price: pd.Series
    volume: pd.Series

    def __post_init__(self) -> None:
        if len(self.price) != len(self.volume):
            raise ValueError(
                f"price and volume must have equal length, got {len(self.price)} and {len(self.volume)}"
            )
        if not self.price.index.equals(self.volume.index):
            raise ValueError("price and volume must be aligned on HourUTC")


@dataclass(frozen=True)
class ValueFactorResult:
    value_factor: float
    captured_price: float
    time_average_price: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "value_factor", float(self.value_factor))
        object.__setattr__(self, "captured_price", float(self.captured_price))
        object.__setattr__(self, "time_average_price", float(self.time_average_price))


def captured_price(series: PriceVolumeSeries) -> float:
    return float(np.sum(series.price * series.volume) / np.sum(series.volume))


def time_average_price(series: PriceVolumeSeries) -> float:
    return float(np.mean(series.price))


def value_factor(series: PriceVolumeSeries) -> ValueFactorResult:
    capt_price = captured_price(series)
    mean_t_price = time_average_price(series)
    return ValueFactorResult(
        value_factor=capt_price / mean_t_price,
        captured_price=capt_price,
        time_average_price=mean_t_price,
    )
