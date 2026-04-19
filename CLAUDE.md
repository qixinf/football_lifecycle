# Football Lifecycle Project — CLAUDE.md

**Project:** Position-Specific Career Lifecycle Curves in Professional Football  
**Course:** Spring 2026 Python course (final project)  
**Priority:** Code + presentation first; written report second.

---

## Project layout

```
football_lifecycle/
├── data/
│   ├── raw/                          # original source files, never modified
│   │   ├── player_profiles.csv
│   │   ├── player_market_value.csv
│   │   └── player_performances.txt
│   ├── interim/                      # cleaned intermediate parquets (A's output)
│   │   ├── player_profiles_clean.parquet
│   │   ├── player_market_value_clean.parquet
│   │   └── player_performances_clean.parquet
│   └── processed/                    # frozen backbone used by all RQ notebooks
│       └── player_lifecycle_backbone.parquet
├── notebooks/
│   ├── 01_A_preprocessing_and_merge.ipynb   # DONE — A's notebook
│   ├── 02_B_rq1_peak_age_analysis.ipynb     # TODO — B
│   ├── 03_C_rq2_peak_performance_analysis.ipynb  # TODO — C
│   └── 04_D_rq3_post_peak_decline_analysis.ipynb # DONE — D
├── src/
│   ├── a_preprocessing_utils.py      # DONE
│   └── d_rq3_decline_utils.py        # DONE
├── outputs/
│   ├── figures/
│   ├── tables/
│   └── profiling/
├── report/
└── slides/
```

---

## Data overview

### Raw sources
Downloaded from the salimt/football-datasets GitHub repository (Transfermarkt data).

| File | Rows | Key columns |
|---|---|---|
| `player_profiles.csv` | 92,671 players | player_id, date_of_birth, main_position |
| `player_market_value.csv` | 901,429 rows | player_id, date_unix, value |
| `player_performances.txt` | 1,878,719 rows | player_id, season_name, goals, assists, minutes_played, clean_sheets |

### Cleaned interim tables (parquet)

**`player_profiles_clean.parquet`** — 92,671 rows  
`player_id`, `player_name`, `date_of_birth`, `raw_position`, `raw_sub_position`, `broad_position` (category), `joined`, `contract_expires`, `current_club_id`

**`player_market_value_clean.parquet`** — 901,429 rows  
`player_id`, `market_value_date`, `market_value_eur`

**`player_performances_clean.parquet`** — 1,878,719 rows  
`player_id`, `season`, `season_start_year`, `competition_id`, `competition_name`, `team_id`, `team_name`, `nb_in_group`, `nb_on_pitch`, `goals`, `assists`, `own_goals`, `subed_in`, `subed_out`, `yellow_cards`, `second_yellow_cards`, `direct_red_cards`, `penalty_goals`, `minutes_played`, `goals_conceded`, `clean_sheets`

> `minutes_played` is missing for ~62% of rows. Use `nb_on_pitch` (appearances) as denominator for per-game rates instead.

### Frozen backbone (`player_lifecycle_backbone.parquet`) — 836,635 rows, 58,944 players

The single shared dataset all RQ notebooks read from. **Do not regenerate without team agreement.**

| Column | Type | Description |
|---|---|---|
| `player_id` | string | Player identifier |
| `market_value_date` | datetime | Date of market value snapshot |
| `market_value_eur` | float64 | Market value in EUR |
| `player_name` | string | Display name |
| `date_of_birth` | datetime | Date of birth |
| `age_days` | float64 | Age in days at observation date |
| `age_years` | float64 | Age in years at observation date |
| `broad_position` | category | Goalkeeper / Defender / Midfielder / Forward |
| `n_market_value_obs` | Int32 | Total observations for this player |
| `market_value_rank_desc` | Int32 | Dense descending rank within player (1 = peak) |
| `is_peak_value_obs` | bool | True when market_value_rank_desc == 1 |
| `raw_position` | string | Original position string from source |
| `raw_sub_position` | string | Original sub-position string from source |

**Backbone filters applied:** positive market value, age 14–45, known broad position, ≥ 3 market value observations per player.

**Position counts in backbone:**

| Position | Rows |
|---|---|
| Defender | 275,452 |
| Midfielder | 246,939 |
| Forward | 227,838 |
| Goalkeeper | 86,406 |

---

## Research questions

| Owner | RQ | Notebook | Utils | Status |
|---|---|---|---|---|
| A | Preprocessing | `01_A_preprocessing_and_merge.ipynb` | `a_preprocessing_utils.py` | Done |
| B | Do players in different positions reach peak market value at different ages? | `02_B_rq1_peak_age_analysis.ipynb` | `b_rq1_peak_age_utils.py` | TODO |
| C | Do players in different positions exhibit different peak-performance profiles? | `03_C_rq2_peak_performance_analysis.ipynb` | `c_rq2_performance_utils.py` | TODO |
| D | Do players in different positions decline at different rates after their peak? | `04_D_rq3_post_peak_decline_analysis.ipynb` | `d_rq3_decline_utils.py` | Done |

