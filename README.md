# US Domestic Airline On-Time Performance Analysis

**Author:** Abishek Singanur Aswan Kumar  
**Program:** M.S. Industrial Engineering, University of Illinois Urbana-Champaign  
**Supervisor:** Prof. Yasin  
**Dataset:** BTS Marketing Carrier On-Time Performance (Beginning January 2018)

---

## Project Overview

This project builds an end-to-end automated data pipeline and analysis system for US domestic airline on-time performance data published by the Bureau of Transportation Statistics (BTS). The pipeline downloads, cleans, stores, and analyses flight-level data covering January 2018 to present (~59 million flights).

---

## Project Structure

```
Airlines/
│
├── Data/
│   ├── Raw/                        # Downloaded zip files from BTS
│   ├── Clean/                      # Processed monthly CSVs (15 fields)
│   ├── OTP_YEAR_YYYY.csv           # Yearly unified files (one per year)
│   ├── OTP_UNIFIED_2024_2025.csv   # Two-year combined dataset
│   ├── OTP_CONSOLIDATED_ALL.csv    # Full 2018-2026 consolidated dataset
│   ├── OTP_SUMMARY_YYYY.txt        # Dataset summary reports
│   └── pipeline_state.json         # Pipeline state tracker
│
├── Notebooks/
│   ├── week_1_schema_exploration.ipynb   # Week 1 EDA notebook
│   └── week_2_pipeline.ipynb            # Week 2 pipeline documentation
│
├── Outputs/
│   ├── *.png                        # Analysis charts
│   └── monitoring_*.txt             # Monitoring reports
│
├── Logs/
│   └── *.log                        # Pipeline run logs
│
├── pipeline_01_auto_download.py     # Stage 1: Automated BTS download
├── pipeline_02_process.py           # Stage 2: Unzip, select, clean
├── pipeline_03_build_dataset.py     # Stage 3: Build unified dataset
├── pipeline_04_carrier_comparison.py # WN vs AA analysis
├── pipeline_05_check_new_data.py    # Check BTS for new releases
├── pipeline_06_smart_update.py      # Auto-download and rebuild if new
├── pipeline_07_monitoring.py        # Data quality and coverage report
├── run_pipeline.py                  # Master runner (Task Scheduler target)
│
├── analyze_aircraft.py              # Interactive aircraft analyzer
├── config.py                        # Chart styles and shared config
│
├── script_01_load_and_explore.py    # Week 1: Load and explore
├── script_02_visualise_rotation.py  # Week 1: Daily delay chart
├── script_03_rotation_tracker.py    # Week 1: Full leg-by-leg rotation
├── script_04_turnaround_analysis.py # Week 1: Turnaround time analysis
├── script_05_cascade_analysis.py    # Week 1: Cascade chain analysis
├── script_06_route_analysis.py      # Week 1: Route analysis
├── script_07_time_of_day.py         # Week 1: Time of day performance
├── script_08_airtime_recovery.py    # Week 1: Air time recovery
├── script_09_april12_investigation.py # Week 1: Anomalous day investigation
│
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

---

## Setup

```bash
# 1. Create virtual environment
python -m venv venv

# 2. Activate
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Pipeline Usage

### Download data for a year
```bash
python pipeline_01_auto_download.py
# Enter: 2025  (or range: 2018-2025)
```

### Process raw downloads
```bash
python pipeline_02_process.py
```

### Build unified dataset
```bash
python pipeline_03_build_dataset.py
```

### Run full pipeline (check + update + monitor)
```bash
python run_pipeline.py
```

### Analyse a specific aircraft
```bash
python analyze_aircraft.py
# Select carrier (e.g. WN) and tail number
```

### Check data quality
```bash
python pipeline_07_monitoring.py
```

---

## Automated Scheduling

The pipeline runs automatically every night at midnight via Windows Task Scheduler (task name: `BTS_OTP_Pipeline`). It checks BTS for new monthly data, downloads and processes anything new, rebuilds datasets, and generates a monitoring report.

```powershell
# Check scheduler status
Get-ScheduledTaskInfo -TaskName "BTS_OTP_Pipeline"

# Run manually
Start-ScheduledTask -TaskName "BTS_OTP_Pipeline"
```

---

## Dataset

| Field | Description |
|---|---|
| FlightDate | Date of flight |
| Carrier | Marketing airline code (WN, AA, DL etc) |
| TailNumber | Physical aircraft identifier |
| FlightNumber | Route/schedule label |
| Origin | Departure airport code |
| Dest | Arrival airport code |
| SchedDep | Scheduled departure time (HHMM) |
| ActualDep | Actual departure time (HHMM) |
| DepDelay | Departure delay (minutes) |
| SchedArr | Scheduled arrival time (HHMM) |
| ActualArr | Actual arrival time (HHMM) |
| ArrDelay | Arrival delay (minutes) |
| Cancelled | 1 = cancelled, 0 = operated |
| Diverted | 1 = diverted, 0 = normal |
| LateAircraftDelay | Delay caused by prior leg (minutes) |

---

## Coverage

| Period | Months | Flights |
|---|---|---|
| 2018 | 12 | ~7.9M |
| 2019 | 12 | ~8.2M |
| 2020 | 12 | ~5.4M (COVID impact) |
| 2021 | 12 | ~6.7M (recovery) |
| 2022 | 12 | ~7.3M |
| 2023 | 12 | ~7.8M |
| 2024 | 12 | ~7.5M |
| 2025 | 12 | ~7.7M |
| 2026 | 5 | ~3.3M (Jan–May) |
| **Total** | **101** | **~59M** |

---

## Key Findings (Week 1 & 2)

- **N923WN (Southwest)** — 175 legs in April 2026, 84.6% on-time vs 78.4% fleet average. Two diversions on April 27 collapsed the rotation producing a 444-minute worst leg delay.
- **Southwest vs American (2024-2025)** — WN outperforms AA on 5 of 6 operational metrics. WN on-time rate 79.6% vs AA 76.8%. WN cancellation rate 0.84% vs AA 1.92%. AA's higher cascade leg rate reflects its hub-and-spoke network structure.
- **Seasonal pattern** — June and July are consistently the worst months (69-70% on-time). September is consistently the best (83-87%).