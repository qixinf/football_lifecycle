
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

VALID_POSITIONS = ["Goalkeeper", "Defender", "Midfielder", "Forward"]
POSITION_PALETTE = {
    "Goalkeeper": "#1976D2",
    "Defender":   "#388E3C",
    "Midfielder": "#F57C00",
    "Forward":    "#D32F2F",
}

def compute_peak_age(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute one peak-age observation per player from the lifecycle backbone table.

    Peak age is defined as the player's age at the earliest observation where
    market value reaches its maximum. This uses the precomputed
    `is_peak_value_obs` flag to avoid repeated groupby/apply work.
    """
    required = [
        "player_id", "player_name", "market_value_date", "market_value_eur",
        "broad_position", "age_years", "n_market_value_obs", "is_peak_value_obs"
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    work = df.copy()
    work["broad_position"] = work["broad_position"].astype(str)

    peak = work.loc[work["is_peak_value_obs"].fillna(False)].copy()
    peak = peak.sort_values(["player_id", "market_value_date"])
    peak = peak.groupby("player_id", observed=True).first().reset_index()

    peak = peak.rename(columns={"age_years": "peak_age"})
    keep_cols = [
        "player_id", "player_name", "broad_position", "peak_age",
        "market_value_eur", "market_value_date", "n_market_value_obs"
    ]
    peak = peak[keep_cols]
    peak = peak[peak["broad_position"].isin(VALID_POSITIONS)].copy()
    return peak

def compute_peak_age_naive(data):
    out = (
        data.sort_values(["player_id", "market_value_date"])
            .groupby("player_id", observed=True)
            .apply(lambda x: x.loc[x["market_value_eur"].eq(x["market_value_eur"].max())].iloc[0])
            .reset_index(drop=True)
    )
    return out

def compute_peak_age_optimized(data):
    peak = (
        data.loc[data["is_peak_value_obs"].fillna(False)]
            .sort_values(["player_id", "market_value_date"])
    )
    out = peak.groupby("player_id", observed=True).first().reset_index()
    return out

def summarize_peak_age(peak_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        peak_df.groupby("broad_position", observed=True)["peak_age"]
        .agg(mean="mean", median="median", std="std", count="count", min="min", max="max")
        .reset_index()
        .sort_values("mean", ascending=False)
    )
    return summary

def plot_peak_age_boxplot(peak_df: pd.DataFrame, output_path: str | None = None):
    data = peak_df[peak_df["broad_position"].isin(VALID_POSITIONS)].copy()
    data["broad_position"] = pd.Categorical(
        data["broad_position"], categories=VALID_POSITIONS, ordered=True
    )

    _, ax = plt.subplots(figsize=(10, 6))

    sns.boxplot(
        data=data,
        x="broad_position",
        y="peak_age",
        hue="broad_position",
        order=VALID_POSITIONS,
        hue_order=VALID_POSITIONS,
        palette=POSITION_PALETTE,
        width=0.45,
        showfliers=True,
        linewidth=1.2,
        legend=False,
        ax=ax,
    )

    # Median annotation above each median line, matching D's annotation style
    for i, pos in enumerate(VALID_POSITIONS):
        s = data.loc[data["broad_position"] == pos, "peak_age"].dropna()
        median_val = s.median()
        ax.text(i, median_val + 0.3, f"{median_val:.1f}",
                ha="center", va="bottom", fontsize=9, fontweight="bold", color="#222222")

    # Sample-size annotation below each box
    counts = data.groupby("broad_position", observed=True)["peak_age"].count()
    for i, pos in enumerate(VALID_POSITIONS):
        n = counts.get(pos, 0)
        ax.text(i, ax.get_ylim()[0] + 0.3, f"n={n:,}",
                ha="center", va="bottom", fontsize=8.5, color="#444444")

    ax.set_xlabel("")
    ax.set_ylabel("Peak age (years)", fontsize=11)
    ax.set_title("Age at Peak Market Value by Broad Position",
                 fontsize=13, fontweight="bold")
    ax.tick_params(axis="x", labelsize=11)
    ax.tick_params(axis="y", labelsize=10)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
    return ax


def plot_peak_age_mean_ci(peak_df: pd.DataFrame, output_path: str | None = None):
    stats_df = (
        peak_df.groupby("broad_position", observed=True)["peak_age"]
        .agg(["mean", "count", "std"])
        .reindex(VALID_POSITIONS)
        .reset_index()
    )
    stats_df["se"] = stats_df["std"] / np.sqrt(stats_df["count"])
    stats_df["ci95"] = 1.96 * stats_df["se"]

    colors = [POSITION_PALETTE[pos] for pos in stats_df["broad_position"]]

    _, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(
        stats_df["broad_position"].astype(str),
        stats_df["mean"],
        yerr=stats_df["ci95"],
        capsize=5,
        color=colors,
        alpha=0.85,
        linewidth=1.2,
        edgecolor="white",
    )

    # μ= annotation above each bar's error cap, matching D's annotation style
    for bar, mean_val, ci in zip(bars, stats_df["mean"], stats_df["ci95"]):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            mean_val + ci + 0.1,
            f"μ={mean_val:.1f}",
            ha="center", va="bottom", fontsize=9, fontweight="bold", color="#222222",
        )

    ax.set_xlabel("")
    ax.set_ylabel("Mean peak age (years)", fontsize=11)
    ax.set_title("Mean Peak Age by Broad Position (95% CI)",
                 fontsize=13, fontweight="bold")
    ax.tick_params(labelsize=11)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=200, bbox_inches="tight")
    return ax
