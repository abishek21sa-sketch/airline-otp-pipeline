# pipeline_02_process.py
# BTS On-Time Performance — Process Raw Downloads
# Unzips each monthly file, selects 15 fields, cleans data, saves as CSV to Data/Clean/

import os
import zipfile
import pandas as pd
from pathlib import Path

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_DIR   = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Raw"
CLEAN_DIR = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Clean"

# The 15 fields we downloaded — using BTS internal column names
# These are what appear in the CSV after unzipping
FIELDS = [
    "FlightDate",
    "Marketing_Airline_Network",
    "Tail_Number",
    "Flight_Number_Marketing_Airline",
    "Origin",
    "Dest",
    "CRSDepTime",
    "DepTime",
    "DepDelay",
    "CRSArrTime",
    "ArrTime",
    "ArrDelay",
    "Cancelled",
    "Diverted",
    "LateAircraftDelay",
    "CarrierDelay",
    "WeatherDelay",
    "NASDelay",
    "SecurityDelay",
    "Distance",
]

# Friendly column names for our clean files
RENAME = {
    "FlightDate"                    : "FlightDate",
    "Marketing_Airline_Network"     : "Carrier",
    "Tail_Number"                   : "TailNumber",
    "Flight_Number_Marketing_Airline": "FlightNumber",
    "Origin"                        : "Origin",
    "Dest"                          : "Dest",
    "CRSDepTime"                    : "SchedDep",
    "DepTime"                       : "ActualDep",
    "DepDelay"                      : "DepDelay",
    "CRSArrTime"                    : "SchedArr",
    "ArrTime"                       : "ActualArr",
    "ArrDelay"                      : "ArrDelay",
    "Cancelled"                     : "Cancelled",
    "Diverted"                      : "Diverted",
    "LateAircraftDelay"             : "LateAircraftDelay",
    "CarrierDelay"                  : "CarrierDelay",
    "WeatherDelay"                  : "WeatherDelay",
    "NASDelay"                      : "NASDelay",
    "SecurityDelay"                 : "SecurityDelay",
    "Distance"                      : "Distance",
}

MONTH_NAMES = {
    1: "January",   2: "February",  3: "March",
    4: "April",     5: "May",       6: "June",
    7: "July",      8: "August",    9: "September",
    10: "October",  11: "November", 12: "December"
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def find_zip_files(raw_dir):
    """Find all BTS zip files in Raw folder."""
    zips = []
    for f in sorted(os.listdir(raw_dir)):
        if f.endswith('.zip') and 'On_Time' in f:
            zips.append(os.path.join(raw_dir, f))
    return zips


def parse_year_month(filename):
    """Extract year and month from BTS filename."""
    # Pattern: ...2025_1.zip or ...2025_12.zip
    name = Path(filename).stem
    parts = name.split('_')
    try:
        year  = int(parts[-2])
        month = int(parts[-1])
        return year, month
    except:
        return None, None


def unzip_file(zip_path, extract_dir):
    """Unzip a BTS file and return path to the CSV inside."""
    os.makedirs(extract_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as z:
        csv_files = [f for f in z.namelist() if f.endswith('.csv')]
        if not csv_files:
            print(f"    No CSV found inside {Path(zip_path).name}")
            return None
        csv_name = csv_files[0]
        z.extract(csv_name, extract_dir)
        return os.path.join(extract_dir, csv_name)


def clean_dataframe(df):
    """Select fields, rename, clean types."""

    # Strip column name whitespace — BTS has trailing spaces on some columns
    df.columns = df.columns.str.strip()

    # Keep only our 15 fields — handle missing gracefully
    available = [f for f in FIELDS if f in df.columns]
    missing   = [f for f in FIELDS if f not in df.columns]
    if missing:
        print(f"    Warning — fields not found in CSV: {missing}")

    df = df[available].copy()

    # Rename to friendly names
    df = df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns})

    # Clean types
    if 'FlightDate' in df.columns:
        df['FlightDate'] = pd.to_datetime(df['FlightDate'], errors='coerce')

    for col in ['DepDelay', 'ArrDelay', 'LateAircraftDelay',
                'CarrierDelay', 'WeatherDelay', 'NASDelay',
                'SecurityDelay', 'Distance']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    for col in ['SchedDep', 'ActualDep', 'SchedArr', 'ActualArr',
                'FlightNumber']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    for col in ['Cancelled', 'Diverted']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

    # Strip whitespace from string columns
    for col in ['Carrier', 'TailNumber', 'Origin', 'Dest']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    # Drop rows where FlightDate is null
    if 'FlightDate' in df.columns:
        before = len(df)
        df = df.dropna(subset=['FlightDate'])
        dropped = before - len(df)
        if dropped > 0:
            print(f"    Dropped {dropped} rows with null FlightDate")

    return df


