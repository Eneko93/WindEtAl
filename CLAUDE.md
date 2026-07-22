# CLAUDE.md — WindEtAl

Guidance for Claude Code when working in this repository.
Status: **scaffold stage.** Module 1 design doc not yet written. No production code exists.

---

## What this project is

WindEtAl is a monorepo for wind-energy × electricity-market analysis.

**Module 1 (current, and the only active work): Capture price / best-site economics — Denmark.**
Question: which Danish bidding zone ranks best on *revenue*, not just wind resource?

Core concept — **value factor**:

```
captured price = volume-weighted average price (weighted by own output)
value factor   = captured price / time-average price

equivalently:
value factor   = 1 + cov(output, price) / (mean(output) * mean(price))
```

Wind output and price are **negatively** covariant: windy hours are windy for everyone,
cheap wind floods the merit order, price falls. So value factor sits below 1, and a
windier site can earn *less per MWh* than a calmer one. That is cannibalization, and it
is the entire argument for this project. Do not "simplify" it away.

---

## Non-negotiable architecture rules

Ports-and-adapters (cosmic-python style). **Dependency arrows point inward only:**

```
apps/  →  modules/  →  libs/core
```

Never the reverse. Concretely:

1. **`libs/core` performs zero I/O.** No `requests`, no `open()`, no reading files, no
   network, no environment variables, no clock reads. Pure functions over plain data.
   If a change would make `libs/core` import from `modules/` or `apps/`, the change is
   wrong — something belongs in a different layer.
2. **Ports are abstract.** `modules/*/ports.py` declares *what* is needed from a data
   source. It never names a provider.
3. **Adapters are the only place vendors exist.** URLs, JSON shapes, pagination,
   timezone quirks, API tokens — all confined to `modules/*/adapters/`. Swapping
   Energinet for ENTSO-E must mean one new adapter file and nothing else.
4. **`apps/` owns no logic.** Presentation only. Streamlit today; the graduation path to
   Dash or Reflex must stay cheap, so no calculation leaks into the app layer.

---

## Working agreement — read this before offering help

The owner (Eneko) is deliberately building architecture and testing judgment. Claude's
role is **reviewer and sounding board, not originator.**

**Do not, unless explicitly asked:**
- Propose or impose an architecture, module boundary, or domain model.
- Decide what the first test should be, or write tests unprompted.
- Write implementation code ahead of a written design doc for that module.
- Expand scope beyond the current thin slice.

**Do:**
- Critique decisions already made — find the flaw, name the tradeoff, ask the sharp question.
- Point out violations of the dependency rule immediately.
- Ask what a decision is *for* when the rationale isn't written down.
- Answer direct technical questions plainly.

**Design-doc-first is a hard gate.** Every module gets a markdown design doc in
`docs/design/` before any implementation. If asked to write code for a module whose
design doc doesn't exist yet, say so and stop.

**Thin vertical slices.** Ship a narrow thing end-to-end, then widen. Resist adding a
second data source, a second zone, or a model "while we're here."

---

## Repository layout

```
libs/core/              Domain logic. Zero I/O. Value factor lives here.
  models.py             Domain types
  economics.py          captured_price(), value_factor()

modules/m1_data_analysis/
  ports.py              Abstract repository interfaces
  adapters/energinet.py Concrete Energi Data Service client
  service.py            Orchestration: port -> core -> result

apps/dashboard/app.py   Streamlit. Imports service. No logic.

docs/design/            Design docs, one per module. Written BEFORE code.
docs/adr/               Architecture Decision Records. Numbered, append-only, dated.

tests/unit/             Fast. No network. Covers libs/core.
tests/integration/      Slow. Touches real or recorded API responses.
```

---

## Scope of the current slice (Module 1, v1)

**In:** DK1, one month, day-ahead prices + wind generation from Energi Data Service
(no token required). Output = one number (value factor for DK1) plus one chart.

**Explicitly out — do not build, suggest, or scaffold these yet:**
- Per-site analysis, ERA5, Renewables.ninja
- ENTSO-E (token-gated; later, for cross-border and validation)
- Any ML: LightGBM, walk-forward CV, SHAP
- FastAPI, MLflow, Docker, CI/CD, Kubernetes

These are gated behind later milestones on purpose. Raising them early is scope creep.

---

## Conventions

- Python. `pandas` is fine in adapters and services; keep it out of `libs/core` where
  plain types will do.
- Charts must **argue a claim**, not label a topic. Titles state the finding
  ("DK1 wind earns 12% below the average price"), never the subject ("Value factor by zone").
- Commit messages: conventional style (`feat:`, `chore:`, `docs:`, `test:`).
- Timestamps: be explicit about timezone and whether a stamp marks interval start or end.
  Danish market data will bite here.

---

## Not yet decided — do not invent answers to these

These are open and belong to the owner. If a task depends on one, ask rather than assume:

- [ ] Contents of the domain types (`PricePoint`, generation representation)
- [ ] Whether `service.py` is justified in a slice this thin, or the app calls core directly
- [ ] The first test
- [ ] Exact Energi Data Service endpoint, fields, and grain
- [ ] Persistence: whether raw pulls are cached to disk, and in what format

---

## Maintaining this file

Update when a decision moves from the open list to settled, or when a rule changes —
not to narrate progress. If something here contradicts the current design doc, the
design doc wins and this file is stale: say so.
