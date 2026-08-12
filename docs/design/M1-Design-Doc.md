# M1 Design Doc — DK1 Onshore Wind Value Factor

_Module: M1 · Status: **critiqued, gate cleared** · Owner: Eneko_
_Repo location: `modules/m1_market_economics/DESIGN.md` (or `docs/design/`)_

> **Gate status:** This document passed critique. Code may begin.
> First task: write the failing test `test_value_factor_simple_int` (§8), then implement `value_factor()` in `libs/core`.

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

### Verified against the live API (2026-08-09)

Ad hoc calls against the real, tokenless endpoints, run to settle open questions before writing the adapter:

- **`end` is exclusive.** A request for Danish-local `00:00`–`02:00` returned exactly 2 records (the `00:00` and `01:00` hours); the `02:00` hour itself was not included. Confirms the API guide's own `start=2022-05-01&end=2022-06-01` "= May" example. The adapter must send `period.end + 1 hour` as the API's `end`, since `DateRange.end` is documented as the last *included* hour.
- **Default sort is descending.** An unsorted request came back newest-first (`23:00` before `22:00`). Order is not incidental — it must be requested explicitly if ascending order is needed.
- **Naive, timezone-less timestamps in `start`/`end` are read as Danish local time.** Sending `2022-05-01T00:00` with no offset returned `HourUTC` rows 2 hours earlier (`2022-04-30T22:00`/`23:00`), consistent with May's CEST (UTC+2) offset. Reinforces the note above — the adapter must convert `DateRange`'s UTC datetimes to Danish local time before sending them, not just before reasoning about the result.
- **An unrecognized filter value does not error, and does not get ignored.** `{"PriceArea":["DK1"],"ProductionType":["NotARealType"]}` returned HTTP 200 with `"total": 0` and empty `records` — a plausible-looking empty result, not an exception. A row-count guard (`len(records) == total`) is what catches a filter typo; nothing else will.
- **A plain (non-`str`) `Enum` does not interpolate to its value.** `f"{Zone.DK1}"` renders `"Zone.DK1"`, not `"DK1"`. The adapter must use `zone.value`.
- **`sort=HourUTC` produces ascending order.** Confirmed by calling `EnerginetRepo._fetch` directly against both live endpoints — records came back oldest-first for a known 3-hour window, with `len(records) == total` in both cases.

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

- Series alignment is a domain fact, not transport logic. The port returns prices and generation independently; the PriceVolumeSeries constructor joins them on HourUTC and raises on mismatch. See ADR 001. Adapters own filtering and parsing; they do not own alignment.
- A calculation that is specific to the statistics of the problem belongs in the domain.
- The domain output carries the computed metrics only. It knows nothing about plots, charts, or presentation.

### Resolved

Join location → ADR 001: the PriceVolumeSeries constructor. See the boundary decisions above.

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

### `test_value_factor_simple_int`

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
assert result.value_factor == pytest.approx(0.925177, rel=1e-5)
```
### `test_value_factor_matches_expected_ratio` — 10-hour case

A longer series, hand-derived independently of the implementation. Verified by exact rational arithmetic (2026-08-10).

| Hour | Price (€/MWh) | Wind generation (MWh) | Revenue (€) |
|---|---|---|---|
| 1 | 25 | 23 | 575 |
| 2 | 40 | 16 | 640 |
| 3 | 42 | 15 | 630 |
| 4 | 46 | 13 | 598 |
| 5 | 48 | 11 | 528 |
| 6 | 50 | 21 | 1050 |
| 7 | 30 | 18 | 540 |
| 8 | 35 | 17 | 595 |
| 9 | 32 | 17.5 | 560 |
| 10 | 28 | 18.5 | 518 |

**Time-average price**
```
376 / 10 = 37.6 €/MWh
```

**Captured price (volume-weighted)**
```
6234 / 170 = 3117/85 = 36.670588 €/MWh
```

**Value factor**
```
3117 / 3196 = 0.9752816
```

**Assertion**
```python
assert value_factor(series).value_factor == pytest.approx(0.97528, rel=1e-5)
```

**Why both cases.** The 3-hour case is small enough to check by inspection; the 10-hour case exercises a non-trivial volume distribution and a fractional MWh value. Both expected values are derived from the table above, not from program output.

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
