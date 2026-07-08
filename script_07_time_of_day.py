# script_07_time_of_day.py
# N923WN — Time of Day Performance Analysis, April 2026

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

plane['dep_hour'] = (plane['CRSDepTime'].astype(str).str.zfill(4)
                     .str[:2].astype(int))
plane['leg_num_of_day'] = plane.groupby('FlightDate').cumcount() + 1


# ── TERMINAL OUTPUT ───────────────────────────────────────────────────────────

print()
print("=" * 70)
print("N923WN — TIME OF DAY PERFORMANCE | APRIL 2026")
print("=" * 70)

hourly = plane.groupby('dep_hour').agg(
    legs         = ('ArrDelay', 'count'),
    avg_delay    = ('ArrDelay', 'mean'),
    max_delay    = ('ArrDelay', 'max'),
    on_time_rate = ('ArrDel15', lambda x: (1 - x.mean()) * 100),
).reset_index()

print(f"\n  {'HOUR':<6} {'LEGS':>5} {'AVG DELAY':>10} {'MAX DELAY':>10} "
      f"{'ON-TIME%':>9}  RATING")
print("  " + "-" * 55)
for _, r in hourly.iterrows():
    if r['on_time_rate'] == 100:  rating = '🟢 Perfect'
    elif r['on_time_rate'] >= 85: rating = '✓ Good'
    elif r['on_time_rate'] >= 70: rating = '🟡 Acceptable'
    else:                          rating = '🔴 Poor'
    print(f"  {int(r['dep_hour']):02d}:xx  "
          f"{int(r['legs']):>5}  "
          f"{r['avg_delay']:>+9.1f}m  "
          f"{r['max_delay']:>+9.0f}m  "
          f"{r['on_time_rate']:>8.1f}%  {rating}")

print()
print("  Key findings:")
best_hour = hourly.loc[hourly['avg_delay'].idxmin()]
worst_hour = hourly.loc[hourly['avg_delay'].idxmax()]
print(f"    Best departure hour  : {int(best_hour['dep_hour']):02d}:xx "
      f"(avg {best_hour['avg_delay']:+.1f}m, "
      f"{best_hour['on_time_rate']:.0f}% on-time)")
print(f"    Worst departure hour : {int(worst_hour['dep_hour']):02d}:xx "
      f"(avg {worst_hour['avg_delay']:+.1f}m, "
      f"{worst_hour['on_time_rate']:.0f}% on-time)")

# Leg position analysis
print(f"\n  Performance by leg position in day:")
leg_pos = plane.groupby('leg_num_of_day').agg(
    count     = ('ArrDelay', 'count'),
    avg_delay = ('ArrDelay', 'mean'),
    on_time   = ('ArrDel15', lambda x: (1-x.mean())*100)
).reset_index()
print(f"  {'LEG #':<7} {'COUNT':>6} {'AVG DELAY':>10} {'ON-TIME%':>9}")
print("  " + "-" * 36)
for _, r in leg_pos.iterrows():
    print(f"  Leg {int(r['leg_num_of_day']):<4} {int(r['count']):>6}  "
          f"{r['avg_delay']:>+9.1f}m  {r['on_time']:>8.1f}%")


# ── CHART ─────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.patch.set_facecolor('#0f1117')
for ax in axes: ax.set_facecolor('#0f1117')
fig.suptitle('N923WN — Time of Day Performance | April 2026',
             color='white', fontsize=14, fontweight='bold', y=1.01)

# ── Left: Avg delay by departure hour ────────────────────────────────────────
ax1 = axes[0]
hours  = hourly['dep_hour'].values
delays = hourly['avg_delay'].values
colors_h = ['#00cc88' if d <= 0 else '#ffcc00' if d <= 15
            else '#ff8800' if d <= 30 else '#ff4444' for d in delays]

bars = ax1.bar([f"{h:02d}:xx" for h in hours], delays,
               color=colors_h, width=0.7, zorder=3)

