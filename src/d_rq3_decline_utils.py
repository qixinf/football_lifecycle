from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats


POSITION_ORDER = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
POSITION_PALETTE = {
    "Goalkeeper": "#1976D2",
    "Defender":   "#388E3C",
    "Midfielder": "#F57C00",
    "Forward":    "#D32F2F",
}


# Peak data
def extract_peak_per_player(backbone: pd.DataFrame) -> pd.DataFrame:
    """
    For each player, return peak_age (mean when tied) and peak_value (max when tied).
    Only considers rows where market_value_rank_desc = 1, the peak.
    """
    peak = (
        backbone[backbone["market_value_rank_desc"] == 1]
        .sort_values(["player_id", "age_years"])
        .groupby("player_id", as_index=False)
        .agg(
            peak_age=("age_years", "mean"), # mean handles ties: if two obs share rank=1, average their ages
            peak_value=("market_value_eur", "max"),
            broad_position=("broad_position", "first") 
        )
    )
    return peak


# Post-peak data
def extract_post_peak_data(backbone: pd.DataFrame, peak_per_player: pd.DataFrame) -> pd.DataFrame:
    """
    Keep only backbone rows strictly after each player's peak age.
    Adds age_since_peak, log_value, and value_ratio (value / peak_value).
    """
    df = backbone.merge(
        peak_per_player[["player_id", "peak_age", "peak_value"]],
        on="player_id",
        how="inner",
    )
    post = df[df["age_years"] > df["peak_age"]].copy()
    post["age_since_peak"] = post["age_years"] - post["peak_age"]
    post["log_value"] = np.log(post["market_value_eur"])
    post["value_ratio"] = post["market_value_eur"] / post["peak_value"]
    return post.reset_index(drop=True)


# Decline slope estimation (vectorized OLS)
def compute_decline_slopes_vectorized(post_peak: pd.DataFrame) -> pd.DataFrame:
    """
    Fit OLS log(market_value_eur) ~ age_since_peak per player using the
    closed-form formula applied through vectorized groupby aggregations.

    Equivalent to scipy.stats.linregress per player but ~10x faster on
    large datasets because it avoids Python-level iteration.

    Returns a DataFrame with player_id, decline_slope, n_post_peak_obs.
    A negative slope means market value is falling after peak.
    """
    pp = post_peak.assign(
        x_sq=post_peak["age_since_peak"] ** 2,
        xy=post_peak["age_since_peak"] * post_peak["log_value"],
    )
    g = pp.groupby("player_id", as_index=False).agg(
        n=("age_since_peak", "size"),
        sum_x=("age_since_peak", "sum"),
        sum_y=("log_value", "sum"),
        sum_xx=("x_sq", "sum"),
        sum_xy=("xy", "sum"),
    )
    denom = g["n"] * g["sum_xx"] - g["sum_x"] ** 2
    g["decline_slope"] = np.where(
        denom.abs() > 1e-12,
        (g["n"] * g["sum_xy"] - g["sum_x"] * g["sum_y"]) / denom,
        np.nan,
    )
    return (
        g[["player_id", "decline_slope", "n"]]
        .rename(columns={"n": "n_post_peak_obs"})
    )

# Decline slope estimation (baseline)
def compute_decline_slopes_base(post_peak: pd.DataFrame) -> pd.DataFrame:
    """
    Baseline (non-optimized) version using groupby.apply + scipy linregress.
    Used for profiling comparison against compute_decline_slopes_vectorized.
    """
    def _slope(grp):
        if len(grp) < 2:
            return np.nan
        s, *_ = stats.linregress(grp["age_since_peak"], grp["log_value"])
        return s

    slopes = (
        post_peak.groupby("player_id")
        .apply(_slope, include_groups=False)
        .rename("decline_slope")
        .reset_index()
    )
    counts = (
        post_peak.groupby("player_id", as_index=False)
        .size()
        .rename(columns={"size": "n_post_peak_obs"})
    )
    return slopes.merge(counts, on="player_id")


