# M1 prediction — DK1 onshore wind value factor, June 2025

_Written 2026-10-12, before pulling any data. (Late vs. ship-week plan; recorded honestly.)_

**Predicted value factor: 0.77**

Reasoning: solar takes the cheapest midday hours (~€32) when wind is low, but when DK1
wind does blow it crashes its own price to ~€25 despite interconnection, and it misses
the calm evening peak (~€85) — so wind earns well below the €42 average.

Toy model (per day; output weights relative):

| Bucket              | Hours | Price | Wind output |
|---------------------|-------|-------|-------------|
| Solar midday (9–16) | 8     | €32   | 0.5         |
| Windy non-solar     | 10    | €25   | 2           |
| Calm evening peak   | 6     | €85   | 0.5         |

Implied: time-average €42.3, captured €32.7, VF 0.77.
