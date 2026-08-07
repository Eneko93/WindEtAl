# WindEtAl — Architecture Reasoning Notes
_Companion to `M1-Design-Doc.md`. Written 2026-08-04. Covers the ports-and-adapters decisions taken in M1 and the reasoning behind each._

**Purpose.** The design doc says *what* was decided. This says *why*, in enough depth to defend it cold. Reference: Percival & Gregory, *Architecture Patterns with Python*.

---

## 1. The one rule everything else follows

**Dependencies point inward.** `libs/core` imports nothing about HTTP, JSON, files, pandas, or Energinet. Everything else may import `libs/core`.

```
Energinet API
     │
     ▼
adapters/           ← knows about requests, JSON, pandas, field names
     │  imports
     ▼
libs/core/          ← knows about prices, volumes, value factor. Nothing else.
```

The arrow never reverses. This is design principle #5 in the project plan, and it is the test you apply whenever you are unsure where something goes: *which way would the import point?*

### Why it's worth the discipline

| Benefit | Concrete instance in M1 |
|---|---|
| The domain is testable with no I/O | `test_wind_val_factor_calc` builds three rows by hand. No network, no fixtures, no mocking |
| External change is contained | Energinet renames a field → one mapper file changes. `economics.py` untouched |
| Sources are swappable | M2 adds ENTSO-E. New adapter, same domain |
| Offline development | The fixture-backed implementation and the live one are interchangeable |

The fourth is the immediate payoff: it's what lets the mapper work be done Thursday with no network at all.

---

## 2. Domain types: data, not behaviour

A **domain type** is a named data structure written in the vocabulary of the problem.

```python
@dataclass(frozen=True)
class PriceSeries:
    timestamps: tuple[datetime, ...]
    prices: tuple[float, ...]  # EUR/MWh
```

That is the whole thing. No methods. No fetching, no parsing, no validation of the outside world. It does not know where it came from.

### Common confusion: type vs. the thing that builds it

These are two separate classes on opposite sides of the boundary.

| | Domain type | Adapter |
|---|---|---|
| Example | `PriceSeries`, `PriceVolumeSeries` | `EnerginetRepository` |
| Lives in | `libs/core` | `adapters/` |
| Contains | Fields | Methods that fetch, parse, filter |
| Knows about | Nothing external | HTTP, JSON, pandas, Energinet field names |
| Role | The shape | The thing that produces the shape |

The adapter has the behaviour. The domain type is what comes out of it.

### Why "domain"

The vocabulary comes from the problem, not the API.

| Energinet says | The domain says |
|---|---|
| `Production_MWh` | volume |
| `SpotPriceEUR` | price |
| `HourUTC` (string) | timestamp (real `datetime`) |
| 22 columns | the three that matter |

Every one of those translations happens in the mapper. What crosses the boundary speaks only your language.

**The test:** if Energinet renamed a field tomorrow, how many files change? Correct answer: one. If `economics.py` is in the list, their vocabulary has leaked inward.

### Why not DataFrames

Tempting, since pandas is already fluent. Three reasons it fails:

1. **It's an import into core.** Principle #5 breaks immediately.
2. **A DataFrame has no contract.** Nothing states which columns exist, what units they carry, or that the rows are aligned. `df['SpotPrice']` when the column is `SpotPriceEUR` fails at runtime, deep inside a calculation.
3. **It makes pure tests impure.** Last week's three-row arithmetic test would need pandas to construct its input.

Pandas is welcome *inside* the adapter — it's a good tool for parsing and joining. It just doesn't cross the line. The adapter's last act is conversion to domain types.

---

## 3. Ports and adapters are one boundary, not two stages

The most common misreading is to picture a pipeline: port → adapter → domain. It isn't. The port and the adapter are the *same boundary viewed from two sides*.

- **Port** — the boundary as the domain sees it: "I need prices for a zone and a date range."
- **Adapter** — that same boundary from outside: "here is how I actually get them from Energinet."

The adapter *implements* the port. There is one contract, and the adapter satisfies it. Nothing is handed from one to the other.

```
Energinet JSON
    ↓  adapter: requests, parse, filter, reshape   (pandas allowed here)
    ↓  mapper:  → domain types
─── the port's contract ───────────────────────────
    ↓
libs/core:  PriceVolumeSeries → value_factor()
```

### What a port looks like

```python
# libs/core/ports.py
from abc import ABC, abstractmethod


class EnergyDataRepository(ABC):
    """What the domain needs from the outside world.
    Says nothing about where the data lives."""

    @abstractmethod
    def get_prices(self, zone: Zone, period: DateRange) -> PriceSeries:
        raise NotImplementedError

    @abstractmethod
    def get_wind_generation(self, zone: Zone, period: DateRange) -> GenerationSeries:
        raise NotImplementedError
```