def process_zip(zip_path, clean_dir, temp_dir):
    """Full pipeline for one zip file."""
    year, month = parse_year_month(zip_path)
    if year is None:
        print(f"  Could not parse year/month from {Path(zip_path).name}")
        return False

    month_name  = MONTH_NAMES.get(month, str(month))
    output_name = f"OTP_{year}_{month:02d}_{month_name}.csv"
    output_path = os.path.join(clean_dir, output_name)

    if os.path.exists(output_path):
        print(f"  [{month:02d}/12] {month_name} {year} — already processed, skipping")
        return True

    print(f"\n  [{month:02d}/12] Processing {month_name} {year}...")
    print(f"    Unzipping {Path(zip_path).name}...")

    csv_path = unzip_file(zip_path, temp_dir)
    if csv_path is None:
        return False

    print(f"    Reading CSV...")
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except UnicodeDecodeError:
        print(f"    UTF-8 failed, trying latin1...")
        df = pd.read_csv(csv_path, low_memory=False, encoding='latin1')

    raw_rows = len(df)
    raw_cols = len(df.columns)
    print(f"    Raw: {raw_rows:,} rows x {raw_cols} columns")

    print(f"    Cleaning and selecting 15 fields...")
    df = clean_dataframe(df)

    print(f"    Clean: {len(df):,} rows x {len(df.columns)} columns")

    # Save clean file
    os.makedirs(clean_dir, exist_ok=True)
    df.to_csv(output_path, index=False)
    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"    Saved → {output_name} ({size_mb:.1f} MB)")

    # Remove temp CSV to save space
    try:
        os.remove(csv_path)
    except:
        pass

    return True


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("  BTS ON-TIME PERFORMANCE — PROCESS PIPELINE")
    print("=" * 60)

    os.makedirs(CLEAN_DIR, exist_ok=True)
    temp_dir = os.path.join(RAW_DIR, "_temp")

    # Find all zip files
    zip_files = find_zip_files(RAW_DIR)

    if not zip_files:
        print(f"\n  No zip files found in {RAW_DIR}")
        print("  Run pipeline_01_auto_download.py first.")
        return

    print(f"\n  Found {len(zip_files)} zip files in Raw folder")
    print(f"  Output folder: {CLEAN_DIR}")
    print()

    # Group by year for display
    by_year = {}
    for z in zip_files:
        year, month = parse_year_month(z)
        if year:
            by_year.setdefault(year, []).append(month)

    for year, months in sorted(by_year.items()):
        print(f"  {year}: {len(months)} months — "
              f"{[MONTH_NAMES[m] for m in sorted(months)]}")

    print()
    confirm = input("  Process all files? (y/n): ").strip().lower()
    if confirm != 'y':
        print("  Cancelled.")
        return

    print()
    results = {}
    for zip_path in zip_files:
        year, month = parse_year_month(zip_path)
        success = process_zip(zip_path, CLEAN_DIR, temp_dir)
        results[(year, month)] = success

    # Clean up temp folder
    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except:
        pass

    # Summary
    print()
    print("=" * 60)
    print("  PROCESSING SUMMARY")
    print("=" * 60)
    success_count = sum(1 for v in results.values() if v)
    fail_count    = sum(1 for v in results.values() if not v)
    print(f"\n  Successful : {success_count}")
    print(f"  Failed     : {fail_count}")
    if fail_count > 0:
        failed = [(y, m) for (y, m), v in results.items() if not v]
        print(f"  Failed files: {failed}")

    print(f"\n  Clean files saved to: {CLEAN_DIR}")

    # Quick stats on clean files
    print()
    print("  Clean file summary:")
    total_rows = 0
    for f in sorted(os.listdir(CLEAN_DIR)):
        if f.endswith('.csv'):
            path = os.path.join(CLEAN_DIR, f)
            size_mb = os.path.getsize(path) / 1024 / 1024
            try:
                row_count = sum(1 for _ in open(path)) - 1
                total_rows += row_count
                print(f"    {f}  ({row_count:,} rows, {size_mb:.1f} MB)")
            except:
                print(f"    {f}  ({size_mb:.1f} MB)")

    print(f"\n  Total rows across all clean files: {total_rows:,}")
    print("\n  Next: run pipeline_03_build_dataset.py")
    print()


if __name__ == '__main__':
    main()