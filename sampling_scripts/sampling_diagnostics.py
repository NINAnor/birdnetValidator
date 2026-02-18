"""Diagnostic plots for annotation sampling datasets."""

import ast
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _parse_arrays(species_list, confidence_list):
    """Parse species/confidence arrays, handling string representations."""
    if isinstance(species_list, str):
        species_list = ast.literal_eval(species_list)
        confidence_list = ast.literal_eval(confidence_list)
    return species_list, confidence_list


def _expand_species_data(df, target_species):
    """Expand dataframe to one row per species detection."""
    records = []
    for _, row in df.iterrows():
        species_list, confidence_list = _parse_arrays(
            row["scientific name"], row["confidence"]
        )
        device_id = row.get("device_id", "unknown")

        for i, species in enumerate(species_list):
            if species in target_species and i < len(confidence_list):
                records.append(
                    {
                        "species": species,
                        "confidence": float(confidence_list[i]),
                        "device_id": device_id,
                    }
                )

    return pd.DataFrame(records)


def generate_diagnostics(
    df, target_species, output_dir, bin_size=0.1, sampling_metadata=None
):
    """
    Generate diagnostic plots for a sampled dataset.

    Args:
        df: Sampled DataFrame
        target_species: List of target species names
        output_dir: Directory to save plots
        bin_size: Confidence bin size for histograms
        sampling_metadata: Optional DataFrame with columns
            [species, confidence, device_id, confidence_bin]
            tracking which species each segment was
            specifically sampled for
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create confidence bins
    bins = np.arange(0, 1 + bin_size, bin_size)
    bin_labels = [f"{bins[i]:.1f}-{bins[i + 1]:.1f}" for i in range(len(bins) - 1)]

    # Generate "sampled-for" plots using metadata (shows what was actually targeted)
    if sampling_metadata is not None and not sampling_metadata.empty:
        print("  Generating sampled-for diagnostics...")
        _plot_sampled_for_species_confidence(
            sampling_metadata, target_species, bin_labels, output_path
        )
        _plot_sampled_for_site_confidence(sampling_metadata, bin_labels, output_path)
        _plot_sampled_for_species_site(sampling_metadata, target_species, output_path)

    # Also generate "all-species" plots (shows all species in each segment)
    expanded_df = _expand_species_data(df, target_species)
    if not expanded_df.empty:
        print("  Generating all-species diagnostics...")
        expanded_df["conf_bin"] = pd.cut(
            expanded_df["confidence"], bins=bins, labels=bin_labels, include_lowest=True
        )
        _plot_species_by_confidence(
            expanded_df, target_species, bin_labels, output_path, suffix="_all_species"
        )
        _plot_site_by_confidence(
            expanded_df, bin_labels, output_path, suffix="_all_species"
        )
        _plot_species_site_matrix(
            expanded_df, target_species, output_path, suffix="_all_species"
        )
        _plot_confidence_distribution(expanded_df, output_path)

    print(f"  ✓ Saved diagnostic plots to {output_path}/")


def _plot_sampled_for_species_confidence(
    metadata, target_species, bin_labels, output_path
):
    """Plot samples per species per confidence bin using sampling metadata."""
    fig, ax = plt.subplots(figsize=(12, max(6, len(target_species) * 0.5)))

    pivot = (
        metadata.groupby(["species", "confidence_bin"], observed=True)
        .size()
        .unstack(fill_value=0)
    )

    for species in target_species:
        if species not in pivot.index:
            pivot.loc[species] = 0
    for bin_label in bin_labels:
        if bin_label not in pivot.columns:
            pivot[bin_label] = 0

    pivot = pivot.reindex(columns=bin_labels).reindex(target_species)

    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")

    ax.set_xticks(range(len(bin_labels)))
    ax.set_xticklabels(bin_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(target_species)))
    ax.set_yticklabels(target_species)

    for i in range(len(target_species)):
        for j in range(len(bin_labels)):
            val = pivot.iloc[i, j]
            color = "white" if val > pivot.values.max() / 2 else "black"
            ax.text(j, i, int(val), ha="center", va="center", color=color, fontsize=8)

    ax.set_xlabel("Confidence Bin")
    ax.set_ylabel("Species")
    ax.set_title("Samples per Species by Confidence Bin (Sampled-For)")

    plt.colorbar(im, ax=ax, label="Count")
    plt.tight_layout()
    plt.savefig(output_path / "species_by_confidence_sampled_for.png", dpi=150)
    plt.close()


def _plot_sampled_for_site_confidence(metadata, bin_labels, output_path):
    """Plot samples per site per confidence bin using sampling metadata."""
    sites = sorted(metadata["device_id"].unique())
    if len(sites) == 0:
        return

    fig, ax = plt.subplots(figsize=(12, max(4, len(sites) * 0.4)))

    pivot = (
        metadata.groupby(["device_id", "confidence_bin"], observed=True)
        .size()
        .unstack(fill_value=0)
    )

    for bin_label in bin_labels:
        if bin_label not in pivot.columns:
            pivot[bin_label] = 0
    pivot = pivot.reindex(columns=bin_labels)

    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu")

    ax.set_xticks(range(len(bin_labels)))
    ax.set_xticklabels(bin_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    for i in range(len(pivot.index)):
        for j in range(len(bin_labels)):
            val = pivot.iloc[i, j]
            color = "white" if val > pivot.values.max() / 2 else "black"
            ax.text(j, i, int(val), ha="center", va="center", color=color, fontsize=8)

    ax.set_xlabel("Confidence Bin")
    ax.set_ylabel("Device ID")
    ax.set_title("Samples per Site by Confidence Bin (Sampled-For)")

    plt.colorbar(im, ax=ax, label="Count")
    plt.tight_layout()
    plt.savefig(output_path / "site_by_confidence_sampled_for.png", dpi=150)
    plt.close()


def _plot_sampled_for_species_site(metadata, target_species, output_path):
    """Plot species x site matrix using sampling metadata."""
    sites = sorted(metadata["device_id"].unique())
    if len(sites) == 0:
        return

    fig, ax = plt.subplots(
        figsize=(max(8, len(sites) * 1.2), max(6, len(target_species) * 0.5))
    )

    pivot = (
        metadata.groupby(["species", "device_id"], observed=True)
        .size()
        .unstack(fill_value=0)
    )

    for species in target_species:
        if species not in pivot.index:
            pivot.loc[species] = 0
    for site in sites:
        if site not in pivot.columns:
            pivot[site] = 0

    pivot = pivot.reindex(columns=sites).reindex(target_species)

    im = ax.imshow(pivot.values, aspect="auto", cmap="Purples")

    ax.set_xticks(range(len(sites)))
    ax.set_xticklabels(sites, rotation=45, ha="right")
    ax.set_yticks(range(len(target_species)))
    ax.set_yticklabels(target_species)

    for i in range(len(target_species)):
        for j in range(len(sites)):
            val = pivot.iloc[i, j]
            color = "white" if val > pivot.values.max() / 2 else "black"
            ax.text(j, i, int(val), ha="center", va="center", color=color, fontsize=9)

    ax.set_xlabel("Device ID")
    ax.set_ylabel("Species")
    ax.set_title("Samples per Species per Site (Sampled-For)")

    plt.colorbar(im, ax=ax, label="Count")
    plt.tight_layout()
    plt.savefig(output_path / "species_site_matrix_sampled_for.png", dpi=150)
    plt.close()


def _plot_species_by_confidence(df, target_species, bin_labels, output_path, suffix=""):
    """Plot number of samples per species per confidence bin."""
    fig, ax = plt.subplots(figsize=(12, max(6, len(target_species) * 0.5)))

    # Create pivot table
    pivot = (
        df.groupby(["species", "conf_bin"], observed=True).size().unstack(fill_value=0)
    )

    # Ensure all species and bins are present
    for species in target_species:
        if species not in pivot.index:
            pivot.loc[species] = 0
    for bin_label in bin_labels:
        if bin_label not in pivot.columns:
            pivot[bin_label] = 0

    pivot = pivot.reindex(columns=bin_labels).reindex(target_species)

    # Plot heatmap
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")

    ax.set_xticks(range(len(bin_labels)))
    ax.set_xticklabels(bin_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(target_species)))
    ax.set_yticklabels(target_species)

    # Add counts as text
    for i in range(len(target_species)):
        for j in range(len(bin_labels)):
            val = pivot.iloc[i, j]
            color = "white" if val > pivot.values.max() / 2 else "black"
            ax.text(j, i, int(val), ha="center", va="center", color=color, fontsize=8)

    ax.set_xlabel("Confidence Bin")
    ax.set_ylabel("Species")
    ax.set_title("Samples per Species by Confidence Bin")

    plt.colorbar(im, ax=ax, label="Count")
    plt.tight_layout()
    plt.savefig(output_path / f"species_by_confidence{suffix}.png", dpi=150)
    plt.close()


def _plot_site_by_confidence(df, bin_labels, output_path, suffix=""):
    """Plot number of samples per site per confidence bin."""
    sites = df["device_id"].unique()
    if len(sites) == 0:
        return

    fig, ax = plt.subplots(figsize=(12, max(4, len(sites) * 0.4)))

    pivot = (
        df.groupby(["device_id", "conf_bin"], observed=True)
        .size()
        .unstack(fill_value=0)
    )

    for bin_label in bin_labels:
        if bin_label not in pivot.columns:
            pivot[bin_label] = 0
    pivot = pivot.reindex(columns=bin_labels)

    im = ax.imshow(pivot.values, aspect="auto", cmap="YlGnBu")

    ax.set_xticks(range(len(bin_labels)))
    ax.set_xticklabels(bin_labels, rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    for i in range(len(pivot.index)):
        for j in range(len(bin_labels)):
            val = pivot.iloc[i, j]
            color = "white" if val > pivot.values.max() / 2 else "black"
            ax.text(j, i, int(val), ha="center", va="center", color=color, fontsize=8)

    ax.set_xlabel("Confidence Bin")
    ax.set_ylabel("Device ID")
    ax.set_title("Samples per Site by Confidence Bin")

    plt.colorbar(im, ax=ax, label="Count")
    plt.tight_layout()
    plt.savefig(output_path / f"site_by_confidence{suffix}.png", dpi=150)
    plt.close()


def _plot_species_site_matrix(df, target_species, output_path, suffix=""):
    """Plot species x site matrix showing sample counts."""
    sites = sorted(df["device_id"].unique())
    if len(sites) == 0:
        return

    fig, ax = plt.subplots(
        figsize=(max(8, len(sites) * 1.2), max(6, len(target_species) * 0.5))
    )

    pivot = (
        df.groupby(["species", "device_id"], observed=True).size().unstack(fill_value=0)
    )

    for species in target_species:
        if species not in pivot.index:
            pivot.loc[species] = 0
    for site in sites:
        if site not in pivot.columns:
            pivot[site] = 0

    pivot = pivot.reindex(columns=sites).reindex(target_species)

    im = ax.imshow(pivot.values, aspect="auto", cmap="Purples")

    ax.set_xticks(range(len(sites)))
    ax.set_xticklabels(sites, rotation=45, ha="right")
    ax.set_yticks(range(len(target_species)))
    ax.set_yticklabels(target_species)

    for i in range(len(target_species)):
        for j in range(len(sites)):
            val = pivot.iloc[i, j]
            color = "white" if val > pivot.values.max() / 2 else "black"
            ax.text(j, i, int(val), ha="center", va="center", color=color, fontsize=9)

    ax.set_xlabel("Device ID")
    ax.set_ylabel("Species")
    ax.set_title("Samples per Species per Site")

    plt.colorbar(im, ax=ax, label="Count")
    plt.tight_layout()
    plt.savefig(output_path / f"species_site_matrix{suffix}.png", dpi=150)
    plt.close()


def _plot_confidence_distribution(df, output_path):
    """Plot overall confidence distribution histogram."""
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.hist(df["confidence"], bins=20, edgecolor="black", alpha=0.7, color="steelblue")
    ax.axvline(
        df["confidence"].mean(),
        color="red",
        linestyle="--",
        label=f"Mean: {df['confidence'].mean():.2f}",
    )
    ax.axvline(
        df["confidence"].median(),
        color="orange",
        linestyle="--",
        label=f"Median: {df['confidence'].median():.2f}",
    )

    ax.set_xlabel("Confidence Score")
    ax.set_ylabel("Count")
    ax.set_title("Overall Confidence Distribution")
    ax.legend()

    plt.tight_layout()
    plt.savefig(output_path / "confidence_distribution.png", dpi=150)
    plt.close()
