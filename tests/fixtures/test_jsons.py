import json

import pandas as pd

with open(
    r"C:\Users\EnekoOscozCob\Documents\z_analytics\repos\WindEtAl\tests\fixtures\declarationproduction_dk1_2025-06-01_2025-06-02.json"
) as json_file:
    items_generation = json.load(json_file)

with open(
    r"C:\Users\EnekoOscozCob\Documents\z_analytics\repos\WindEtAl\tests\fixtures\elspotprices_dk1_2025-06-01_2025-06-02.json"
) as json_file:
    items_prices = json.load(json_file)

print("generation total:", items_generation["total"])
print("generation records[:3]:", items_generation["records"][:3])
print("prices total:", items_prices["total"])
print("prices records[:3]:", items_prices["records"][:3])

prices = pd.Series([r["SpotPriceEUR"] for r in items_prices["records"]])
generation = pd.Series([r["Production_MWh"] for r in items_generation["records"]])

total_price = prices.sum()
total_generation = generation.sum()
total_revenue = (prices * generation).sum()
captured_price = (prices * generation).sum() / generation.sum()
time_averaged_price = prices.mean()

wind_value_factor = captured_price / time_averaged_price

print("total revenue:", total_revenue)
print("wind_value_factor:", wind_value_factor)