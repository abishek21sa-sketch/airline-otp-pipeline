# diagnostic_bts_fields.py
# Opens the BTS download page and prints all checkbox IDs
# Run this to find the exact field names before the main downloader

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

BTS_URL = "https://transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FGK&QO_fu146_anzr=b0-gvzr"

print("Opening BTS page...")
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)

driver.get(BTS_URL)
time.sleep(5)

print("\nAll checkboxes found on page:")
print("=" * 60)
checkboxes = driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
print(f"Total checkboxes: {len(checkboxes)}")
print()
for cb in checkboxes:
    cb_id    = cb.get_attribute('id')
    cb_name  = cb.get_attribute('name')
    cb_value = cb.get_attribute('value')
    checked  = cb.is_selected()
    print(f"  id={cb_id}  name={cb_name}  value={cb_value}  checked={checked}")

print()
print("=" * 60)
print("All dropdowns/selects found:")
selects = driver.find_elements(By.TAG_NAME, "select")
for sel in selects:
    sel_id   = sel.get_attribute('id')
    sel_name = sel.get_attribute('name')
    print(f"  id={sel_id}  name={sel_name}")

print()
print("=" * 60)
print("Download button:")
buttons = driver.find_elements(By.XPATH,
    "//input[@type='button'] | //input[@type='submit'] | //button")
for btn in buttons:
    print(f"  tag={btn.tag_name}  type={btn.get_attribute('type')}  "
          f"id={btn.get_attribute('id')}  value={btn.get_attribute('value')}  "
          f"text={btn.text}")

print()
input("Press Enter to close browser...")
driver.quit()
print("Done.")