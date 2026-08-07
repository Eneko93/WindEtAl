from abc import ABC, abstractmethod
from enum import Enum

from dataclasses import dataclass
from datetime import datetime

from series import PriceSeries, GenerationSeries


class Zone(Enum):
    DK1 = "DK1"
    DK2 = "DK2"


@dataclass(frozen=True)
class DateRange:
    """An inclusive time window in UTC.

    Both endpoints are hour-resolution timestamps, and both are
    included: June 2025 is 2025-06-01T00:00Z to 2025-06-30T23:00Z,
    which is 720 hours. Note that `end` is an hour, not a day —
    passing 2025-06-30T00:00Z gives 697 hours, not 720.

    Datetimes must be timezone-aware and in UTC, matching HourUTC,
    the canonical timestamp of the domain. This is a domain
    convention only: Energi Data Service takes its start/end query
    parameters in Danish local time, and converting to it is the
    adapter's responsibility.
    """

    start: datetime
    end: datetime

    def __post_init__(self):
        if self.start >= self.end:
            raise ValueError("Start date must be strictly before end date.")


class EnergyDataRepo(ABC):
    @abstractmethod
    def get_wind_prices(self, zone: Zone, period: DateRange) -> PriceSeries:
        raise NotImplementedError

    @abstractmethod
    def get_wind_generation(self, zone: Zone, period: DateRange) -> GenerationSeries:
        raise NotImplementedError
