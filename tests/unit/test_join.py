from datetime import UTC, datetime, timedelta

import pytest

from libs.core.economics import MisalignedSeriesError, PriceVolumeSeries
from libs.core.series import GenerationSeries, PriceSeries

START = datetime(2025, 5, 31, 22, tzinfo=UTC)


def _hours(offset: int, count: int) -> tuple[datetime, ...]:
    return tuple(START + timedelta(hours=offset + h) for h in range(count))


def test_join_matching_hours_pairs_price_and_volume():
    prices = PriceSeries(timestamps=_hours(0, 3), prices=(35.0, 30.0, 50.0))
    generation = GenerationSeries(timestamps=_hours(0, 3), volumes=(15.0, 20.0, 8.0))

    series = PriceVolumeSeries.from_series(prices, generation)

    assert tuple(series.timestamps) == _hours(0, 3)
    assert tuple(series.price) == (35.0, 30.0, 50.0)
    assert tuple(series.volume) == (15.0, 20.0, 8.0)


def test_join_equal_length_but_shifted_raises():
    # The only case that catches a positional join: same length, different hours.
    prices = PriceSeries(timestamps=_hours(0, 3), prices=(35.0, 30.0, 50.0))
    generation = GenerationSeries(timestamps=_hours(1, 3), volumes=(15.0, 20.0, 8.0))

    with pytest.raises(MisalignedSeriesError):
        PriceVolumeSeries.from_series(prices, generation)


def test_join_missing_hour_raises():
    prices = PriceSeries(timestamps=_hours(0, 3), prices=(35.0, 30.0, 50.0))
    generation = GenerationSeries(
        timestamps=(_hours(0, 3)[0], _hours(0, 3)[2]), volumes=(15.0, 8.0)
    )

    with pytest.raises(MisalignedSeriesError):
        PriceVolumeSeries.from_series(prices, generation)
