# Economics
from collections.abc import (
    Sequence,
)  # accepts either a list or tuple from the adapter side without forcing a concrete container in the domain's contract.
from dataclasses import dataclass
from datetime import datetime

from libs.core.series import GenerationSeries, PriceSeries


class MisalignedSeriesError(ValueError):
    """Price and generation do not cover exactly the same HourUTC hours (ADR 0002)."""


def _index_by_hour(
    timestamps: Sequence[datetime], values: Sequence[float], name: str
) -> dict[datetime, float]:
    by_hour = dict(zip(timestamps, values, strict=True))
    if len(by_hour) != len(timestamps):
        raise MisalignedSeriesError(f"{name}: duplicate HourUTC values")
    return by_hour


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

    @classmethod
    def from_series(
        cls, prices: PriceSeries, generation: GenerationSeries
    ) -> "PriceVolumeSeries":
        """Join on HourUTC. Any hour present in only one series raises; nothing is filled or dropped."""
        price_by_hour = _index_by_hour(prices.timestamps, prices.prices, "prices")
        volume_by_hour = _index_by_hour(generation.timestamps, generation.volumes, "generation")
        if price_by_hour.keys() != volume_by_hour.keys():
            only_prices = sorted(price_by_hour.keys() - volume_by_hour.keys())
            only_generation = sorted(volume_by_hour.keys() - price_by_hour.keys())
            raise MisalignedSeriesError(
                f"HourUTC mismatch: {len(only_prices)} hour(s) only in prices "
                f"{only_prices[:3]}, {len(only_generation)} hour(s) only in generation "
                f"{only_generation[:3]}"
            )
        hours = sorted(price_by_hour)
        return cls(
            timestamps=tuple(hours),
            price=tuple(price_by_hour[h] for h in hours),
            volume=tuple(volume_by_hour[h] for h in hours),
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
