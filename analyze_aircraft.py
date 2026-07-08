# analyze_aircraft.py
# DOT On-Time Performance — Interactive Aircraft Analyzer
# Replaces scripts 01-09. Works for any carrier and tail number.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import sys

from config import (
    DATA_FILE, OUTPUT_DIR,
    ON_TIME_THRESHOLD, TIGHT_TURNAROUND, TARGET_TURNAROUND, MAJOR_DELAY,
    BG_COLOR, GRID_COLOR, SPINE_COLOR, TEXT_COLOR, WHITE,
    COLOR_GOOD, COLOR_WARN, COLOR_BAD, COLOR_CRITICAL, COLOR_ACCENT,
    COLOR_HIGHLIGHT, SOURCE_NOTE
)


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
    fig.text(0.99, 0.01, SOURCE_NOTE, ha='right', va='bottom',
             fontsize=7, color=SPINE_COLOR)

def save_chart(fig, name, tail, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    safe_tail = tail.replace(' ', '_')
    path = os.path.join(output_dir, f"{safe_tail}_{name}.png")
    plt.savefig(path, dpi=150, bbox_inches='tight',
                facecolor=fig.get_facecolor())
    print(f"  Chart saved → {path}")
    plt.show()
    plt.close()

def primary_cause(row):
    if row['Diverted']  == 1: return 'DIVERTED'
    if row['Cancelled'] == 1: return 'CANCELLED'
    if pd.isna(row['ArrDelay']) or row['ArrDelay'] <= 0: return '—'
    cd  = row['CarrierDelay']      if not pd.isna(row['CarrierDelay'])      else 0
    wd  = row['WeatherDelay']      if not pd.isna(row['WeatherDelay'])      else 0
    nd  = row['NASDelay']          if not pd.isna(row['NASDelay'])          else 0
    lad = row['LateAircraftDelay'] if not pd.isna(row['LateAircraftDelay']) else 0
    causes = {'Carrier': cd, 'Weather': wd, 'NAS': nd, 'LateAC': lad}
    dominant = max(causes, key=causes.get)
    return dominant if causes[dominant] > 0 else '—'


# ── LOAD DATA ─────────────────────────────────────────────────────────────────

def load_data():
    print(f"\nLoading dataset...")
    df = pd.read_csv(DATA_FILE, low_memory=False)
    df.columns = df.columns.str.strip()
    print(f"Loaded {len(df):,} rows x {len(df.columns)} columns")
    print(f"Date range: {df['FlightDate'].min()} to {df['FlightDate'].max()}")
    return df


# ── INTERACTIVE SELECTION ─────────────────────────────────────────────────────

def select_carrier(df):
    print("\n" + "=" * 60)
    print("CARRIERS IN DATASET")
    print("=" * 60)
    counts = df['Operating_Airline'].value_counts()
    for carrier, count in counts.items():
        print(f"  {carrier:<6} {count:>8,} flights")
    carrier = input("\nEnter carrier code [default: WN]: ").strip().upper()
    if carrier == '':
        carrier = 'WN'
    if carrier not in df['Operating_Airline'].values:
        print(f"Carrier {carrier} not found. Defaulting to WN.")
        carrier = 'WN'
    return carrier

def select_tail(df, carrier):
    fleet = df[df['Operating_Airline'] == carrier].copy()
    print(f"\n{carrier} fleet: {fleet['Tail_Number'].nunique()} aircraft, "
          f"{len(fleet):,} flights")

    print("\n" + "=" * 60)
    print(f"TOP 20 BUSIEST {carrier} AIRCRAFT")
    print("=" * 60)
    summary = fleet.groupby('Tail_Number').agg(
        legs         = ('FlightDate', 'count'),
        days         = ('FlightDate', 'nunique'),
        cancellations= ('Cancelled', 'sum'),
        diversions   = ('Diverted', 'sum'),
        avg_delay    = ('ArrDelay', 'mean'),
        on_time      = ('ArrDel15', lambda x: (1-x.mean())*100),
    ).sort_values('legs', ascending=False).head(20)

    print(f"  {'TAIL':<10} {'LEGS':>5} {'DAYS':>5} {'CNCL':>5} "
          f"{'DIV':>4} {'AVG DLY':>8} {'ON-TIME%':>9}")
    print("  " + "-" * 55)
    for tail, r in summary.iterrows():
        flags = []
        if r['cancellations'] > 0: flags.append(f"C{int(r['cancellations'])}")
        if r['diversions']    > 0: flags.append(f"D{int(r['diversions'])}")
        flag_str = ' '.join(flags)
        print(f"  {tail:<10} {int(r['legs']):>5} {int(r['days']):>5} "
              f"{int(r['cancellations']):>5} {int(r['diversions']):>4} "
              f"{r['avg_delay']:>+7.1f}m {r['on_time']:>8.1f}%  {flag_str}")

    tail = input(f"\nEnter tail number [default: top aircraft]: ").strip().upper()
    if tail == '':
        tail = summary.index[0]
        print(f"Defaulting to {tail}")
    if tail not in fleet['Tail_Number'].values:
        print(f"Tail {tail} not found for {carrier}. Defaulting to top aircraft.")
        tail = summary.index[0]
    return tail, fleet


# ── FLEET BENCHMARKS ─────────────────────────────────────────────────────────

def compute_fleet_benchmarks(fleet):
    operated = fleet[fleet['Cancelled'] == 0]
    late     = operated[operated['DepDelay'] > 0].copy()
    late['made_up'] = late['DepDelay'] - late['ArrDelay']

    return {
        'on_time_rate'  : (operated['ArrDelay'] <= ON_TIME_THRESHOLD).mean() * 100,
        'avg_delay'     : fleet['ArrDelay'].mean(),
        'cancel_rate'   : fleet['Cancelled'].mean() * 100,
        'divert_rate'   : fleet['Diverted'].mean() * 100,
        'recovery_rate' : (late['made_up'] > 0).mean() * 100,
        'avg_made_up'   : late['made_up'].mean(),
        'avg_legs'      : fleet.groupby('Tail_Number')['FlightDate'].count().mean(),
        'avg_cascade'   : fleet.groupby('Tail_Number')['LateAircraftDelay'].apply(
                              lambda x: (x > 0).sum()).mean(),
    }


# ── PREPARE AIRCRAFT DATA ─────────────────────────────────────────────────────

def prepare_plane(fleet, tail):
    plane = fleet[fleet['Tail_Number'] == tail].sort_values(
        ['FlightDate', 'CRSDepTime']
    ).reset_index(drop=True)

    # Turnaround
    plane['prev_arr']  = plane['ArrTime'].shift(1)
    plane['prev_date'] = plane['FlightDate'].shift(1)
    same_day = plane['FlightDate'] == plane['prev_date']
    plane['turnaround'] = None
    plane.loc[same_day, 'turnaround'] = (
        plane.loc[same_day, 'CRSDepTime'] - plane.loc[same_day, 'prev_arr']
    )

    # Cascade
    plane['cascade'] = plane['LateAircraftDelay'].fillna(0) > 0

    # Primary cause
    plane['primary_cause'] = plane.apply(primary_cause, axis=1)

    # Route
    plane['route'] = plane['Origin'] + '→' + plane['Dest']

    # Dep hour
    plane['dep_hour'] = (plane['CRSDepTime'].astype(str).str.zfill(4)
                         .str[:2].astype(int))

    # Leg number of day
    plane['leg_num'] = plane.groupby('FlightDate').cumcount() + 1

    # Made up time
    operated = plane[plane['Cancelled'] == 0].copy()
    plane['made_up'] = plane['DepDelay'] - plane['ArrDelay']

    return plane


# ── SECTION 1: HEADLINE SUMMARY ───────────────────────────────────────────────

def print_summary(plane, tail, carrier, benchmarks):
    operated = plane[plane['Cancelled'] == 0]
    late_dep = operated[operated['DepDelay'] > 0].copy()
    late_dep['made_up'] = late_dep['DepDelay'] - late_dep['ArrDelay']

    on_time      = (operated['ArrDelay'] <= ON_TIME_THRESHOLD).mean() * 100
    avg_delay    = plane['ArrDelay'].mean()
    recovery     = (late_dep['made_up'] > 0).mean() * 100
    cascade_legs = plane['cascade'].sum()

    def vs(val, bench, higher_is_better=True):
        diff = val - bench
        if higher_is_better:
            symbol = '▲' if diff > 0 else '▼'
            color  = 'above' if diff > 0 else 'below'
        else:
            symbol = '▼' if diff < 0 else '▲'
            color  = 'better' if diff < 0 else 'worse'
        return f"{symbol} {abs(diff):.1f} {color} fleet avg"

    print()
    print("=" * 70)
    print(f"AIRCRAFT SUMMARY — {tail} ({carrier}) | APRIL 2026")
    print("=" * 70)
    print(f"\n  {'METRIC':<25} {'AIRCRAFT':>12}   {'FLEET AVG':>12}   COMPARISON")
    print("  " + "-" * 65)
    print(f"  {'Total legs':<25} {len(plane):>12,}   "
          f"{benchmarks['avg_legs']:>12.0f}")
    print(f"  {'Days flown':<25} {plane['FlightDate'].nunique():>12}   "
          f"{'30':>12}")
    print(f"  {'On-time rate':<25} {on_time:>11.1f}%   "
          f"{benchmarks['on_time_rate']:>11.1f}%   "
          f"{vs(on_time, benchmarks['on_time_rate'])}")
    print(f"  {'Avg arrival delay':<25} {avg_delay:>+11.1f}m   "
          f"{benchmarks['avg_delay']:>+11.1f}m   "
          f"{vs(-avg_delay, -benchmarks['avg_delay'])}")
    print(f"  {'Recovery rate':<25} {recovery:>11.1f}%   "
          f"{benchmarks['recovery_rate']:>11.1f}%   "
          f"{vs(recovery, benchmarks['recovery_rate'])}")
    print(f"  {'Cascade legs':<25} {int(cascade_legs):>12}   "
          f"{benchmarks['avg_cascade']:>12.1f}   "
          f"{vs(-cascade_legs, -benchmarks['avg_cascade'])}")
    print(f"  {'Cancellations':<25} {int(plane['Cancelled'].sum()):>12}   "
          f"{'—':>12}")
    print(f"  {'Diversions':<25} {int(plane['Diverted'].sum()):>12}   "
          f"{'—':>12}")
    print(f"  {'Total air time':<25} {plane['AirTime'].sum()/60:>11.1f}h   "
          f"{'—':>12}")
    print(f"  {'Total distance':<25} {plane['Distance'].sum():>11,.0f}mi   "
          f"{benchmarks['avg_legs']*119:>11,.0f}mi")
    print(f"  {'Airports visited':<25} {plane['Origin'].nunique():>12}   "
          f"{'—':>12}")
    print(f"  {'Worst delay':<25} {plane['ArrDelay'].max():>+11.0f}m   "
          f"{'—':>12}")
    print(f"  {'Best arrival':<25} {plane['ArrDelay'].min():>+11.0f}m   "
          f"{'—':>12}")


# ── SECTION 2: DAILY ROTATION ────────────────────────────────────────────────

def print_rotation(plane, tail):
    print()
    print("=" * 110)
    print(f"{tail} — FULL ROTATION")
    print("=" * 110)
    print(f"  {'#':<4} {'DATE':<12} {'FL':<6} {'ROUTE':<10} "
          f"{'SCHED DEP':>9} {'ACT DEP':>8} {'DEP DLY':>8} "
          f"{'SCHED ARR':>9} {'ACT ARR':>8} {'ARR DLY':>8} "
          f"{'TRNRD':>6} {'AIR':>5} {'CAUSE':<10} FLAGS")
    print("  " + "-" * 108)

    prev_date = None
    leg_num   = 0

    for _, row in plane.iterrows():
        if row['FlightDate'] != prev_date:
            if prev_date is not None: print()
            day_group = plane[plane['FlightDate'] == row['FlightDate']]
            avg_d = day_group['ArrDelay'].mean()
            print(f"  ── {row['FlightDate']}  |  {len(day_group)} legs  |  "
                  f"{day_group['Origin'].iloc[0]} → {day_group['Dest'].iloc[-1]}  |  "
                  f"avg delay: {avg_d:+.0f} min")
            prev_date = row['FlightDate']

        leg_num += 1
        route     = f"{row['Origin']}→{row['Dest']}"
        dep_sched = f"{int(row['CRSDepTime']):04d}" if not pd.isna(row['CRSDepTime']) else '----'
        dep_act   = f"{int(row['DepTime']):04d}"    if not pd.isna(row['DepTime'])    else '----'
        arr_sched = f"{int(row['CRSArrTime']):04d}" if not pd.isna(row['CRSArrTime']) else '----'
        arr_act   = f"{int(row['ArrTime']):04d}"    if not pd.isna(row['ArrTime'])    else '----'
        dep_delay = f"{row['DepDelay']:+.0f}m"      if not pd.isna(row['DepDelay'])   else '  NaN'
        arr_delay = f"{row['ArrDelay']:+.0f}m"      if not pd.isna(row['ArrDelay'])   else '  NaN'
        ta  = f"{int(row['turnaround']):>3}m" if row['turnaround'] is not None else '  — '
        air = f"{int(row['AirTime'])}m"       if not pd.isna(row['AirTime'])   else ' — '

        flags = []
        if row['Diverted']  == 1: flags.append('DIVERTED')
        if row['cascade']:         flags.append('CASCADE')
        if not pd.isna(row['ArrDelay']) and row['ArrDelay'] >= MAJOR_DELAY:
            flags.append('MAJOR')
        elif not pd.isna(row['ArrDelay']) and row['ArrDelay'] >= ON_TIME_THRESHOLD:
            flags.append('LATE')
        elif not pd.isna(row['ArrDelay']) and row['ArrDelay'] < 0:
            flags.append('EARLY')

        print(f"  {leg_num:<4} {'':<12} {int(row['Flight_Number_Operating_Airline']):<6} "
              f"{route:<10} "
              f"{dep_sched:>9} {dep_act:>8} {dep_delay:>8} "
              f"{arr_sched:>9} {arr_act:>8} {arr_delay:>8} "
              f"{ta:>6} {air:>5}  {row['primary_cause']:<10} {'  '.join(flags)}")


# ── SECTION 3: CHARTS ─────────────────────────────────────────────────────────

def chart_daily_delay(plane, tail, carrier, output_dir):
    daily = plane.groupby('FlightDate').agg(
        legs       = ('FlightDate', 'count'),
        avg_delay  = ('ArrDelay',   'mean'),
        max_delay  = ('ArrDelay',   'max'),
        diversions = ('Diverted',   'sum'),
        start      = ('Origin',     'first'),
        end        = ('Dest',       'last')
    ).reset_index()

    dates  = pd.to_datetime(daily['FlightDate'])
    days   = [d.strftime('%b %d') for d in dates]
    delays = daily['avg_delay'].values

    colors = []
    for i, row in daily.iterrows():
        if row['diversions'] > 0:         colors.append(COLOR_CRITICAL)
        elif row['avg_delay'] >= 30:      colors.append(COLOR_BAD)
        elif row['avg_delay'] >= 0:       colors.append(COLOR_WARN)
        else:                             colors.append(COLOR_GOOD)

    fig, ax = plt.subplots(figsize=(16, 7))
    style_fig(fig, f"{tail} ({carrier}) — Daily Average Arrival Delay")
    style_ax(ax)

    ax.bar(days, delays, color=colors, width=0.6, zorder=3)
    ax.axhline(0,  color=WHITE,       linewidth=0.8, linestyle='--', alpha=0.4)
    ax.axhline(15, color=COLOR_CRITICAL, linewidth=0.8, linestyle=':', alpha=0.6)

    for i, row in daily.iterrows():
        y = delays[i]
        ax.text(i, y + (2 if y >= 0 else -5), f"{int(row['legs'])}L",
                ha='center', va='bottom' if y >= 0 else 'top',
                fontsize=6.5, color=WHITE, alpha=0.7)

    # Auto-annotate worst and best days
    worst_idx = daily['avg_delay'].idxmax()
    best_idx  = daily['avg_delay'].idxmin()
    for idx, label in [(worst_idx, 'Worst day'), (best_idx, 'Best day')]:
        val = delays[idx]
        offset = 30 if val >= 0 else -30
        ax.annotate(f"{label}\n{daily.loc[idx,'start']}→{daily.loc[idx,'end']}\n{val:+.0f}m avg",
                    xy=(idx, val),
                    xytext=(idx, val + offset),
                    fontsize=7.5, color=WHITE, ha='center',
                    arrowprops=dict(arrowstyle='->', color=WHITE, lw=0.8),
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#222233',
                              edgecolor=SPINE_COLOR, alpha=0.9))

    ax.set_xlabel('Date', color=TEXT_COLOR)
    ax.set_ylabel('Avg Arrival Delay (minutes)', color=TEXT_COLOR)
    ax.tick_params(axis='x', rotation=45, labelsize=8)
    ax.xaxis.grid(False)

    legend_items = [
        mpatches.Patch(color=COLOR_GOOD,     label='Avg early'),
        mpatches.Patch(color=COLOR_WARN,     label='Avg 0–30m late'),
        mpatches.Patch(color=COLOR_BAD,      label='Avg 30m+ late'),
        mpatches.Patch(color=COLOR_CRITICAL, label='Diversion day'),
    ]
    ax.legend(handles=legend_items, loc='upper left',
              facecolor='#1a1a2e', edgecolor=SPINE_COLOR,
              labelcolor=WHITE, fontsize=8)

    plt.tight_layout()
    save_chart(fig, 'daily_delay', tail, output_dir)


