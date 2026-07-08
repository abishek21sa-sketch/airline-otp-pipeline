# pipeline_04_carrier_comparison.py
# Southwest (WN) vs American Airlines (AA) — Two Year Comparison
# Uses OTP_UNIFIED_2024_2025.csv

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

# ── CONFIG ────────────────────────────────────────────────────────────────────

DATA_PATH   = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\OTP_UNIFIED_2024_2025.csv"
OUTPUT_DIR  = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Outputs"

BG_COLOR    = '#0f1117'
GRID_COLOR  = '#222233'
SPINE_COLOR = '#333344'
TEXT_COLOR  = '#aaaaaa'
WHITE       = 'white'

COLOR_WN    = '#ff8800'   # Southwest orange
COLOR_AA    = '#0066cc'   # American blue

MONTH_NAMES = {
    1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
    5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
    9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
}


# ── HELPERS ───────────────────────────────────────────────────────────────────

def style_ax(ax):
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE_COLOR)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax.set_axisbelow(True)

def style_fig(fig, title):
    fig.patch.set_facecolor(BG_COLOR)
    fig.suptitle(title, color=WHITE, fontsize=14, fontweight='bold', y=1.01)
    fig.text(0.99, 0.01,
             'Source: BTS Marketing Carrier On-Time Performance | 2024-2025',
             ha='right', va='bottom', fontsize=7, color=SPINE_COLOR)


# ── LOAD DATA ─────────────────────────────────────────────────────────────────

print()
print("=" * 65)
print("  SOUTHWEST (WN) vs AMERICAN AIRLINES (AA) — 2024/2025")
print("=" * 65)

print("\n  Loading unified dataset...")
df = pd.read_csv(DATA_PATH, low_memory=False)
df['FlightDate'] = pd.to_datetime(df['FlightDate'], errors='coerce')
print(f"  Loaded {len(df):,} rows")

wn = df[df['Carrier'] == 'WN'].copy()
aa = df[df['Carrier'] == 'AA'].copy()

print(f"  WN flights: {len(wn):,}")
print(f"  AA flights: {len(aa):,}")


# ── TERMINAL COMPARISON ───────────────────────────────────────────────────────

def carrier_stats(data, name):
    operated = data[data['Cancelled'] == 0]
    late_dep  = operated[operated['DepDelay'] > 0].copy()
    late_dep['made_up'] = late_dep['DepDelay'] - late_dep['ArrDelay']
    return {
        'name'          : name,
        'flights'       : len(data),
        'operated'      : len(operated),
        'cancel_rate'   : data['Cancelled'].mean() * 100,
        'divert_rate'   : data['Diverted'].mean() * 100,
        'on_time_rate'  : (operated['ArrDelay'] <= 15).mean() * 100,
        'avg_arr_delay' : operated['ArrDelay'].mean(),
        'avg_dep_delay' : operated['DepDelay'].mean(),
        'recovery_rate' : (late_dep['made_up'] > 0).mean() * 100,
        'cascade_rate'  : (data['LateAircraftDelay'].fillna(0) > 0).mean() * 100,
        'unique_tails'  : data['TailNumber'].nunique(),
        'unique_routes' : (data['Origin'] + data['Dest']).nunique(),
    }

wn_stats = carrier_stats(wn, 'Southwest (WN)')
aa_stats = carrier_stats(aa, 'American (AA)')

print()
print("=" * 65)
print("  HEAD TO HEAD — 2024 & 2025 COMBINED")
print("=" * 65)
print()
print(f"  {'METRIC':<28} {'SOUTHWEST (WN)':>15} {'AMERICAN (AA)':>15}   WINNER")
print("  " + "-" * 62)

