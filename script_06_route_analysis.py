# script_06_route_analysis.py
# N923WN — Route Analysis, April 2026

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

plane['route'] = plane['Origin'] + '→' + plane['Dest']


# ── TERMINAL OUTPUT ───────────────────────────────────────────────────────────

print()
print("=" * 70)
print("N923WN — ROUTE ANALYSIS | APRIL 2026")
print("=" * 70)

route_summary = plane.groupby('route').agg(
    legs       = ('ArrDelay', 'count'),
    avg_delay  = ('ArrDelay', 'mean'),
    max_delay  = ('ArrDelay', 'max'),
    on_time    = ('ArrDel15', lambda x: (1 - x.mean()) * 100),
    avg_dist   = ('Distance', 'mean'),
    avg_air    = ('AirTime',  'mean'),
).sort_values('legs', ascending=False)

print(f"\n  Unique routes flown   : {len(route_summary)}")
print(f"  Total route-legs      : {len(plane)}")
print(f"\n  Routes flown more than once:")
print(f"  {'ROUTE':<12} {'LEGS':>5} {'AVG DELAY':>10} {'MAX DELAY':>10} "
      f"{'ON-TIME%':>9} {'AVG DIST':>9} {'AVG AIR':>8}")
print("  " + "-" * 65)
for route, r in route_summary[route_summary['legs'] > 1].iterrows():
    print(f"  {route:<12} {int(r['legs']):>5} "
          f"{r['avg_delay']:>+9.1f}m "
          f"{r['max_delay']:>+9.0f}m "
          f"{r['on_time']:>8.1f}% "
          f"{r['avg_dist']:>8.0f}mi "
          f"{r['avg_air']:>7.0f}m")

print(f"\n  Top 10 airports by visits:")
visits = pd.concat([plane['Origin'], plane['Dest']]).value_counts().head(10)
for airport, count in visits.items():
    bar = '█' * count
    print(f"    {airport}  {count:>3}  {bar}")

print(f"\n  Worst routes (avg delay > 15 mins):")
worst = route_summary[route_summary['avg_delay'] > 15].sort_values('avg_delay', ascending=False)
if len(worst) == 0:
    print("    None — all routes avg ≤15 mins")
else:
    for route, r in worst.iterrows():
        print(f"    {route:<12} avg {r['avg_delay']:+.0f}m  ({int(r['legs'])} legs)")


# ── CHART ─────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor('#0f1117')
for ax in axes: ax.set_facecolor('#0f1117')
fig.suptitle('N923WN — Route Analysis | April 2026',
             color='white', fontsize=14, fontweight='bold', y=1.01)

# ── Left: Top 15 airports by visits ──────────────────────────────────────────
ax1 = axes[0]
top15 = pd.concat([plane['Origin'], plane['Dest']]).value_counts().head(15)
colors_ap = ['#ff4444' if c >= 20 else '#ff8800' if c >= 15
             else '#ffcc00' if c >= 10 else '#00cc88' for c in top15.values]
ax1.barh(top15.index[::-1], top15.values[::-1], color=colors_ap[::-1], zorder=3)
for i, (airport, count) in enumerate(zip(top15.index[::-1], top15.values[::-1])):
    ax1.text(count + 0.3, i, str(count), va='center', color='white', fontsize=8)
ax1.set_title('Top 15 Airports by Visits', color='white', fontsize=11, pad=10)
ax1.set_xlabel('Number of visits (departures + arrivals)', color='#aaaaaa')
ax1.tick_params(colors='#aaaaaa')
for spine in ax1.spines.values(): spine.set_edgecolor('#333344')
ax1.xaxis.grid(True, color='#222233', linewidth=0.5)

# ── Right: Distance vs Avg Delay scatter ─────────────────────────────────────
ax2 = axes[1]
multi = route_summary[route_summary['legs'] > 1]
sc_c = ['#ff4444' if d > 15 else '#ffcc00' if d > 0 else '#00cc88'
        for d in multi['avg_delay']]
sc = ax2.scatter(multi['avg_dist'], multi['avg_delay'],
                 c=sc_c, s=multi['legs']*30, alpha=0.8, zorder=3)
ax2.axhline(0,  color='white',   linewidth=0.8, linestyle='--', alpha=0.4)
ax2.axhline(15, color='#ff6666', linewidth=0.8, linestyle=':',  alpha=0.6)

for route, r in multi.iterrows():
    if abs(r['avg_delay']) > 20 or r['legs'] > 3:
        ax2.annotate(route, xy=(r['avg_dist'], r['avg_delay']),
                     xytext=(r['avg_dist']+20, r['avg_delay']+3),
                     fontsize=7, color='white')

ax2.set_title('Route Distance vs Avg Arrival Delay\n(size = number of legs)',
              color='white', fontsize=11, pad=10)
ax2.set_xlabel('Average Distance (miles)', color='#aaaaaa')
ax2.set_ylabel('Avg Arrival Delay (minutes)', color='#aaaaaa')
ax2.tick_params(colors='#aaaaaa')
for spine in ax2.spines.values(): spine.set_edgecolor('#333344')
ax2.yaxis.grid(True, color='#222233', linewidth=0.5)
ax2.xaxis.grid(True, color='#222233', linewidth=0.5)

legend_items = [
    mpatches.Patch(color='#ff4444', label='Avg delay > 15m'),
    mpatches.Patch(color='#ffcc00', label='Avg delay 0–15m'),
    mpatches.Patch(color='#00cc88', label='Avg early'),
]
ax2.legend(handles=legend_items, facecolor='#1a1a2e',
           edgecolor='#333344', labelcolor='white', fontsize=8)

fig.text(0.99, 0.01,
         'Source: BTS Marketing Carrier On-Time Performance | April 2026',
         ha='right', va='bottom', fontsize=7, color='#555566')

plt.tight_layout()
OUTPUT = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs\N923WN_routes_APR2026.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\nChart saved → {OUTPUT}")
plt.show()
print("\nScript complete.")
