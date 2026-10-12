"""M1 scratch composition: DK1 onshore wind value factor, June 2025 (Danish time).

M1 entry point: wires the Energinet adapter -> domain join -> value factor, then writes
the result file and chart 2. Run from the repo root:  uv run python -m scripts.m1_number
"""

import math
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from adapters.adapter_M1 import EnerginetRepo
from libs.core.economics import PriceVolumeSeries, ValueFactorResult, value_factor
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
FIGURE_PATH = Path("modules/m1_data_analysis/figures/m1_captured_vs_average_dk1_2025-06.png")


def save_chart(result: ValueFactorResult) -> None:
    surface, ink, ink_muted = "#fcfcfb", "#0b0b0b", "#52514e"
    wind, reference = "#2a78d6", "#a3a29d"
    discount = 1 - result.value_factor

    fig, ax = plt.subplots(figsize=(9, 5.5), facecolor=surface)
    ax.set_facecolor(surface)
    labels = ["Time-average price\n(every hour equal)", "Captured price\n(weighted by wind output)"]
    values = [result.time_average_price, result.captured_price]
    bars = ax.bar(labels, values, width=0.5, color=[reference, wind])
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 1, f"€{value:.1f}/MWh",
                ha="center", va="bottom", fontsize=12, fontweight="bold", color=ink)

    # Gap annotation: the distance between the bars is the cannibalization.
    gap_x = bars[1].get_x() + bars[1].get_width() + 0.05
    ax.annotate("", xy=(gap_x, result.captured_price), xytext=(gap_x, result.time_average_price),
                arrowprops={"arrowstyle": "<->", "color": ink_muted, "lw": 1.5})
    ax.text(gap_x + 0.04, (result.captured_price + result.time_average_price) / 2,
            f"−{discount:.0%}\nvalue factor {result.value_factor:.2f}",
            va="center", ha="left", fontsize=11, color=ink)

    fig.text(0.03, 0.95, f"DK1 onshore wind earned {discount:.0%} less than the average power price in June 2025",
             ha="left", va="top", fontsize=13, fontweight="bold", color=ink)
    fig.text(0.03, 0.89, "Day-ahead spot price, EUR/MWh · 720 hours, Danish time · Source: Energi Data Service",
             ha="left", va="top", fontsize=9.5, color=ink_muted)
    ax.set_ylim(0, max(values) * 1.18)
    ax.set_xlim(-0.5, 1.75)
    ax.yaxis.set_visible(False)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(ink_muted)
    ax.tick_params(axis="x", colors=ink, labelsize=10.5, length=0)

    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0, 0, 1, 0.84))
    fig.savefig(FIGURE_PATH, dpi=150, facecolor=surface)
    plt.close(fig)


def main() -> None:
    repo = EnerginetRepo()
    prices = repo.get_prices(Zone.DK1, PERIOD)
    generation = repo.get_generation(Zone.DK1, PERIOD)

    # Pull-time checks: 720 describes this request, not the type (architecture notes §6).
    assert len(prices.timestamps) == EXPECTED_HOURS, f"prices: {len(prices.timestamps)} rows"
    assert len(generation.timestamps) == EXPECTED_HOURS, f"generation: {len(generation.timestamps)} rows"
    assert not any(math.isnan(p) for p in prices.prices), "NaN in prices"
    assert not any(math.isnan(v) for v in generation.volumes), "NaN in volumes"

    # ADR 0002: the domain joins on HourUTC and raises MisalignedSeriesError on any mismatch.
    series = PriceVolumeSeries.from_series(prices, generation)
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
    save_chart(result)
    print(f"written: {FIGURE_PATH}")


if __name__ == "__main__":
    main()
