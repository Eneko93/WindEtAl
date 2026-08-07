from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True)
class PriceSeries:
    timestamps: tuple[datetime, ...]
    prices: tuple[float, ...] # Eur/MWh
    
@dataclass(frozen=True)
class GenerationSeries:
    timestamps: tuple[datetime, ...]
    volumes: tuple[float, ...] # MWh