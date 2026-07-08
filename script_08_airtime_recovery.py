# script_08_airtime_recovery.py
# N923WN — Air Time Recovery Analysis, April 2026

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

operated = plane[plane['Cancelled'] == 0].copy()
operated['made_up']    = operated['DepDelay'] - operated['ArrDelay']
operated['recovered']  = operated['made_up'] > 0
late_dep = operated[operated['DepDelay'] > 0].copy()


# ── TERMINAL OUTPUT ───────────────────────────────────────────────────────────

print()
print("=" * 70)
print("N923WN — AIR TIME RECOVERY ANALYSIS | APRIL 2026")
print("=" * 70)

print(f"\n  Total operated legs      : {len(operated)}")
print(f"  Late departures          : {len(late_dep)}")
print(f"  Early departures         : {(operated['DepDelay'] < 0).sum()}")
print(f"  On-time departures       : {(operated['DepDelay'] == 0).sum()}")

print(f"\n  Of {len(late_dep)} late-departing flights:")
print(f"    Made up time in air    : {late_dep['recovered'].sum()} "
      f"({late_dep['recovered'].mean()*100:.0f}%)")
print(f"    Did NOT recover        : {(~late_dep['recovered']).sum()} "
      f"({(~late_dep['recovered']).mean()*100:.0f}%)")
print(f"    Departed late, arrived early: "
      f"{((late_dep['DepDelay'] > 0) & (late_dep['ArrDelay'] < 0)).sum()}")
print(f"\n    Avg time made up       : {late_dep['made_up'].mean():.1f} mins")
print(f"    Max time made up       : {late_dep['made_up'].max():.1f} mins")
print(f"    Max time lost further  : {late_dep['made_up'].min():.1f} mins")

print(f"\n  Best recoveries (departed late, arrived earliest):")
best_rec = late_dep.nlargest(5, 'made_up')[
    ['FlightDate', 'Origin', 'Dest', 'DepDelay', 'ArrDelay', 'made_up',
     'Distance', 'AirTime', 'CRSElapsedTime', 'ActualElapsedTime']]
print(f"  {'DATE':<12} {'ROUTE':<10} {'DEP DLY':>8} {'ARR DLY':>8} "
      f"{'MADE UP':>8} {'DIST':>6} {'AIR':>5}")
for _, r in best_rec.iterrows():
    print(f"  {r['FlightDate']:<12} {r['Origin']}→{r['Dest']:<7} "
          f"{r['DepDelay']:>+7.0f}m {r['ArrDelay']:>+7.0f}m "
          f"{r['made_up']:>+7.0f}m {r['Distance']:>5.0f}mi "
          f"{r['AirTime']:>4.0f}m")

print(f"\n  Worst non-recoveries (delay grew in air):")
worst_rec = late_dep.nsmallest(5, 'made_up')[
    ['FlightDate', 'Origin', 'Dest', 'DepDelay', 'ArrDelay', 'made_up']]
for _, r in worst_rec.iterrows():
    print(f"  {r['FlightDate']:<12} {r['Origin']}→{r['Dest']:<7} "
          f"dep {r['DepDelay']:>+.0f}m → arr {r['ArrDelay']:>+.0f}m "
          f"(lost {abs(r['made_up']):.0f} more mins in air)")

print(f"\n  Sched vs actual air time (all legs):")
print(f"    Avg scheduled elapsed  : {operated['CRSElapsedTime'].mean():.0f} mins")
print(f"    Avg actual elapsed     : {operated['ActualElapsedTime'].mean():.0f} mins")
print(f"    Avg difference         : "
      f"{(operated['ActualElapsedTime'] - operated['CRSElapsedTime']).mean():+.1f} mins")


# ── CHART ─────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor('#0f1117')
for ax in axes: ax.set_facecolor('#0f1117')
fig.suptitle('N923WN — Air Time Recovery Analysis | April 2026',
             color='white', fontsize=14, fontweight='bold', y=1.01)

# ── Left: Dep delay vs Arr delay scatter ─────────────────────────────────────
ax1 = axes[0]
x = operated['DepDelay'].values
y = operated['ArrDelay'].values

colors_s = []
for dep, arr in zip(x, y):
    if dep <= 0:                   colors_s.append('#4488ff')  # early/on-time dep
    elif arr < dep:                colors_s.append('#00cc88')  # recovered
    else:                          colors_s.append('#ff4444')  # got worse

