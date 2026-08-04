# M1 Design Doc — DK1 Onshore Wind Value Factor

_Module: M1 · Status: **critiqued, gate cleared** · Owner: Eneko_
_Repo location: `modules/m1_market_economics/DESIGN.md` (or `docs/design/`)_

> **Gate status:** This document passed critique. Code may begin.
> First task: write the failing test `test_wind_val_factor_calc` (§8), then implement `value_factor()` in `libs/core`.

---

## 1. Question this slice answers

> **What was DK1's onshore wind value factor in June 2025, and what does it reveal about when wind earns relative to the market average?**

---

## 2. Data source and contract

**Energi Data Service — two datasets, DK1 only, June 2025.**

Window chosen deliberately: a pre-October-2025 hourly period, which avoids the `Elspotprices` → `DayAheadPrices` transition to 15-minute MTU. Both sources are natively hourly in this window, so no aggregation rule is required.

### Prices — `Elspotprices`

| Field | Value |
|---|---|
| Endpoint | `https://api.energidataservice.dk/dataset/Elspotprices` |
| Fields used | `HourUTC`, `HourDK`, `PriceArea`, `SpotPriceEUR` |
| Currency | EUR/MWh (`SpotPriceDKK` also available, not used) |
| Filter | `{"PriceArea":["DK1"]}` |
| Rows returned | **720** (30 days × 24 h, no gaps) |

### Wind volume — `DeclarationProduction`

| Field | Value |
|---|---|
| Endpoint | `https://api.energidataservice.dk/dataset/DeclarationProduction` |
| Fields used | `HourUTC`, `HourDK`, `ProductionType`, `Production_MWh`, `Version` |
| Filter | `{"PriceArea":["DK1"],"FuelAllocationMethod":["All"],"ProductionType":["WindOnshore"]}` |
| Rows returned | **720** — matches the price series exactly, same `HourUTC` values |
| Version | `"Final"` — settled data, reproducible (not `"Preliminary"`) |

### Contract notes

- **Canonical timestamp:** `HourUTC`.
- **Scope:** `WindOnshore` only. `WindOffshore` excluded (see §7).
- **`FuelAllocationMethod: "All"` is mandatory.** Without it the dataset fans out across allocation methods and a naive sum overcounts volume by roughly 4×.
- **Negative prices occur in this window.** This is real market behaviour, not a data error. Captured price and time-average price can both be negative; the domain must not assume positivity.
- **Request window is in Danish local time** while records are keyed on `HourUTC`. June 2025 therefore means Danish June — the first record is `HourUTC 2025-05-31T22:00` = `HourDK 2025-06-01T00:00`.

---

## 3. Domain model (`libs/core`)

Value factor is computed from captured price and time-average price. Each has its own function; a third composes them.

### Types

```
PriceVolumeSeries
  - timestamps : canonical HourUTC
  - price      : EUR/MWh
  - volume     : MWh
```

### Signatures

```python
captured_price(series)      -> float
time_average_price(series)  -> float
value_factor(series)        -> ValueFactorResult
    .value_factor
    .captured_price
    .time_average_price
```

### Boundary decisions

- **Filtering and mismatched input are handled in the adapter, not the domain.** The domain trusts the port's contract; series alignment is guaranteed by the adapter.
- A calculation that is specific to the statistics of the problem belongs in the domain.
- The domain output carries the computed metrics only. It knows nothing about plots, charts, or presentation.

### Open — resolve while coding

The port exposes `get_prices` and `get_generation` separately, so something must join them on `HourUTC` to form a `PriceVolumeSeries`. Where that join lives (adapter, app layer, or a domain constructor) is deliberately left for TDD to surface.

---

## 4. Ports

- A class with methods such as `get_prices` and `get_generation`.
- The port returns **domain types**, not raw responses. The adapter performs the translation.
- **`libs/core` imports nothing from the adapter.** Dependencies point inward.
- The port takes a small value type as input: a `Zone` enum (`DK1`, `DK2`) and a typed date range.

---

## 5. Adapter