def chart_delay_causes(plane, tail, carrier, benchmarks, output_dir):
    causes = ['CarrierDelay', 'WeatherDelay', 'NASDelay',
              'SecurityDelay', 'LateAircraftDelay']
    labels = ['Carrier', 'Weather', 'NAS', 'Security', 'Late AC']
    totals = [plane[c].sum() for c in causes]
    legs   = [(plane[c] > 0).sum() for c in causes]
    colors_c = [COLOR_CRITICAL, COLOR_ACCENT, COLOR_WARN,
                '#aa88ff', COLOR_BAD]

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    style_fig(fig, f"{tail} ({carrier}) — Delay Cause Breakdown vs Fleet")
    for ax in axes: style_ax(ax)

    # Left: total delay minutes by cause
    ax1 = axes[0]
    bars = ax1.bar(labels, totals, color=colors_c, width=0.6, zorder=3)
    for bar, t, l in zip(bars, totals, legs):
        if t > 0:
            ax1.text(bar.get_x() + bar.get_width()/2,
                     bar.get_height() + 5,
                     f'{t:.0f}m\n{l} legs',
                     ha='center', va='bottom', fontsize=8, color=WHITE)
    ax1.set_title('Total Delay Minutes by Cause', color=WHITE, fontsize=11, pad=10)
    ax1.set_xlabel('Delay Cause', color=TEXT_COLOR)
    ax1.set_ylabel('Total Minutes', color=TEXT_COLOR)

    # Right: on-time rate vs fleet benchmark
    ax2 = axes[1]
    operated = plane[plane['Cancelled'] == 0]
    late_dep = operated[operated['DepDelay'] > 0].copy()
    late_dep['made_up'] = late_dep['DepDelay'] - late_dep['ArrDelay']

    metrics = ['On-Time Rate', 'Recovery Rate']
    aircraft_vals = [
        (operated['ArrDelay'] <= ON_TIME_THRESHOLD).mean() * 100,
        (late_dep['made_up'] > 0).mean() * 100,
    ]
    fleet_vals = [
        benchmarks['on_time_rate'],
        benchmarks['recovery_rate'],
    ]

    x = np.arange(len(metrics))
    width = 0.35
    ax2.bar(x - width/2, aircraft_vals, width=width,
            color=COLOR_ACCENT, alpha=0.9, label=tail, zorder=3)
    ax2.bar(x + width/2, fleet_vals,    width=width,
            color=SPINE_COLOR, alpha=0.9, label='Fleet avg', zorder=3)

    for i, (av, fv) in enumerate(zip(aircraft_vals, fleet_vals)):
        ax2.text(i - width/2, av + 0.5, f'{av:.1f}%',
                 ha='center', fontsize=8, color=WHITE)
        ax2.text(i + width/2, fv + 0.5, f'{fv:.1f}%',
                 ha='center', fontsize=8, color=WHITE)

    ax2.set_xticks(x)
    ax2.set_xticklabels(metrics)
    ax2.set_ylim(0, 110)
    ax2.set_title(f'{tail} vs Fleet Benchmark', color=WHITE, fontsize=11, pad=10)
    ax2.set_ylabel('Rate (%)', color=TEXT_COLOR)
    ax2.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR,
               labelcolor=WHITE, fontsize=8)

    plt.tight_layout()
    save_chart(fig, 'delay_causes', tail, output_dir)


