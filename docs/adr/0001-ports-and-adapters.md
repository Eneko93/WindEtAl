# 0001 — Ports and adapters, dependencies point inward

_ADR 0001 · Decided 2026-08-04 (scaffold) · Recorded 2026-10-12 · Owner: Eneko · Status: **Accepted** · Scope: whole repo_

> The decision was taken at scaffold time and argued in
> [`WindEtAl-Architecture-Reasoning.md`](../design/WindEtAl-Architecture-Reasoning.md). This file records
> it in ADR form; the reasoning notes stay the long-form defence.

---

## 1. Context

WindEtAl computes market economics (value factor first) from external data. M1 uses
Energi Data Service; ENTSO-E, ERA5 and others are planned. The domain arithmetic is
small and stable. The data sources are many, change their field names and APIs, and need
the network.

Two pressures follow:

- The domain must be testable with **no I/O**: hand-built series, no network, no fixtures.
- Swapping or adding a data source must **not** touch the domain.

## 2. Options considered

| Option | Assessment |
|---|---|
| **Script / notebook per question** | Fastest start. Vendor field names, HTTP and arithmetic mix in one file; every new source rewrites the calculation. Rejected. |
| **Layered app with DataFrames throughout** | Familiar. A DataFrame carries no contract (columns, units, alignment), and pandas would enter the domain, making pure tests impure. Rejected. |
| **Ports and adapters** | ✅ **Chosen.** |

## 3. Decision

**Ports and adapters (Percival & Gregory, _Architecture Patterns with Python_), with dependencies pointing inward only:**

```
apps/  →  modules/ + adapters/  →  libs/core
```

1. **`libs/core` performs zero I/O and is stdlib-only.** No `requests`, files, network,
   environment variables, clock reads, or pandas. Pure functions over plain data.
2. **Ports are abstract and live in `libs/core/ports.py`** (`EnergyDataRepo`, `Zone`,
   `DateRange`). A port says *what* the domain needs and never names a provider.
3. **Adapters are the only place vendors exist** (`adapters/`). URLs, JSON shapes,
   timezone quirks of the request, rate limits and tokens stay there. A **mapper**
   translates vendor records into domain types; it is the only code that knows
   Energinet's field names.
4. **The domain defines the types adapters must produce** (`PriceSeries`,
   `GenerationSeries`, `PriceVolumeSeries`). The import direction decides this: a type
   defined in an adapter would make the domain import outward.
5. **`apps/` owns no logic.** Presentation only.

The test for any placement question: _which way would the import point?_

## 4. Consequences

**Gained**

| | |
|---|---|
| Pure domain tests | Value-factor and join tests build series by hand; no network, no mocks. |
| Contained vendor change | Energinet renames a field → only the mapper changes. |
| Swappable sources | Adding ENTSO-E = one new adapter implementing the same port. |
| Offline development | A fixture-backed implementation and the live one are interchangeable. |

**Accepted costs**

- More files and indirection than a script for a one-number result.
- Vendor-to-domain translation must be written and tested explicitly (mapper).
- Something must still wire adapter → domain. In M1 that is `scripts/m1_number.py`;
  whether `modules/*/service.py` earns its place is still open.

## 5. Related

- [ADR 0002](0002-join-location.md): where the price/generation join lives — a direct
  consequence of rule 3 (the adapter cannot guarantee alignment between two series it
  never holds at once).

## 6. Revisit if

- A data source arrives that cannot be expressed through the existing port without
  changing its shape.
- The domain needs a capability that seems to require I/O. The answer is a new port, not
  an import.
