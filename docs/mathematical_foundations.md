# Mathematical Foundations

## Table of contents

1. [Purpose](#purpose)
2. [Vector operations](#vector-operations)
3. [Signal construction](#signal-construction)
4. [Emotional update equation](#emotional-update-equation)
5. [Similarity metrics](#similarity-metrics)
6. [Risk equations](#risk-equations)
7. [Trend, momentum, moving average, volatility](#trend-momentum-moving-average-volatility)
8. [Differential privacy noise](#differential-privacy-noise)
9. [Current implementation and future extension](#current-implementation-and-future-extension)
10. [Related documentation](#related-documentation)

## Purpose

This document gathers equations used across the system so other documents can reference them without duplicating derivations.

## Vector operations

Vectors are fixed-length arrays. Emotional vectors have dimension 4; memory embeddings have dimension 768. Clipping is defined as `clip(x,l,u)=max(l,min(u,x))`.

## Signal construction

For each axis, the rule-based signal combines polarity, negativity, and keyword score:

```text
S_axis = clip(w1 * polarity + w2 * negativity + w3 * keyword_axis, -1, 1)
```

Axis-specific weights are configured in code constants.

## Emotional update equation

```text
V_next = clip((1 - lambda)V_current + alpha S, -1, 1)
```

This is an exponential smoothing style recurrence. Decay reduces stale state; sensitivity controls how strongly the current message changes the vector.

## Similarity metrics

pgvector cosine distance is used for memory retrieval:

```text
cosine_distance(a,b) = 1 - (a · b)/(||a|| ||b||)
```

Lower distance means greater similarity.

## Risk equations

```text
risk = clip(0.20d + 0.30sh + 0.40s + 0.10a, 0, 1)
```

Because weights sum to 1, the score remains interpretable as a weighted normalized aggregate when inputs are in `[0,1]`.

## Trend, momentum, moving average, volatility

```text
M_t = V_t - V_{t-1}
MA_i = (1/n) sum V_j[i]
volatility = sqrt((1/n) sum (risk_j - mean_risk)^2)
slope = sum((x_i - mean_x)(y_i - mean_y)) / sum((x_i - mean_x)^2)
```

Trend is `IMPROVING` if slope `< -0.01`, `DECLINING` if slope `> 0.01`, and `STABLE` otherwise.

## Differential privacy noise

```text
V_private = clip(V + N(0, sigma^2), -1, 1)
```

The current mechanism is optional and does not include privacy-budget composition accounting.

## Current implementation and future extension

### Current Implementation

All equations above are implemented as lightweight Python functions with deterministic tests possible for most components.

### Future Extension

Add formal calibration notes, empirical validation, and explicit numeric bounds for clinically reviewed operation.

## Related documentation

- [Architecture](architecture.md) for the end-to-end backend structure.
- [Database schema](database_schema.md) for persistence details.
- [Privacy model](privacy_model.md) and [Threat model](threat_model.md) for security and privacy constraints.
- [Mathematical foundations](mathematical_foundations.md) for equations used by the engines.
