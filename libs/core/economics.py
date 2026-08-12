# Economics
from dataclasses import dataclass
from datetime import datetime

from collections.abc import (
    Sequence,
)  # accepts either a list or tuple from the adapter side without forcing a concrete container in the domain's contract.


@dataclass(frozen=True)
class PriceVolumeSeries:
    timestamps: Sequence[datetime]  # HourUTC, tz-aware — canonical per §2
    price: Sequence[float]
    volume: Sequence[float]

    def __post_init__(self) -> None:
        if not (len(self.timestamps) == len(self.price) == len(self.volume)):
            raise ValueError(
                f"timestamps, price, and volume must have equal length, got "
                f"{len(self.timestamps)}, {len(self.price)}, {len(self.volume)}"
            )


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
    revenue = sum(p * v for p, v in zip(series.price, series.volume, strict=True))
    return revenue / sum(series.volume)


def time_average_price(series: PriceVolumeSeries) -> float:
    return sum(series.price) / len(series.price)


def value_factor(series: PriceVolumeSeries) -> ValueFactorResult:
    capt_price = captured_price(series)
    mean_t_price = time_average_price(series)
    return ValueFactorResult(
        value_factor=capt_price / mean_t_price,
        captured_price=capt_price,
        time_average_price=mean_t_price,
    )