| Present | Absent |
|---|---|
| Method names in domain vocabulary | Any method body |
| Domain types in (`Zone`, `DateRange`) | SQL, HTTP, filenames, pandas |
| Domain types out | Dicts, DataFrames, raw JSON |
| A docstring stating the contract | Any hint of *where* the data lives |

The empty bodies are the point. The class cannot be instantiated. It is a promise someone else must keep.

### What an implementation looks like

Identical signatures — same names, same parameters, same return types. Only the bodies differ.

```python
# adapters/energinet.py
class EnerginetRepository(EnergyDataRepository):
    def get_prices(self, zone: Zone, period: DateRange) -> PriceSeries:
        raw = requests.get(...).json()
        return to_price_series(raw)  # mapper does the translation
```

And the fixture-backed one, for offline work:

```python
# tests/
class FixtureRepository(EnergyDataRepository):
    def get_prices(self, zone: Zone, period: DateRange) -> PriceSeries:
        raw = json.loads(FIXTURE_PATH.read_text())
        return to_price_series(raw)
```

Two implementations, one contract. The domain cannot tell which it has been handed. **This is why the port exists at all** — it is what makes Thursday's work possible with no network.

### Why `@abstractmethod` specifically

Without the decorator, a subclass can silently skip a method. With it, Python refuses to instantiate the subclass at all. A missing `get_wind_generation` fails at construction time, not mid-pull on a Saturday.

---

## 4. Where each thing lives, and why

| File | Contents | Reason |
|---|---|---|
| `libs/core/economics.py` | `PriceVolumeSeries`, `ValueFactorResult`, `captured_price`, `time_average_price`, `value_factor` | Named for what it is *about*, not for a generic layer word like `models.py` |
| `libs/core/ports.py` | `EnergyDataRepository`, `Zone`, `DateRange` | Different reason to change: the port changes when data-access shape changes, `economics.py` only when the economics change |
| `adapters/energinet.py` | Repository implementation + mapper | Everything Energinet-specific, quarantined |

### Why the port sits in `libs/core` but isn't part of the domain model

Two different kinds of thing live in core:

- **The domain** (`economics.py`) — what the problem *is*
- **The port** (`ports.py`) — a declaration of what the domain *needs*

The port is in core because the domain must be able to reference it without importing outward. It gets its own file because it isn't the model.

### Why the domain defines the type the adapter must produce

Instinct says the adapter should own `PriceVolumeSeries`, since the adapter is what guarantees the data is well-formed. Follow the imports:

```
Type in adapter:   economics.py → imports from adapter    ✗ points outward
Type in core:      adapter → imports from libs.core       ✓ points inward
```

The general rule: **the domain defines the shape it accepts; the adapter is obliged to produce it.** Like a wall socket — the socket defines the plug shape and every appliance conforms. The socket does not live inside the toaster.

The adapter still does all the conforming work. It just doesn't get to define what conforming means — otherwise the domain's contract would be dictated by whichever API happened to come first, and adding ENTSO-E in M2 would force the domain to change.

---

## 5. Why separate `PriceSeries` and `GenerationSeries`

The alternative was one shared `EnergyTimeSeries` returned by both methods.

| | Two distinct types | One shared type |
|---|---|---|
| Code | Two small dataclasses | One |
| Mixing prices and volumes | Type error at the call site | Compiles fine |
| Failure mode if mixed | Immediate | A plausible-looking wrong value factor |

The calculation is `sum(price × volume) / sum(volume)`. Swapping the arguments produces a number, not a crash — and a number that looks reasonable. That is the worst class of bug: silent, and it invalidates the headline result.

Distinctness costs about eight lines and removes the failure mode entirely.

**Note on the port's own name.** The port is broad (`EnergyDataRepository`) because it genuinely serves several kinds of data. That breadth does *not* propagate to the return types — a repository serving books and journals doesn't return `LibraryItem` from `get_by_isbn`. Name each return type after its contents.

---

## 6. Invariants: what belongs in a type and what doesn't

June 2025 in DK1 gives 720 rows. That number does **not** belong in `PriceVolumeSeries`.

| Describes | Belongs |
|---|---|
| The shape of the thing — the three arrays are equal-length and aligned on `HourUTC` | In the type. True at 3 rows and at 720 |
| One instance — "I asked for June, so I expect 720" | A check at pull time, in the adapter or app layer |

A week is 168. A day is 24. M2's three years is ~26,000. The test's three hours is just another valid length. Bake 720 into the type and last week's test breaks for no reason.