def chart_time_of_day(plane, tail, carrier, output_dir):
    hourly = plane.groupby('dep_hour').agg(
        legs         = ('ArrDelay', 'count'),
        avg_delay    = ('ArrDelay', 'mean'),
        on_time_rate = ('ArrDel15', lambda x: (1 - x.mean()) * 100),
    ).reset_index()

    leg_pos = plane.groupby('leg_num').agg(
        count     = ('ArrDelay', 'count'),
        avg_delay = ('ArrDelay', 'mean'),
        on_time   = ('ArrDel15', lambda x: (1-x.mean())*100)
    ).reset_index()

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    style_fig(fig, f"{tail} ({carrier}) — Time of Day Performance")
    for ax in axes: style_ax(ax)

    ax1 = axes[0]
    delays = hourly['avg_delay'].values
    colors_h = [COLOR_GOOD if d <= 0 else COLOR_WARN if d <= 15
                else COLOR_BAD if d <= 30 else COLOR_CRITICAL for d in delays]
    ax1.bar([f"{h:02d}:xx" for h in hourly['dep_hour']], delays,
            color=colors_h, width=0.7, zorder=3)
    ax1.axhline(0,  color=WHITE,         linewidth=0.8, linestyle='--', alpha=0.4)
    ax1.axhline(15, color=COLOR_CRITICAL, linewidth=0.8, linestyle=':',  alpha=0.6)
    ax1.set_title('Avg Arrival Delay by Departure Hour',
                  color=WHITE, fontsize=11, pad=10)
    ax1.set_xlabel('Scheduled Departure Hour', color=TEXT_COLOR)
    ax1.set_ylabel('Avg Arrival Delay (minutes)', color=TEXT_COLOR)
    ax1.tick_params(axis='x', rotation=45, labelsize=8)
    ax1.xaxis.grid(False)

    ax2 = axes[1]
    x = range(len(leg_pos))
    ax2.bar(x, leg_pos['on_time'].values, color=COLOR_GOOD,
            alpha=0.8, label='On-time rate (%)', zorder=3)
    ax2_twin = ax2.twinx()
    ax2_twin.set_facecolor(BG_COLOR)
    ax2_twin.bar([i + 0.35 for i in x], leg_pos['avg_delay'].values,
                 width=0.35, color=COLOR_BAD, alpha=0.8,
                 label='Avg delay (mins)', zorder=3)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels([f'Leg {int(p)}' for p in leg_pos['leg_num']])
    ax2.set_title('Performance by Leg Position in Day',
                  color=WHITE, fontsize=11, pad=10)
    ax2.set_ylabel('On-time rate (%)', color=COLOR_GOOD)
    ax2_twin.set_ylabel('Avg delay (mins)', color=COLOR_BAD)
    ax2.tick_params(colors=TEXT_COLOR)
    ax2_twin.tick_params(colors=COLOR_BAD)
    for spine in ax2.spines.values(): spine.set_edgecolor(SPINE_COLOR)
    ax2.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)

    plt.tight_layout()
    save_chart(fig, 'time_of_day', tail, output_dir)