ax1.scatter(x, y, c=colors_s, s=30, alpha=0.7, zorder=3)

# y=x line (no recovery)
lim = max(abs(min(x)), abs(max(x)), abs(min(y)), abs(max(y))) * 1.1
ax1.plot([-lim, lim], [-lim, lim], color='white', linewidth=1,
         linestyle='--', alpha=0.4, label='No recovery (dep=arr delay)')
ax1.axhline(0,  color='#888888', linewidth=0.5, linestyle=':')
ax1.axvline(0,  color='#888888', linewidth=0.5, linestyle=':')
ax1.axhline(15, color='#ff6666', linewidth=0.8, linestyle=':', alpha=0.6)

ax1.fill_between([-lim, lim], [-lim, -lim], [x for x in [-lim, lim]],
                 alpha=0.05, color='#00cc88')
ax1.text(-20, lim*0.85, '← Recovery zone\n(arrived less late)',
         color='#00cc88', fontsize=7, alpha=0.7)

ax1.set_xlim(-lim, lim)
ax1.set_ylim(-lim, lim)
ax1.set_title('Departure Delay vs Arrival Delay',
              color='white', fontsize=11, pad=10)
ax1.set_xlabel('Departure Delay (minutes)', color='#aaaaaa')
ax1.set_ylabel('Arrival Delay (minutes)', color='#aaaaaa')
ax1.tick_params(colors='#aaaaaa')
for spine in ax1.spines.values(): spine.set_edgecolor('#333344')
ax1.yaxis.grid(True, color='#222233', linewidth=0.5)
ax1.xaxis.grid(True, color='#222233', linewidth=0.5)

legend_items = [
    mpatches.Patch(color='#4488ff', label='Early/on-time departure'),
    mpatches.Patch(color='#00cc88', label='Late dep → recovered in air'),
    mpatches.Patch(color='#ff4444', label='Late dep → got worse'),
]
ax1.legend(handles=legend_items, facecolor='#1a1a2e',
           edgecolor='#333344', labelcolor='white', fontsize=8)

# ── Right: Time made up distribution ─────────────────────────────────────────
ax2 = axes[1]
made_up_vals = late_dep['made_up'].values
colors_b = ['#00cc88' if v > 0 else '#ff4444' for v in made_up_vals]

bins = range(int(min(made_up_vals))-5, int(max(made_up_vals))+10, 5)
n, bin_edges, patches = ax2.hist(made_up_vals, bins=bins,
                                  edgecolor='#0f1117', linewidth=0.5)
for patch, left in zip(patches, bin_edges):
    patch.set_facecolor('#00cc88' if left >= 0 else '#ff4444')

ax2.axvline(0, color='white', linewidth=1.5, linestyle='--', alpha=0.6)
ax2.axvline(late_dep['made_up'].mean(), color='#ff8800', linewidth=1.5,
            label=f"Mean: {late_dep['made_up'].mean():+.1f}m")

ax2.text(late_dep['made_up'].mean() + 1, n.max()*0.9,
         f"Mean\n{late_dep['made_up'].mean():+.1f}m",
         color='#ff8800', fontsize=8)

ax2.set_title('Time Made Up in Air\n(late departures only)',
              color='white', fontsize=11, pad=10)
ax2.set_xlabel('Minutes recovered (positive = arrived less late than departed)',
               color='#aaaaaa')
ax2.set_ylabel('Number of flights', color='#aaaaaa')
ax2.tick_params(colors='#aaaaaa')
for spine in ax2.spines.values(): spine.set_edgecolor('#333344')
ax2.yaxis.grid(True, color='#222233', linewidth=0.5)

legend_items2 = [
    mpatches.Patch(color='#00cc88', label='Made up time (recovered)'),
    mpatches.Patch(color='#ff4444', label='Lost more time (got worse)'),
]
ax2.legend(handles=legend_items2, facecolor='#1a1a2e',
           edgecolor='#333344', labelcolor='white', fontsize=8)

fig.text(0.99, 0.01,
         'Source: BTS Marketing Carrier On-Time Performance | April 2026',
         ha='right', va='bottom', fontsize=7, color='#555566')

plt.tight_layout()
OUTPUT = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs\N923WN_recovery_APR2026.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\nChart saved → {OUTPUT}")
plt.show()
print("\nScript complete.")
