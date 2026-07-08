# config.py
# Paths and settings for the Aircraft Analyzer

import os

# ── PATHS ─────────────────────────────────────────────────────────────────────

BASE_DIR    = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines"
DATA_DIR    = os.path.join(BASE_DIR, "Data")
OUTPUT_DIR  = os.path.join(BASE_DIR, "Outputs")

DATA_FILE   = os.path.join(DATA_DIR, "OTP_APR2026.csv")

# ── THRESHOLDS ────────────────────────────────────────────────────────────────

ON_TIME_THRESHOLD   = 15    # minutes — FAA definition
TIGHT_TURNAROUND    = 25    # minutes — risky for Southwest
TARGET_TURNAROUND   = 45    # minutes — Southwest target upper bound
MAJOR_DELAY         = 60    # minutes — flag as major delay

# ── CHART STYLE ───────────────────────────────────────────────────────────────

BG_COLOR        = '#0f1117'
GRID_COLOR      = '#222233'
SPINE_COLOR     = '#333344'
TEXT_COLOR      = '#aaaaaa'
WHITE           = 'white'

COLOR_GOOD      = '#00cc88'   # green  — early / on-time
COLOR_WARN      = '#ffcc00'   # yellow — minor delay
COLOR_BAD       = '#ff8800'   # orange — major delay
COLOR_CRITICAL  = '#ff4444'   # red    — diversion / severe
COLOR_ACCENT    = '#4488ff'   # blue   — neutral / long gaps
COLOR_HIGHLIGHT = '#ff8800'   # orange — trend lines / means

SOURCE_NOTE = 'Source: BTS Marketing Carrier On-Time Performance | April 2026'