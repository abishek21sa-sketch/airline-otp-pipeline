# pipeline_01_auto_download.py
# BTS On-Time Performance — Automated Downloader
# Uses Selenium to control Chrome and download all 12 monthly files for a given year
# Run this script, enter a year, walk away — files appear in Data/Raw/

import os
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_DIR = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Raw"

BTS_URL = "https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGK&QO_fu146_anzr=b0-gvzr"

MONTH_NAMES = {
    1: "January",   2: "February",  3: "March",
    4: "April",     5: "May",       6: "June",
    7: "July",      8: "August",    9: "September",
    10: "October",  11: "November", 12: "December"
}

# Actual BTS checkbox IDs from diagnostic
FIELDS = [
    "FL_DATE",
    "MKT_UNIQUE_CARRIER",
    "TAIL_NUM",
    "MKT_CARRIER_FL_NUM",
    "ORIGIN",
    "DEST",
    "CRS_DEP_TIME",
    "DEP_TIME",
    "DEP_DELAY",
    "CRS_ARR_TIME",
    "ARR_TIME",
    "ARR_DELAY",
    "CANCELLED",
    "DIVERTED",
    "LATE_AIRCRAFT_DELAY",
]

# Fields BTS pre-checks by default — we need to uncheck these
DEFAULT_CHECKED = [
    "ORIGIN_AIRPORT_ID",
    "ORIGIN_AIRPORT_SEQ_ID",
    "ORIGIN_CITY_MARKET_ID",
    "DEST_AIRPORT_ID",
    "DEST_AIRPORT_SEQ_ID",
    "DEST_CITY_MARKET_ID",
]

DOWNLOAD_WAIT = 180


# ── SETUP ─────────────────────────────────────────────────────────────────────

def get_year():
    print()
    print("=" * 60)
    print("  BTS ON-TIME PERFORMANCE — AUTO DOWNLOADER")
    print("=" * 60)
    print()
    while True:
        year_input = input("  Enter year to download (2018-2026): ").strip()
        if year_input.isdigit() and 2018 <= int(year_input) <= 2026:
            return int(year_input)
        print("  Please enter a valid year between 2018 and 2026.")


def check_existing(year):
    os.makedirs(RAW_DIR, exist_ok=True)
    existing, missing = [], []
    for month in range(1, 13):
        pattern = f"_{year}_{month}.zip"
        found = any(f.endswith(pattern) for f in os.listdir(RAW_DIR))
        if found:
            existing.append(month)
        else:
            missing.append(month)
    return existing, missing


