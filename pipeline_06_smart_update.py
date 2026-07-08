# pipeline_06_smart_update.py
# BTS On-Time Performance — Smart Auto-Updater
# Checks for new data, downloads only what's missing, processes it,
# and updates both year-by-year and consolidated datasets.
# Designed to run unattended (e.g. via Windows Task Scheduler at midnight).

import os
import sys
import json
import time
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline_05_check_new_data import (
    get_latest_available_from_bts, get_local_months,
    build_expected_months, MONTH_NAMES
)
from pipeline_01_auto_download import setup_driver, download_month
from pipeline_02_process import process_zip

from selenium.webdriver.support.ui import WebDriverWait

import pandas as pd

# ── CONFIG ────────────────────────────────────────────────────────────────────

BASE_DIR   = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines"
RAW_DIR    = os.path.join(BASE_DIR, "Data", "Raw")
CLEAN_DIR  = os.path.join(BASE_DIR, "Data", "Clean")
DATA_DIR   = os.path.join(BASE_DIR, "Data")
LOG_DIR    = os.path.join(BASE_DIR, "Logs")

os.makedirs(LOG_DIR, exist_ok=True)

# ── LOGGING SETUP ─────────────────────────────────────────────────────────────

log_filename = os.path.join(LOG_DIR, f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


# ── STEP 1: CHECK FOR NEW DATA ────────────────────────────────────────────────

def check_for_new_data():
    log.info("=" * 60)
    log.info("STEP 1 - Checking BTS for new data")
    log.info("=" * 60)

    year, month, month_name = get_latest_available_from_bts()
    if year is None:
        log.error("Could not reach BTS or parse latest available data.")
        return None, []

    log.info(f"BTS latest available: {month_name} {year}")

    local_months = get_local_months()
    expected_months = build_expected_months(
        earliest_year=2018, earliest_month=1,
        latest_year=year, latest_month=month
    )
    missing = [m for m in expected_months if m not in local_months]

    log.info(f"Local months found: {len(local_months)}")
    log.info(f"Missing months: {len(missing)}")
    for y, m in missing:
        log.info(f"  Missing: {MONTH_NAMES[m]} {y}")

    return (year, month), missing


# ── STEP 2: DOWNLOAD MISSING MONTHS ───────────────────────────────────────────

def download_missing(missing_months):
    if not missing_months:
        log.info("No missing months - skipping download step.")
        return True

    log.info("=" * 60)
    log.info(f"STEP 2 - Downloading {len(missing_months)} missing months")
    log.info("=" * 60)

    driver = setup_driver()
    wait   = WebDriverWait(driver, 30)

    success_count = 0
    fail_count    = 0

    try:
        for i, (year, month) in enumerate(missing_months, 1):
            log.info(f"[{i}/{len(missing_months)}] Downloading "
                      f"{MONTH_NAMES[month]} {year}...")
            try:
                success = download_month(driver, wait, year, month)
                if success:
                    success_count += 1
                    log.info(f"  Success: {MONTH_NAMES[month]} {year}")
                else:
                    fail_count += 1
                    log.warning(f"  Failed: {MONTH_NAMES[month]} {year}")
            except Exception as e:
                fail_count += 1
                log.error(f"  Error downloading {MONTH_NAMES[month]} {year}: {e}")
                try:
                    driver.switch_to.alert.accept()
                except:
                    pass
            if i < len(missing_months):
                time.sleep(5)
    finally:
        driver.quit()

    log.info(f"Download complete: {success_count} success, {fail_count} failed")
    return fail_count == 0


# ── STEP 3: PROCESS NEW RAW FILES ─────────────────────────────────────────────

def process_new_files():
    log.info("=" * 60)
    log.info("STEP 3 - Processing new raw files")
    log.info("=" * 60)

    if not os.path.exists(RAW_DIR):
        log.warning("Raw directory does not exist.")
        return 0

    zip_files = sorted([
        os.path.join(RAW_DIR, f) for f in os.listdir(RAW_DIR)
        if f.endswith('.zip') and 'On_Time' in f
    ])

    temp_dir = os.path.join(RAW_DIR, "_temp")
    processed_count = 0

    for zip_path in zip_files:
        try:
            result = process_zip(zip_path, CLEAN_DIR, temp_dir)
            if result:
                processed_count += 1
        except Exception as e:
            log.error(f"Error processing {os.path.basename(zip_path)}: {e}")

    try:
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)
    except:
        pass

    log.info(f"Processing complete: {processed_count} files handled")
    return processed_count


