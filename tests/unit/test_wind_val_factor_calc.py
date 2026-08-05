import pandas as pd
import pytest

from libs.core.economics import PriceVolumeSeries, value_factor


def test_value_factor_matches_expected_ratio():
    price = pd.Series([25, 40, 42, 46, 48, 50, 30, 35, 32, 28])
    wind = pd.Series([23, 16, 15, 13, 11, 21, 18, 17, 17.5, 18.5])
    series = PriceVolumeSeries(price=price, volume=wind)

    result = value_factor(series)

    assert result.value_factor == pytest.approx(0.97528, rel=1e-5)