# Full pipeline
def compute_all_decline_metrics(
    backbone: pd.DataFrame,
    min_post_peak_obs: int = 3,
) -> tuple:
    """
    End-to-end pipeline:
      1. Extract peak per player from backbone.
      2. Extract post-peak observations.
      3. Filter to players with at least min_post_peak_obs post-peak rows.
      4. Fit vectorized decline slope.
      5. Attach final value ratio (value at last post-peak obs / peak).

    Returns (peak_per_player, post_peak_filtered, decline_df).
    decline_df adds decline_pct_per_year = (exp(slope) - 1) * 100,
    which is interpretable as the approximate % change in market value per year.
    """
    peak_per_player = extract_peak_per_player(backbone)
    post_peak = extract_post_peak_data(backbone, peak_per_player)

    n_post = post_peak.groupby("player_id").size()
    eligible = n_post[n_post >= min_post_peak_obs].index
    post_peak_filtered = post_peak[post_peak["player_id"].isin(eligible)].copy()

    slopes = compute_decline_slopes_vectorized(post_peak_filtered)

    last_obs = (
        post_peak_filtered
        .sort_values("age_years")
        .groupby("player_id", as_index=False)
        .last()[["player_id", "value_ratio", "age_years"]]
        .rename(columns={"value_ratio": "final_value_ratio", "age_years": "last_obs_age"})
    )

    decline_df = (
        peak_per_player
        .merge(slopes, on="player_id", how="inner")
        .merge(last_obs, on="player_id", how="left")
        .dropna(subset=["decline_slope"])
    )
    decline_df["decline_pct_per_year"] = (np.exp(decline_df["decline_slope"]) - 1) * 100
    decline_df["broad_position"] = decline_df["broad_position"].astype("category")
    return peak_per_player, post_peak_filtered, decline_df