def chart_recovery(plane, tail, carrier, output_dir):
    operated = plane[plane['Cancelled'] == 0].copy()
    late_dep = operated[operated['DepDelay'] > 0].copy()
    late_dep['made_up'] = late_dep['DepDelay'] - late_dep['ArrDelay']

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    style_fig(fig, f"{tail} ({carrier}) — Air Time Recovery Analysis")
    for ax in axes: style_ax(ax)

    ax1 = axes[0]
    x = operated['DepDelay'].astype(float).values
    y = operated['ArrDelay'].astype(float).values
    colors_s = []
    for dep, arr in zip(x, y):
        if dep <= 0:     colors_s.append(COLOR_ACCENT)
        elif arr < dep:  colors_s.append(COLOR_GOOD)
        else:            colors_s.append(COLOR_CRITICAL)
    ax1.scatter(x, y, c=colors_s, s=30, alpha=0.7, zorder=3)
    lim = max(abs(np.nanmin(x)), abs(np.nanmax(x)),
              abs(np.nanmin(y)), abs(np.nanmax(y))) * 1.1
    ax1.plot([-lim, lim], [-lim, lim], color=WHITE, linewidth=1,
             linestyle='--', alpha=0.4)
    ax1.axhline(0,  color='#888888', linewidth=0.5, linestyle=':')
    ax1.axvline(0,  color='#888888', linewidth=0.5, linestyle=':')
    ax1.set_xlim(-lim, lim)
    ax1.set_ylim(-lim, lim)
    ax1.set_title('Departure Delay vs Arrival Delay', color=WHITE, fontsize=11, pad=10)
    ax1.set_xlabel('Departure Delay (minutes)', color=TEXT_COLOR)
    ax1.set_ylabel('Arrival Delay (minutes)', color=TEXT_COLOR)
    legend_items = [
        mpatches.Patch(color=COLOR_ACCENT,   label='Early/on-time departure'),
        mpatches.Patch(color=COLOR_GOOD,     label='Late dep, recovered'),
        mpatches.Patch(color=COLOR_CRITICAL, label='Late dep, got worse'),
    ]
    ax1.legend(handles=legend_items, facecolor='#1a1a2e',
               edgecolor=SPINE_COLOR, labelcolor=WHITE, fontsize=8)

    ax2 = axes[1]
    made_up_vals = late_dep['made_up'].astype(float).values
    bins = range(int(np.nanmin(made_up_vals))-5, int(np.nanmax(made_up_vals))+10, 5)
    n, bin_edges, patches = ax2.hist(made_up_vals, bins=bins,
                                      edgecolor=BG_COLOR, linewidth=0.5)
    for patch, left in zip(patches, bin_edges):
        patch.set_facecolor(COLOR_GOOD if left >= 0 else COLOR_CRITICAL)
    ax2.axvline(0, color=WHITE, linewidth=1.5, linestyle='--', alpha=0.6)
    mean_val = float(np.nanmean(made_up_vals))
    ax2.axvline(mean_val, color=COLOR_HIGHLIGHT, linewidth=1.5)
    ax2.text(mean_val + 0.5, n.max()*0.85,
             f'Mean\n{mean_val:+.1f}m', color=COLOR_HIGHLIGHT, fontsize=8)
    ax2.set_title('Time Made Up in Air\n(late departures only)',
                  color=WHITE, fontsize=11, pad=10)
    ax2.set_xlabel('Minutes recovered', color=TEXT_COLOR)
    ax2.set_ylabel('Number of flights', color=TEXT_COLOR)

    plt.tight_layout()
    save_chart(fig, 'recovery', tail, output_dir)


