# pipeline_07_monitoring.py
# BTS On-Time Performance — Monitoring & Data Quality Report
# Checks pipeline health, data coverage, quality metrics.
# Safe to run anytime — read-only.

import os
import sys
import json
import re
from datetime import datetime
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pipeline_05_check_new_data import MONTH_NAMES, STATE_FILE

BASE_DIR   = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines"
RAW_DIR    = os.path.join(BASE_DIR, "Data", "Raw")
CLEAN_DIR  = os.path.join(BASE_DIR, "Data", "Clean")
DATA_DIR   = os.path.join(BASE_DIR, "Data")
LOG_DIR    = os.path.join(BASE_DIR, "Logs")
REPORT_DIR = os.path.join(BASE_DIR, "Outputs")

os.makedirs(REPORT_DIR, exist_ok=True)

EXPECTED_COLS = [
    'FlightDate', 'Carrier', 'TailNumber', 'FlightNumber',
    'Origin', 'Dest', 'SchedDep', 'ActualDep', 'DepDelay',
    'SchedArr', 'ActualArr', 'ArrDelay', 'Cancelled',
    'Diverted', 'LateAircraftDelay'
]


def parse_clean_filename(filename):
    m = re.match(r"OTP_(\d{4})_(\d{2})_", filename)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def get_all_clean_files():
    if not os.path.exists(CLEAN_DIR):
        return []
    files = []
    for f in sorted(os.listdir(CLEAN_DIR)):
        if f.startswith('OTP_') and f.endswith('.csv'):
            year, month = parse_clean_filename(f)
            if year:
                files.append({
                    'filename': f,
                    'path': os.path.join(CLEAN_DIR, f),
                    'year': year,
                    'month': month,
                    'size_mb': os.path.getsize(os.path.join(CLEAN_DIR, f)) / 1024 / 1024
                })
    return files


def load_pipeline_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None


def section_pipeline_state(R):
    R.append("=" * 65)
    R.append("SECTION 1 — PIPELINE STATE")
    R.append("=" * 65)
    state = load_pipeline_state()
    if state is None:
        R.append("  No state file found. Run pipeline_05_check_new_data.py first.")
        return
    R.append(f"  Last checked  : {state.get('last_checked', 'Never')}")
    R.append(f"  Latest on BTS : {state.get('last_known_latest', 'Unknown')}")
    history = state.get('check_history', [])
    if history:
        R.append(f"\n  Recent checks (last {min(5, len(history))}):")
        for entry in history[-5:]:
            flag = " *** NEW RELEASE ***" if entry.get('new_release') else ""
            R.append(f"    {entry['checked_at'][:19]}  latest={entry['latest_available']}"
                     f"  missing={entry['missing_count']}{flag}")


def section_coverage(R, clean_files):
    R.append("")
    R.append("=" * 65)
    R.append("SECTION 2 — COVERAGE")
    R.append("=" * 65)
    if not clean_files:
        R.append("  No clean files found.")
        return
    years = sorted(set(f['year'] for f in clean_files))
    R.append(f"  Total files : {len(clean_files)}")
    R.append(f"  Years       : {years[0]} to {years[-1]}")
    R.append(f"  Total size  : {sum(f['size_mb'] for f in clean_files):.1f} MB")
    R.append("")
    R.append(f"  {'YEAR':<6} {'MONTHS':>7} {'MISSING':>8} {'SIZE MB':>9}  STATUS")
    R.append("  " + "-" * 50)
    current_year = datetime.now().year
    for year in years:
        yf = [f for f in clean_files if f['year'] == year]
        present = sorted(f['month'] for f in yf)
        missing = [m for m in range(1, 13) if m not in present]
        size = sum(f['size_mb'] for f in yf)
        if year == current_year:
            status = f"In progress ({len(yf)} months)"
        elif missing:
            status = f"INCOMPLETE — missing {[MONTH_NAMES[m] for m in missing]}"
        else:
            status = "Complete"
        R.append(f"  {year:<6} {len(yf):>7} {len(missing):>8} {size:>8.1f}  {status}")

    # Timeline gap check
    all_months = sorted((f['year'], f['month']) for f in clean_files)
    y, m = all_months[0]
    ly, lm = all_months[-1]
    expected = []
    while (y, m) <= (ly, lm):
        expected.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    gaps = [x for x in expected if x not in set(all_months)]
    if gaps:
        R.append(f"\n  Timeline gaps:")
        for gy, gm in gaps:
            R.append(f"    Missing: {MONTH_NAMES[gm]} {gy}")
    else:
        R.append(f"\n  No gaps — continuous coverage from "
                 f"{MONTH_NAMES[all_months[0][1]]} {all_months[0][0]} to "
                 f"{MONTH_NAMES[all_months[-1][1]]} {all_months[-1][0]}")