def row(label, wn_val, aa_val, fmt, higher_better=True):
    wn_str = fmt.format(wn_val)
    aa_str = fmt.format(aa_val)
    if higher_better:
        winner = 'WN' if wn_val > aa_val else 'AA' if aa_val > wn_val else 'TIE'
    else:
        winner = 'WN' if wn_val < aa_val else 'AA' if aa_val < wn_val else 'TIE'
    print(f"  {label:<28} {wn_str:>15} {aa_str:>15}   {winner}")

row('Total flights',       wn_stats['flights'],       aa_stats['flights'],       '{:>14,.0f}')
row('On-time rate',        wn_stats['on_time_rate'],  aa_stats['on_time_rate'],  '{:>13.1f}%')
row('Avg arrival delay',   wn_stats['avg_arr_delay'], aa_stats['avg_arr_delay'], '{:>13.1f}m', False)
row('Avg dep delay',       wn_stats['avg_dep_delay'], aa_stats['avg_dep_delay'], '{:>13.1f}m', False)
row('Cancellation rate',   wn_stats['cancel_rate'],   aa_stats['cancel_rate'],   '{:>13.2f}%', False)
row('Diversion rate',      wn_stats['divert_rate'],   aa_stats['divert_rate'],   '{:>13.3f}%', False)
row('Recovery rate',       wn_stats['recovery_rate'], aa_stats['recovery_rate'], '{:>13.1f}%')
row('Cascade leg rate',    wn_stats['cascade_rate'],  aa_stats['cascade_rate'],  '{:>13.1f}%', False)
row('Unique aircraft',     wn_stats['unique_tails'],  aa_stats['unique_tails'],  '{:>14,.0f}')
row('Unique routes',       wn_stats['unique_routes'], aa_stats['unique_routes'], '{:>14,.0f}')


# ── MONTHLY TRENDS ────────────────────────────────────────────────────────────

def monthly_stats(data):
    operated = data[data['Cancelled'] == 0]
    return operated.groupby(['Year', 'Month']).agg(
        on_time_rate = ('ArrDelay', lambda x: (x <= 15).mean() * 100),
        avg_delay    = ('ArrDelay', 'mean'),
        cancel_rate  = ('Cancelled', lambda x: x.mean() * 100),
    ).reset_index()

wn_monthly = monthly_stats(wn)
aa_monthly = monthly_stats(aa)

# Add month labels
def add_labels(df):
    df['label'] = df.apply(
        lambda r: f"{MONTH_NAMES[int(r['Month'])]}\n{int(r['Year'])}", axis=1)
    return df

wn_monthly = add_labels(wn_monthly)
aa_monthly = add_labels(aa_monthly)


# ── CHART 1: ON-TIME RATE & AVG DELAY ────────────────────────────────────────

fig, axes = plt.subplots(2, 2, figsize=(18, 10))
style_fig(fig, "Southwest (WN) vs American Airlines (AA) | 2024–2025")

x = np.arange(len(wn_monthly))
width = 0.35
months = wn_monthly['label'].values

# Top left — On-time rate monthly
ax1 = axes[0][0]
style_ax(ax1)
ax1.bar(x - width/2, wn_monthly['on_time_rate'], width,
        color=COLOR_WN, alpha=0.85, label='Southwest (WN)', zorder=3)
ax1.bar(x + width/2, aa_monthly['on_time_rate'], width,
        color=COLOR_AA, alpha=0.85, label='American (AA)', zorder=3)
ax1.axhline(79.0, color=WHITE, linewidth=0.8, linestyle='--', alpha=0.4)
ax1.set_title('Monthly On-Time Rate (%)', color=WHITE, fontsize=11, pad=10)
ax1.set_ylabel('On-Time Rate (%)', color=TEXT_COLOR)
ax1.set_xticks(x)
ax1.set_xticklabels(months, fontsize=6.5)
ax1.tick_params(axis='x', colors=TEXT_COLOR)
ax1.set_ylim(60, 100)
ax1.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR,
           labelcolor=WHITE, fontsize=8)