# ── SECTION 4: TURNAROUND ANALYSIS ───────────────────────────────────────────

def chart_turnaround(plane, tail, carrier, output_dir):
    plane = plane.copy()
    same_day = plane['FlightDate'] == plane['prev_date']
    ta_valid = plane[same_day & plane['turnaround'].notna() &
                     (plane['turnaround'].astype(float) >= 0)].copy()
    ta_valid['turnaround'] = ta_valid['turnaround'].astype(float)
    ta_valid['ArrDelay']   = ta_valid['ArrDelay'].astype(float)

    if len(ta_valid) < 2:
        print("  Not enough turnaround data to chart.")
        return

    print(f"\n  Turnaround summary:")
    mean_val = float(ta_valid['turnaround'].mean())
    print(f"    Valid turnarounds  : {len(ta_valid)}")
    print(f"    Mean               : {mean_val:.0f} mins")
    print(f"    Median             : {float(ta_valid['turnaround'].median()):.0f} mins")
    print(f"    Tight (<25m)       : {(ta_valid['turnaround'] < 25).sum()}")
    print(f"    Negative (chasing) : {(plane[same_day]['turnaround'].astype(float) < 0).sum()}")

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    style_fig(fig, f"{tail} ({carrier}) — Turnaround Time Analysis")
    for ax in axes: style_ax(ax)

    ax1 = axes[0]
    vals = ta_valid['turnaround'].values
    bins = range(0, int(max(vals)) + 20, 15)
    n, bin_edges, patches = ax1.hist(vals, bins=bins, edgecolor=BG_COLOR, linewidth=0.5)
    for patch, left in zip(patches, bin_edges):
        if left < 25:   patch.set_facecolor(COLOR_CRITICAL)
        elif left < 45: patch.set_facecolor(COLOR_GOOD)
        elif left < 90: patch.set_facecolor(COLOR_WARN)
        else:           patch.set_facecolor(COLOR_ACCENT)
    ax1.axvline(25, color=WHITE, linewidth=1, linestyle='--', alpha=0.5)
    ax1.axvline(45, color=WHITE, linewidth=1, linestyle='--', alpha=0.5)
    ax1.axvline(90, color=WHITE, linewidth=1, linestyle='--', alpha=0.5)
    ax1.axvline(mean_val, color=COLOR_HIGHLIGHT, linewidth=1.5, label=f'Mean: {mean_val:.0f}m')
    if n.max() > 0:
        ax1.text(12,  n.max()*0.9, 'Tight\n<25m',    color=COLOR_CRITICAL, fontsize=8, ha='center')
        ax1.text(35,  n.max()*0.9, 'Target\n25-45m', color=COLOR_GOOD,     fontsize=8, ha='center')
        ax1.text(67,  n.max()*0.9, 'Buffer\n45-90m', color=COLOR_WARN,     fontsize=8, ha='center')
    ax1.set_title('Turnaround Time Distribution', color=WHITE, fontsize=11, pad=10)
    ax1.set_xlabel('Turnaround (minutes)', color=TEXT_COLOR)
    ax1.set_ylabel('Number of turnarounds', color=TEXT_COLOR)
    ax1.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR, labelcolor=WHITE, fontsize=8)

    ax2 = axes[1]
    x = ta_valid['turnaround'].values
    y = ta_valid['ArrDelay'].values
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    sc_c = [COLOR_CRITICAL if v < 25 else COLOR_GOOD if v < 45
            else COLOR_WARN if v < 90 else COLOR_ACCENT for v in x]
    ax2.scatter(x, y, c=sc_c, s=50, alpha=0.8, zorder=3)
    ax2.axhline(0,  color=WHITE,         linewidth=0.8, linestyle='--', alpha=0.4)
    ax2.axhline(15, color=COLOR_CRITICAL, linewidth=0.8, linestyle=':',  alpha=0.6)
    if len(x) > 1:
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        xline = np.linspace(min(x), max(x), 100)
        r = float(np.corrcoef(x, y)[0, 1])
        ax2.plot(xline, p(xline), color=COLOR_HIGHLIGHT, linewidth=1.5, label=f'Trend (r={r:.2f})')
        ax2.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR, labelcolor=WHITE, fontsize=8)
    ax2.set_title('Turnaround vs Next Leg Arrival Delay', color=WHITE, fontsize=11, pad=10)
    ax2.set_xlabel('Turnaround Time (minutes)', color=TEXT_COLOR)
    ax2.set_ylabel('Arrival Delay of Next Leg (minutes)', color=TEXT_COLOR)
    ax2.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax2.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    for spine in ax2.spines.values(): spine.set_edgecolor(SPINE_COLOR)

    plt.tight_layout()
    save_chart(fig, 'turnaround', tail, output_dir)