- **One adapter class**, implementing the single port from §4.
- JSON parsing is **delegated to a separate mapper function** — independently unit-testable against a saved fixture, offline.
- **`requests`, synchronous, one call.** The workload is a single batch pull; there is no concurrency pressure. Async (`httpx`) is deferred until a real concurrency need appears — adding DK2 is two sequential calls and does not qualify.
- Errors are caught and re-raised as **domain-meaningful errors**.

### Owned by the adapter — never seen by the domain

- The exact endpoint URL and query parameters (including the `columns` parameter — 6 fields requested instead of 22)
- JSON field names (Energinet's naming, not ours)
- Timestamp / timezone parsing (`start`/`end` are Danish local time; records are keyed on `HourUTC`)
- Pagination
- JSON parsing — field names, nesting, raw response structure
- HTTP mechanics — headers, status codes, retries, timeouts
- HTTP 429 rate limiting on Energinet calls (respect the returned retry delay; do not poll)
- Authentication / tokens (N/A for Energi Data Service v1)
- Missing-data filtering — not handled in M1. If missing data would change the result, that logic belongs in the domain. For now: report or confirm that no data is missing.

---

## 6. Output

**One number, plus its components:** value factor, captured price, time-average price.

### Charts (ABT-titled — every title states a claim, not a topic)

1. **Prices vs. wind**
   > "DK1's highest-wind hours in June 2025 cleared at €X/MWh against a monthly average of €Y — wind produces most when the market pays least."

2. **Captured vs. time-average price**
   > "DK1 onshore wind captured less than the market average price over June 2025."

3. **Single-day close-up (29 June)**
   > "On 29 June, DK1 wind hit peak output during the only hours the price went negative."

The output should answer: **when does wind earn, relative to the market average?**

---

## 7. Explicitly OUT

| Item | Note |
|---|---|
| Missing-data handling | If data is missing it is not analysed. No filling, no filtering — it may change the result. |
| Pagination | — |
| DST duplicate-hour resolution | Deferred. `HourUTC` as canonical makes this cheaper later. |
| ML / forecasting | M2. |
| DK2 comparison | Later phase. The `Zone` enum stays; selecting DK2 shows "data not available". |
| Error handling / retry beyond basic translation | — |
| ERA5, ENTSO-E | M3 and M2 respectively. |
| WindOffshore | Onshore only. Offshore has a different capture profile. |
| Aggregation rule | Not needed — both sources are hourly in this window. |
| Value factor vs. penetration over time | Requires multi-year data. Deferred. |
| Merit-order effect / causal claims about price levels | Requires a counterfactual. M2. |

---

## 8. Test plan

**Domain first.** A short hand-computed series, asserted against a number calculated independently beforehand. Location: `tests/unit`. Integration tests follow later.

### `test_wind_val_factor_calc`

Three hours of data:

| Hour | Price (€/MWh) | Wind generation (MWh) | Revenue (€) |
|---|---|---|---|
| 1 | 35 | 15 | 525 |
| 2 | 30 | 20 | 600 |
| 3 | 50 | 8 | 400 |

**Time-average price**
```
(35 + 30 + 50) / 3 = 115 / 3 = 38.3333 €/MWh
```

**Captured price (volume-weighted)**
```
(525 + 600 + 400) / (15 + 20 + 8) = 1525 / 43 = 35.4651 €/MWh
```

**Value factor**
```
35.4651 / 38.3333 = 0.925177
```

**Assertion**
```python
assert value_factor(series).value_factor == pytest.approx(0.9252, rel=1e-3)
```

### Subsequent tests

- **Mapper test** — a saved Energi Data Service JSON response as a fixture in `tests/fixtures/`, asserting the JSON → domain mapping. Catches timezone, unit, and field-name bugs offline.
- **Integration test** — adapter against the live API.

---

## Design principles honoured

| # | Principle | How |
|---|---|---|
| 1 | Design-doc first | This document, critiqued before any code. |
| 2 | Thin vertical slice | One zone, one month, one production type, one number. |
| 5 | Dependencies point inward | `libs/core` knows nothing of HTTP, JSON, or Energinet. |
| 7 | Negative results ship | Whatever June 2025 returns is the result. |
