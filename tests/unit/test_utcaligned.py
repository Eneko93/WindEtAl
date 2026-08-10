from libs.core.series import PriceSeries, GenerationSeries

## from libs.core.series import PriceSeries, GenerationSeries #For tests
import json
import pandas as pd


def test_utc_aligned():
    with open(
        r"C:\Users\EnekoOscozCob\Documents\z_analytics\repos\WindEtAl\tests\fixtures\declarationproduction_dk1_2025-06-01_2025-06-02.json"
    ) as json_file:
        items_generation = json.load(json_file)

    with open(
        r"C:\Users\EnekoOscozCob\Documents\z_analytics\repos\WindEtAl\tests\fixtures\elspotprices_dk1_2025-06-01_2025-06-02.json"
    ) as json_file:
        items_prices = json.load(json_file)

    prices = PriceSeries(
        timestamps=pd.Series([r["HourUTC"] for r in items_prices["records"]]),
        prices=pd.Series([r["SpotPriceEUR"] for r in items_prices["records"]]),
    )
    generation = GenerationSeries(
        timestamps=pd.Series([r["HourUTC"] for r in items_generation["records"]]),
        volumes=pd.Series([r["Production_MWh"] for r in items_generation["records"]]),
    )
    print(prices)
    print(generation)
    assert prices.timestamps.equals(generation.timestamps)