**General heuristic:** when a number appears in a design doc, ask whether it describes *the shape of the thing* or *one instance of it*. Only the first belongs in the type.

The 720-vs-720 match between the two datasets is a **join-time** check, not a type-time one — and it is exactly the question that decides where the join lives.

### Validation: trust or check?

§3 of the design doc says the domain **trusts the adapter**. The adapter guarantees alignment; `PriceVolumeSeries` does not re-verify it. Consequence: if the adapter is wrong, the domain silently computes a wrong number. Accepted for M1 because the adapter is the only producer and it is tested. Worth revisiting when a second source appears in M2.

---

## 7. Open decision — where the join lives

`value_factor()` needs one `PriceVolumeSeries`: timestamps, price, volume. The port returns two objects. Something must join them on `HourUTC`.

| Option | Consequence |
|---|---|
| Adapter joins, returns `PriceVolumeSeries` from a combined method | Simplest domain surface. Port methods no longer map 1:1 to datasets; join logic sits outside the domain |
| App layer joins | Port stays honest and dataset-shaped. Join logic lives in a layer with no tests yet |
| Domain constructor joins | Join logic is testable with pure data. Domain takes on a responsibility the design doc says the adapter owns |

**The question that settles it:** when 720 prices meet 719 generation rows, where do you want to find out? Whichever component discovers the mismatch is the one that should own the join.

Unresolved by design — §3 defers it to TDD. **This is decision log entry #1.**

---
## 8. DateRange as a validated type

Context. The port needs a time window. Options: two loose datetime params, pd.date_range, or a dedicated type.

Decision. Frozen DateRange dataclass, validating start < end in __post_init__. pd.date_range rejected — pandas cannot be imported in libs/core (principle #5), and materialising 720 timestamps to express two endpoints is the wrong shape.

Why validate here when PriceVolumeSeries doesn't. PriceVolumeSeries is produced only by a tested adapter that guarantees alignment; it has an upstream guarantor. DateRange is constructed by hand at arbitrary call sites and has none, so the invariant has nowhere else to live. Validation belongs where no upstream component can be trusted to have already enforced it.

Consequence. An invalid range cannot exist. Callers get the error at construction, not mid-pull.
---
## 9. UTC - closed interval

Context. HourUTC is the canonical domain timestamp. Energinet's start/end query params are Danish local time. A range also needs an inclusivity convention.

Decision. DateRange carries tz-aware UTC datetimes. The interval is closed — end is included and is an hour, not a day. June 2025 = 2025-06-01T00:00Z → 2025-06-30T23:00Z, 720 hours.

Note. This does not change Energinet's API. The local-time conversion stays in the adapter (design doc §5). Domain convention and API convention are independent.

Consequence. Off-by-one shows as 719 or 721 rows, which the pull-time count check catches. Half-open would have been equally valid; what matters is that one is chosen and documented.
---
## 10. Decision log — entries generated so far

Short entries, `docs/decisions/`. Format: context → options → choice → consequence.

| # | Decision | Status |
|---|---|---|
| 0 | Port in `ports.py`, separate from `economics.py` — different reasons to change | Decided |
| 1 | Where the price/generation join lives | **Open — resolve in code** |
| 2 | `PriceSeries` / `GenerationSeries` distinct rather than one shared type — prevents silent argument-swap bug | Decided |
| 3 | Domain trusts adapter for alignment; no self-validation in the type | Decided, revisit in M2 |
| 4 | `requests` sync over `httpx` async — no concurrency pressure | Decided (design doc §5) |
| 5 | DateRange added as a validated type in its own data class
| 6 | UTC used for timezone, as a closed interval

This log is the artefact that reads as senior judgment. The decisions above are already made; writing them down costs minutes and is the difference between "code that works" and "engineer who can explain trade-offs."
---
## 11. Recall questions

Answer cold, no notes.

1. Which way do dependencies point, and what breaks if `economics.py` imports pandas?
2. Why does the port return domain types rather than DataFrames? Name three distinct reasons.
3. Port and adapter — are they two stages in a pipeline? Explain.
4. Why does `PriceVolumeSeries` live in `libs/core` rather than in the adapter? Use the import-direction argument.
5. Why not one shared `EnergyTimeSeries` for both methods? What exactly is the failure mode?
6. Why is 720 not an invariant of `PriceVolumeSeries`?
7. What does `@abstractmethod` buy that plain inheritance doesn't?
8. If Energinet renamed `Production_MWh`, which files change?
9. What does `FuelAllocationMethod: "All"` prevent, and what would the bug look like if forgotten?

**Feynman target:** explain ports and adapters to someone who has never seen it, in five sentences, without the words "port," "adapter," or "hexagonal."
