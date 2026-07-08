# script_02_visualise_rotation.py
# N923WN — Daily Delay Visualisation, April 2026

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── 1. LOAD & FILTER ─────────────────────────────────────────────────────────

DATA_PATH = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\OTP_APR2026.csv"

print("Loading data...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df.columns = df.columns.str.strip()

wn    = df[df['Operating_Airline'] == 'WN'].copy()
plane = wn[wn['Tail_Number'] == 'N923WN'].sort_values(['FlightDate', 'CRSDepTime']).reset_index(drop=True)
print(f"N923WN: {len(plane)} legs loaded\n")


# ── 2. DAILY SUMMARY ─────────────────────────────────────────────────────────

daily = plane.groupby('FlightDate').agg(
    legs         = ('FlightDate', 'count'),
    avg_delay    = ('ArrDelay',   'mean'),
    max_delay    = ('ArrDelay',   'max'),
    late_legs    = ('ArrDel15',   'sum'),
    diversions   = ('Diverted',   'sum'),
    start        = ('Origin',     'first'),
    end          = ('Dest',       'last')
).reset_index()

dates      = pd.to_datetime(daily['FlightDate'])
avg_delays = daily['avg_delay'].values
days       = [d.strftime('%b %d') for d in dates]


# ── 3. CHART — DAILY AVG ARRIVAL DELAY ───────────────────────────────────────

fig, ax = plt.subplots(figsize=(16, 7))
fig.patch.set_facecolor('#0f1117')
ax.set_facecolor('#0f1117')

# Colour bars by performance
colors = []
for d in daily.itertuples():
    if d.diversions > 0:
        colors.append('#ff4444')       # red — diversion day
    elif d.avg_delay >= 30:
        colors.append('#ff8800')       # orange — major delay
    elif d.avg_delay >= 0:
        colors.append('#ffcc00')       # yellow — minor delay
    else:
        colors.append('#00cc88')       # green — arrived early on average

bars = ax.bar(days, avg_delays, color=colors, width=0.6, zorder=3)

# Zero line
ax.axhline(0,  color='white',  linewidth=0.8, linestyle='--', alpha=0.4, zorder=2)

# On-time threshold line
ax.axhline(15, color='#ff6666', linewidth=0.8, linestyle=':', alpha=0.6, zorder=2)
ax.text(29.6, 16, 'On-time\nthreshold', color='#ff6666', fontsize=7, va='bottom', ha='right')

# ── Annotations on notable days ──────────────────────────────────────────────

ax.set_ylim(-40, 175)

notable = {
    '2026-04-12': ('Apr 12\n2 legs only\n(missing rotation?)', -25),
    '2026-04-22': ('Apr 22\n200 min NAS delay\ncascade', 25),
    '2026-04-27': ('Apr 27\n⚠ TWO DIVERSIONS\n444 min worst leg', 20),
    '2026-04-30': ('Apr 30\nCarrier cascade\n4-leg chain', 25),
}

for date_str, (label, y_offset) in notable.items():
    row = daily[daily['FlightDate'] == date_str]
    if len(row) == 0:
        continue
    idx = list(daily['FlightDate']).index(date_str)
    val = row['avg_delay'].values[0]
    ax.annotate(
        label,
        xy=(idx, val),
        xytext=(idx, val + y_offset),
        fontsize=7.5,
        color='white',
        ha='center',
        arrowprops=dict(arrowstyle='->', color='white', lw=0.8),
        bbox=dict(boxstyle='round,pad=0.3', facecolor='#222233', edgecolor='#555566', alpha=0.9)
    )

# ── Leg count as small text on each bar ──────────────────────────────────────

for i, row in daily.iterrows():
    ax.text(
        i, avg_delays[i] + (3 if avg_delays[i] >= 0 else -6),
        f"{int(row['legs'])}L",
        ha='center', va='bottom' if avg_delays[i] >= 0 else 'top',
        fontsize=6.5, color='white', alpha=0.7
    )

# ── Styling ───────────────────────────────────────────────────────────────────

ax.set_title('N923WN — Daily Average Arrival Delay | April 2026',
             color='white', fontsize=14, fontweight='bold', pad=20)
ax.set_xlabel('Date', color='#aaaaaa', fontsize=10)
ax.set_ylabel('Avg Arrival Delay (minutes)', color='#aaaaaa', fontsize=10)

ax.tick_params(colors='#aaaaaa', labelsize=8)
ax.tick_params(axis='x', rotation=45)

for spine in ax.spines.values():
    spine.set_edgecolor('#333344')

ax.yaxis.grid(True, color='#222233', linewidth=0.5, zorder=0)
ax.set_axisbelow(True)

# Legend
legend_items = [
    mpatches.Patch(color='#00cc88', label='Avg early (great day)'),
    mpatches.Patch(color='#ffcc00', label='Avg 0–30 min late'),
    mpatches.Patch(color='#ff8800', label='Avg 30+ min late'),
    mpatches.Patch(color='#ff4444', label='Diversion day'),
]
ax.legend(handles=legend_items, loc='upper left',
          facecolor='#1a1a2e', edgecolor='#333344',
          labelcolor='white', fontsize=8)

# Footer
fig.text(0.99, 0.01,
         'Source: BTS Marketing Carrier On-Time Performance | April 2026',
         ha='right', va='bottom', fontsize=7, color='#555566')

plt.tight_layout()

OUTPUT = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs\N923WN_daily_delay_APR2026.png"
plt.savefig(OUTPUT, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
print(f"Chart saved to: {OUTPUT}")
plt.show()