# Top right — Avg arrival delay monthly
ax2 = axes[0][1]
style_ax(ax2)
ax2.plot(x, wn_monthly['avg_delay'], color=COLOR_WN,
         linewidth=2, marker='o', markersize=4, label='Southwest (WN)', zorder=3)
ax2.plot(x, aa_monthly['avg_delay'], color=COLOR_AA,
         linewidth=2, marker='s', markersize=4, label='American (AA)', zorder=3)
ax2.axhline(0,  color=WHITE, linewidth=0.8, linestyle='--', alpha=0.3)
ax2.axhline(15, color='#ff4444', linewidth=0.8, linestyle=':', alpha=0.6)
ax2.fill_between(x, wn_monthly['avg_delay'], aa_monthly['avg_delay'],
                 alpha=0.1, color=WHITE)
ax2.set_title('Monthly Avg Arrival Delay (minutes)', color=WHITE, fontsize=11, pad=10)
ax2.set_ylabel('Avg Arrival Delay (mins)', color=TEXT_COLOR)
ax2.set_xticks(x)
ax2.set_xticklabels(months, fontsize=6.5)
ax2.tick_params(axis='x', colors=TEXT_COLOR)
ax2.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR,
           labelcolor=WHITE, fontsize=8)
ax2.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)

# Bottom left — Head to head bar chart key metrics
ax3 = axes[1][0]
style_ax(ax3)
metrics      = ['On-Time Rate', 'Recovery Rate']
wn_vals      = [wn_stats['on_time_rate'], wn_stats['recovery_rate']]
aa_vals      = [aa_stats['on_time_rate'], aa_stats['recovery_rate']]
x3           = np.arange(len(metrics))
bars_wn = ax3.bar(x3 - width/2, wn_vals, width, color=COLOR_WN,
                   alpha=0.85, label='Southwest (WN)', zorder=3)
bars_aa = ax3.bar(x3 + width/2, aa_vals, width, color=COLOR_AA,
                   alpha=0.85, label='American (AA)', zorder=3)
for bar, val in zip(bars_wn, wn_vals):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
             f'{val:.1f}%', ha='center', fontsize=8, color=WHITE)
for bar, val in zip(bars_aa, aa_vals):
    ax3.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.3,
             f'{val:.1f}%', ha='center', fontsize=8, color=WHITE)
ax3.set_title('Performance Rates — 2-Year Average', color=WHITE, fontsize=11, pad=10)
ax3.set_ylabel('Rate (%)', color=TEXT_COLOR)
ax3.set_xticks(x3)
ax3.set_xticklabels(metrics)
ax3.set_ylim(0, 110)
ax3.tick_params(axis='x', colors=TEXT_COLOR)
ax3.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR,
           labelcolor=WHITE, fontsize=8)

# Bottom right — Cancellation & diversion rates
ax4 = axes[1][1]
style_ax(ax4)
metrics4 = ['Cancellation\nRate', 'Diversion\nRate', 'Cascade\nLeg Rate']
wn_vals4 = [wn_stats['cancel_rate'], wn_stats['divert_rate'],
            wn_stats['cascade_rate']]
aa_vals4 = [aa_stats['cancel_rate'], aa_stats['divert_rate'],
            aa_stats['cascade_rate']]
x4 = np.arange(len(metrics4))
bars_wn4 = ax4.bar(x4 - width/2, wn_vals4, width, color=COLOR_WN,
                    alpha=0.85, label='Southwest (WN)', zorder=3)
bars_aa4 = ax4.bar(x4 + width/2, aa_vals4, width, color=COLOR_AA,
                    alpha=0.85, label='American (AA)', zorder=3)
for bar, val in zip(bars_wn4, wn_vals4):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f'{val:.2f}%', ha='center', fontsize=8, color=WHITE)
for bar, val in zip(bars_aa4, aa_vals4):
    ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
             f'{val:.2f}%', ha='center', fontsize=8, color=WHITE)