# ── SECTION 5: CASCADE ANALYSIS ──────────────────────────────────────────────

def chart_cascade(plane, tail, carrier, output_dir):
    chains = []
    for date, group in plane.groupby('FlightDate'):
        group = group.reset_index(drop=True)
        in_chain, chain_legs = False, []
        for i, row in group.iterrows():
            if row['cascade']:
                chain_legs.append(row); in_chain = True
            else:
                if in_chain and chain_legs:
                    prior = [idx for idx in group.index if idx < chain_legs[0].name]
                    trigger = group.loc[max(prior)] if prior else None
                    chains.append({'date': date, 'trigger': trigger, 'legs': chain_legs.copy(),
                                   'chain_len': len(chain_legs),
                                   'total_lateAC': sum(l['LateAircraftDelay'] for l in chain_legs),
                                   'max_delay': max((l['ArrDelay'] for l in chain_legs if not pd.isna(l['ArrDelay'])), default=0)})
                    chain_legs, in_chain = [], False
        if in_chain and chain_legs:
            prior = [idx for idx in group.index if idx < chain_legs[0].name]
            trigger = group.loc[max(prior)] if prior else None
            chains.append({'date': date, 'trigger': trigger, 'legs': chain_legs,
                           'chain_len': len(chain_legs),
                           'total_lateAC': sum(l['LateAircraftDelay'] for l in chain_legs),
                           'max_delay': max((l['ArrDelay'] for l in chain_legs if not pd.isna(l['ArrDelay'])), default=0)})

    print(f"\n  Cascade summary:")
    print(f"    Total chains      : {len(chains)}")
    print(f"    Total cascade legs: {plane['cascade'].sum()}")
    print(f"    Total LateAC mins : {plane['LateAircraftDelay'].sum():.0f}")
    for i, chain in enumerate(chains, 1):
        t = chain['trigger']
        print(f"\n    Chain {i} — {chain['date']} ({chain['chain_len']} legs, {chain['total_lateAC']:.0f} LateAC mins)")
        if t is not None:
            print(f"      Trigger: FL{int(t['Flight_Number_Operating_Airline'])} {t['Origin']}→{t['Dest']} ArrDelay: {t['ArrDelay']:+.0f}m")
        for leg in chain['legs']:
            lad = leg['LateAircraftDelay'] if not pd.isna(leg['LateAircraftDelay']) else 0
            arr = leg['ArrDelay'] if not pd.isna(leg['ArrDelay']) else float('nan')
            print(f"      -> FL{int(leg['Flight_Number_Operating_Airline'])} {leg['Origin']}→{leg['Dest']} ArrDelay: {arr:+.0f}m LateAC: {lad:.0f}m")

    if not chains:
        print("  No cascade chains found.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    style_fig(fig, f"{tail} ({carrier}) — Cascade Chain Analysis")
    for ax in axes: style_ax(ax)

    ax1 = axes[0]
    chain_dates  = [c['date'].replace('2026-04-', 'Apr ') for c in chains]
    chain_lateAC = [c['total_lateAC'] for c in chains]
    chain_lens   = [c['chain_len'] for c in chains]
    colors_b     = [COLOR_CRITICAL if l >= 3 else COLOR_BAD if l == 2 else COLOR_WARN for l in chain_lens]
    bars = ax1.bar(chain_dates, chain_lateAC, color=colors_b, width=0.6, zorder=3)
    for bar, length, lateAC in zip(bars, chain_lens, chain_lateAC):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f'{length}L\n{lateAC:.0f}m', ha='center', va='bottom', fontsize=8, color=WHITE)
    ax1.set_title('LateAC Delay per Cascade Chain', color=WHITE, fontsize=11, pad=10)
    ax1.set_xlabel('Date', color=TEXT_COLOR)
    ax1.set_ylabel('Total Late Aircraft Delay (minutes)', color=TEXT_COLOR)
    ax1.tick_params(axis='x', rotation=45, colors=TEXT_COLOR)
    ax1.tick_params(axis='y', colors=TEXT_COLOR)
    legend_items = [mpatches.Patch(color=COLOR_CRITICAL, label='3+ leg chain'),
                    mpatches.Patch(color=COLOR_BAD,      label='2 leg chain'),
                    mpatches.Patch(color=COLOR_WARN,     label='1 leg chain')]
    ax1.legend(handles=legend_items, facecolor='#1a1a2e', edgecolor=SPINE_COLOR, labelcolor=WHITE, fontsize=8)

    ax2 = axes[1]
    trigger_indices = set()
    cascade_indices = set()
    for chain in chains:
        if chain['trigger'] is not None: trigger_indices.add(chain['trigger'].name)
        for leg in chain['legs']: cascade_indices.add(leg.name)
    delays, colors_legs = [], []
    for idx, row in plane.iterrows():
        d = row['ArrDelay'] if not pd.isna(row['ArrDelay']) else 0
        delays.append(d)
        if idx in trigger_indices:   colors_legs.append(COLOR_CRITICAL)
        elif idx in cascade_indices: colors_legs.append(COLOR_BAD)
        else:                        colors_legs.append(COLOR_GOOD)
    ax2.bar(range(len(plane)), delays, color=colors_legs, width=0.7, zorder=3)
    ax2.axhline(0,  color=WHITE,         linewidth=0.8, linestyle='--', alpha=0.4)
    ax2.axhline(15, color=COLOR_CRITICAL, linewidth=0.8, linestyle=':',  alpha=0.6)
    ax2.set_title('All Legs — Trigger, Cascade & Normal', color=WHITE, fontsize=11, pad=10)
    ax2.set_xlabel('Leg number (chronological)', color=TEXT_COLOR)
    ax2.set_ylabel('Arrival Delay (minutes)', color=TEXT_COLOR)
    ax2.tick_params(colors=TEXT_COLOR)
    legend_items2 = [mpatches.Patch(color=COLOR_CRITICAL, label='Trigger leg'),
                     mpatches.Patch(color=COLOR_BAD,      label='Cascade leg'),
                     mpatches.Patch(color=COLOR_GOOD,     label='Normal leg')]
    ax2.legend(handles=legend_items2, facecolor='#1a1a2e', edgecolor=SPINE_COLOR, labelcolor=WHITE, fontsize=8)

    plt.tight_layout()
    save_chart(fig, 'cascade', tail, output_dir)