def section_data_quality(R, clean_files):
    R.append("")
    R.append("=" * 65)
    R.append("SECTION 3 — DATA QUALITY (latest 3 months)")
    R.append("=" * 65)
    R.append("")
    for file_info in clean_files[-3:]:
        df = pd.read_csv(file_info['path'], low_memory=False)
        mn = MONTH_NAMES[file_info['month']]
        yr = file_info['year']
        R.append(f"  {mn} {yr}:")
        R.append(f"    Rows     : {len(df):,}")
        R.append(f"    Columns  : {len(df.columns)}")
        missing_cols = [c for c in EXPECTED_COLS if c not in df.columns]
        if missing_cols:
            R.append(f"    MISSING  : {missing_cols}")
        else:
            R.append(f"    Schema   : All 15 expected columns present")
        if 'ArrDelay' in df.columns and 'Cancelled' in df.columns:
            operated = df[df['Cancelled'] == 0]
            R.append(f"    On-time  : {(operated['ArrDelay'] <= 15).mean()*100:.1f}%")
            R.append(f"    Avg delay: {operated['ArrDelay'].mean():.1f} mins")
            R.append(f"    Cancelled: {df['Cancelled'].mean()*100:.2f}%")
            R.append(f"    Carriers : {df['Carrier'].nunique()}")
        R.append("")


def section_row_counts(R, clean_files):
    R.append("=" * 65)
    R.append("SECTION 4 — ROW COUNTS")
    R.append("=" * 65)
    R.append("")
    R.append(f"  {'MONTH':<20} {'ROWS':>10} {'MB':>7}")
    R.append("  " + "-" * 40)
    total = 0
    current_year = None
    for fi in clean_files:
        if fi['year'] != current_year:
            if current_year is not None:
                R.append("")
            current_year = fi['year']
        with open(fi['path']) as f:
            rows = sum(1 for _ in f) - 1
        total += rows
        label = f"{MONTH_NAMES[fi['month']]} {fi['year']}"
        R.append(f"  {label:<20} {rows:>10,} {fi['size_mb']:>6.1f}")
    R.append("  " + "-" * 40)
    R.append(f"  {'TOTAL':<20} {total:>10,}")
    R.append(f"\n  Total flights in pipeline: {total:,}")


def section_logs(R):
    R.append("")
    R.append("=" * 65)
    R.append("SECTION 5 — RECENT UPDATE LOGS")
    R.append("=" * 65)
    if not os.path.exists(LOG_DIR):
        R.append("  No log directory found.")
        return
    logs = sorted(os.listdir(LOG_DIR), reverse=True)[:10]
    if not logs:
        R.append("  No logs found yet.")
        return
    R.append(f"  {'LOG FILE':<40} {'KB':>6}  MODIFIED")
    R.append("  " + "-" * 62)
    for f in logs:
        path = os.path.join(LOG_DIR, f)
        kb = os.path.getsize(path) / 1024
        mod = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
        R.append(f"  {f:<40} {kb:>5.1f}  {mod}")


def section_dataset_files(R):
    R.append("")
    R.append("=" * 65)
    R.append("SECTION 6 — DATASET FILES")
    R.append("=" * 65)
    R.append("")
    R.append(f"  {'FILENAME':<40} {'MB':>7}  MODIFIED")
    R.append("  " + "-" * 60)
    found = False
    for f in sorted(os.listdir(DATA_DIR)):
        if (f.startswith('OTP_YEAR_') or f.startswith('OTP_UNIFIED_') or
                f == 'OTP_CONSOLIDATED_ALL.csv') and f.endswith('.csv'):
            path = os.path.join(DATA_DIR, f)
            mb = os.path.getsize(path) / 1024 / 1024
            mod = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M')
            R.append(f"  {f:<40} {mb:>6.1f}  {mod}")
            found = True
    if not found:
        R.append("  No unified dataset files found.")
        R.append("  Run pipeline_06_smart_update.py to build them.")


def main():
    print()
    print("=" * 65)
    print("  BTS ON-TIME PERFORMANCE — MONITORING REPORT")
    print("=" * 65)
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    clean_files = get_all_clean_files()

    R = []
    R.append("BTS ON-TIME PERFORMANCE — MONITORING REPORT")
    R.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    R.append("")

    section_pipeline_state(R)
    section_coverage(R, clean_files)
    section_data_quality(R, clean_files)
    section_row_counts(R, clean_files)
    section_logs(R)
    section_dataset_files(R)

    R.append("")
    R.append("=" * 65)
    R.append("END OF REPORT")
    R.append("=" * 65)

    for line in R:
        print(line)

    report_path = os.path.join(
        REPORT_DIR,
        f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )
    with open(report_path, 'w') as f:
        f.write('\n'.join(R))

    print()
    print(f"  Report saved to: {os.path.basename(report_path)}")
    print()


if __name__ == '__main__':
    main()