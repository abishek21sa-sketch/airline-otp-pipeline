# script_04_turnaround_analysis.py
# N923WN — Turnaround Time Analysis, April 2026

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

DATA_PATH = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\OTP_APR2026.csv"

print("Loading data...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip()
wn    = df[df['Operating_Airline'] == 'WN'].copy()
plane = wn[wn['Tail_Number'] == 'N923WN'].sort_values(
    ['FlightDate', 'CRSDepTime']
).reset_index(drop=True)


# ── TURNAROUND CALC ───────────────────────────────────────────────────────────

plane['prev_arr']  = plane['ArrTime'].shift(1)
plane['prev_date'] = plane['FlightDate'].shift(1)
same_day = plane['FlightDate'] == plane['prev_date']
plane['turnaround'] = None
plane.loc[same_day, 'turnaround'] = (
    plane.loc[same_day, 'CRSDepTime'] - plane.loc[same_day, 'prev_arr']
)

ta       = plane[same_day].copy()
ta_valid = ta[ta['turnaround'] >= 0].copy()
ta_neg   = ta[ta['turnaround'] <  0].copy()


# ── TERMINAL OUTPUT ───────────────────────────────────────────────────────────

print()
print("=" * 70)
print("N923WN — TURNAROUND TIME ANALYSIS | APRIL 2026")
print("=" * 70)

print(f"\n  Total same-day turnarounds : {len(ta)}")
print(f"  Valid (≥0 mins)            : {len(ta_valid)}")
print(f"  Negative (chasing sched)   : {len(ta_neg)}")
print(f"\n  Min turnaround  : {ta_valid['turnaround'].min():.0f} mins")
print(f"  Max turnaround  : {ta_valid['turnaround'].max():.0f} mins")
print(f"  Mean turnaround : {ta_valid['turnaround'].mean():.0f} mins")
print(f"  Median          : {ta_valid['turnaround'].median():.0f} mins")

print(f"\n  Breakdown by category:")
tight  = (ta_valid['turnaround'] < 25).sum()
normal = ((ta_valid['turnaround'] >= 25) & (ta_valid['turnaround'] < 45)).sum()
buffer = ((ta_valid['turnaround'] >= 45) & (ta_valid['turnaround'] < 90)).sum()
long_  = (ta_valid['turnaround'] >= 90).sum()
print(f"    Under 25 mins (tight / risky) : {tight}")
print(f"    25–45 mins  (Southwest target) : {normal}")
print(f"    45–90 mins  (comfortable buffer): {buffer}")
print(f"    90+ mins    (long gap / downtime): {long_}")

print(f"\n  Tight turnarounds (< 30 mins):")
print(f"  {'DATE':<12} {'ROUTE':<10} {'TRNRD':>6} {'DEP DLY':>8} {'ARR DLY':>8}  NOTE")
for _, r in ta_valid[ta_valid['turnaround'] < 30].iterrows():
    note = '⚠ risky' if r['turnaround'] < 15 else ''
    print(f"  {r['FlightDate']:<12} {r['Origin']}→{r['Dest']:<7} "
          f"{int(r['turnaround']):>5}m "
          f"{r['DepDelay']:>+7.0f}m "
          f"{r['ArrDelay']:>+7.0f}m  {note}")

print(f"\n  Negative turnarounds (plane chasing its own schedule):")
print(f"  {'DATE':<12} {'ROUTE':<10} {'TRNRD':>7} {'DEP DLY':>8} {'ARR DLY':>8}")
for _, r in ta_neg.iterrows():
    print(f"  {r['FlightDate']:<12} {r['Origin']}→{r['Dest']:<7} "
          f"{int(r['turnaround']):>6}m "
          f"{r['DepDelay']:>+7.0f}m "
          f"{r['ArrDelay']:>+7.0f}m")


# ── CHART ─────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor('#0f1117')
for ax in axes: ax.set_facecolor('#0f1117')

fig.suptitle('N923WN — Turnaround Time Analysis | April 2026',
             color='white', fontsize=14, fontweight='bold', y=1.01)

# ── Left: Histogram ───────────────────────────────────────────────────────────
ax1 = axes[0]
vals = ta_valid['turnaround'].values

colors_hist = []
for v in sorted(vals):
    if v < 25:   colors_hist.append('#ff4444')
    elif v < 45: colors_hist.append('#00cc88')
    elif v < 90: colors_hist.append('#ffcc00')
    else:        colors_hist.append('#4488ff')

bins = range(0, int(max(vals)) + 20, 15)
n, bin_edges, patches = ax1.hist(vals, bins=bins, edgecolor='#0f1117', linewidth=0.5)
for patch, left in zip(patches, bin_edges):
    if left < 25:   patch.set_facecolor('#ff4444')
    elif left < 45: patch.set_facecolor('#00cc88')
    elif left < 90: patch.set_facecolor('#ffcc00')
    else:           patch.set_facecolor('#4488ff')

ax1.axvline(25,  color='white',   linewidth=1, linestyle='--', alpha=0.5)
ax1.axvline(45,  color='white',   linewidth=1, linestyle='--', alpha=0.5)
ax1.axvline(90,  color='white',   linewidth=1, linestyle='--', alpha=0.5)
ax1.axvline(ta_valid['turnaround'].mean(), color='#ff8800', linewidth=1.5,
            linestyle='-', label=f"Mean: {ta_valid['turnaround'].mean():.0f}m")

ax1.text(12,  n.max()*0.92, 'Tight\n<25m',   color='#ff4444', fontsize=8, ha='center')
ax1.text(35,  n.max()*0.92, 'Target\n25–45m', color='#00cc88', fontsize=8, ha='center')
ax1.text(67,  n.max()*0.92, 'Buffer\n45–90m', color='#ffcc00', fontsize=8, ha='center')
ax1.text(150, n.max()*0.92, 'Long\n90m+',     color='#4488ff', fontsize=8, ha='center')

ax1.set_title('Turnaround Time Distribution', color='white', fontsize=11, pad=10)
ax1.set_xlabel('Turnaround (minutes)', color='#aaaaaa')
ax1.set_ylabel('Number of turnarounds', color='#aaaaaa')
ax1.tick_params(colors='#aaaaaa')
for spine in ax1.spines.values(): spine.set_edgecolor('#333344')
ax1.yaxis.grid(True, color='#222233', linewidth=0.5)
ax1.legend(facecolor='#1a1a2e', edgecolor='#333344', labelcolor='white', fontsize=8)


# ── Right: Turnaround vs Next Leg Arrival Delay scatter ──────────────────────
ax2 = axes[1]

x = ta_valid['turnaround'].astype(float).values
y = ta_valid['ArrDelay'].astype(float).values

sc_colors = ['#ff4444' if v < 25 else '#00cc88' if v < 45
             else '#ffcc00' if v < 90 else '#4488ff' for v in x]

ax2.scatter(x, y, c=sc_colors, s=50, alpha=0.8, zorder=3)
ax2.axhline(0,  color='white',   linewidth=0.8, linestyle='--', alpha=0.4)
ax2.axhline(15, color='#ff6666', linewidth=0.8, linestyle=':',  alpha=0.6)
ax2.axvline(25, color='white',   linewidth=0.8, linestyle='--', alpha=0.3)

# Trend line
z = np.polyfit(x, y, 1)
p = np.poly1d(z)
xline = np.linspace(min(x), max(x), 100)
ax2.plot(xline, p(xline), color='#ff8800', linewidth=1.5,
         linestyle='-', label=f'Trend (r={np.corrcoef(x,y)[0,1]:.2f})')

# Annotate notable tight turnarounds
for _, r in ta_valid[ta_valid['turnaround'] < 16].iterrows():
    ax2.annotate(
        f"{r['Origin']}→{r['Dest']}\n{int(r['turnaround'])}m turn",
        xy=(r['turnaround'], r['ArrDelay']),
        xytext=(r['turnaround'] + 15, r['ArrDelay'] + 8),
        fontsize=7, color='white',
        arrowprops=dict(arrowstyle='->', color='white', lw=0.7),
        bbox=dict(boxstyle='round,pad=0.2', facecolor='#222233',
                  edgecolor='#555566', alpha=0.9)
    )

ax2.set_title('Turnaround Time vs Next Leg Arrival Delay',
              color='white', fontsize=11, pad=10)
ax2.set_xlabel('Turnaround Time (minutes)', color='#aaaaaa')
ax2.set_ylabel('Arrival Delay of Next Leg (minutes)', color='#aaaaaa')
ax2.tick_params(colors='#aaaaaa')
for spine in ax2.spines.values(): spine.set_edgecolor('#333344')
ax2.yaxis.grid(True, color='#222233', linewidth=0.5)
ax2.xaxis.grid(True, color='#222233', linewidth=0.5)
ax2.legend(facecolor='#1a1a2e', edgecolor='#333344', labelcolor='white', fontsize=8)

ax2.text(200, ax2.get_ylim()[1]*0.9, 'On-time threshold',
         color='#ff6666', fontsize=7, ha='right')

legend_items = [
    mpatches.Patch(color='#ff4444', label='< 25m (tight)'),
    mpatches.Patch(color='#00cc88', label='25–45m (target)'),
    mpatches.Patch(color='#ffcc00', label='45–90m (buffer)'),
    mpatches.Patch(color='#4488ff', label='90m+ (long)'),
]
ax2.legend(handles=legend_items, loc='upper right',
           facecolor='#1a1a2e', edgecolor='#333344',
           labelcolor='white', fontsize=8)

fig.text(0.99, 0.01,
         'Source: BTS Marketing Carrier On-Time Performance | April 2026',
         ha='right', va='bottom', fontsize=7, color='#555566')

plt.tight_layout()
OUTPUT = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs\N923WN_turnaround_APR2026.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\nChart saved → {OUTPUT}")
plt.show()
print("\nScript complete.")