---

## Position mapping

Broad positions are mapped from the raw `main_position` field via regex in `map_broad_position()`:

| Broad position | Keywords matched |
|---|---|
| Goalkeeper | goalkeeper, keeper |
| Defender | defender, centre back, left back, right back, full back, sweeper |
| Midfielder | midfield, defensive midfield, attacking midfield, central midfield |
| Forward | forward, striker, winger, attack, inside forward, second striker |

---

## Known data issues

- `date_of_birth` missing for ~1,006 players — those players are excluded from the backbone.
- `minutes_played` missing ~62% of rows in performances table — never use as a reliable filter or denominator for the full sample; use `nb_on_pitch` instead.
- Performance table has no date column — season alignment to market value observations must use `season_start_year` + player `date_of_birth`, not a direct join on date.
- Joining performance table directly to backbone on `player_id` alone creates many-to-many duplication — always aggregate performance per `(player_id, season_start_year)` first.

---

## RQ3 key results (D — completed)

Decline metric: log-linear OLS slope of `log(market_value_eur) ~ age_since_peak`, converted to `% change per year = (exp(slope) - 1) * 100`. Minimum 3 post-peak observations required per player.

| Position | N players | Median peak age | Median decline |
|---|---|---|---|
| Goalkeeper | 4,070 | 25.7 | −19.6% / yr |
| Defender | 12,831 | 25.3 | −21.4% / yr |
| Midfielder | 11,628 | 24.8 | −21.6% / yr |
| Forward | 10,803 | 24.7 | −22.8% / yr |

Kruskal-Wallis: H = 108.3, p = 2.5×10⁻²³. Goalkeepers decline slowest; Forwards fastest. Defender vs Midfielder difference is not significant (Bonferroni-corrected p = 1.0).

---

## `d_rq3_decline_utils.py` — function reference

| Function | Returns | Notes |
|---|---|---|
| `extract_peak_per_player(backbone)` | DataFrame | peak_age (mean if tied), peak_value, broad_position per player |
| `extract_post_peak_data(backbone, peak_per_player)` | DataFrame | backbone rows after peak_age; adds age_since_peak, log_value, value_ratio |
| `compute_decline_slopes_vectorized(post_peak)` | DataFrame | OLS slope per player via closed-form groupby aggregations; ~10x faster than apply |
| `compute_decline_slopes_apply(post_peak)` | DataFrame | Baseline using groupby.apply + scipy.linregress; use only for profiling comparison |
| `compute_all_decline_metrics(backbone, min_post_peak_obs=3)` | tuple(3) | Full pipeline; returns (peak_per_player, post_peak_filtered, decline_df) |
| `summarize_decline_by_position(decline_df)` | DataFrame | Median/mean decline rate, IQR, peak age by position |
| `run_kruskal_wallis(decline_df)` | dict | H, p-value, n_groups |
| `run_pairwise_mannwhitney(decline_df)` | DataFrame | All pairs, Bonferroni-corrected p-values |
| `build_performance_post_peak(perf, profiles, peak_per_player)` | DataFrame | Season-level pre/post-peak output table; uses nb_on_pitch not minutes_played |
| `plot_decline_boxplot(decline_df, ax)` | ax | Figure 1 |
| `plot_mean_trajectory(post_peak_filtered, ax)` | ax | Figure 2; post_peak_filtered already has broad_position — do NOT merge with peak_per_player again |
| `plot_contribution_pre_post(perf_df, fig)` | fig | Figure 3 |

> **Known bug (fixed):** `plot_mean_trajectory` originally took `peak_per_player` as a second argument and merged on it, which caused `broad_position` to be renamed to `broad_position_x`/`_y` → `KeyError`. The parameter was removed; the function now uses the `broad_position` column already present in `post_peak_filtered`.

---

## Environment

- Python 3.10 (`.venv` at `/Users/fqxin/Desktop/1019_Py/.venv`)
- Key packages: `pandas`, `numpy`, `scipy`, `matplotlib`, `seaborn`, `pyarrow`
- Install missing packages: `.venv/bin/pip install pyarrow scipy matplotlib seaborn`
- Run scripts: `.venv/bin/python` (not system python3)
- Notebooks developed on Google Colab (A) and locally (D); path resolution handles both via `_candidates` list at top of each notebook

---

## Shared conventions

- **Position order** for all plots and tables: `["Goalkeeper", "Defender", "Midfielder", "Forward"]`
- **Position palette:** GK `#1976D2`, DEF `#388E3C`, MID `#F57C00`, FWD `#D32F2F`
- All figures saved to `outputs/figures/`, tables to `outputs/tables/`, profiling notes to `outputs/profiling/`
- Each RQ notebook must include: cProfile timing, a before/after benchmark for at least one optimization, and a saved `*_profile.md`
- Performance join pattern: merge `performances_clean` with `profiles_clean` to get DOB → compute `age_at_season = season_start_year + 0.5 - birth_year` → then join with `peak_per_player` for peak_age
