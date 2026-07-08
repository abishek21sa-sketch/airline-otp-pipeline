# pipeline_03_build_dataset.py
# BTS On-Time Performance — Build Unified Dataset
# Combines all clean monthly files into one dataset
# Produces a summary report of what you have

import os
import pandas as pd
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

CLEAN_DIR   = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Clean"
OUTPUT_DIR  = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data"
SUMMARY_DIR = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs"

MONTH_NAMES = {
    1: "January",   2: "February",  3: "March",
    4: "April",     5: "May",       6: "June",
    7: "July",      8: "August",    9: "September",
    10: "October",  11: "November", 12: "December"
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def find_clean_files(clean_dir):
    """Find all clean monthly CSV files."""
    files = []
    for f in sorted(os.listdir(clean_dir)):
        if f.startswith('OTP_') and f.endswith('.csv'):
            files.append(os.path.join(clean_dir, f))
    return files


def parse_year_month_from_clean(filename):
    """Extract year and month from OTP_2025_01_January.csv pattern."""
    name = Path(filename).stem
    parts = name.split('_')
    try:
        year  = int(parts[1])
        month = int(parts[2])
        return year, month
    except:
        return None, None


def load_and_tag(filepath):
    """Load one clean file and add year/month columns."""
    year, month = parse_year_month_from_clean(filepath)
    df = pd.read_csv(filepath, low_memory=False)
    df['Year']  = year
    df['Month'] = month
    return df, year, month


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("  BTS ON-TIME PERFORMANCE — BUILD DATASET")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR,  exist_ok=True)
    os.makedirs(SUMMARY_DIR, exist_ok=True)

    clean_files = find_clean_files(CLEAN_DIR)

    if not clean_files:
        print(f"\n  No clean files found in {CLEAN_DIR}")
        print("  Run pipeline_02_process.py first.")
        return

    print(f"\n  Found {len(clean_files)} clean files")
    for f in clean_files:
        size_mb = os.path.getsize(f) / 1024 / 1024
        year, month = parse_year_month_from_clean(f)
        print(f"    {MONTH_NAMES.get(month,'')} {year}  ({size_mb:.1f} MB)")

    print()
    confirm = input("  Build unified dataset? (y/n): ").strip().lower()
    if confirm != 'y':
        print("  Cancelled.")
        return

    # ── LOAD ALL FILES ────────────────────────────────────────────────────────

    print("\n  Loading all clean files...")
    frames = []
    for f in clean_files:
        year, month = parse_year_month_from_clean(f)
        print(f"    Loading {MONTH_NAMES.get(month,'')} {year}...")
        df, year, month = load_and_tag(f)
        frames.append(df)

    print("\n  Combining into unified dataset...")
    combined = pd.concat(frames, ignore_index=True)

    # Parse FlightDate
    combined['FlightDate'] = pd.to_datetime(combined['FlightDate'], errors='coerce')

    print(f"  Combined: {len(combined):,} rows x {len(combined.columns)} columns")
    print(f"  Date range: {combined['FlightDate'].min().date()} to "
          f"{combined['FlightDate'].max().date()}")

    # ── SAVE UNIFIED DATASET ──────────────────────────────────────────────────

    years = sorted(combined['Year'].unique())
    year_str = f"{min(years)}" if len(years) == 1 else f"{min(years)}_{max(years)}"
    output_name = f"OTP_UNIFIED_{year_str}.csv"
    output_path = os.path.join(OUTPUT_DIR, output_name)

    print(f"\n  Saving unified dataset...")
    combined.to_csv(output_path, index=False)
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"  Saved → {output_name} ({size_mb:.1f} MB)")

    # ── SUMMARY REPORT ────────────────────────────────────────────────────────

    print()
    print("=" * 60)
    print("  DATASET SUMMARY")
    print("=" * 60)

    operated = combined[combined['Cancelled'] == 0]

    print(f"\n  COVERAGE")
    print(f"    Total flights    : {len(combined):,}")
    print(f"    Operated flights : {len(operated):,}")
    print(f"    Cancelled        : {int(combined['Cancelled'].sum()):,} "
          f"({combined['Cancelled'].mean()*100:.2f}%)")
    print(f"    Diverted         : {int(combined['Diverted'].sum()):,} "
          f"({combined['Diverted'].mean()*100:.3f}%)")
    print(f"    Date range       : {combined['FlightDate'].min().date()} to "
          f"{combined['FlightDate'].max().date()}")
    print(f"    Unique carriers  : {combined['Carrier'].nunique()}")
    print(f"    Unique aircraft  : {combined['TailNumber'].nunique():,}")
    print(f"    Unique routes    : "
          f"{(combined['Origin'] + combined['Dest']).nunique():,}")

    print(f"\n  PERFORMANCE")
    print(f"    On-time rate (<=15m) : "
          f"{(operated['ArrDelay'] <= 15).mean()*100:.1f}%")
    print(f"    Avg arrival delay    : {operated['ArrDelay'].mean():.1f} mins")
    print(f"    Avg dep delay        : {operated['DepDelay'].mean():.1f} mins")

    print(f"\n  MONTHLY BREAKDOWN")
    monthly = combined.groupby(['Year','Month']).agg(
        flights      = ('FlightDate', 'count'),
        cancelled    = ('Cancelled', 'sum'),
        avg_delay    = ('ArrDelay', 'mean'),
        on_time_rate = ('ArrDelay', lambda x: (x <= 15).mean() * 100)
    ).reset_index()

    print(f"    {'MONTH':<15} {'FLIGHTS':>8} {'CNCL':>6} "
          f"{'AVG DLY':>8} {'ON-TIME%':>9}")
    print("    " + "-" * 52)
    for _, r in monthly.iterrows():
        name = f"{MONTH_NAMES.get(int(r['Month']),'')} {int(r['Year'])}"
        print(f"    {name:<15} {int(r['flights']):>8,} "
              f"{int(r['cancelled']):>6,} "
              f"{r['avg_delay']:>+7.1f}m "
              f"{r['on_time_rate']:>8.1f}%")

    print(f"\n  TOP 10 CARRIERS BY FLIGHTS")
    carrier_counts = combined['Carrier'].value_counts().head(10)
    for carrier, count in carrier_counts.items():
        pct = count / len(combined) * 100
        print(f"    {carrier:<6} {count:>8,}  ({pct:.1f}%)")

    print(f"\n  DELAY CAUSE SUMMARY (operated flights only)")
    for cause, col in [
        ('Carrier delay',  'CarrierDelay'),
        ('Late aircraft',  'LateAircraftDelay'),
    ]:
        if col in operated.columns:
            total = operated[col].sum()
            legs  = (operated[col] > 0).sum()
            print(f"    {cause:<20}: {total:>10,.0f} mins  across {legs:>6,} legs")

    # ── SAVE SUMMARY TEXT ────────────────────────────────────────────────────

    summary_path = os.path.join(SUMMARY_DIR, f"OTP_SUMMARY_{year_str}.txt")
    with open(summary_path, 'w') as f:
        f.write(f"BTS On-Time Performance — Dataset Summary\n")
        f.write(f"{'='*60}\n\n")
        f.write(f"Year(s)          : {year_str}\n")
        f.write(f"Total flights    : {len(combined):,}\n")
        f.write(f"Date range       : {combined['FlightDate'].min().date()} "
                f"to {combined['FlightDate'].max().date()}\n")
        f.write(f"Unique carriers  : {combined['Carrier'].nunique()}\n")
        f.write(f"Unique aircraft  : {combined['TailNumber'].nunique():,}\n")
        f.write(f"On-time rate     : {(operated['ArrDelay'] <= 15).mean()*100:.1f}%\n")
        f.write(f"Avg arrival delay: {operated['ArrDelay'].mean():.1f} mins\n")
        f.write(f"\nMonthly breakdown:\n")
        for _, r in monthly.iterrows():
            name = f"{MONTH_NAMES.get(int(r['Month']),'')} {int(r['Year'])}"
            f.write(f"  {name:<15} {int(r['flights']):>8,} flights  "
                    f"avg delay {r['avg_delay']:>+.1f}m  "
                    f"on-time {r['on_time_rate']:.1f}%\n")

    print(f"\n  Summary saved → {Path(summary_path).name}")
    print(f"\n  Unified dataset : {output_path}")
    print(f"  Size            : {size_mb:.1f} MB")
    print(f"  Rows            : {len(combined):,}")
    print(f"  Columns         : {len(combined.columns)}")
    print()
    print("  Pipeline complete. All 3 stages done.")
    print()


if __name__ == '__main__':
    main()