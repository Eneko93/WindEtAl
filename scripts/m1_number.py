"""M1 scratch composition: DK1 onshore wind value factor, June 2025 (Danish time).

Throwaway by design. Replaced by a composition root in M2 (see M1 ship-week debt list).
Run from the repo root:  uv run python -m scripts.m1_number
"""

import math
from datetime import UTC, datetime
from pathlib import Path

from adapters.adapter_M1 import EnerginetRepo
from libs.core.economics import PriceVolumeSeries, value_factor
from libs.core.ports import DateRange, Zone

# June 2025 in Danish time (CEST, UTC+2): 2025-06-01T00:00 DK = 2025-05-31T22:00Z.
PERIOD = DateRange(
    start=datetime(2025, 5, 31, 22, tzinfo=UTC),
    end=datetime(2025, 6, 30, 21, tzinfo=UTC),
)
EXPECTED_HOURS = 720
SANITY_BAND = (0.75, 1.05)
PREDICTION = 0.77
RESULT_PATH = Path("docs/decisions/m1-result.md")


def main() -> None:
    repo = EnerginetRepo()
    prices = repo.get_prices(Zone.DK1, PERIOD)
    generation = repo.get_generation(Zone.DK1, PERIOD)

    # ADR 001: timestamps must align exactly. Mismatch raises; no fill, no drop.
    assert len(prices.timestamps) == EXPECTED_HOURS, f"prices: {len(prices.timestamps)} rows"
    assert len(generation.timestamps) == EXPECTED_HOURS, f"generation: {len(generation.timestamps)} rows"
    assert prices.timestamps == generation.timestamps, "HourUTC mismatch between prices and generation"
    assert not any(math.isnan(p) for p in prices.prices), "NaN in prices"
    assert not any(math.isnan(v) for v in generation.volumes), "NaN in volumes"

    series = PriceVolumeSeries(
        timestamps=prices.timestamps,
        price=prices.prices,
        volume=generation.volumes,
    )
    result = value_factor(series)

    low, high = SANITY_BAND
    in_band = low <= result.value_factor <= high
    if not in_band:
        print(f"WARNING: VF {result.value_factor:.4f} outside sanity band {SANITY_BAND}. "
              "Check FuelAllocationMethod and the join before believing it.")

    negative_hours = sum(1 for p in prices.prices if p < 0)
    print(f"value_factor       = {result.value_factor:.4f}")
    print(f"captured_price     = {result.captured_price:.2f} EUR/MWh")
    print(f"time_average_price = {result.time_average_price:.2f} EUR/MWh")
    print(f"negative-price hrs = {negative_hours}")

    RESULT_PATH.write_text(
        "# M1 result — DK1 onshore wind value factor, June 2025\n\n"
        f"_Computed {datetime.now(UTC):%Y-%m-%d} by `scripts/m1_number.py`._\n\n"
        "| Metric | Value |\n|---|---|\n"
        f"| Value factor | **{result.value_factor:.4f}** |\n"
        f"| Captured price | {result.captured_price:.2f} EUR/MWh |\n"
        f"| Time-average price | {result.time_average_price:.2f} EUR/MWh |\n"
        f"| Hours | {EXPECTED_HOURS} (HourUTC 2025-05-31T22:00 → 2025-06-30T21:00) |\n"
        f"| Negative-price hours | {negative_hours} |\n"
        f"| Sanity band {SANITY_BAND} | {'inside' if in_band else 'OUTSIDE'} |\n\n"
        f"Prediction (see `m1-prediction.md`): {PREDICTION} → "
        f"error {result.value_factor - PREDICTION:+.4f}.\n\n"
        "Source: Energi Data Service — `Elspotprices` (SpotPriceEUR, DK1) and "
        "`DeclarationProduction` (Production_MWh, DK1, WindOnshore, FuelAllocationMethod=All).\n",
        encoding="utf-8",
    )
    print(f"written: {RESULT_PATH}")


if __name__ == "__main__":
    main()