# Summary statistics
def summarize_decline_by_position(decline_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-position summary: player count, median peak age, median/mean decline rate,
    IQR of decline rate, and median final value ratio.
    """
    summary = (
        decline_df[decline_df["broad_position"].isin(POSITION_ORDER)]
        .groupby("broad_position", observed=True)
        .agg(
            n_players=("player_id", "count"),
            median_peak_age=("peak_age", "median"),
            mean_peak_age=("peak_age", "mean"),
            median_decline_pct_yr=("decline_pct_per_year", "median"),
            mean_decline_pct_yr=("decline_pct_per_year", "mean"),
            q25_decline=("decline_pct_per_year", lambda x: x.quantile(0.25)),
            q75_decline=("decline_pct_per_year", lambda x: x.quantile(0.75)),
            median_final_value_ratio=("final_value_ratio", "median"),
        )
        .reset_index()
    )
    summary["broad_position"] = pd.Categorical(
        summary["broad_position"], categories=POSITION_ORDER, ordered=True
    )
    return summary.sort_values("broad_position").reset_index(drop=True)

# ---------------------------------------------------------------------------
# Figures

def plot_decline_boxplot(decline_df: pd.DataFrame, ax=None):
    """
    Hybrid box plot of annual % market value change post-peak by position.
    Y-axis is fitted to the actual 1.5*IQR whisker extents so no whisker tip is clipped.
    Individual outlier points are hidden (showfliers=False) for a cleaner look.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 5))

    data = (
        decline_df[decline_df["broad_position"].isin(POSITION_ORDER)]
        .assign(
            broad_position=lambda d: pd.Categorical(
                d["broad_position"], categories=POSITION_ORDER, ordered=True
            )
        )
    )

    sns.boxplot(
        data=data,
        x="broad_position",
        y="decline_pct_per_year",
        hue="broad_position",
        order=POSITION_ORDER,
        hue_order=POSITION_ORDER,
        palette=POSITION_PALETTE,
        width=0.45,
        showfliers=False,
        linewidth=1.2,
        legend=False,
        ax=ax,
    )

    ax.axhline(0, color="crimson", linewidth=1.0, linestyle="--", alpha=0.7, label="No change")

    # --- y-axis: fit to actual whisker extents (1.5*IQR per position) ---
    # Using percentiles of the raw series would clip whisker tips because the
    # whisker top (last point within Q3 + 1.5*IQR) can exceed p97.5 of the
    # pooled distribution.  Computing bounds position-by-position is exact.
    whisker_lo, whisker_hi = [], []
    for pos in POSITION_ORDER:
        s = data.loc[data["broad_position"] == pos, "decline_pct_per_year"].dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        whisker_lo.append(s[s >= q1 - 1.5 * iqr].min())
        whisker_hi.append(s[s <= q3 + 1.5 * iqr].max())
    y_lo, y_hi = min(whisker_lo), max(whisker_hi)
    pad = (y_hi - y_lo) * 0.10          # 10 % headroom above/below whisker tips
    ax.set_ylim(min(y_lo - pad, -5), max(y_hi + pad, 5))

    # --- y-axis: format as % with sign ---
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
    ax.yaxis.set_major_locator(mticker.MultipleLocator(10))   # tick every 5%

    # --- sample size annotation under each box ---
    counts = data.groupby("broad_position", observed=True)["decline_pct_per_year"].count()
    for i, pos in enumerate(POSITION_ORDER):
        n = counts.get(pos, 0)
        ax.text(i, ax.get_ylim()[0] + 0.5, f"n={n}",
                ha="center", va="bottom", fontsize=8.5, color="#444444")

    # --- labels ---
    ax.set_xlabel("")                           
    ax.set_ylabel("Annual Market Value Change (% / year)", fontsize=11)
    ax.set_title("Post-Peak Market Value Decline Rate by Position",
                 fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", labelsize=11)
    ax.tick_params(axis="y", labelsize=10)

    # --- footnote: whiskers = 1.5*IQR; individual outlier points hidden ---
    ax.annotate(
        "Whiskers extend to 1.5 × IQR. Individual outlier points not shown.",
        xy=(0, -0.13), xycoords="axes fraction",
        fontsize=7.5, color="#666666", ha="left"
    )

    return ax

def plot_mean_trajectory(
    post_peak: pd.DataFrame,
    ax=None,
    max_years_since_peak: float = 8.0,
):
    """
    Mean (value / peak_value) vs years-since-peak, one line per position.
    Observations are binned into 0.5-year intervals and averaged per bin.
    The dashed line at y=1.0 marks the peak level.

    post_peak must already contain broad_position (it comes from the backbone
    via extract_post_peak_data, which inherits all backbone columns).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 5))

    pp = post_peak[post_peak["age_since_peak"] <= max_years_since_peak].copy()
    pp["years_bin"] = (pp["age_since_peak"] * 2).round() / 2

    traj = (
        pp.groupby(["broad_position", "years_bin"], observed=True)["value_ratio"]
        .mean()
        .reset_index()
    )

    for pos in POSITION_ORDER:
        sub = traj[traj["broad_position"] == pos].sort_values("years_bin")
        if sub.empty:
            continue
        ax.plot(
            sub["years_bin"],
            sub["value_ratio"],
            label=pos,
            color=POSITION_PALETTE[pos],
            linewidth=2.2,
            marker="o",
            markersize=3.5,
        )

    ax.axhline(1.0, color="gray", linewidth=0.8, linestyle="--", alpha=0.6, label="Peak level")
    ax.set_xlabel("Years After Peak Market Value", fontsize=12)
    ax.set_ylabel("Mean Value / Peak Value", fontsize=11)
    ax.set_title("Average Post-Peak Market Value Trajectory by Position", fontsize=13, fontweight="bold")
    ax.legend(title="Position", fontsize=10)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=0))
    ax.tick_params(labelsize=11)
    return ax
