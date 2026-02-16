"""
Subsample parquet files for annotation tasks.

Creates annotation datasets by:
- Loading aggregated parquet files from S3
- Filtering by species and sites
- Sampling by confidence bins
- Distributing among annotators

Usage:
uv run python sampling_scripts/subsample_annotations.py \
    --species "Rallus aquaticus" "Porzana porzana" "Zapornia parva" \
        "Zapornia pusilla" "Botaurus stellaris" "Locustella luscinioides" \
    --sites cfc291d3 fb104ba8 44e6e23b 3b425ce9 \
    --samples-per-bin 10 \
    --bin-size 0.1 \
    --stratify-by-device \
    --stratify-by-species \
    --user-ids daniel \
    --output-path validation_dataset/loenderveen.parquet
    --diagnostics
"""

import argparse

import numpy as np
from sampling_core import load_segments_from_s3, subsample_by_confidence_bins
from sampling_diagnostics import generate_diagnostics
from sampling_s3 import upload_to_s3
from sampling_utils import assign_user_ids, count_unique_species

# S3 defaults
DEFAULT_S3_BUCKET = "bencretois-ns8129k-proj-tabmon"
DEFAULT_INPUT_PATH = "Listening_Lab"
DEFAULT_OUTPUT_PATH = "validation_dataset/annotations_sample.parquet"


def print_header(args):
    """Print formatted script header with parameters."""
    print("=" * 70)
    print("TABMON Annotation Subsampling Script")
    print("=" * 70)
    print(f"\n📂 Input:  s3://{args.s3_bucket}/{args.input_prefix}/")
    print(f"📂 Output: s3://{args.s3_bucket}/{args.output_path}")
    print(f"\n🎯 Target species ({len(args.species)}):")
    for species in args.species:
        print(f"   • {species}")

    if args.sites:
        print(f"\n📍 Sites ({len(args.sites)}): {', '.join(args.sites)}")
    else:
        print("\n📍 Sites: All")

    print("\n📊 Sampling:")
    print(f"   • Per bin: {args.samples_per_bin}")
    print(f"   • Bin size: {args.bin_size}")
    print(f"   • Stratify by device: {args.stratify_by_device}")
    print(f"   • Stratify by species: {args.stratify_by_species}")
    print(f"   • Seed: {args.random_seed}")

    if args.user_ids:
        print(f"\n👥 Annotators ({len(args.user_ids)}): {', '.join(args.user_ids)}")
    print("\n" + "=" * 70)


def print_summary(df_final, args, output_s3_path):
    """Print formatted summary of results."""
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("\n✅ Successfully created annotation sample")
    print(f"   • Total clips: {len(df_final):,}")
    print(f"   • Target species found: {count_unique_species(df_final, args.species)}")
    if "device_id" in df_final.columns:
        print(f"   • Devices: {len(df_final['device_id'].unique())}")
    print(f"   • Deployments: {len(df_final['deployment_id'].unique())}")
    if args.user_ids:
        print(f"   • Annotators: {len(args.user_ids)}")
    print(f"\n📦 Output: {output_s3_path}")
    print("\n" + "=" * 70)


def main():
    """Main entry point for annotation subsampling."""
    parser = argparse.ArgumentParser(
        description="Subsample parquet files for annotation tasks."
    )
    parser.add_argument("--s3-bucket", default=DEFAULT_S3_BUCKET, help="S3 bucket name")
    parser.add_argument(
        "--input-prefix",
        default=DEFAULT_INPUT_PATH,
        help=f"S3 input prefix (default: {DEFAULT_INPUT_PATH})",
    )
    parser.add_argument(
        "--output-path",
        default=DEFAULT_OUTPUT_PATH,
        help=f"S3 output path with filename (default: {DEFAULT_OUTPUT_PATH})",
    )
    parser.add_argument(
        "--species",
        nargs="+",
        required=True,
        help="Species scientific names to include",
    )
    parser.add_argument(
        "--sites",
        nargs="*",
        default=None,
        help="Deployment IDs to include (optional)",
    )
    parser.add_argument(
        "--samples-per-bin",
        type=int,
        default=50,
        help="Samples per confidence bin (default: 50)",
    )
    parser.add_argument(
        "--bin-size",
        type=float,
        default=0.1,
        help="Confidence bin size (default: 0.1)",
    )
    parser.add_argument(
        "--user-ids",
        nargs="+",
        default=None,
        help="User IDs for annotation assignment",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--stratify-by-device",
        action="store_true",
        help="Sample per bin per device instead of globally",
    )
    parser.add_argument(
        "--stratify-by-species",
        action="store_true",
        help="Sample independently for each species",
    )
    parser.add_argument(
        "--diagnostics",
        action="store_true",
        help="Generate diagnostic plots for the sampled dataset",
    )
    parser.add_argument(
        "--diagnostics-dir",
        default="diagnostics",
        help="Directory to save diagnostic plots (default: diagnostics)",
    )

    args = parser.parse_args()
    print_header(args)

    # Step 1: Load segments
    print("\n[1/4] Loading segments from S3...")
    df_segments = load_segments_from_s3(
        args.s3_bucket, args.input_prefix, args.species, args.sites
    )

    if df_segments.empty:
        print("\n❌ No segments found. Exiting.")
        return

    # Step 2: Subsample by confidence
    strategies = []
    if args.stratify_by_device:
        strategies.append("per device")
    if args.stratify_by_species:
        strategies.append("per species")
    strategy = " + ".join(strategies) if strategies else "global"
    print(f"\n[2/4] Subsampling by confidence bins ({strategy})...")
    df_sampled, sampling_metadata = subsample_by_confidence_bins(
        df_segments,
        args.species,
        samples_per_bin=args.samples_per_bin,
        bin_size=args.bin_size,
        random_seed=args.random_seed,
        stratify_by_device=args.stratify_by_device,
        stratify_by_species=args.stratify_by_species,
    )

    if df_sampled.empty:
        print("\n❌ No samples after binning. Exiting.")
        return

    print(f"\n  ✓ Sampled: {len(df_sampled):,} segments")

    # Step 3: Assign users
    print("\n[3/4] Assigning users...")
    if args.user_ids:
        df_sampled = assign_user_ids(df_sampled, args.user_ids)
        print("\n  Distribution:")
        for user_id in args.user_ids:
            count = (df_sampled["userID"] == user_id).sum()
            print(f"    {user_id}: {count:,} clips")
    else:
        df_sampled["userID"] = np.nan

    # Prepare final output
    column_order = [
        "filename",
        "deployment_id",
        "fullPath",
        "start time",
        "scientific name",
        "confidence",
        "max uncertainty",
        "userID",
    ]
    df_final = df_sampled[[col for col in column_order if col in df_sampled.columns]]

    # Step 4: Upload to S3
    print("\n[4/5] Uploading to S3...")
    output_s3_path = upload_to_s3(df_final, args.s3_bucket, args.output_path)
    print(f"  ✓ Uploaded to {output_s3_path}")

    # Step 5: Generate diagnostics
    if args.diagnostics:
        print("\n[5/5] Generating diagnostic plots...")
        generate_diagnostics(
            df_sampled,
            args.species,
            args.diagnostics_dir,
            args.bin_size,
            sampling_metadata=sampling_metadata,
        )

    # Print summary
    print_summary(df_final, args, output_s3_path)


if __name__ == "__main__":
    main()
