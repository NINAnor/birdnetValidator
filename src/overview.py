"""Overview tab — annotation diagnostics matrix.

Shows a species × time matrix with correct/annotated counts and
unannotated totals, helping users prioritize annotation effort.
"""

import io
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

from s3_utils import is_s3_path, list_s3_files, read_s3_text
from selection_handlers import VALIDATIONS_PREFIX

GRANULARITY_OPTIONS = {
    "Hour": "hour",
    "Day": "day",
    "Week": "week",
    "Month": "month",
}


def _build_matrix_data(clips, validations, granularity):
    """Build the species × time matrix from clips and validations.

    Returns a dict of {(species, time_bin): {annotated, correct, unannotated}}.
    """
    # Index validations by (filename, start_time) for fast lookup
    validation_index = {}
    for val in validations:
        key = (val.get("filepath", val.get("filename")), val["start_time"])
        validation_index[key] = val

    # Collect stats per (species, time_bin)
    stats = defaultdict(lambda: {"annotated": 0, "correct": 0, "unannotated": 0})

    for clip in clips:
        recording_dt = clip.get("recording_datetime")
        if recording_dt is None:
            time_bin = "Unknown"
        elif granularity == "hour":
            time_bin = recording_dt.strftime("%Y-%m-%d %H:00")
        elif granularity == "day":
            time_bin = recording_dt.strftime("%Y-%m-%d")
        elif granularity == "week":
            time_bin = recording_dt.strftime("%Y-W%W")
        else:  # month
            time_bin = recording_dt.strftime("%Y-%m")

        clip_key = (clip["filename"], clip["start_time"])
        val = validation_index.get(clip_key)

        for species in clip["species_array"]:
            cell = stats[(species, time_bin)]
            if val is None:
                cell["unannotated"] += 1
            else:
                cell["annotated"] += 1
                identified = val.get("identified_species", "")
                if isinstance(identified, str):
                    identified_list = identified.split("|")
                else:
                    identified_list = []
                if species in identified_list:
                    cell["correct"] += 1

    return stats


def _generate_full_time_bins(time_bins, granularity):
    """Generate a contiguous sequence of time bins covering the full range."""
    if not time_bins or granularity not in ("hour", "day", "week", "month"):
        return sorted(time_bins)

    # Separate "Unknown" bins (unparseable datetimes) from real date bins
    parseable = sorted(b for b in time_bins if b != "Unknown")
    has_unknown = "Unknown" in time_bins

    if not parseable:
        return ["Unknown"] if has_unknown else []

    first, last = parseable[0], parseable[-1]

    if granularity == "hour":
        start = pd.Timestamp(first)
        end = pd.Timestamp(last)
        result = [
            t.strftime("%Y-%m-%d %H:00")
            for t in pd.date_range(start, end, freq="h")
        ]
    elif granularity == "day":
        start = date.fromisoformat(first)
        end = date.fromisoformat(last)
        days = (end - start).days
        result = [
            (start + timedelta(days=i)).isoformat()
            for i in range(days + 1)
        ]
    elif granularity == "week":
        # Format: YYYY-Www
        start = pd.Timestamp.strptime(first + "-1", "%Y-W%W-%w")
        end = pd.Timestamp.strptime(last + "-1", "%Y-W%W-%w")
        result = [
            t.strftime("%Y-W%W")
            for t in pd.date_range(start, end, freq="W-MON")
        ]
    else:  # month
        result = [
            t.strftime("%Y-%m")
            for t in pd.date_range(first + "-01", last + "-01", freq="MS")
        ]

    if has_unknown:
        result.append("Unknown")
    return result