def setup_driver():
    os.makedirs(RAW_DIR, exist_ok=True)
    options = webdriver.ChromeOptions()
    prefs = {
        "download.default_directory": RAW_DIR,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    options.add_experimental_option("prefs", prefs)
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    driver.maximize_window()
    return driver


# ── DOWNLOAD LOGIC ────────────────────────────────────────────────────────────

def wait_for_download(raw_dir, existing_files, timeout=180):
    start = time.time()
    while time.time() - start < timeout:
        current_files = set(os.listdir(raw_dir))
        new_files = current_files - existing_files
        complete = [f for f in new_files
                    if not f.endswith('.crdownload') and
                       not f.endswith('.tmp') and
                       not f.startswith('.')]
        if complete:
            return complete[0]
        time.sleep(2)
    return None


def set_filters(driver, wait, year, month):
    """Set year and month dropdowns."""
    # Year
    try:
        year_select = Select(wait.until(
            EC.presence_of_element_located((By.ID, "cboYear"))
        ))
        year_select.select_by_visible_text(str(year))
        print(f"    Year set to {year}")
    except Exception as e:
        print(f"    Warning - year filter failed: {e}")
    time.sleep(1)

    # Month
    try:
        period_select = Select(driver.find_element(By.ID, "cboPeriod"))
        period_select.select_by_index(month - 1)
        print(f"    Month set to {MONTH_NAMES[month]}")
    except Exception as e:
        print(f"    Warning - month filter failed: {e}")
    time.sleep(1)


def uncheck_defaults(driver):
    """Uncheck the fields BTS pre-selects."""
    for field_id in DEFAULT_CHECKED:
        try:
            cb = driver.find_element(By.ID, field_id)
            if cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
        except:
            pass
    time.sleep(0.5)


def select_our_fields(driver):
    """Check our 15 target fields."""
    checked = 0
    for field_id in FIELDS:
        try:
            cb = driver.find_element(By.ID, field_id)
            if not cb.is_selected():
                driver.execute_script("arguments[0].click();", cb)
            checked += 1
        except Exception as e:
            print(f"    Warning - field not found: {field_id}")
    print(f"    {checked}/{len(FIELDS)} fields selected")
    time.sleep(0.5)


def check_prezipped(driver):
    """Check the Prezipped File checkbox."""
    try:
        cb = driver.find_element(By.ID, "chkDownloadZip")
        if not cb.is_selected():
            driver.execute_script("arguments[0].click();", cb)
        print(f"    Prezipped File checked")
    except Exception as e:
        print(f"    Warning - could not check Prezipped: {e}")
    time.sleep(0.5)


def click_download(driver, wait):
    """Click the Download button."""
    try:
        btn = wait.until(EC.element_to_be_clickable((By.ID, "btnDownload")))
        driver.execute_script("arguments[0].click();", btn)
        print(f"    Download clicked")
    except Exception as e:
        print(f"    Warning - could not click Download: {e}")


def download_month(driver, wait, year, month):
    print(f"\n  [{month}/12] Downloading {MONTH_NAMES[month]} {year}...")

    existing_files = set(os.listdir(RAW_DIR))

    driver.get(BTS_URL)
    wait.until(EC.presence_of_element_located((By.ID, "cboYear")))
    time.sleep(3)

    set_filters(driver, wait, year, month)
    uncheck_defaults(driver)
    select_our_fields(driver)
    check_prezipped(driver)
    click_download(driver, wait)

    print(f"    Waiting for download...")
    filename = wait_for_download(RAW_DIR, existing_files, timeout=DOWNLOAD_WAIT)

    if filename:
        size_mb = os.path.getsize(os.path.join(RAW_DIR, filename)) / 1024 / 1024
        print(f"    Done — {filename} ({size_mb:.1f} MB)")
        return True
    else:
        print(f"    Timed out — {MONTH_NAMES[month]} {year} may have failed")
        return False


# ── MAIN ──────────────────────────────────────────────────────────────────────

def get_year_range():
    print()
    print("=" * 60)
    print("  BTS ON-TIME PERFORMANCE — AUTO DOWNLOADER")
    print("=" * 60)
    print()
    print("  Enter a single year (e.g. 2025) or a range (e.g. 2018-2025)")
    print("  Data available from 2018 to present.")
    print()
    while True:
        year_input = input("  Year or range: ").strip()
        if '-' in year_input:
            parts = year_input.split('-')
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                start, end = int(parts[0]), int(parts[1])
                if 2018 <= start <= end <= 2026:
                    return list(range(start, end + 1))
        elif year_input.isdigit() and 2018 <= int(year_input) <= 2026:
            return [int(year_input)]
        print("  Please enter a valid year or range (e.g. 2018-2025).")


def main():
    years = get_year_range()

    all_missing = []
    for year in years:
        existing, missing = check_existing(year)
        for month in missing:
            all_missing.append((year, month))

    print()
    print("=" * 60)
    print(f"  DOWNLOAD PLAN FOR {years[0]}-{years[-1]}")
    print("=" * 60)
    print(f"\n  Years requested  : {years}")
    print(f"  Files to download: {len(all_missing)}")

    if len(all_missing) == 0:
        print("  All months already downloaded.")
        return

    for year in years:
        existing, missing = check_existing(year)
        if missing:
            print(f"  {year} — have {len(existing)}, need {len(missing)}")

    confirm = input(f"\n  Download {len(all_missing)} files automatically? (y/n): ").strip().lower()
    if confirm != 'y':
        print("  Cancelled.")
        return

    print("\n  Starting Chrome...")
    driver = setup_driver()
    wait   = WebDriverWait(driver, 30)

    results = {}
    total = len(all_missing)
    try:
        for i, (year, month) in enumerate(all_missing, 1):
            print(f"\n  [{i}/{total}]", end=" ")
            success = download_month(driver, wait, year, month)
            results[(year, month)] = success
            if i < total:
                print(f"    Pausing 5 seconds...")
                time.sleep(5)
    finally:
        driver.quit()

    print()
    print("=" * 60)
    print("  DOWNLOAD SUMMARY")
    print("=" * 60)
    success_count = sum(1 for v in results.values() if v)
    fail_count    = sum(1 for v in results.values() if not v)
    print(f"\n  Successful : {success_count}")
    print(f"  Failed     : {fail_count}")
    if fail_count > 0:
        failed = [MONTH_NAMES[m] for m, v in results.items() if not v]
        print(f"  Retry      : {failed}")
    print(f"\n  Files saved to: {RAW_DIR}")
    print("\n  Next: run pipeline_02_process.py")
    print()


if __name__ == '__main__':
    main()