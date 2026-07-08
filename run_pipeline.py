# run_pipeline.py
# BTS On-Time Performance — Master Runner
# One command runs the full pipeline:
# 1. Check BTS for new data
# 2. Download and process anything new
# 3. Rebuild datasets
# 4. Generate monitoring report
#
# This is the script Windows Task Scheduler runs at midnight.

import os
import sys
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE_DIR = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines"
LOG_DIR  = os.path.join(BASE_DIR, "Logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_filename = os.path.join(
    LOG_DIR,
    f"master_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


def main():
    start = datetime.now()
    log.info("")
    log.info("#" * 65)
    log.info(f"# MASTER PIPELINE STARTED — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    log.info("#" * 65)
    log.info("")

    # ── STEP 1: Smart Update (check + download + process + rebuild) ───────────
    log.info("Running smart update...")
    try:
        from pipeline_06_smart_update import main as smart_update
        smart_update()
        log.info("Smart update complete.")
    except Exception as e:
        log.error(f"Smart update failed: {e}")

    # ── STEP 2: Monitoring Report ─────────────────────────────────────────────
    log.info("")
    log.info("Generating monitoring report...")
    try:
        from pipeline_07_monitoring import main as monitoring
        monitoring()
        log.info("Monitoring report complete.")
    except Exception as e:
        log.error(f"Monitoring report failed: {e}")

    # ── STEP 3: Push to Hugging Face ──────────────────────────────────────────
    log.info("")
    log.info("Pushing new data to Hugging Face...")
    try:
        from pipeline_08_push_to_hf import main as push_to_hf
        push_to_hf()
        log.info("Hugging Face push complete.")
    except Exception as e:
        log.error(f"Hugging Face push failed: {e}")

    elapsed = (datetime.now() - start).total_seconds()
    log.info("")
    log.info("#" * 65)
    log.info(f"# MASTER PIPELINE COMPLETE — {elapsed:.0f} seconds")
    log.info("#" * 65)
    log.info(f"# Log: {log_filename}")
    log.info("")


if __name__ == '__main__':
    main()