def _stats_to_dataframe(stats, granularity):
    """Convert stats dict to a pivot-style DataFrame.

    Returns (display_df, precision_df) where display_df has string cells
    like '5/8 (12)' and precision_df has float precision for coloring.
    """
    if not stats:
        return pd.DataFrame(), pd.DataFrame()

    # Collect all species and time bins
    species_set = set()
    time_bins_set = set()
    for (species, time_bin) in stats:
        species_set.add(species)
        time_bins_set.add(time_bin)

    species_list = sorted(species_set)
    time_bins = _generate_full_time_bins(time_bins_set, granularity)

    display_rows = []
    precision_rows = []
    for species in species_list:
        display_row = {"Species": species}
        precision_row = {"Species": species}
        total_correct = 0
        total_annotated = 0
        total_unannotated = 0
        for time_bin in time_bins:
            cell = stats.get((species, time_bin))
            if cell is None or (cell["annotated"] == 0 and cell["unannotated"] == 0):
                display_row[time_bin] = ""
                precision_row[time_bin] = None
            else:
                correct = cell["correct"]
                annotated = cell["annotated"]
                unannotated = cell["unannotated"]
                display_row[time_bin] = f"{correct}/{annotated} ({unannotated})"
                precision_row[time_bin] = (
                    correct / annotated if annotated > 0 else None
                )
                total_correct += correct
                total_annotated += annotated
                total_unannotated += unannotated
        # Total column for this species
        display_row["Total"] = f"{total_correct}/{total_annotated} ({total_unannotated})"
        precision_row["Total"] = (
            total_correct / total_annotated if total_annotated > 0 else None
        )
        display_rows.append(display_row)
        precision_rows.append(precision_row)

    # Total row across all species
    total_display = {"Species": "Total"}
    total_precision = {"Species": "Total"}
    for col in [*time_bins, "Total"]:
        col_correct = 0
        col_annotated = 0
        col_unannotated = 0
        for species in species_list:
            if col == "Total":
                # Sum all time bins for this species
                for tb in time_bins:
                    cell = stats.get((species, tb))
                    if cell:
                        col_correct += cell["correct"]
                        col_annotated += cell["annotated"]
                        col_unannotated += cell["unannotated"]
            else:
                cell = stats.get((species, col))
                if cell:
                    col_correct += cell["correct"]
                    col_annotated += cell["annotated"]
                    col_unannotated += cell["unannotated"]
        if col_annotated == 0 and col_unannotated == 0:
            total_display[col] = ""
            total_precision[col] = None
        else:
            total_display[col] = f"{col_correct}/{col_annotated} ({col_unannotated})"
            total_precision[col] = (
                col_correct / col_annotated if col_annotated > 0 else None
            )
    display_rows.append(total_display)
    precision_rows.append(total_precision)

    display_df = pd.DataFrame(display_rows).set_index("Species")
    precision_df = pd.DataFrame(precision_rows).set_index("Species")
    return display_df, precision_df


def _style_matrix(display_df, precision_df):
    """Apply background color based on precision values."""

    def _cell_color(species, col):
        precision = precision_df.at[species, col]
        if precision is None or pd.isna(precision):
            return ""
        # Green for high precision, red for low, white/neutral for no data
        r = int(255 * (1 - precision))
        g = int(200 * precision)
        return f"background-color: rgba({r}, {g}, 80, 0.35)"

    styler = display_df.style.apply(
        lambda row: [
            _cell_color(row.name, col) for col in display_df.columns
        ],
        axis=1,
    )
    return styler


# Confidence bin labels in fixed order
_CONFIDENCE_BINS = [f"{i/10:.1f}–{(i+1)/10:.1f}" for i in range(10)]


def _confidence_bin(confidence):
    """Map a confidence value (0.0–1.0) to its bin label."""
    idx = min(int(confidence * 10), 9)
    return _CONFIDENCE_BINS[idx]


def _build_confidence_matrix_data(clips, validations):
    """Build species × confidence-bin matrix.

    Returns dict of {(species, conf_bin): {annotated, correct, unannotated}}.
    """
    validation_index = {}
    for val in validations:
        key = (val.get("filepath", val.get("filename")), val["start_time"])
        validation_index[key] = val

    stats = defaultdict(lambda: {"annotated": 0, "correct": 0, "unannotated": 0})

    for clip in clips:
        clip_key = (clip["filename"], clip["start_time"])
        val = validation_index.get(clip_key)

        for species, confidence in zip(
            clip["species_array"], clip["confidence_array"], strict=False
        ):
            conf_bin = _confidence_bin(confidence)
            cell = stats[(species, conf_bin)]
            if val is None:
                cell["unannotated"] += 1
            else:
                cell["annotated"] += 1
                identified = val.get("identified_species", "")
                if isinstance(identified, str):
                    identified_list = identified.split("|")
                else:
                    identified_list = []
                if species in identified_list:
                    cell["correct"] += 1

    return stats


def _confidence_stats_to_dataframe(stats):
    """Convert confidence stats to display and precision DataFrames."""
    if not stats:
        return pd.DataFrame(), pd.DataFrame()

    species_list = sorted({s for s, _ in stats})

    display_rows = []
    precision_rows = []
    for species in species_list:
        display_row = {"Species": species}
        precision_row = {"Species": species}
        total_correct = 0
        total_annotated = 0
        total_unannotated = 0
        for conf_bin in _CONFIDENCE_BINS:
            cell = stats.get((species, conf_bin))
            if cell is None or (cell["annotated"] == 0 and cell["unannotated"] == 0):
                display_row[conf_bin] = ""
                precision_row[conf_bin] = None
            else:
                correct = cell["correct"]
                annotated = cell["annotated"]
                unannotated = cell["unannotated"]
                display_row[conf_bin] = f"{correct}/{annotated} ({unannotated})"
                precision_row[conf_bin] = (
                    correct / annotated if annotated > 0 else None
                )
                total_correct += correct
                total_annotated += annotated
                total_unannotated += unannotated
        display_row["Total"] = f"{total_correct}/{total_annotated} ({total_unannotated})"
        precision_row["Total"] = (
            total_correct / total_annotated if total_annotated > 0 else None
        )
        display_rows.append(display_row)
        precision_rows.append(precision_row)

    # Total row
    total_display = {"Species": "Total"}
    total_precision = {"Species": "Total"}
    for col in [*_CONFIDENCE_BINS, "Total"]:
        col_correct = 0
        col_annotated = 0
        col_unannotated = 0
        for species in species_list:
            if col == "Total":
                for cb in _CONFIDENCE_BINS:
                    cell = stats.get((species, cb))
                    if cell:
                        col_correct += cell["correct"]
                        col_annotated += cell["annotated"]
                        col_unannotated += cell["unannotated"]
            else:
                cell = stats.get((species, col))
                if cell:
                    col_correct += cell["correct"]
                    col_annotated += cell["annotated"]
                    col_unannotated += cell["unannotated"]
        if col_annotated == 0 and col_unannotated == 0:
            total_display[col] = ""
            total_precision[col] = None
        else:
            total_display[col] = f"{col_correct}/{col_annotated} ({col_unannotated})"
            total_precision[col] = (
                col_correct / col_annotated if col_annotated > 0 else None
            )
    display_rows.append(total_display)
    precision_rows.append(total_precision)

    display_df = pd.DataFrame(display_rows).set_index("Species")
    precision_df = pd.DataFrame(precision_rows).set_index("Species")
    return display_df, precision_df