ax1.axhline(0,  color='white',   linewidth=0.8, linestyle='--', alpha=0.4)
ax1.axhline(15, color='#ff6666', linewidth=0.8, linestyle=':',  alpha=0.6)

# Leg count labels
for bar, count in zip(bars, hourly['legs'].values):
    y = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2,
             y + (1 if y >= 0 else -3),
             f'{count}L', ha='center',
             va='bottom' if y >= 0 else 'top',
             fontsize=7, color='white', alpha=0.7)

ax1.set_title('Avg Arrival Delay by Departure Hour',
              color='white', fontsize=11, pad=10)
ax1.set_xlabel('Scheduled Departure Hour', color='#aaaaaa')
ax1.set_ylabel('Avg Arrival Delay (minutes)', color='#aaaaaa')
ax1.tick_params(colors='#aaaaaa', axis='x', rotation=45, labelsize=8)
ax1.tick_params(colors='#aaaaaa', axis='y')
for spine in ax1.spines.values(): spine.set_edgecolor('#333344')
ax1.yaxis.grid(True, color='#222233', linewidth=0.5)

legend_items = [
    mpatches.Patch(color='#00cc88', label='Avg early'),
    mpatches.Patch(color='#ffcc00', label='0–15m late'),
    mpatches.Patch(color='#ff8800', label='15–30m late'),
    mpatches.Patch(color='#ff4444', label='30m+ late'),
]
ax1.legend(handles=legend_items, facecolor='#1a1a2e',
           edgecolor='#333344', labelcolor='white', fontsize=8)


# ── Right: On-time rate by leg position in day ────────────────────────────────
ax2 = axes[1]
positions = leg_pos['leg_num_of_day'].values
ot_rates  = leg_pos['on_time'].values
avg_dels  = leg_pos['avg_delay'].values

x = range(len(positions))
width = 0.35

bars1 = ax2.bar([i - width/2 for i in x], ot_rates,
                width=width, color='#00cc88', alpha=0.8,
                label='On-time rate (%)', zorder=3)
ax2_twin = ax2.twinx()
ax2_twin.set_facecolor('#0f1117')
bars2 = ax2_twin.bar([i + width/2 for i in x], avg_dels,
                     width=width, color='#ff8800', alpha=0.8,
                     label='Avg delay (mins)', zorder=3)

ax2.axhline(85, color='#00cc88', linewidth=0.8, linestyle=':', alpha=0.5)
ax2_twin.axhline(0, color='white', linewidth=0.8, linestyle='--', alpha=0.3)

ax2.set_xticks(list(x))
ax2.set_xticklabels([f'Leg {int(p)}' for p in positions])
ax2.set_title('Performance by Leg Position in Day',
              color='white', fontsize=11, pad=10)
ax2.set_xlabel('Leg position', color='#aaaaaa')
ax2.set_ylabel('On-time rate (%)', color='#00cc88')
ax2_twin.set_ylabel('Avg arrival delay (mins)', color='#ff8800')
ax2.tick_params(colors='#aaaaaa')
ax2_twin.tick_params(colors='#ff8800')
for spine in ax2.spines.values(): spine.set_edgecolor('#333344')
ax2.yaxis.grid(True, color='#222233', linewidth=0.5)

lines = [mpatches.Patch(color='#00cc88', label='On-time rate (%)'),
         mpatches.Patch(color='#ff8800', label='Avg delay (mins)')]
ax2.legend(handles=lines, facecolor='#1a1a2e',
           edgecolor='#333344', labelcolor='white', fontsize=8)

fig.text(0.99, 0.01,
         'Source: BTS Marketing Carrier On-Time Performance | April 2026',
         ha='right', va='bottom', fontsize=7, color='#555566')

plt.tight_layout()
OUTPUT = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs\N923WN_timeofday_APR2026.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"\nChart saved → {OUTPUT}")
plt.show()
print("\nScript complete.")
