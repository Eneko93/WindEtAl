from datetime import UTC, datetime, timedelta

import pytest

from libs.core.economics import PriceVolumeSeries, value_factor


def test_value_factor_matches_expected_ratio():
    price = (25, 40, 42, 46, 48, 50, 30, 35, 32, 28)
    wind = (23, 16, 15, 13, 11, 21, 18, 17, 17.5, 18.5)
    start = datetime(2025, 6, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(hours=h) for h in range(len(price)))

    series = PriceVolumeSeries(timestamps=timestamps, price=price, volume=wind)

    result = value_factor(series)

    assert result.value_factor == pytest.approx(0.97528, rel=1e-5)


def test_value_factor_simple_int():
    price = (35, 30, 50)
    wind = (15, 20, 8)
    start = datetime(2025, 6, 1, tzinfo=UTC)
    timestamps = tuple(start + timedelta(hours=h) for h in range(len(price)))

    series = PriceVolumeSeries(timestamps=timestamps, price=price, volume=wind)
    result = value_factor(series)

    assert result.value_factor == pytest.approx(0.925177, rel=1e-5)
