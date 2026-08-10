import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from adapters.mapper import topriceseries, tovolumeseries
from libs.core.ports import DateRange, EnergyDataRepo, Zone
from libs.core.series import GenerationSeries, PriceSeries

_DANISH_TZ = ZoneInfo("Europe/Copenhagen")


def _to_danish_local(moment: datetime) -> str:
    return moment.astimezone(_DANISH_TZ).strftime("%Y-%m-%dT%H:%M")


class EnerginetRepo(EnergyDataRepo):
    _BASE_URL = "https://api.energidataservice.dk/dataset"

    def get_prices(self, zone: Zone, period: DateRange) -> PriceSeries:
        records = self._fetch(
            dataset="Elspotprices",
            period=period,
            filter_dict={"PriceArea": [zone.value]},
            columns="HourUTC,SpotPriceEUR",
        )
        return topriceseries(records)

    def get_generation(self, zone: Zone, period: DateRange) -> GenerationSeries:
        records = self._fetch(
            dataset="DeclarationProduction",
            period=period,
            filter_dict={
                "PriceArea": [zone.value],
                "FuelAllocationMethod": ["All"],
                "ProductionType": ["WindOnshore"],
            },
            columns="HourUTC,Production_MWh",
        )
        return tovolumeseries(records)

    def _fetch(self, *, dataset: str, period: DateRange, filter_dict: dict, columns: str) -> list[dict]:
        # API's `end` is exclusive; DateRange.end is the last included hour (see design doc §2).
        exclusive_end = period.end + timedelta(hours=1)
        params = {
            "start": _to_danish_local(period.start),
            "end": _to_danish_local(exclusive_end),
            "filter": json.dumps(filter_dict),
            "columns": columns,
            "sort": "HourUTC ASC",
        }
        response = requests.get(f"{self._BASE_URL}/{dataset}", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        records = payload["records"]
        if len(records) != payload["total"]:
            raise ValueError(
                f"{dataset}: expected {payload['total']} records, got {len(records)} "
                "(response may be truncated)"
            )
        return records
