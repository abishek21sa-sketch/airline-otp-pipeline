# script_05_cascade_analysis.py
# N923WN — Cascade Chain Analysis, April 2026

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DATA_PATH = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\OTP_APR2026.csv"

print("Loading data...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip()
wn    = df[df['Operating_Airline'] == 'WN'].copy()
plane = wn[wn['Tail_Number'] == 'N923WN'].sort_values(
    ['FlightDate', 'CRSDepTime']
).reset_index(drop=True)

plane['cascade'] = plane['LateAircraftDelay'].fillna(0) > 0


# ── BUILD CASCADE CHAINS ──────────────────────────────────────────────────────

chains = []
for date, group in plane.groupby('FlightDate'):
    group = group.reset_index(drop=True)
    in_chain   = False
    chain_legs = []

    for i, row in group.iterrows():
        if row['cascade']:
            chain_legs.append(row)
            in_chain = True
        else:
            if in_chain and len(chain_legs) > 0:
                # Find trigger leg (the non-cascade leg just before chain started)
                trigger_idx = group.index[group.index < chain_legs[0].name].max() \
                    if any(group.index < chain_legs[0].name) else None
                trigger = group.loc[trigger_idx] if trigger_idx is not None else None
                chains.append({
                    'date'       : date,
                    'trigger'    : trigger,
                    'legs'       : chain_legs.copy(),
                    'chain_len'  : len(chain_legs),
                    'total_lateAC': sum(l['LateAircraftDelay'] for l in chain_legs),
                    'max_delay'  : max(l['ArrDelay'] for l in chain_legs
                                      if not pd.isna(l['ArrDelay'])),
                })
                chain_legs = []
                in_chain   = False

    if in_chain and chain_legs:
        trigger_idx = group.index[group.index < chain_legs[0].name].max() \
            if any(group.index < chain_legs[0].name) else None
        trigger = group.loc[trigger_idx] if trigger_idx is not None else None
        chains.append({
            'date'       : date,
            'trigger'    : trigger,
            'legs'       : chain_legs,
            'chain_len'  : len(chain_legs),
            'total_lateAC': sum(l['LateAircraftDelay'] for l in chain_legs),
            'max_delay'  : max(l['ArrDelay'] for l in chain_legs
                               if not pd.isna(l['ArrDelay'])),
        })


# ── TERMINAL OUTPUT ───────────────────────────────────────────────────────────

print()
print("=" * 70)
print("N923WN — CASCADE CHAIN ANALYSIS | APRIL 2026")
print("=" * 70)
print(f"\n  Total cascade chains identified : {len(chains)}")
print(f"  Total cascade legs             : {plane['cascade'].sum()}")
print(f"  Total LateAC delay minutes     : {plane['LateAircraftDelay'].sum():.0f} mins")
print(f"  Days with cascade              : {plane[plane['cascade']]['FlightDate'].nunique()}")
print()

for i, chain in enumerate(chains, 1):
    t = chain['trigger']
    print(f"  CHAIN {i} — {chain['date']}  "
          f"({chain['chain_len']} cascade legs, "
          f"{chain['total_lateAC']:.0f} LateAC mins, "
          f"max delay {chain['max_delay']:+.0f}m)")

    if t is not None:
        print(f"    TRIGGER → FL{int(t['Flight_Number_Operating_Airline'])} "
              f"{t['Origin']}→{t['Dest']}  "
              f"ArrDelay: {t['ArrDelay']:+.0f}m  "
              f"Cause: {t['CarrierDelay'] if not pd.isna(t['CarrierDelay']) else 0:.0f}m Carrier / "
              f"{t['NASDelay'] if not pd.isna(t['NASDelay']) else 0:.0f}m NAS")

    for leg in chain['legs']:
        lad = leg['LateAircraftDelay'] if not pd.isna(leg['LateAircraftDelay']) else 0
        arr = leg['ArrDelay'] if not pd.isna(leg['ArrDelay']) else float('nan')
        print(f"    ↩ CASCADE FL{int(leg['Flight_Number_Operating_Airline'])} "
              f"{leg['Origin']}→{leg['Dest']}  "
              f"ArrDelay: {arr:+.0f}m  LateAC: {lad:.0f}m")
    print()


# ── CHART ─────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor('#0f1117')
for ax in axes: ax.set_facecolor('#0f1117')
fig.suptitle('N923WN — Cascade Chain Analysis | April 2026',
             color='white', fontsize=14, fontweight='bold', y=1.01)

# ── Left: Chain length vs total LateAC delay ─────────────────────────────────
ax1 = axes[0]
chain_dates   = [c['date'].replace('2026-04-', 'Apr ') for c in chains]
chain_lateAC  = [c['total_lateAC'] for c in chains]
chain_lengths = [c['chain_len'] for c in chains]

colors_bar = ['#ff4444' if l >= 3 else '#ff8800' if l == 2 else '#ffcc00'
              for l in chain_lengths]
bars = ax1.bar(chain_dates, chain_lateAC, color=colors_bar, width=0.6, zorder=3)

for bar, length, lateAC in zip(bars, chain_lengths, chain_lateAC):
    ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 3,
             f'{length}L\n{lateAC:.0f}m',
             ha='center', va='bottom', fontsize=8, color='white')

