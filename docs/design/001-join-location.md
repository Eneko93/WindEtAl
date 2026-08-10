# 001 — Where the price/generation join on `HourUTC` lives

_Decision 001 · Created 2026-08-09 · Owner: Eneko · Status: **Accepted** · Module: M1_

> Flagged as open in `M1-Design-Doc.md` §3 ("Open — resolve while coding") and carried in `Learning-Current-State.md` as decision log entry #1. Resolved during adapter implementation, before the full June 2025 pull.

---

## 1. Context

Value factor requires price and generation **paired on the same hour**:

```
captured_price = Σ(price_h × volume_h) / Σ(volume_h)
```

The port (§4) exposes `get_prices` and `get_generation` as **separate methods**, backed by **two separate HTTP calls** to two different Energi Data Service datasets, returning two distinct domain types (`PriceSeries`, `GenerationSeries`). The two types are deliberately not a shared supertype — that separation exists to prevent silent argument-swap bugs.

So something, somewhere, must pair them. This document decides where.

### What triggered the decision

A throwaway script computed the value factor over the two-day fixture by building two `pd.Series` from two record lists and multiplying them elementwise. `HourUTC` was never read. The result (1.0974) was **correct** — the timestamp lists happened to be identical — but nothing in the code established that, and nothing would have flagged it if they had not been.

This is the failure mode the decision must close: a positional join produces a plausible, confident, wrong number and no test fails.

---

## 2. Options considered

| Option | Assessment |
|---|---|
| **Adapter joins** | Would require changing the port's shape — a combined fetch method — so the adapter can hold both series at once. Changes an architectural contract to serve a data-shape convenience. Rejected. |
| **Mapper joins** | Not viable. A mapper maps *one payload → one series*; there are two mapper functions because there are two datasets and two payloads. A mapper receiving both payloads is not a mapper. It would also place the alignment rule inside a module that only exists because of Energinet's field naming — swapping in ENTSO-E would mean rewriting join logic that has nothing to do with either vendor. Rejected. |
| **App layer joins** | Keeps core pure and the adapter simple, but the rule "these two series must align on `HourUTC`" would live in glue code with no home and no test. Rejected. |
| **Domain constructor joins** | ✅ **Chosen.** |

---

## 3. Decision

**The join lives in the domain, in a constructor that builds `PriceVolumeSeries` from a `PriceSeries` and a `GenerationSeries`, aligning on `HourUTC`.**

### Reasoning

> The adapter cannot guarantee alignment between two series it never holds at the same time. Guaranteeing it would mean restructuring the port so both fetches happen together.
>
> Alignment is **a fact about the problem, not about HTTP.** The two series must be paired on the hour because that is what the value factor formula requires — it would be equally required with a different data source, a different API, or a CSV on disk.

`PriceVolumeSeries` is already named in design doc §3 as the type `captured_price()` consumes, while `series.py` holds only `PriceSeries` and `GenerationSeries`. Something already had to construct it. This is that something.

### Behaviour on mismatch: **raise**

Not an inner join, not a silent drop.

Design doc §7 is explicit: *"Missing-data handling — if data is missing it is not analysed. No filling, no filtering — it may change the result."* An inner join **is** filtering. It would let a partial month produce a confident number, which is precisely the class of error this decision exists to prevent.

Raise a domain error naming the mismatch.

---

## 4. Consequences

**Gained**

| | |
|---|---|
| Testable offline | Exercised by the existing hand-computed 3-hour fixture. No network, no fixture files. |
| The rule has a home | Alignment becomes a testable domain invariant, not a convention. |
| Core stays pure | No I/O, no vendor field names. Principle 5 intact. |
| Port stays honest | The adapter is not asked to guarantee something it cannot observe. |

**Accepted costs**

- The domain now owns a validation step, not only arithmetic. Justified: it is a validation of the *problem's* precondition, not of a transport format.
- Callers must handle the mismatch error. Correct — a mismatch means the analysis cannot be run.

**Ordering is now explicitly NOT a port guarantee.** Joining on the `HourUTC` key makes record order irrelevant to correctness. `sort: "HourUTC ASC"` stays in the adapter for chart legibility and diff-friendly fixtures, but no code may depend on it.

---

## 5. Follow-up actions

- [ ] **Correct design doc §3.** It currently reads *"series alignment is guaranteed by the adapter."* That is now false and would mislead a future reader into implementing the rejected option.
- [ ] Write the failing test first: two series with a mismatched hour → asserts raise. Include an **equal-length but shifted** case, which is the only one that catches a positional join.
- [ ] Add the domain error type to the error-translation work deferred from §5.

---

## 6. Revisit if

- A future module needs a genuinely combined fetch (e.g. a single dataset carrying both price and volume), making the port shape argument moot.
- Missing-data handling moves in scope from OUT to IN, at which point "raise" may become "raise unless an explicit gap policy is supplied."