def _load_all_validations(output_dir):
    """Load validations from all annotators in the output directory."""
    all_records = []
    if is_s3_path(output_dir):
        all_files = list_s3_files(output_dir, extension=".csv")
        csv_files = [
            f for f in all_files
            if f.split("/")[-1].startswith(VALIDATIONS_PREFIX)
        ]
        for csv_uri in csv_files:
            text = read_s3_text(csv_uri)
            df = pd.read_csv(io.StringIO(text))
            all_records.extend(df.to_dict("records"))
    else:
        output_path = Path(output_dir)
        for csv_path in output_path.glob(f"{VALIDATIONS_PREFIX}*.csv"):
            df = pd.read_csv(csv_path)
            all_records.extend(df.to_dict("records"))

    return all_records


@st.fragment
def render_overview_tab():
    """Render the annotation overview/diagnostics tab.

    Decorated with @st.fragment so it only re-executes when the user
    interacts with widgets inside this tab, not on every app rerun.
    """
    clips = st.session_state.get("local_clips", [])
    output_dir = st.session_state.get("local_output_dir")

    if not clips:
        st.info("📂 No data loaded yet. Configure paths in the sidebar.")
        return

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        granularity = st.selectbox(
            "⏱️ Time granularity",
            options=list(GRANULARITY_OPTIONS.keys()),
            index=1,  # default: Day
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        refresh = st.button("🔄 Refresh", help="Reload validations from disk")

    # Load validations only on first render or when refresh is clicked
    cache_key = "_overview_validations"
    if refresh or cache_key not in st.session_state:
        st.session_state[cache_key] = (
            _load_all_validations(output_dir) if output_dir else []
        )

    validations = st.session_state[cache_key]

    stats = _build_matrix_data(
        clips, validations, GRANULARITY_OPTIONS[granularity]
    )

    if not stats:
        st.info("No detection data to display.")
        return

    display_df, precision_df = _stats_to_dataframe(stats, GRANULARITY_OPTIONS[granularity])

    if display_df.empty:
        st.info("No detection data to display.")
        return

    # Summary metrics
    total_detections = sum(
        cell["annotated"] + cell["unannotated"]
        for cell in stats.values()
    )
    total_annotated = sum(cell["annotated"] for cell in stats.values())
    total_correct = sum(cell["correct"] for cell in stats.values())
    total_unannotated = sum(cell["unannotated"] for cell in stats.values())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total detections", total_detections)
    m2.metric("Annotated", total_annotated)
    m3.metric("Correct", total_correct)
    m4.metric("Unannotated", total_unannotated)

    st.markdown("---")

    st.markdown(
        "Cells show **correct / annotated (unannotated)**. "
        "Color: 🟢 high precision → 🔴 low precision."
    )

    styled = _style_matrix(display_df, precision_df)
    st.dataframe(styled, use_container_width=True, height=min(len(display_df) * 40 + 50, 600))

    # --- Confidence matrix ---
    st.markdown("---")
    st.markdown("### Species × Confidence")
    st.markdown(
        "Cells show **correct / annotated (unannotated)** per confidence bin. "
        "Color: 🟢 high precision → 🔴 low precision."
    )

    conf_stats = _build_confidence_matrix_data(clips, validations)
    if conf_stats:
        conf_display_df, conf_precision_df = _confidence_stats_to_dataframe(conf_stats)
        if not conf_display_df.empty:
            conf_styled = _style_matrix(conf_display_df, conf_precision_df)
            st.dataframe(conf_styled, use_container_width=True, height=min(len(conf_display_df) * 40 + 50, 600))
        else:
            st.info("No confidence data to display.")
    else:
        st.info("No confidence data to display.")
