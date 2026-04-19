# RQ3 Results and Advanced Python / Technical Execution

## 3.1 RQ3 Methods

### Research question

Do players in different positions decline at different rates after their peak market value?

### Decline metric definition

We modelled the post-peak career as a log-linear decay in market value over time. For each player we fit an ordinary least-squares regression:

```
log(market_value_eur) = α + β · age_since_peak + ε
```

where `age_since_peak` is the number of years elapsed since the player's personal peak. The slope coefficient β is the decline metric. Using the log scale means β is directly interpretable as an approximate annual proportional change: converting via `(exp(β) − 1) × 100` gives the **% change in market value per year** post-peak. A negative value indicates declining value.

This formulation has three concrete advantages over a raw-value slope: it is robust to the extreme right-skew of transfer market values, the coefficient is scale-free so it can be compared across positions with very different absolute values, and it matches the multiplicative intuition behind market value erosion (a player losing "half their value" is the same phenomenon regardless of whether they were worth €1M or €50M at peak).

### Peak identification

The peak observation for each player was identified using the `market_value_rank_desc` column in the frozen backbone, where rank = 1 corresponds to the highest recorded market value. If two observations are tied at rank 1 (i.e., the same maximum value appears more than once), `peak_age` is taken as their mean age and `peak_value` as their maximum. Only observations **strictly after** the peak age are included in the post-peak regression.

### Sample construction

Starting from 58,944 players in the frozen backbone, we required at least three post-peak market value observations to fit a meaningful regression line per player. This threshold excludes players whose peak occurs at or near their final observation, where a two-point line would be unreliable. The resulting analytic sample contains **39,332 players** distributed across the four broad positions.


## 3.2 RQ3 Results

### Peak age by position

Before examining post-peak decline, we note that peak market value age itself varies modestly across positions. The table below summarises the distribution of peak ages for the full set of players with an identified peak:

| Position | N (slope sample) | Median peak age | Mean peak age |
|---|---|---|---|
| Goalkeeper | 4,070 | 25.7 | 25.8 |
| Defender | 12,831 | 25.3 | 25.3 |
| Midfielder | 11,628 | 24.8 | 24.9 |
| Forward | 10,803 | 24.7 | 24.8 |

Goalkeepers peak latest, consistent with the role's lower dependence on explosive athleticism. Forwards peak earliest, roughly a year before Goalkeepers.

### Post-peak decline rates

| Position | N players | Median decline (% / yr) | Mean decline (% / yr) | IQR (% / yr) | Median final value / peak |
|---|---|---|---|---|---|
| Goalkeeper | 4,070 | −19.6 | −19.5 | [−31.4, −8.3] | 33.3% |
| Defender | 12,831 | −21.4 | −21.6 | [−33.0, −10.8] | 32.0% |
| Midfielder | 11,628 | −21.6 | −21.5 | [−33.4, −10.9] | 31.3% |
| Forward | 10,803 | −22.8 | −22.7 | [−34.4, −12.1] | 30.0% |

All four positions show substantial negative slopes, confirming that market value declines consistently after peak across the sport. The median player loses roughly 20–23% of their market value per year in the post-peak period.

**Goalkeepers decline most slowly** (median −19.6% / yr) and **Forwards decline fastest** (median −22.8% / yr). The median final value ratio — the ratio of market value at the last post-peak observation to the player's personal peak — ranges from 30.0% (Forward) to 33.3% (Goalkeeper), indicating that the typical player retains roughly a third of their peak value by the end of their tracked career.


### Interpretation

The position-level pattern aligns with the physical demands of each role. Forwards rely most heavily on pace, agility, and explosive movement — attributes that deteriorate with age — and their market value reflects this with the steepest post-peak decline. Goalkeepers, by contrast, depend more on positioning, decision-making, and reflexes, qualities that are more age-resilient, explaining their slower value erosion.

The Defender–Midfielder symmetry is also interpretable: both roles increasingly reward tactical intelligence and passing range over speed, leading to similar decline trajectories.

---

## 3.3 Advanced Python / Technical Execution

### Overview

The RQ3 pipeline processes 836,635 backbone rows and estimates a per-player OLS slope for 39,332 players. The primary technical challenge is that a naive loop-based implementation of this per-player regression does not scale. This section documents the profiling approach used, the bottleneck identified, and the vectorized optimization applied.

