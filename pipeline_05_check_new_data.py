# pipeline_05_check_new_data.py
# BTS On-Time Performance — New Data Checker
# Visits BTS, reads the "Latest Available Data" label, compares against
# what you have locally, and reports exactly what's new.

import os
import re
import time
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ── CONFIG ────────────────────────────────────────────────────────────────────

RAW_DIR    = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Raw"
CLEAN_DIR  = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Clean"
STATE_FILE = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\pipeline_state.json"

BTS_URL = "https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGK&QO_fu146_anzr=b0-gvzr"

MONTH_NAMES = {
    1:'January', 2:'February', 3:'March', 4:'April',
    5:'May', 6:'June', 7:'July', 8:'August',
    9:'September', 10:'October', 11:'November', 12:'December'
}
MONTH_NUM = {v: k for k, v in MONTH_NAMES.items()}


def get_latest_available_from_bts():
    """Visit BTS and read the 'Latest Available Data: Month Year' label."""
    print("  Opening BTS to check latest available data...")

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    try:
        driver.get(BTS_URL)
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)

        page_text = driver.find_element(By.TAG_NAME, "body").text

        match = re.search(
            r"Latest Available Data:\s*([A-Za-z]+)\s+(\d{4})",
            page_text
        )
        if match:
            month_name, year = match.group(1), int(match.group(2))
            month_num = MONTH_NUM.get(month_name)
            if month_num:
                return year, month_num, month_name
        return None, None, None
    finally:
        driver.quit()


def get_local_months():
    """Return set of (year, month) tuples we already have as clean files."""
    local = set()
    if not os.path.exists(CLEAN_DIR):
        return local
    for f in os.listdir(CLEAN_DIR):
        m = re.match(r"OTP_(\d{4})_(\d{2})_", f)
        if m:
            local.add((int(m.group(1)), int(m.group(2))))
    return local


def build_expected_months(earliest_year=2018, earliest_month=1,
                            latest_year=None, latest_month=None):
    """Build the full list of months that should exist from earliest to latest."""
    expected = []
    y, m = earliest_year, earliest_month
    while (y, m) <= (latest_year, latest_month):
        expected.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return expected


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_checked": None, "last_known_latest": None, "check_history": []}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    print()
    print("=" * 60)
    print("  BTS DATA CHECKER")
    print("=" * 60)
    print(f"  Run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    state = load_state()

    year, month, month_name = get_latest_available_from_bts()

    if year is None:
        print("  Could not determine latest available data from BTS.")
        print("  BTS page structure may have changed, or site is unreachable.")
        return

    print(f"  BTS latest available: {month_name} {year}")

    previous_latest = state.get("last_known_latest")
    is_new_release = previous_latest != f"{year}-{month:02d}"

    if is_new_release and previous_latest is not None:
        print(f"  NEW RELEASE detected since last check (was: {previous_latest})")
    elif previous_latest is None:
        print(f"  First check — no previous baseline.")
    else:
        print(f"  No new release since last check.")

    local_months = get_local_months()
    expected_months = build_expected_months(
        earliest_year=2018, earliest_month=1,
        latest_year=year, latest_month=month
    )

    missing = [m for m in expected_months if m not in local_months]

    print()
    print("=" * 60)
    print("  COVERAGE REPORT")
    print("=" * 60)
    print(f"  Expected months (2018-01 to {year}-{month:02d}): {len(expected_months)}")
    print(f"  Local months found                          : {len(local_months)}")
    print(f"  Missing months                               : {len(missing)}")

    if missing:
        print(f"\n  Missing:")
        for y, m in missing:
            print(f"    {MONTH_NAMES[m]} {y}")
    else:
        print(f"\n  Fully up to date — no missing months.")

    state["last_checked"] = datetime.now().isoformat()
    state["last_known_latest"] = f"{year}-{month:02d}"
    state["check_history"].append({
        "checked_at": datetime.now().isoformat(),
        "latest_available": f"{year}-{month:02d}",
        "missing_count": len(missing),
        "new_release": is_new_release
    })
    state["check_history"] = state["check_history"][-30:]
    save_state(state)

    print()
    print(f"  State saved to: {STATE_FILE}")

    if missing:
        print()
        print("  Next step: run pipeline_06_smart_update.py to download and")
        print("  process the missing months automatically.")

    print()
    print("  Check complete.")
    print()

    return missing


if __name__ == '__main__':
    main()