# ── SECTION 6: ROUTE ANALYSIS ────────────────────────────────────────────────

def chart_routes(plane, tail, carrier, output_dir):
    route_summary = plane.groupby('route').agg(
        legs      = ('ArrDelay', 'count'),
        avg_delay = ('ArrDelay', 'mean'),
        on_time   = ('ArrDel15', lambda x: (1 - x.mean()) * 100),
        avg_dist  = ('Distance', 'mean'),
    ).sort_values('legs', ascending=False)

    print(f"\n  Route summary:")
    print(f"    Unique routes : {len(route_summary)}")
    visits = pd.concat([plane['Origin'], plane['Dest']]).value_counts().head(5)
    print(f"    Top airports  :")
    for ap, count in visits.items():
        print(f"      {ap}  {count} visits")

    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    style_fig(fig, f"{tail} ({carrier}) — Route Analysis")
    for ax in axes: style_ax(ax)

    ax1 = axes[0]
    top15 = pd.concat([plane['Origin'], plane['Dest']]).value_counts().head(15)
    colors_ap = [COLOR_CRITICAL if c >= 20 else COLOR_BAD if c >= 15
                 else COLOR_WARN if c >= 10 else COLOR_GOOD for c in top15.values]
    ax1.barh(top15.index[::-1], top15.values[::-1], color=colors_ap[::-1], zorder=3)
    for i, (ap, count) in enumerate(zip(top15.index[::-1], top15.values[::-1])):
        ax1.text(count + 0.2, i, str(count), va='center', color=WHITE, fontsize=8)
    ax1.set_title('Top 15 Airports by Visits', color=WHITE, fontsize=11, pad=10)
    ax1.set_xlabel('Number of visits', color=TEXT_COLOR)
    ax1.tick_params(colors=TEXT_COLOR)
    ax1.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)

    ax2 = axes[1]
    multi = route_summary[route_summary['legs'] > 1]
    if len(multi) > 0:
        sc_c = [COLOR_CRITICAL if d > 15 else COLOR_WARN if d > 0 else COLOR_GOOD for d in multi['avg_delay']]
        ax2.scatter(multi['avg_dist'], multi['avg_delay'], c=sc_c, s=multi['legs']*30, alpha=0.8, zorder=3)
        for route, r in multi.iterrows():
            if abs(r['avg_delay']) > 20 or r['legs'] > 3:
                ax2.annotate(route, xy=(r['avg_dist'], r['avg_delay']),
                             xytext=(r['avg_dist']+10, r['avg_delay']+2), fontsize=7, color=WHITE)
    ax2.axhline(0,  color=WHITE,         linewidth=0.8, linestyle='--', alpha=0.4)
    ax2.axhline(15, color=COLOR_CRITICAL, linewidth=0.8, linestyle=':',  alpha=0.6)
    ax2.set_title('Route Distance vs Avg Delay\n(size = legs flown)', color=WHITE, fontsize=11, pad=10)
    ax2.set_xlabel('Average Distance (miles)', color=TEXT_COLOR)
    ax2.set_ylabel('Avg Arrival Delay (minutes)', color=TEXT_COLOR)
    ax2.tick_params(colors=TEXT_COLOR)
    ax2.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax2.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    legend_items = [mpatches.Patch(color=COLOR_CRITICAL, label='Avg delay > 15m'),
                    mpatches.Patch(color=COLOR_WARN,     label='Avg delay 0-15m'),
                    mpatches.Patch(color=COLOR_GOOD,     label='Avg early')]
    ax2.legend(handles=legend_items, facecolor='#1a1a2e', edgecolor=SPINE_COLOR, labelcolor=WHITE, fontsize=8)

    plt.tight_layout()
    save_chart(fig, 'routes', tail, output_dir)


# ── SECTION 7: ANOMALOUS DAY INVESTIGATION ───────────────────────────────────