ax4.set_title('Disruption Rates — 2-Year Average', color=WHITE, fontsize=11, pad=10)
ax4.set_ylabel('Rate (%)', color=TEXT_COLOR)
ax4.set_xticks(x4)
ax4.set_xticklabels(metrics4)
ax4.tick_params(axis='x', colors=TEXT_COLOR)
ax4.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR,
           labelcolor=WHITE, fontsize=8)

plt.tight_layout()
output_path = os.path.join(OUTPUT_DIR, 'WN_vs_AA_comparison_2024_2025.png')
plt.savefig(output_path, dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
print(f"\n  Chart saved → WN_vs_AA_comparison_2024_2025.png")
plt.show()

print()
print("=" * 65)
print("  KEY FINDINGS")
print("=" * 65)
print()

# Who wins overall
wn_score = sum([
    wn_stats['on_time_rate'] > aa_stats['on_time_rate'],
    wn_stats['avg_arr_delay'] < aa_stats['avg_arr_delay'],
    wn_stats['cancel_rate'] < aa_stats['cancel_rate'],
    wn_stats['divert_rate'] < aa_stats['divert_rate'],
    wn_stats['recovery_rate'] > aa_stats['recovery_rate'],
    wn_stats['cascade_rate'] < aa_stats['cascade_rate'],
])
aa_score = 6 - wn_score

print(f"  Overall score (6 metrics): WN {wn_score} — AA {aa_score}")
print()
print(f"  WN advantages:")
if wn_stats['cancel_rate'] < aa_stats['cancel_rate']:
    print(f"    Lower cancellation rate: {wn_stats['cancel_rate']:.2f}% vs {aa_stats['cancel_rate']:.2f}%")
if wn_stats['on_time_rate'] > aa_stats['on_time_rate']:
    print(f"    Higher on-time rate: {wn_stats['on_time_rate']:.1f}% vs {aa_stats['on_time_rate']:.1f}%")
if wn_stats['recovery_rate'] > aa_stats['recovery_rate']:
    print(f"    Better air time recovery: {wn_stats['recovery_rate']:.1f}% vs {aa_stats['recovery_rate']:.1f}%")
if wn_stats['avg_arr_delay'] < aa_stats['avg_arr_delay']:
    print(f"    Lower avg arrival delay: {wn_stats['avg_arr_delay']:.1f}m vs {aa_stats['avg_arr_delay']:.1f}m")

print()
print(f"  AA advantages:")
if aa_stats['cancel_rate'] < wn_stats['cancel_rate']:
    print(f"    Lower cancellation rate: {aa_stats['cancel_rate']:.2f}% vs {wn_stats['cancel_rate']:.2f}%")
if aa_stats['on_time_rate'] > wn_stats['on_time_rate']:
    print(f"    Higher on-time rate: {aa_stats['on_time_rate']:.1f}% vs {wn_stats['on_time_rate']:.1f}%")
if aa_stats['recovery_rate'] > wn_stats['recovery_rate']:
    print(f"    Better air time recovery: {aa_stats['recovery_rate']:.1f}% vs {wn_stats['recovery_rate']:.1f}%")
if aa_stats['avg_arr_delay'] < wn_stats['avg_arr_delay']:
    print(f"    Lower avg arrival delay: {aa_stats['avg_arr_delay']:.1f}m vs {wn_stats['avg_arr_delay']:.1f}m")

print()
print(f"  Network comparison:")
print(f"    WN operates {wn_stats['unique_tails']:,} aircraft across "
      f"{wn_stats['unique_routes']:,} routes")
print(f"    AA operates {aa_stats['unique_tails']:,} aircraft across "
      f"{aa_stats['unique_routes']:,} routes")
print(f"    AA fleet is {aa_stats['unique_tails']/wn_stats['unique_tails']:.1f}x larger than WN")
print()
print("  Script complete.")
print()