### Profiling methodology

We used Python's standard `cProfile` module to identify the dominant costs in the full pipeline, capturing cumulative time per function call. Timing was measured with `time.perf_counter()` for wall-clock precision. The profiling target was `compute_all_decline_metrics()`, which encompasses peak extraction, post-peak filtering, slope estimation, and result assembly.

### Bottleneck: per-player slope estimation

The conceptually natural implementation of the decline slope fits a separate `scipy.stats.linregress` for each player using `groupby.apply`:

```python
# Baseline: compute_decline_slopes_base()
def _slope(grp):
    s, *_ = stats.linregress(grp["age_since_peak"], grp["log_value"])
    return s

slopes = post_peak.groupby("player_id").apply(_slope, include_groups=False)
```

This creates a Python-level loop over all 39,332 player groups. Each call to `linregress` is itself fast, but the overhead of dispatching 39K Python function calls through `groupby.apply` is substantial. The per-call cost includes Python object creation, function dispatch, and NumPy array construction for each group.

### Optimization: vectorized closed-form OLS

OLS has a closed-form solution. For a univariate regression y ~ x with n observations, the slope is:

```
β = (n · Σxy − Σx · Σy) / (n · Σx² − (Σx)²)
```

All five quantities (n, Σx, Σy, Σx², Σxy) are simple aggregations that pandas can compute in a single vectorized `groupby.agg` pass, without any Python-level iteration:

```python
# Optimized: compute_decline_slopes_vectorized()
pp = post_peak.assign(
    x_sq = post_peak["age_since_peak"] ** 2,
    xy   = post_peak["age_since_peak"] * post_peak["log_value"],
)
g = pp.groupby("player_id", as_index=False).agg(
    n    = ("age_since_peak", "size"),
    sum_x  = ("age_since_peak", "sum"),
    sum_y  = ("log_value",      "sum"),
    sum_xx = ("x_sq",           "sum"),
    sum_xy = ("xy",             "sum"),
)
denom = g["n"] * g["sum_xx"] - g["sum_x"] ** 2
g["decline_slope"] = np.where(
    denom.abs() > 1e-12,
    (g["n"] * g["sum_xy"] - g["sum_x"] * g["sum_y"]) / denom,
    np.nan,
)
```

The key insight is pre-computing `x_sq` and `xy` as DataFrame columns before the `groupby`. This means the aggregation pass only needs to call `.sum()` and `.size()` — operations that pandas executes entirely in compiled C code. The division to recover the slope is then a single vectorized arithmetic expression on the grouped result.

### Benchmark results

| Implementation | Runtime (39,332 players) |
|---|---|
| Baseline (`groupby.apply` + `linregress`) | Python-level loop; prohibitively slow at scale |
| Optimized (vectorized `groupby.agg`) | **0.042 s** |

The vectorized implementation completes in under 50 milliseconds for the full 39K-player sample. This is the dominant bottleneck in the RQ3 pipeline; with it resolved, the full `compute_all_decline_metrics()` call runs in under 2 seconds end-to-end.

### Additional technical contributions (distributed)

The project-wide technical execution was distributed across all four analysis owners:

**A (preprocessing):** Implemented vectorized age calculation (`(market_value_date − date_of_birth).dt.days / 365.25`) replacing any row-wise approach; applied early column pruning after each cleaning step to reduce memory footprint; used `category` dtype for `broad_position` throughout; applied `Int32` nullable integer types for all performance metrics to avoid silent float conversion of missing values. Profiling identified `clean_performances()` as the dominant preprocessing cost (~24 s out of a 39 s end-to-end run) due to repeated string operations on the 1.9M-row performance table.

**B (RQ1):** Applied optimizations to the peak-age extraction and position-level groupby operations, reducing repeated sorting and groupby calls in the peak-age computation workflow.

**C (RQ2):** Implemented vectorized aggregation for season-level performance metrics, avoiding repeated joins when building position-specific performance profiles across seasons.

**D (RQ3):** Led the final optimization pass. Identified per-player slope estimation as the primary bottleneck in the RQ3 pipeline and replaced the `groupby.apply` baseline with the vectorized closed-form OLS described above.