def chart_anomalous_days(plane, tail, carrier, output_dir):
    daily_legs = plane.groupby('FlightDate').size()
    avg_legs   = daily_legs.mean()
    low_days   = daily_legs[daily_legs < avg_legs * 0.6]

    print(f"\n  Anomalous day investigation:")
    print(f"    Avg legs per day : {avg_legs:.1f}")
    print(f"    Anomalous days   : {len(low_days)}")

    if len(low_days) == 0:
        print("    No anomalous days found.")
        return

    for date, count in low_days.items():
        day_data = plane[plane['FlightDate'] == date]
        print(f"\n    {date} — only {count} legs (vs avg {avg_legs:.1f})")
        for _, row in day_data.iterrows():
            arr = int(row['ArrTime']) if not pd.isna(row['ArrTime']) else 0
            print(f"      FL{int(row['Flight_Number_Operating_Airline'])} "
                  f"{row['Origin']}→{row['Dest']} "
                  f"dep {int(row['CRSDepTime']):04d} arr {arr:04d} "
                  f"ArrDelay: {row['ArrDelay']:+.0f}m")

    anom_date = low_days.index[0]
    anom_dt   = pd.to_datetime(anom_date)
    prev_date = (anom_dt - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    next_date = (anom_dt + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    three_days = plane[plane['FlightDate'].isin([prev_date, anom_date, next_date])]

    fig, ax = plt.subplots(figsize=(16, 5))
    style_fig(fig, f"{tail} ({carrier}) — Anomalous Day: {anom_date}")
    ax.set_facecolor(BG_COLOR)

    colors_day = {prev_date: COLOR_ACCENT, anom_date: COLOR_CRITICAL, next_date: COLOR_GOOD}
    y_pos      = {prev_date: 2, anom_date: 1, next_date: 0}
    y_labels   = {2: prev_date[-5:], 1: anom_date[-5:] + ' (anomaly)', 0: next_date[-5:]}

    def time_to_float(t):
        if pd.isna(t): return None
        t = int(t)
        return (t // 100) + (t % 100) / 60

    for date in [prev_date, anom_date, next_date]:
        day = three_days[three_days['FlightDate'] == date]
        y, col = y_pos[date], colors_day[date]
        for _, row in day.iterrows():
            dep = time_to_float(row['DepTime'] if not pd.isna(row['DepTime']) else row['CRSDepTime'])
            arr = time_to_float(row['ArrTime'] if not pd.isna(row['ArrTime']) else row['CRSArrTime'])
            if dep is None or arr is None: continue
            ax.barh(y, arr - dep, left=dep, height=0.4, color=col, alpha=0.8, zorder=3)
            ax.text(dep + (arr - dep)/2, y, f"{row['Origin']}→{row['Dest']}",
                    ha='center', va='center', fontsize=7, color=WHITE, fontweight='bold')

    anom_data = three_days[three_days['FlightDate'] == anom_date].sort_values('CRSDepTime')
    if len(anom_data) > 1:
        for i in range(len(anom_data) - 1):
            gap_start = time_to_float(anom_data.iloc[i]['ArrTime'])
            gap_end   = time_to_float(anom_data.iloc[i+1]['CRSDepTime'])
            if gap_start and gap_end and (gap_end - gap_start) > 2:
                ax.barh(1, gap_end - gap_start, left=gap_start, height=0.4,
                        color=COLOR_HIGHLIGHT, alpha=0.3, hatch='///', zorder=2)
                mid   = gap_start + (gap_end - gap_start) / 2
                dest  = anom_data.iloc[i]['Dest']
                orig  = anom_data.iloc[i+1]['Origin']
                label = f'{(gap_end - gap_start)*60:.0f}-min gap ({dest}→{orig}?)'
                ax.text(mid, 1.35, label, ha='center', color=COLOR_HIGHLIGHT, fontsize=7.5,
                        bbox=dict(boxstyle='round', facecolor='#222233', edgecolor=COLOR_HIGHLIGHT, alpha=0.9))

    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels([y_labels[i] for i in [0, 1, 2]], color=WHITE, fontsize=10)
    ax.set_xlabel('Time (local hours)', color=TEXT_COLOR)
    ax.set_xlim(0, 28)
    ax.set_xticks(range(0, 28, 2))
    ax.set_xticklabels([f'{h%24:02d}:00' for h in range(0, 28, 2)], color=TEXT_COLOR)
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ax.spines.values(): spine.set_edgecolor(SPINE_COLOR)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5, zorder=0)
    legend_items = [mpatches.Patch(color=COLOR_ACCENT,    label=f'{prev_date[-5:]} legs'),
                    mpatches.Patch(color=COLOR_CRITICAL,  label=f'{anom_date[-5:]} legs (anomaly)'),
                    mpatches.Patch(color=COLOR_GOOD,      label=f'{next_date[-5:]} legs'),
                    mpatches.Patch(color=COLOR_HIGHLIGHT, alpha=0.4, label='Unexplained gap')]
    ax.legend(handles=legend_items, loc='lower right', facecolor='#1a1a2e',
              edgecolor=SPINE_COLOR, labelcolor=WHITE, fontsize=8)

    plt.tight_layout()
    save_chart(fig, 'anomalous_day', tail, output_dir)


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print("\n" + "=" * 60)
    print("  DOT ON-TIME PERFORMANCE — AIRCRAFT ANALYZER")
    print("=" * 60)

    df = load_data()

    carrier        = select_carrier(df)
    tail, fleet    = select_tail(df, carrier)
    benchmarks     = compute_fleet_benchmarks(fleet)
    plane          = prepare_plane(fleet, tail)

    print_summary(plane, tail, carrier, benchmarks)
    print_rotation(plane, tail)

    print("\n\nGenerating charts...")
    output_dir = os.path.join(OUTPUT_DIR, f"{tail}_analysis")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Charts will be saved to: {output_dir}\n")

    chart_daily_delay(plane, tail, carrier, output_dir)
    chart_delay_causes(plane, tail, carrier, benchmarks, output_dir)
    chart_turnaround(plane, tail, carrier, output_dir)
    chart_cascade(plane, tail, carrier, output_dir)
    chart_routes(plane, tail, carrier, output_dir)
    chart_time_of_day(plane, tail, carrier, output_dir)
    chart_recovery(plane, tail, carrier, output_dir)
    chart_anomalous_days(plane, tail, carrier, output_dir)

    print("\n" + "=" * 60)
    print(f"  Analysis complete for {tail}")
    print(f"  Charts saved to: {output_dir}")
    print("=" * 60)



if __name__ == '__main__':
    main()