ax1.set_title('LateAC Delay per Cascade Chain', color='white', fontsize=11, pad=10)
ax1.set_xlabel('Date', color='#aaaaaa')
ax1.set_ylabel('Total Late Aircraft Delay (minutes)', color='#aaaaaa')
ax1.tick_params(colors='#aaaaaa', axis='x', rotation=45)
ax1.tick_params(colors='#aaaaaa', axis='y')
for spine in ax1.spines.values(): spine.set_edgecolor('#333344')
ax1.yaxis.grid(True, color='#222233', linewidth=0.5)

legend_items = [
    mpatches.Patch(color='#ff4444', label='3+ leg chain'),
    mpatches.Patch(color='#ff8800', label='2 leg chain'),
    mpatches.Patch(color='#ffcc00', label='1 leg chain'),
]
ax1.legend(handles=legend_items, facecolor='#1a1a2e',
           edgecolor='#333344', labelcolor='white', fontsize=8)


# ── Right: All legs coloured by role ─────────────────────────────────────────
ax2 = axes[1]

# Identify trigger legs
trigger_indices = set()
cascade_indices = set()
for chain in chains:
    if chain['trigger'] is not None:
        trigger_indices.add(chain['trigger'].name)
    for leg in chain['legs']:
        cascade_indices.add(leg.name)

delays = []
colors_legs = []
labels_legs = []
for idx, row in plane.iterrows():
    d = row['ArrDelay'] if not pd.isna(row['ArrDelay']) else 0
    delays.append(d)
    if idx in trigger_indices:
        colors_legs.append('#ff4444')
        labels_legs.append('Trigger')
    elif idx in cascade_indices:
        colors_legs.append('#ff8800')
        labels_legs.append('Cascade')
    else:
        colors_legs.append('#00cc88')
        labels_legs.append('Normal')

ax2.bar(range(len(plane)), delays, color=colors_legs, width=0.7, zorder=3)
ax2.axhline(0,  color='white',   linewidth=0.8, linestyle='--', alpha=0.4)
ax2.axhline(15, color='#ff6666', linewidth=0.8, linestyle=':',  alpha=0.6)

ax2.set_title('All 175 Legs — Trigger, Cascade & Normal',
              color='white', fontsize=11, pad=10)
ax2.set_xlabel('Leg number (chronological)', color='#aaaaaa')
ax2.set_ylabel('Arrival Delay (minutes)', color='#aaaaaa')
ax2.tick_params(colors='#aaaaaa')
for spine in ax2.spines.values(): spine.set_edgecolor('#333344')
ax2.yaxis.grid(True, color='#222233', linewidth=0.5)

legend_items2 = [
    mpatches.Patch(color='#ff4444', label='Trigger leg'),
    mpatches.Patch(color='#ff8800', label='Cascade leg'),
    mpatches.Patch(color='#00cc88', label='Normal leg'),
]
ax2.legend(handles=legend_items2, facecolor='#1a1a2e',
           edgecolor='#333344', labelcolor='white', fontsize=8)

fig.text(0.99, 0.01,
         'Source: BTS Marketing Carrier On-Time Performance | April 2026',
         ha='right', va='bottom', fontsize=7, color='#555566')

plt.tight_layout()
OUTPUT = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs\N923WN_cascade_APR2026.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"Chart saved → {OUTPUT}")
plt.show()
print("\nScript complete.")
