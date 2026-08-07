from ..libs.core.ports import EnergyDataRepo, Zone, GenerationSeries, PriceSeries, DateRange
from ..libs.core.mapper import to

class EnerginetRepo(EnergyDataRepo):
    def get_prices(self, zone:Zone, period:DateRange) -> PriceSeries:
        raw = request.
        return topriceseries(raw)