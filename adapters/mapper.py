from datetime import UTC, datetime

from libs.core.series import GenerationSeries, PriceSeries


def _parse_hour_utc(value: str) -> datetime:
    # Energi Data Service returns HourUTC without an offset; it is UTC by definition.
    return datetime.fromisoformat(value).replace(tzinfo=UTC)


def topriceseries(raw: list[dict]) -> PriceSeries:
    return PriceSeries(
        timestamps=tuple(_parse_hour_utc(r["HourUTC"]) for r in raw),
        prices=tuple(float(r["SpotPriceEUR"]) for r in raw),
    )


def tovolumeseries(raw: list[dict]) -> GenerationSeries:
    return GenerationSeries(
        timestamps=tuple(_parse_hour_utc(r["HourUTC"]) for r in raw),
        volumes=tuple(float(r["Production_MWh"]) for r in raw),
    )