# ── STEP 4: REBUILD YEAR-BY-YEAR AND CONSOLIDATED DATASETS ───────────────────

def rebuild_datasets():
    log.info("=" * 60)
    log.info("STEP 4 - Rebuilding year-by-year and consolidated datasets")
    log.info("=" * 60)

    clean_files = sorted([
        os.path.join(CLEAN_DIR, f) for f in os.listdir(CLEAN_DIR)
        if f.startswith('OTP_') and f.endswith('.csv')
    ])

    if not clean_files:
        log.warning("No clean files found.")
        return None

    by_year = {}
    for f in clean_files:
        name = os.path.basename(f)
        parts = name.replace('.csv', '').split('_')
        year = int(parts[1])
        by_year.setdefault(year, []).append(f)

    log.info("Building year-by-year files...")
    for year, files in sorted(by_year.items()):
        frames = [pd.read_csv(f, low_memory=False) for f in sorted(files)]
        year_df = pd.concat(frames, ignore_index=True)
        year_path = os.path.join(DATA_DIR, f"OTP_YEAR_{year}.csv")
        year_df.to_csv(year_path, index=False)
        size_mb = os.path.getsize(year_path) / 1024 / 1024
        log.info(f"  {year}: {len(year_df):,} rows -> "
                  f"OTP_YEAR_{year}.csv ({size_mb:.1f} MB)")

    log.info("Building consolidated dataset (all years)...")
    all_frames = []
    for f in clean_files:
        name = os.path.basename(f)
        parts = name.replace('.csv', '').split('_')
        year, month = int(parts[1]), int(parts[2])
        df = pd.read_csv(f, low_memory=False)
        df['Year']  = year
        df['Month'] = month
        all_frames.append(df)

    combined = pd.concat(all_frames, ignore_index=True)
    combined['FlightDate'] = pd.to_datetime(combined['FlightDate'], errors='coerce')

    consolidated_path = os.path.join(DATA_DIR, "OTP_CONSOLIDATED_ALL.csv")
    combined.to_csv(consolidated_path, index=False)
    size_mb = os.path.getsize(consolidated_path) / 1024 / 1024

    log.info(f"Consolidated: {len(combined):,} rows -> "
              f"OTP_CONSOLIDATED_ALL.csv ({size_mb:.1f} MB)")
    log.info(f"Date range: {combined['FlightDate'].min().date()} to "
              f"{combined['FlightDate'].max().date()}")

    return len(combined)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    start_time = datetime.now()
    log.info("")
    log.info("#" * 60)
    log.info(f"# SMART UPDATE STARTED - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("#" * 60)

    latest, missing = check_for_new_data()

    if latest is None:
        log.error("Could not check BTS. Aborting.")
        return

    if not missing:
        log.info("Dataset is already fully up to date. Nothing to do.")
        log.info(f"Log saved to: {log_filename}")
        return

    download_ok = download_missing(missing)

    processed = process_new_files()

    total_rows = None
    if processed > 0:
        total_rows = rebuild_datasets()

    elapsed = (datetime.now() - start_time).total_seconds()

    log.info("")
    log.info("#" * 60)
    log.info("# SMART UPDATE COMPLETE")
    log.info("#" * 60)
    log.info(f"Elapsed time      : {elapsed:.0f} seconds")
    log.info(f"Months downloaded : {len(missing)}")
    log.info(f"Files processed   : {processed}")
    if total_rows:
        log.info(f"Total rows in dataset: {total_rows:,}")
    log.info(f"Log saved to: {log_filename}")
    log.info("")


if __name__ == '__main__':
    main()