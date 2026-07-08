# script_01_load_and_explore.py
# DOT On-Time Performance — Load, Explore, Track N923WN
# Dataset: OTP_APR2026.csv (April 2026, all carriers)

import pandas as pd

# ── 1. LOAD ──────────────────────────────────────────────────────────────────

DATA_PATH = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\OTP_APR2026.csv"

print("Loading dataset...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip()          # removes hidden whitespace in column names

print(f"Done. {len(df):,} rows x {len(df.columns)} columns\n")


# ── 2. BASIC SANITY CHECK ────────────────────────────────────────────────────

print("=" * 60)
print("DATASET OVERVIEW")
print("=" * 60)
print(f"Date range   : {df['FlightDate'].min()} to {df['FlightDate'].max()}")
print(f"Total flights: {len(df):,}")
print(f"Columns      : {len(df.columns)}")
print()


# ── 3. CARRIER BREAKDOWN ─────────────────────────────────────────────────────

print("=" * 60)
print("FLIGHTS BY OPERATING CARRIER (top 10)")
print("=" * 60)
carrier_counts = df['Operating_Airline'].value_counts().head(10)
for carrier, count in carrier_counts.items():
    bar = "█" * (count // 2000)
    print(f"  {carrier:<6} {count:>7,}  {bar}")
print()


# ── 4. FILTER TO SOUTHWEST ───────────────────────────────────────────────────

wn = df[df['Operating_Airline'] == 'WN'].copy()

print("=" * 60)
print("SOUTHWEST (WN) SUMMARY")
print("=" * 60)
print(f"Total WN flights    : {len(wn):,}")
print(f"Unique tail numbers : {wn['Tail_Number'].nunique():,}")
print(f"Unique routes       : {(wn['Origin'] + '→' + wn['Dest']).nunique():,}")
print(f"Unique airports     : {wn['Origin'].nunique():,}")
print(f"On-time rate (≤15m) : {(wn['ArrDelay'] <= 15).sum() / wn['Cancelled'].eq(0).sum() * 100:.1f}%")
print(f"Avg arrival delay   : {wn['ArrDelay'].mean():.1f} mins")
print()


# ── 5. TOP SOUTHWEST TAIL NUMBERS ────────────────────────────────────────────

print("=" * 60)
print("TOP 10 BUSIEST SOUTHWEST AIRCRAFT (by legs flown)")
print("=" * 60)
tail_summary = wn.groupby('Tail_Number').agg(
    legs        =('FlightDate', 'count'),
    days_flown  =('FlightDate', 'nunique'),
    cancellations=('Cancelled', 'sum'),
    diversions  =('Diverted', 'sum'),
    avg_delay   =('ArrDelay', 'mean')
).sort_values('legs', ascending=False).head(10)

print(tail_summary.to_string())
print()


# ── 6. TRACK N923WN ──────────────────────────────────────────────────────────

TAIL = 'N923WN'

plane = wn[wn['Tail_Number'] == TAIL].sort_values(
    ['FlightDate', 'CRSDepTime']
).reset_index(drop=True)

print("=" * 60)
print(f"TRACKING {TAIL} — FULL APRIL 2026 ROTATION")
print("=" * 60)
print(f"Total legs      : {len(plane)}")
print(f"Days flown      : {plane['FlightDate'].nunique()}")
print(f"Cancellations   : {int(plane['Cancelled'].sum())}")
print(f"Diversions      : {int(plane['Diverted'].sum())}")
print(f"Total air time  : {plane['AirTime'].sum() / 60:.1f} hrs")
print(f"Total distance  : {plane['Distance'].sum():,.0f} miles")
print(f"Avg arr delay   : {plane['ArrDelay'].mean():.1f} mins")
print(f"On-time rate    : {(plane['ArrDelay'] <= 15).sum() / len(plane[plane['Cancelled']==0]) * 100:.1f}%")
print(f"Worst delay     : {plane['ArrDelay'].max():.0f} mins")
print(f"Best arrival    : {plane['ArrDelay'].min():.0f} mins")
print(f"Airports visited: {plane['Origin'].nunique()}")
print()


# ── 7. DAILY ROTATION SUMMARY ────────────────────────────────────────────────

print("=" * 60)
print(f"{TAIL} — DAILY SUMMARY")
print("=" * 60)

daily = plane.groupby('FlightDate').agg(
    legs            =('FlightDate', 'count'),
    avg_delay       =('ArrDelay', 'mean'),
    max_delay       =('ArrDelay', 'max'),
    late_legs       =('ArrDel15', 'sum'),
    diversions      =('Diverted', 'sum'),
    start_airport   =('Origin', 'first'),
    end_airport     =('Dest', 'last')
).reset_index()

for _, row in daily.iterrows():
    flag = ""
    if row['diversions'] > 0:
        flag = "  ⚠ DIVERSION"
    elif row['max_delay'] >= 60:
        flag = "  ⚠ MAJOR DELAY"
    elif row['avg_delay'] < -10:
        flag = "  ✓ GREAT DAY"

    print(f"  {row['FlightDate']}  "
          f"{int(row['legs'])} legs  "
          f"{row['start_airport']}→{row['end_airport']}  "
          f"avg delay: {row['avg_delay']:+.0f}m  "
          f"max: {row['max_delay']:+.0f}m"
          f"{flag}")
print()


# ── 8. THE APRIL 27 DIVERSION DAY ────────────────────────────────────────────

print("=" * 60)
print(f"{TAIL} — APRIL 27 DIVERSION DAY (detail)")
print("=" * 60)

day27 = plane[plane['FlightDate'] == '2026-04-27']
cols = ['Flight_Number_Operating_Airline', 'Origin', 'Dest',
        'CRSDepTime', 'DepTime', 'DepDelay',
        'CRSArrTime', 'ArrTime', 'ArrDelay',
        'TaxiOut', 'AirTime', 'TaxiIn',
        'Diverted', 'CarrierDelay', 'NASDelay', 'LateAircraftDelay']

print(day27[cols].to_string(index=False))
print()


# ── 9. DELAY CAUSE BREAKDOWN ─────────────────────────────────────────────────

print("=" * 60)
print(f"{TAIL} — DELAY CAUSES (full month)")
print("=" * 60)

causes = ['CarrierDelay', 'WeatherDelay', 'NASDelay', 'SecurityDelay', 'LateAircraftDelay']
for c in causes:
    total = plane[c].sum()
    legs  = (plane[c] > 0).sum()
    print(f"  {c:<22}: {total:>6.0f} mins  across {legs:>2} legs")

print()
print("Script complete.")