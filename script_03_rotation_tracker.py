# script_03_rotation_tracker.py
# N923WN — Full Leg-by-Leg Rotation Tracker, April 2026

import pandas as pd

# ── 1. LOAD & FILTER ─────────────────────────────────────────────────────────

DATA_PATH = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\OTP_APR2026.csv"

print("Loading data...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip()

wn    = df[df['Operating_Airline'] == 'WN'].copy()
plane = wn[wn['Tail_Number'] == 'N923WN'].sort_values(
    ['FlightDate', 'CRSDepTime']
).reset_index(drop=True)

print(f"N923WN: {len(plane)} legs loaded\n")


# ── 2. DERIVED FIELDS ────────────────────────────────────────────────────────

# Turnaround time — only between legs on the same day
plane['prev_arr']  = plane['ArrTime'].shift(1)
plane['prev_date'] = plane['FlightDate'].shift(1)
same_day = plane['FlightDate'] == plane['prev_date']
plane['turnaround'] = None
plane.loc[same_day, 'turnaround'] = (
    plane.loc[same_day, 'CRSDepTime'] - plane.loc[same_day, 'prev_arr']
)

# Cascade flag — this leg suffered from a prior leg's delay
plane['cascade'] = plane['LateAircraftDelay'].fillna(0) > 0


# Primary delay cause
def primary_cause(row):
    if row['Diverted']  == 1: return 'DIVERTED'
    if row['Cancelled'] == 1: return 'CANCELLED'
    if pd.isna(row['ArrDelay']) or row['ArrDelay'] <= 0:
        return '—'
    cd  = row['CarrierDelay']      if not pd.isna(row['CarrierDelay'])      else 0
    wd  = row['WeatherDelay']      if not pd.isna(row['WeatherDelay'])      else 0
    nd  = row['NASDelay']          if not pd.isna(row['NASDelay'])          else 0
    lad = row['LateAircraftDelay'] if not pd.isna(row['LateAircraftDelay']) else 0
    causes = {'Carrier': cd, 'Weather': wd, 'NAS': nd, 'LateAC': lad}
    dominant = max(causes, key=causes.get)
    return dominant if causes[dominant] > 0 else '—'

plane['primary_cause'] = plane.apply(primary_cause, axis=1)


# ── 3. PRINT FULL ROTATION ───────────────────────────────────────────────────

print("=" * 110)
print(f"N923WN — FULL APRIL 2026 ROTATION")
print("=" * 110)
print(f"{'#':<4} {'DATE':<12} {'FL':<6} {'ROUTE':<10} "
      f"{'SCHED DEP':>9} {'ACT DEP':>8} {'DEP DLY':>8} "
      f"{'SCHED ARR':>9} {'ACT ARR':>8} {'ARR DLY':>8} "
      f"{'TRNRD':>6} {'AIR':>5} {'CAUSE':<10} {'FLAGS'}")
print("-" * 110)

prev_date = None
leg_num   = 0

for _, row in plane.iterrows():
    # Day separator
    if row['FlightDate'] != prev_date:
        if prev_date is not None:
            print()
        day_plane = plane[plane['FlightDate'] == row['FlightDate']]
        avg_d = day_plane['ArrDelay'].mean()
        print(f"  ── {row['FlightDate']}  |  "
              f"{len(day_plane)} legs  |  "
              f"{day_plane['Origin'].iloc[0]} → {day_plane['Dest'].iloc[-1]}  |  "
              f"avg delay: {avg_d:+.0f} min")
        prev_date = row['FlightDate']

    leg_num += 1

    # Format fields
    route    = f"{row['Origin']}→{row['Dest']}"
    dep_sched = f"{int(row['CRSDepTime']):04d}" if not pd.isna(row['CRSDepTime']) else '----'
    dep_act   = f"{int(row['DepTime']):04d}"    if not pd.isna(row['DepTime'])    else '----'
    arr_sched = f"{int(row['CRSArrTime']):04d}" if not pd.isna(row['CRSArrTime']) else '----'
    arr_act   = f"{int(row['ArrTime']):04d}"    if not pd.isna(row['ArrTime'])    else '----'

    dep_delay = f"{row['DepDelay']:+.0f}m" if not pd.isna(row['DepDelay']) else '  NaN'
    arr_delay = f"{row['ArrDelay']:+.0f}m" if not pd.isna(row['ArrDelay']) else '  NaN'

    ta        = f"{int(row['turnaround']):>3}m" if row['turnaround'] is not None else '  — '
    air       = f"{int(row['AirTime'])}m"        if not pd.isna(row['AirTime'])   else ' — '

    # Flags
    flags = []
    if row['Diverted']  == 1:    flags.append('⚠ DIVERTED')
    if row['cascade']:            flags.append('↩ CASCADE')
    if not pd.isna(row['ArrDelay']) and row['ArrDelay'] >= 60:
        flags.append('🔴 MAJOR')
    elif not pd.isna(row['ArrDelay']) and row['ArrDelay'] >= 15:
        flags.append('🟡 LATE')
    elif not pd.isna(row['ArrDelay']) and row['ArrDelay'] < 0:
        flags.append('🟢 EARLY')
    flag_str = '  '.join(flags)

    print(f"  {leg_num:<4} {'':<12} {int(row['Flight_Number_Operating_Airline']):<6} "
          f"{route:<10} "
          f"{dep_sched:>9} {dep_act:>8} {dep_delay:>8} "
          f"{arr_sched:>9} {arr_act:>8} {arr_delay:>8} "
          f"{ta:>6} {air:>5}  {row['primary_cause']:<10} {flag_str}")


# ── 4. MONTH SUMMARY ─────────────────────────────────────────────────────────

print()
print("=" * 110)
print("MONTH SUMMARY — N923WN APRIL 2026")
print("=" * 110)
operated = plane[plane['Cancelled'] == 0]

print(f"  Total legs          : {len(plane)}")
print(f"  Days flown          : {plane['FlightDate'].nunique()} / 30")
print(f"  Total air time      : {plane['AirTime'].sum() / 60:.1f} hrs")
print(f"  Total distance      : {plane['Distance'].sum():,.0f} miles")
print(f"  Airports visited    : {plane['Origin'].nunique()}")
print()
print(f"  On-time rate (≤15m) : {(operated['ArrDelay'] <= 15).sum() / len(operated) * 100:.1f}%")
print(f"  Avg arrival delay   : {plane['ArrDelay'].mean():.1f} mins")
print(f"  Worst single delay  : {plane['ArrDelay'].max():.0f} mins  (Apr 27, MDW→DEN)")
print(f"  Best arrival        : {plane['ArrDelay'].min():.0f} mins  (Apr 04, SAN→EUG)")
print()
print(f"  Cancellations       : {int(plane['Cancelled'].sum())}")
print(f"  Diversions          : {int(plane['Diverted'].sum())}  (Apr 27 — SRQ→STL and STL→MDW)")
print(f"  Cascade legs        : {plane['cascade'].sum()}  legs affected by prior leg delay")
print()
print("  Delay cause breakdown:")
print(f"    Carrier delay     : {plane['CarrierDelay'].sum():.0f} mins  across {(plane['CarrierDelay']>0).sum()} legs")
print(f"    Weather delay     : {plane['WeatherDelay'].sum():.0f} mins  across {(plane['WeatherDelay']>0).sum()} legs")
print(f"    NAS delay         : {plane['NASDelay'].sum():.0f} mins  across {(plane['NASDelay']>0).sum()} legs")
print(f"    Security delay    : {plane['SecurityDelay'].sum():.0f} mins  across {(plane['SecurityDelay']>0).sum()} legs")
print(f"    Late aircraft     : {plane['LateAircraftDelay'].sum():.0f} mins  across {(plane['LateAircraftDelay']>0).sum()} legs")
print()
print("  Top 5 airports by visits:")
visits = pd.concat([plane['Origin'], plane['Dest']]).value_counts().head(5)
for airport, count in visits.items():
    print(f"    {airport}  {count} visits")

print()
print("Script complete.")