import json
from datetime import UTC, datetime
from pathlib import Path

from adapters.mapper import topriceseries, tovolumeseries

FIXTURES = Path(__file__).parent.parent / "fixtures"
FIRST_HOUR = datetime(2025, 5, 31, 22, tzinfo=UTC)  # HourDK 2025-06-01T00:00


def _records(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text())["records"]


def test_mapper_builds_tz_aware_price_series():
    prices = topriceseries(_records("elspotprices_dk1_2025-06-01_2025-06-02.json"))

    assert len(prices.timestamps) == len(prices.prices) == 48
    assert prices.timestamps[0] == FIRST_HOUR
    assert prices.timestamps[0].tzinfo is not None
    assert prices.prices[0] == 92.529999


def test_mapper_builds_tz_aware_generation_series():
    generation = tovolumeseries(_records("declarationproduction_dk1_2025-06-01_2025-06-02.json"))

    assert len(generation.timestamps) == len(generation.volumes) == 48
    assert generation.timestamps[0] == FIRST_HOUR
    assert generation.timestamps[0].tzinfo is not None
    assert generation.volumes[0] == 331.259613
