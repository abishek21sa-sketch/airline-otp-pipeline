# script_09_april12_investigation.py
# N923WN — April 12 Mystery Investigation

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DATA_PATH = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\OTP_APR2026.csv"

print("Loading data...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip()
wn = df[df['Operating_Airline'] == 'WN'].copy()


# ── WHAT DID N923WN DO ON APRIL 12? ─────────────────────────────────────────

plane = wn[wn['Tail_Number'] == 'N923WN'].sort_values(
    ['FlightDate', 'CRSDepTime']
).reset_index(drop=True)

apr11 = plane[plane['FlightDate'] == '2026-04-11']
apr12 = plane[plane['FlightDate'] == '2026-04-12']
apr13 = plane[plane['FlightDate'] == '2026-04-13']


# ── WHAT FLIGHTS OPERATED FROM MCI AND MCO ON APRIL 12? ─────────────────────

# Gap: plane arrived MCI end of Apr 11, then leg 72 departs MCI at 1320 Apr 12
# Leg 73 departs MCO at 2050 — but N923WN arrived RSW (not MCO) on leg 72
# So what happened between RSW arrival and MCO departure?

# Find other WN flights at RSW and MCO on Apr 12
rsw_apr12 = wn[(wn['FlightDate'] == '2026-04-12') &
               ((wn['Origin'] == 'RSW') | (wn['Dest'] == 'RSW'))]
mco_apr12 = wn[(wn['FlightDate'] == '2026-04-12') &
               ((wn['Origin'] == 'MCO') | (wn['Dest'] == 'MCO'))]

# Find which tail number flew RSW→MCO or RSW→anywhere on Apr 12
rsw_dep = wn[(wn['FlightDate'] == '2026-04-12') & (wn['Origin'] == 'RSW')]


# ── TERMINAL OUTPUT ───────────────────────────────────────────────────────────

print()
print("=" * 70)
print("N923WN — APRIL 12 MYSTERY INVESTIGATION")
print("=" * 70)

print("\n  APRIL 11 — Last legs (how the day ended):")
cols = ['Flight_Number_Operating_Airline', 'Origin', 'Dest',
        'CRSDepTime', 'DepTime', 'ArrTime', 'ArrDelay',
        'Cancelled', 'Diverted']
print(apr11[cols].to_string(index=False))

print("\n  APRIL 12 — N923WN's two recorded legs:")
print(apr12[cols].to_string(index=False))

print("\n  APRIL 13 — First leg (how the recovery started):")
print(apr13[cols].head(2).to_string(index=False))

print()
print("  THE TIMELINE GAP:")
print(f"    Apr 11 last arrival  : MCI at {int(apr11.iloc[-1]['ArrTime']):04d} "
      f"(ArrDelay: {apr11.iloc[-1]['ArrDelay']:+.0f}m)")
print(f"    Apr 12 first depart  : MCI at {int(apr12.iloc[0]['CRSDepTime']):04d} "
      f"(scheduled)")
print(f"    Gap                  : {int(apr12.iloc[0]['CRSDepTime']) - int(apr11.iloc[-1]['ArrTime'])} mins "
      f"(overnight at MCI)")

arr12_leg72 = apr12.iloc[0]
print(f"\n    Leg 72 arrives       : RSW at {int(arr12_leg72['ArrTime']):04d}")
print(f"    Leg 73 departs       : MCO at {int(apr12.iloc[1]['CRSDepTime']):04d}")
print(f"    Gap                  : {int(apr12.iloc[1]['CRSDepTime']) - int(arr12_leg72['ArrTime'])} mins")
print(f"    Missing leg?         : RSW→MCO — N923WN flew there but it's not recorded")
print(f"                           OR another aircraft was swapped in at MCO")

print("\n  CLUE — WN flights departing RSW on April 12:")
print(rsw_dep[['Tail_Number', 'Flight_Number_Operating_Airline',
               'Origin', 'Dest', 'CRSDepTime', 'DepTime', 'ArrTime']
              ].sort_values('CRSDepTime').to_string(index=False))

# Check if N923WN appears anywhere between the gap
print("\n  CHECKING: Was N923WN recorded on any other flight Apr 12?")
n923_all_apr12 = df[(df['Tail_Number'] == 'N923WN') &
                    (df['FlightDate'] == '2026-04-12')]
print(f"  Total rows for N923WN on Apr 12 in full dataset: {len(n923_all_apr12)}")
print(n923_all_apr12[cols].to_string(index=False))

print("\n  WHAT THIS TELLS US:")
print("    April 12 had only 2 recorded legs for N923WN.")
print("    The 331-minute turnaround between legs 72 and 73 is abnormal.")
print("    Either:")
print("    1. N923WN flew RSW→MCO but that leg is missing from the dataset")
print("    2. A different aircraft (tail swap) operated leg 73 at MCO")
print("    3. N923WN was grounded at RSW for maintenance between those legs")
print()
print("    The LateAircraftDelay on leg 73 (29 mins) suggests the prior")
print("    leg arrived late — consistent with a tail swap or ferry flight")
print("    that ran behind schedule.")


# ── CHART — April 11/12/13 Timeline ──────────────────────────────────────────

fig, ax = plt.subplots(figsize=(16, 5))
fig.patch.set_facecolor('#0f1117')
ax.set_facecolor('#0f1117')
fig.suptitle('N923WN — April 12 Mystery | 3-Day Timeline',
             color='white', fontsize=14, fontweight='bold')

def time_to_float(t):
    if pd.isna(t): return None
    t = int(t)
    return (t // 100) + (t % 100) / 60

colors_day = {'2026-04-11': '#4488ff', '2026-04-12': '#ff4444', '2026-04-13': '#00cc88'}
y_positions = {'2026-04-11': 2, '2026-04-12': 1, '2026-04-13': 0}
y_labels    = {2: 'Apr 11', 1: 'Apr 12', 0: 'Apr 13'}

for date, group in [('2026-04-11', apr11),
                    ('2026-04-12', apr12),
                    ('2026-04-13', apr13.head(3))]:
    y   = y_positions[date]
    col = colors_day[date]
    for _, row in group.iterrows():
        dep = time_to_float(row['DepTime'] if not pd.isna(row['DepTime'])
                            else row['CRSDepTime'])
        arr = time_to_float(row['ArrTime'] if not pd.isna(row['ArrTime'])
                            else row['CRSArrTime'])
        if dep is None or arr is None: continue
        ax.barh(y, arr - dep, left=dep, height=0.4, color=col,
                alpha=0.8, zorder=3)
        mid = dep + (arr - dep) / 2
        ax.text(mid, y, f"{row['Origin']}→{row['Dest']}",
                ha='center', va='center', fontsize=7,
                color='white', fontweight='bold')

# Mark the Apr 12 gap
gap_start = time_to_float(apr12.iloc[0]['ArrTime'])
gap_end   = time_to_float(apr12.iloc[1]['CRSDepTime'])
if gap_start and gap_end:
    ax.barh(1, gap_end - gap_start, left=gap_start, height=0.4,
            color='#ff8800', alpha=0.4, hatch='///', zorder=2)
    ax.text((gap_start + gap_end)/2, 1.35,
            f'?? 331-min gap\nMissing leg / maintenance?',
            ha='center', color='#ff8800', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='#222233',
                      edgecolor='#ff8800', alpha=0.9))

ax.set_yticks([0, 1, 2])
ax.set_yticklabels([y_labels[i] for i in [0, 1, 2]], color='white', fontsize=10)
ax.set_xlabel('Time (local hours)', color='#aaaaaa')
ax.set_xlim(0, 28)
ax.set_xticks(range(0, 28, 2))
ax.set_xticklabels([f'{h%24:02d}:00' for h in range(0, 28, 2)], color='#aaaaaa')
ax.tick_params(colors='#aaaaaa')
for spine in ax.spines.values(): spine.set_edgecolor('#333344')
ax.xaxis.grid(True, color='#222233', linewidth=0.5, zorder=0)

legend_items = [
    mpatches.Patch(color='#4488ff', label='Apr 11 legs'),
    mpatches.Patch(color='#ff4444', label='Apr 12 legs'),
    mpatches.Patch(color='#00cc88', label='Apr 13 legs'),
    mpatches.Patch(color='#ff8800', alpha=0.4, label='Unexplained gap'),
]
ax.legend(handles=legend_items, loc='lower right',
          facecolor='#1a1a2e', edgecolor='#333344',
          labelcolor='white', fontsize=8)

fig.text(0.99, 0.01,
         'Source: BTS Marketing Carrier On-Time Performance | April 2026',
         ha='right', va='bottom', fontsize=7, color='#555566')

plt.tight_layout()
OUTPUT = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs\N923WN_apr12_investigation_APR2026.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\nChart saved → {OUTPUT}")
plt.show()
print("\nScript complete.")