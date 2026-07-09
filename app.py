# app.py
# US Airline On-Time Performance Dashboard
# Streamlit app — runs locally against full dataset
# or on Streamlit Cloud against selected months

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os
import re
import sys
import json
import subprocess
from datetime import datetime

# ── PAGE CONFIG ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="US Airline On-Time Performance",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── DARK THEME STYLES ─────────────────────────────────────────────────────────

st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .metric-card {
        background-color: #1a1a2e;
        border: 1px solid #333344;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .metric-value { font-size: 28px; font-weight: bold; color: white; }
    .metric-label { font-size: 12px; color: #aaaaaa; margin-top: 4px; }
    .metric-delta { font-size: 13px; margin-top: 2px; }
    .good  { color: #00cc88; }
    .warn  { color: #ffcc00; }
    .bad   { color: #ff4444; }
</style>
""", unsafe_allow_html=True)

BG_COLOR    = '#0f1117'
GRID_COLOR  = '#222233'
SPINE_COLOR = '#333344'
TEXT_COLOR  = '#aaaaaa'
WHITE       = 'white'
COLOR_GOOD  = '#00cc88'
COLOR_WARN  = '#ffcc00'
COLOR_BAD   = '#ff8800'
COLOR_CRIT  = '#ff4444'

CARRIER_NAMES = {
    'AA': 'American Airlines',
    'DL': 'Delta Air Lines',
    'UA': 'United Airlines',
    'WN': 'Southwest Airlines',
    'AS': 'Alaska Airlines',
    'B6': 'JetBlue Airways',
    'F9': 'Frontier Airlines',
    'NK': 'Spirit Airlines',
    'G4': 'Allegiant Air',
    'HA': 'Hawaiian Airlines',
    'SY': 'Sun Country Airlines',
    'MX': 'Breeze Airways',
}

MONTH_NAMES = {
    1:'January', 2:'February', 3:'March', 4:'April',
    5:'May', 6:'June', 7:'July', 8:'August',
    9:'September', 10:'October', 11:'November', 12:'December'
}

HF_REPO_ID = "Babbi21SA/airline-otp-data"

AVAILABLE_MONTHS = [
    (2018, 1), (2018, 2), (2018, 3), (2018, 4), (2018, 5), (2018, 6),
    (2018, 7), (2018, 8), (2018, 9), (2018, 10), (2018, 11), (2018, 12),
    (2019, 1), (2019, 2), (2019, 3), (2019, 4), (2019, 5), (2019, 6),
    (2019, 7), (2019, 8), (2019, 9), (2019, 10), (2019, 11), (2019, 12),
    (2020, 1), (2020, 2), (2020, 3), (2020, 4), (2020, 5), (2020, 6),
    (2020, 7), (2020, 8), (2020, 9), (2020, 10), (2020, 11), (2020, 12),
    (2021, 1), (2021, 2), (2021, 3), (2021, 4), (2021, 5), (2021, 6),
    (2021, 7), (2021, 8), (2021, 9), (2021, 10), (2021, 11), (2021, 12),
    (2022, 1), (2022, 2), (2022, 3), (2022, 4), (2022, 5), (2022, 6),
    (2022, 7), (2022, 8), (2022, 9), (2022, 10), (2022, 11), (2022, 12),
    (2023, 1), (2023, 2), (2023, 3), (2023, 4), (2023, 5), (2023, 6),
    (2023, 7), (2023, 8), (2023, 9), (2023, 10), (2023, 11), (2023, 12),
    (2024, 1), (2024, 2), (2024, 3), (2024, 4), (2024, 5), (2024, 6),
    (2024, 7), (2024, 8), (2024, 9), (2024, 10), (2024, 11), (2024, 12),
    (2025, 1), (2025, 2), (2025, 3), (2025, 4), (2025, 5), (2025, 6),
    (2025, 7), (2025, 8), (2025, 9), (2025, 10), (2025, 11), (2025, 12),
    (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5),
]


# ── DATA LOADING ──────────────────────────────────────────────────────────────

def detect_environment():
    """Detect if running locally or on Streamlit Cloud."""
    local_clean = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\Clean"
    if os.path.exists(local_clean):
        return "local", local_clean
    return "cloud", None


@st.cache_data(show_spinner=False, ttl=86400)
def load_months_hf(selected_months):
    """Load specific months from Hugging Face with retry logic."""
    import io
    import requests
    frames = []
    failed = []
    
    print(f"[INFO] Loading {len(selected_months)} months from HF...")
    
    for i, (year, month) in enumerate(selected_months):
        month_name = MONTH_NAMES[month]
        filename = f"OTP_{year}_{month:02d}_{month_name}.csv"
        url = f"https://huggingface.co/datasets/{HF_REPO_ID}/resolve/main/Data/Clean/{filename}"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                df = pd.read_csv(io.StringIO(response.text), low_memory=False)
                df['Year']  = year
                df['Month'] = month
                frames.append(df)
                print(f"  [{i+1}/{len(selected_months)}] ✓ {filename}")
            else:
                failed.append(f"{filename} (HTTP {response.status_code})")
                print(f"  [{i+1}/{len(selected_months)}] ✗ {filename} (HTTP {response.status_code})")
        except requests.Timeout:
            failed.append(f"{filename} (timeout)")
            print(f"  [{i+1}/{len(selected_months)}] ✗ {filename} (timeout after 30s)")
        except Exception as e:
            failed.append(f"{filename} ({type(e).__name__})")
            print(f"  [{i+1}/{len(selected_months)}] ✗ {filename}: {type(e).__name__}")

    if not frames:
        print(f"[ERROR] Failed to load ANY files. All {len(failed)} failed.")
        return pd.DataFrame()
    
    print(f"[INFO] Successfully loaded {len(frames)}/{len(selected_months)} months")
    
    combined = pd.concat(frames, ignore_index=True)
    combined['FlightDate'] = pd.to_datetime(combined['FlightDate'], errors='coerce')
    combined['Carrier'] = combined['Carrier'].astype(str).str.strip()
    
    if failed:
        print(f"[WARN] {len(failed)} files failed to load (will continue with {len(frames)} months)")
    
    return combined


@st.cache_data(show_spinner=False, ttl=86400)
def get_available_months(clean_dir):
    """List all available year/month combinations."""
    months = []
    for f in sorted(os.listdir(clean_dir)):
        m = re.match(r"OTP_(\d{4})_(\d{2})_", f)
        if m:
            months.append((int(m.group(1)), int(m.group(2))))
    return sorted(months)


@st.cache_data(show_spinner=False, ttl=86400)
def load_months(clean_dir, selected_months):
    """Load specific months from clean files."""
    frames = []
    for year, month in selected_months:
        month_name = MONTH_NAMES[month]
        path = os.path.join(clean_dir, f"OTP_{year}_{month:02d}_{month_name}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path, low_memory=False)
            df['Year']  = year
            df['Month'] = month
            frames.append(df)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    combined['FlightDate'] = pd.to_datetime(combined['FlightDate'], errors='coerce')
    combined['Carrier'] = combined['Carrier'].astype(str).str.strip()
    return combined


# ── CHART HELPERS ─────────────────────────────────────────────────────────────

def style_fig(fig):
    fig.patch.set_facecolor(BG_COLOR)


def style_ax(ax):
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors=TEXT_COLOR)
    for spine in ax.spines.values():
        spine.set_edgecolor(SPINE_COLOR)
    ax.yaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    ax.set_axisbelow(True)


# ── METRIC CARDS ──────────────────────────────────────────────────────────────

def metric_card(label, value, delta=None, good_direction="high"):
    if delta is not None:
        if (good_direction == "high" and delta > 0) or \
           (good_direction == "low"  and delta < 0):
            delta_class = "good"
            delta_str = f"▲ {abs(delta):.1f}"
        elif delta == 0:
            delta_class = "warn"
            delta_str = "— unchanged"
        else:
            delta_class = "bad"
            delta_str = f"▼ {abs(delta):.1f}"
        delta_html = f'<div class="metric-delta {delta_class}">{delta_str}</div>'
    else:
        delta_html = ""

    return f"""
    <div class="metric-card">
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {delta_html}
    </div>
    """


# ── PAGE 1: OVERVIEW ─────────────────────────────────────────────────────────

def page_overview(df):
    st.header("📊 Fleet Overview")

    if df.empty:
        st.warning("No data loaded. Adjust your filters.")
        return

    operated = df[df['Cancelled'] == 0]

    # Carrier filter
    carriers = sorted(df['Carrier'].unique())
    carrier_display = [f"{c} — {CARRIER_NAMES.get(c, c)}" for c in carriers]
    selected_display = st.multiselect(
        "Filter by Carrier (leave empty for all)",
        options=carrier_display,
        default=[]
    )
    if selected_display:
        selected_carriers = [d.split(' — ')[0] for d in selected_display]
        df = df[df['Carrier'].isin(selected_carriers)]
        operated = df[df['Cancelled'] == 0]

    # Metric cards
    total       = len(df)
    on_time     = (operated['ArrDelay'] <= 15).mean() * 100
    avg_delay   = operated['ArrDelay'].mean()
    cancel_rate = df['Cancelled'].mean() * 100
    diverts     = df['Diverted'].sum()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(metric_card("Total Flights", f"{total:,.0f}"),
                    unsafe_allow_html=True)
    with c2:
        st.markdown(metric_card("On-Time Rate", f"{on_time:.1f}%"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Avg Arrival Delay", f"{avg_delay:.1f}m"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Cancellation Rate", f"{cancel_rate:.2f}%"),
                    unsafe_allow_html=True)
    with c5:
        st.markdown(metric_card("Diversions", f"{int(diverts):,}"),
                    unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    # Monthly on-time rate chart
    with col1:
        st.subheader("Monthly On-Time Rate")
        monthly = df.groupby(['Year', 'Month']).agg(
            on_time_rate=('ArrDelay', lambda x: (x <= 15).mean() * 100),
            flights=('FlightDate', 'count')
        ).reset_index()
        monthly['label'] = monthly.apply(
            lambda r: f"{MONTH_NAMES[int(r['Month'])][:3]}\n{int(r['Year'])}",
            axis=1
        )

        fig, ax = plt.subplots(figsize=(8, 4))
        style_fig(fig); style_ax(ax)
        colors = [COLOR_GOOD if v >= 80 else COLOR_WARN if v >= 75
                  else COLOR_BAD for v in monthly['on_time_rate']]
        ax.bar(range(len(monthly)), monthly['on_time_rate'],
               color=colors, width=0.7, zorder=3)
        ax.axhline(79, color=WHITE, linewidth=0.8, linestyle='--', alpha=0.4)
        ax.set_xticks(range(len(monthly)))
        ax.set_xticklabels(monthly['label'], fontsize=7)
        ax.set_ylabel('On-Time Rate (%)', color=TEXT_COLOR)
        ax.set_ylim(60, 100)
        ax.tick_params(axis='x', colors=TEXT_COLOR)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close()

    # Carrier breakdown table
    with col2:
        st.subheader("Carrier Performance Summary")
        carrier_summary = df.groupby('Carrier').agg(
            Flights        = ('FlightDate', 'count'),
            On_Time_Rate   = ('ArrDelay', lambda x: f"{(x <= 15).mean()*100:.1f}%"),
            Avg_Delay      = ('ArrDelay', lambda x: f"{x.mean():.1f}m"),
            Cancel_Rate    = ('Cancelled', lambda x: f"{x.mean()*100:.2f}%"),
        ).reset_index()
        carrier_summary['Carrier Name'] = carrier_summary['Carrier'].map(
            lambda c: CARRIER_NAMES.get(c, c)
        )
        carrier_summary = carrier_summary.rename(columns={
            'Carrier': 'Code',
            'On_Time_Rate': 'On-Time %',
            'Avg_Delay': 'Avg Delay',
            'Cancel_Rate': 'Cancel %'
        })
        carrier_summary['Flights'] = carrier_summary['Flights'].apply(lambda x: f"{x:,}")
        st.dataframe(
            carrier_summary[['Code', 'Carrier Name', 'Flights',
                              'On-Time %', 'Avg Delay', 'Cancel %']],
            use_container_width=True, hide_index=True
        )

    # Monthly avg delay line chart
    st.subheader("Monthly Average Arrival Delay")
    monthly2 = df.groupby(['Year', 'Month', 'Carrier']).agg(
        avg_delay=('ArrDelay', 'mean')
    ).reset_index()

    fig2, ax2 = plt.subplots(figsize=(14, 4))
    style_fig(fig2); style_ax(ax2)

    all_monthly = df.groupby(['Year', 'Month']).agg(
        avg_delay=('ArrDelay', 'mean')
    ).reset_index()
    all_monthly['label'] = all_monthly.apply(
        lambda r: f"{MONTH_NAMES[int(r['Month'])][:3]} {int(r['Year'])}", axis=1
    )

    ax2.plot(range(len(all_monthly)), all_monthly['avg_delay'],
             color='#4488ff', linewidth=2, marker='o', markersize=4, zorder=3)
    ax2.axhline(0,  color=WHITE,    linewidth=0.8, linestyle='--', alpha=0.3)
    ax2.axhline(15, color=COLOR_CRIT, linewidth=0.8, linestyle=':', alpha=0.5)
    ax2.fill_between(range(len(all_monthly)), 0, all_monthly['avg_delay'],
                     alpha=0.15, color='#4488ff')
    ax2.set_xticks(range(len(all_monthly)))
    ax2.set_xticklabels(all_monthly['label'], rotation=45, fontsize=7)
    ax2.set_ylabel('Avg Arrival Delay (mins)', color=TEXT_COLOR)
    ax2.tick_params(axis='x', colors=TEXT_COLOR)
    fig2.tight_layout()
    st.pyplot(fig2)
    plt.close()


# ── PAGE 2: ROUTE EXPLORER ────────────────────────────────────────────────────

def page_routes(df):
    st.header("🗺 Route Explorer")

    if df.empty:
        st.warning("No data loaded.")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        carriers = ['All'] + sorted(df['Carrier'].unique())
        selected_carrier = st.selectbox("Carrier", carriers)
    with col2:
        all_origins = ['All'] + sorted(df['Origin'].unique())
        selected_origin = st.selectbox("Origin Airport", all_origins)
    with col3:
        all_dests = ['All'] + sorted(df['Dest'].unique())
        selected_dest = st.selectbox("Destination Airport", all_dests)

    filtered = df.copy()
    if selected_carrier != 'All':
        filtered = filtered[filtered['Carrier'] == selected_carrier]
    if selected_origin != 'All':
        filtered = filtered[filtered['Origin'] == selected_origin]
    if selected_dest != 'All':
        filtered = filtered[filtered['Dest'] == selected_dest]

    filtered['Route'] = filtered['Origin'] + ' → ' + filtered['Dest']
    operated = filtered[filtered['Cancelled'] == 0]

    st.markdown(f"**{len(filtered):,} flights** match your filters")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Top Routes by Volume")
        route_table = operated.groupby('Route').agg(
            Flights      = ('ArrDelay', 'count'),
            On_Time_Rate = ('ArrDelay', lambda x: f"{(x <= 15).mean()*100:.1f}%"),
            Avg_Delay    = ('ArrDelay', lambda x: f"{x.mean():.1f}m"),
            Avg_Distance = ('Distance', 'mean') if 'Distance' in operated.columns
                           else ('ArrDelay', lambda x: 0)
        ).sort_values('Flights', ascending=False).head(20).reset_index()
        route_table['Flights'] = route_table['Flights'].apply(lambda x: f"{x:,}")
        st.dataframe(route_table, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Top 15 Airports by Traffic")
        visits = pd.concat([filtered['Origin'], filtered['Dest']]).value_counts().head(15)

        fig, ax = plt.subplots(figsize=(6, 5))
        style_fig(fig); style_ax(ax)
        colors = [COLOR_CRIT if c >= 50000 else COLOR_BAD if c >= 20000
                  else COLOR_WARN if c >= 10000 else COLOR_GOOD
                  for c in visits.values]
        ax.barh(visits.index[::-1], visits.values[::-1],
                color=colors[::-1], zorder=3)
        for i, (airport, count) in enumerate(
                zip(visits.index[::-1], visits.values[::-1])):
            ax.text(count + 100, i, f"{count:,}", va='center',
                    color=WHITE, fontsize=7)
        ax.set_xlabel('Total Visits', color=TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR)
        ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close()


# ── PAGE 3: CARRIER COMPARISON ────────────────────────────────────────────────

def page_carrier_comparison(df):
    st.header("📈 Carrier Comparison")

    if df.empty:
        st.warning("No data loaded.")
        return

    carriers = sorted(df['Carrier'].unique())
    carrier_options = [f"{c} — {CARRIER_NAMES.get(c, c)}" for c in carriers]

    selected = st.multiselect(
        "Select carriers to compare (2–4 recommended)",
        options=carrier_options,
        default=carrier_options[:2] if len(carrier_options) >= 2 else carrier_options
    )

    if len(selected) < 2:
        st.info("Select at least 2 carriers to compare.")
        return

    selected_codes = [s.split(' — ')[0] for s in selected]
    filtered = df[df['Carrier'].isin(selected_codes)]
    operated = filtered[filtered['Cancelled'] == 0]

    # Build comparison table
    rows = []
    for code in selected_codes:
        c_data = filtered[filtered['Carrier'] == code]
        c_op   = c_data[c_data['Cancelled'] == 0]
        late_dep = c_op[c_op['DepDelay'] > 0].copy()
        late_dep['made_up'] = late_dep['DepDelay'] - late_dep['ArrDelay']
        rows.append({
            'Carrier'        : f"{code} — {CARRIER_NAMES.get(code, code)}",
            'Flights'        : f"{len(c_data):,}",
            'On-Time Rate'   : f"{(c_op['ArrDelay'] <= 15).mean()*100:.1f}%",
            'Avg Delay'      : f"{c_op['ArrDelay'].mean():.1f}m",
            'Cancel Rate'    : f"{c_data['Cancelled'].mean()*100:.2f}%",
            'Divert Rate'    : f"{c_data['Diverted'].mean()*100:.3f}%",
            'Recovery Rate'  : f"{(late_dep['made_up'] > 0).mean()*100:.1f}%"
                                if len(late_dep) > 0 else 'N/A',
        })

    comp_df = pd.DataFrame(rows)
    st.subheader("Head-to-Head Metrics")
    st.dataframe(comp_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Monthly on-time rate comparison chart
    st.subheader("Monthly On-Time Rate by Carrier")
    monthly = filtered.groupby(['Year', 'Month', 'Carrier']).agg(
        on_time_rate=('ArrDelay', lambda x: (x <= 15).mean() * 100)
    ).reset_index()

    fig, ax = plt.subplots(figsize=(14, 5))
    style_fig(fig); style_ax(ax)

    palette = ['#ff8800', '#0066cc', '#00cc88', '#ff4444',
               '#aa44ff', '#ffcc00', '#4488ff']

    all_periods = sorted(monthly[['Year', 'Month']].drop_duplicates().values.tolist())
    period_labels = [f"{MONTH_NAMES[m][:3]}\n{y}" for y, m in all_periods]
    x = range(len(all_periods))

    for i, code in enumerate(selected_codes):
        c_monthly = monthly[monthly['Carrier'] == code].copy()
        c_monthly['period_idx'] = c_monthly.apply(
            lambda r: all_periods.index([int(r['Year']), int(r['Month'])]), axis=1
        )
        ax.plot(c_monthly['period_idx'], c_monthly['on_time_rate'],
                color=palette[i % len(palette)], linewidth=2,
                marker='o', markersize=4,
                label=f"{code} — {CARRIER_NAMES.get(code, code)}", zorder=3)

    ax.axhline(79, color=WHITE, linewidth=0.8, linestyle='--', alpha=0.3)
    ax.set_xticks(list(x))
    ax.set_xticklabels(period_labels, fontsize=7)
    ax.set_ylabel('On-Time Rate (%)', color=TEXT_COLOR)
    ax.set_ylim(55, 100)
    ax.tick_params(axis='x', colors=TEXT_COLOR)
    ax.legend(facecolor='#1a1a2e', edgecolor=SPINE_COLOR,
              labelcolor=WHITE, fontsize=8)
    ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close()


# ── PAGE 4: AIRCRAFT TRACKER ──────────────────────────────────────────────────

def page_aircraft_tracker(df):
    st.header("🛩 Aircraft Tracker")

    if df.empty:
        st.warning("No data loaded.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        carrier_filter = st.selectbox(
            "Carrier",
            ['All'] + sorted(df['Carrier'].unique())
        )
    with col2:
        if carrier_filter != 'All':
            fleet = df[df['Carrier'] == carrier_filter]
        else:
            fleet = df

        top_tails = fleet['TailNumber'].value_counts().head(50).index.tolist()
        tail_input = st.selectbox(
            "Tail Number (top 50 by flights)",
            options=top_tails
        )

    if not tail_input:
        st.info("Select a tail number to begin tracking.")
        return

    plane = fleet[fleet['TailNumber'] == tail_input].sort_values(
        ['FlightDate', 'SchedDep']
    ).reset_index(drop=True)

    operated = plane[plane['Cancelled'] == 0]

    st.markdown(f"**Tracking {tail_input}** — "
                f"{len(plane)} legs across "
                f"{plane['FlightDate'].dt.date.nunique()} days")

    # Metric cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(metric_card("Total Legs", f"{len(plane)}"),
                    unsafe_allow_html=True)
    with c2:
        ot = (operated['ArrDelay'] <= 15).mean() * 100
        st.markdown(metric_card("On-Time Rate", f"{ot:.1f}%"),
                    unsafe_allow_html=True)
    with c3:
        st.markdown(metric_card("Cancellations", f"{int(plane['Cancelled'].sum())}"),
                    unsafe_allow_html=True)
    with c4:
        st.markdown(metric_card("Diversions", f"{int(plane['Diverted'].sum())}"),
                    unsafe_allow_html=True)

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        # Daily delay chart
        st.subheader("Daily Average Delay")
        daily = plane.groupby('FlightDate').agg(
            legs=('FlightDate', 'count'),
            avg_delay=('ArrDelay', 'mean'),
            diversions=('Diverted', 'sum')
        ).reset_index()

        fig, ax = plt.subplots(figsize=(8, 4))
        style_fig(fig); style_ax(ax)
        colors = [COLOR_CRIT if row['diversions'] > 0
                  else COLOR_BAD if row['avg_delay'] >= 30
                  else COLOR_WARN if row['avg_delay'] >= 0
                  else COLOR_GOOD for _, row in daily.iterrows()]
        ax.bar(range(len(daily)), daily['avg_delay'],
               color=colors, width=0.7, zorder=3)
        ax.axhline(0,  color=WHITE,    linewidth=0.8, linestyle='--', alpha=0.4)
        ax.axhline(15, color=COLOR_CRIT, linewidth=0.8, linestyle=':', alpha=0.5)
        dates = [str(d)[-5:] for d in daily['FlightDate'].dt.date]
        tick_indices = []
        tick_labels  = []
        seen_months  = set()
        for i, d in enumerate(daily['FlightDate'].dt.to_period('M')):
            if d not in seen_months:
                seen_months.add(d)
                tick_indices.append(i)
                tick_labels.append(str(d))
        ax.set_xticks(tick_indices)
        ax.set_xticklabels(tick_labels, rotation=45, fontsize=7)
        ax.set_ylabel('Avg Arrival Delay (mins)', color=TEXT_COLOR)
        ax.tick_params(axis='x', colors=TEXT_COLOR)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col2:
        # Delay cause breakdown
        st.subheader("Delay Cause Breakdown")
        cause_cols = {
            'Carrier' : 'CarrierDelay',
            'Late AC' : 'LateAircraftDelay',
            'NAS'     : 'NASDelay',
            'Weather' : 'WeatherDelay',
            'Security': 'SecurityDelay',
        }
        causes = {}
        for label, col in cause_cols.items():
            if col in operated.columns:
                val = operated[col].sum()
                if val > 0:
                    causes[label] = val

        if len(causes) > 1:
            fig2, ax2 = plt.subplots(figsize=(5, 4))
            style_fig(fig2)
            ax2.set_facecolor(BG_COLOR)
            colors_pie = [COLOR_CRIT, COLOR_BAD, COLOR_WARN,
                          '#4488ff', '#aa44ff']
            wedges, texts, autotexts = ax2.pie(
                list(causes.values()),
                labels=list(causes.keys()),
                autopct='%1.1f%%',
                colors=colors_pie[:len(causes)],
                textprops={'color': WHITE, 'fontsize': 10}
            )
            for autotext in autotexts:
                autotext.set_color(WHITE)
            fig2.tight_layout()
            st.pyplot(fig2)
            plt.close()
        elif len(causes) == 1:
            label, val = list(causes.items())[0]
            st.info(f"All recorded delay minutes attributed to: **{label}** "
                    f"({val:,.0f} mins).")
        else:
            st.info("No delay cause columns found.")

    # Rotation table
    st.subheader("Full Rotation")
    show_cols = ['FlightDate', 'FlightNumber', 'Origin', 'Dest',
                 'SchedDep', 'ActualDep', 'DepDelay',
                 'SchedArr', 'ActualArr', 'ArrDelay',
                 'Cancelled', 'Diverted', 'LateAircraftDelay']
    show_cols = [c for c in show_cols if c in plane.columns]
    display_df = plane[show_cols].copy()
    display_df['FlightDate'] = display_df['FlightDate'].dt.date
    st.dataframe(
        display_df.rename(columns={
            'FlightDate': 'Date', 'FlightNumber': 'FL#',
            'SchedDep': 'Sched Dep', 'ActualDep': 'Act Dep',
            'SchedArr': 'Sched Arr', 'ActualArr': 'Act Arr',
        }),
        use_container_width=True, hide_index=True
    )


# ── PAGE 5: DELAY ANALYSIS ───────────────────────────────────────────────────

def page_delay_analysis(df):
    st.header("⏱ Delay Analysis")

    if df.empty:
        st.warning("No data loaded.")
        return

    # Carrier filter
    carriers = ['All'] + sorted(df['Carrier'].unique())
    selected_carrier = st.selectbox("Filter by Carrier", carriers)
    if selected_carrier != 'All':
        df = df[df['Carrier'] == selected_carrier]

    operated = df[df['Cancelled'] == 0]

    st.markdown("---")

    # ── Row 1: Delay cause breakdown ─────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Delay Cause Breakdown")
        cause_cols = {
            'Carrier'  : 'CarrierDelay',
            'Late AC'  : 'LateAircraftDelay',
            'NAS'      : 'NASDelay',
            'Weather'  : 'WeatherDelay',
            'Security' : 'SecurityDelay',
        }
        causes = {}
        for label, col in cause_cols.items():
            if col in operated.columns:
                val = operated[col].sum()
                if val > 0:
                    causes[label] = val

        if causes:
            fig, ax = plt.subplots(figsize=(6, 5))
            style_fig(fig)
            ax.set_facecolor(BG_COLOR)
            colors_pie = [COLOR_CRIT, COLOR_BAD, COLOR_WARN, '#4488ff', '#aa44ff']
            wedges, texts, autotexts = ax.pie(
                list(causes.values()),
                labels=list(causes.keys()),
                autopct='%1.1f%%',
                colors=colors_pie[:len(causes)],
                textprops={'color': WHITE, 'fontsize': 11}
            )
            for a in autotexts:
                a.set_color(WHITE)
            total_mins = sum(causes.values())
            ax.set_title(f"Total: {total_mins:,.0f} delay minutes",
                         color=TEXT_COLOR, fontsize=9)
            fig.tight_layout()
            st.pyplot(fig)
            plt.close()

            # Table version
            cause_df = pd.DataFrame([
                {'Cause': k, 'Total Mins': f"{v:,.0f}",
                 'Share': f"{v/total_mins*100:.1f}%"}
                for k, v in sorted(causes.items(),
                                    key=lambda x: x[1], reverse=True)
            ])
            st.dataframe(cause_df, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Time of Day Performance")
        operated2 = df[df['Cancelled'] == 0].copy()
        operated2['dep_hour'] = (
            operated2['SchedDep'].astype(str).str.zfill(4).str[:2]
        )
        operated2['dep_hour'] = pd.to_numeric(
            operated2['dep_hour'], errors='coerce'
        )
        operated2 = operated2.dropna(subset=['dep_hour'])
        operated2['dep_hour'] = operated2['dep_hour'].astype(int)
        operated2 = operated2[operated2['dep_hour'] < 24]

        hourly = operated2.groupby('dep_hour').agg(
            legs         = ('ArrDelay', 'count'),
            avg_delay    = ('ArrDelay', 'mean'),
            on_time_rate = ('ArrDelay', lambda x: (x <= 15).mean() * 100)
        ).reset_index()

        fig2, ax2 = plt.subplots(figsize=(6, 5))
        style_fig(fig2); style_ax(ax2)
        colors_h = [COLOR_GOOD if d <= 0 else COLOR_WARN if d <= 15
                    else COLOR_BAD if d <= 30 else COLOR_CRIT
                    for d in hourly['avg_delay']]
        ax2.bar([f"{h:02d}:xx" for h in hourly['dep_hour']],
                hourly['avg_delay'], color=colors_h, width=0.7, zorder=3)
        ax2.axhline(0,  color=WHITE,    linewidth=0.8, linestyle='--', alpha=0.4)
        ax2.axhline(15, color=COLOR_CRIT, linewidth=0.8, linestyle=':', alpha=0.5)
        ax2.set_ylabel('Avg Arrival Delay (mins)', color=TEXT_COLOR)
        ax2.tick_params(axis='x', rotation=45, colors=TEXT_COLOR, labelsize=7)
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close()

    st.markdown("---")

    # ── Row 2: Delay by day of week ───────────────────────────────────────────
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Delay by Day of Week")
        operated3 = df[df['Cancelled'] == 0].copy()
        operated3['DayOfWeek'] = operated3['FlightDate'].dt.day_name()
        day_order = ['Monday','Tuesday','Wednesday','Thursday',
                     'Friday','Saturday','Sunday']
        dow = operated3.groupby('DayOfWeek').agg(
            avg_delay    = ('ArrDelay', 'mean'),
            on_time_rate = ('ArrDelay', lambda x: (x <= 15).mean() * 100)
        ).reindex(day_order).reset_index()

        fig3, ax3 = plt.subplots(figsize=(6, 4))
        style_fig(fig3); style_ax(ax3)
        colors_d = [COLOR_GOOD if d <= 0 else COLOR_WARN if d <= 10
                    else COLOR_BAD if d <= 20 else COLOR_CRIT
                    for d in dow['avg_delay']]
        ax3.bar(range(len(dow)), dow['avg_delay'],
                color=colors_d, width=0.6, zorder=3)
        ax3.axhline(0,  color=WHITE,    linewidth=0.8, linestyle='--', alpha=0.4)
        ax3.axhline(15, color=COLOR_CRIT, linewidth=0.8, linestyle=':', alpha=0.5)
        ax3.set_xticks(range(len(dow)))
        ax3.set_xticklabels([d[:3] for d in dow['DayOfWeek']],
                             color=TEXT_COLOR)
        ax3.set_ylabel('Avg Arrival Delay (mins)', color=TEXT_COLOR)
        fig3.tight_layout()
        st.pyplot(fig3)
        plt.close()

    with col4:
        st.subheader("Leg Position in Day")
        operated4 = df[df['Cancelled'] == 0].copy()
        operated4['leg_num'] = operated4.groupby(
            ['TailNumber', operated4['FlightDate'].dt.date]
        ).cumcount() + 1

        leg_pos = operated4[operated4['leg_num'] <= 8].groupby('leg_num').agg(
            count     = ('ArrDelay', 'count'),
            avg_delay = ('ArrDelay', 'mean'),
            on_time   = ('ArrDelay', lambda x: (x <= 15).mean() * 100)
        ).reset_index()

        fig4, axes4 = plt.subplots(2, 1, figsize=(6, 5))
        style_fig(fig4)

        ax4a = axes4[0]
        style_ax(ax4a)
        colors4 = [COLOR_GOOD if v >= 80 else COLOR_WARN if v >= 70
                   else COLOR_BAD for v in leg_pos['on_time']]
        ax4a.bar(range(len(leg_pos)), leg_pos['on_time'],
                 color=colors4, width=0.6, zorder=3)
        ax4a.axhline(79, color=WHITE, linewidth=0.8, linestyle='--', alpha=0.4)
        ax4a.set_xticks(range(len(leg_pos)))
        ax4a.set_xticklabels([f"Leg {int(p)}" for p in leg_pos['leg_num']],
                              color=TEXT_COLOR, fontsize=8)
        ax4a.set_ylabel('On-time %', color=TEXT_COLOR, fontsize=8)
        ax4a.set_ylim(50, 100)

        ax4b = axes4[1]
        style_ax(ax4b)
        colors4b = [COLOR_GOOD if d <= 0 else COLOR_WARN if d <= 10
                    else COLOR_BAD for d in leg_pos['avg_delay']]
        ax4b.bar(range(len(leg_pos)), leg_pos['avg_delay'],
                 color=colors4b, width=0.6, zorder=3)
        ax4b.axhline(0,  color=WHITE,    linewidth=0.8, linestyle='--', alpha=0.4)
        ax4b.axhline(15, color=COLOR_CRIT, linewidth=0.8, linestyle=':', alpha=0.5)
        ax4b.set_xticks(range(len(leg_pos)))
        ax4b.set_xticklabels([f"Leg {int(p)}" for p in leg_pos['leg_num']],
                              color=TEXT_COLOR, fontsize=8)
        ax4b.set_ylabel('Avg Delay (mins)', color=TEXT_COLOR, fontsize=8)

        fig4.tight_layout()
        st.pyplot(fig4)
        plt.close()

    st.markdown("---")

    # ── Row 3: Monthly cancellation rate ─────────────────────────────────────
    st.subheader("Monthly Cancellation Rate")
    monthly_cancel = df.groupby(['Year', 'Month']).agg(
        cancel_rate = ('Cancelled', lambda x: x.mean() * 100),
        flights     = ('Cancelled', 'count')
    ).reset_index()
    monthly_cancel['label'] = monthly_cancel.apply(
        lambda r: f"{MONTH_NAMES[int(r['Month'])][:3]}\n{int(r['Year'])}",
        axis=1
    )

    fig5, ax5 = plt.subplots(figsize=(14, 3))
    style_fig(fig5); style_ax(ax5)
    colors5 = [COLOR_CRIT if v > 3 else COLOR_BAD if v > 1.5
               else COLOR_WARN if v > 0.5 else COLOR_GOOD
               for v in monthly_cancel['cancel_rate']]
    ax5.bar(range(len(monthly_cancel)), monthly_cancel['cancel_rate'],
            color=colors5, width=0.7, zorder=3)
    ax5.axhline(1.5, color=WHITE, linewidth=0.8, linestyle='--', alpha=0.4)
    ax5.set_xticks(range(len(monthly_cancel)))
    ax5.set_xticklabels(monthly_cancel['label'], fontsize=7)
    ax5.set_ylabel('Cancellation Rate (%)', color=TEXT_COLOR)
    ax5.tick_params(axis='x', colors=TEXT_COLOR)
    fig5.tight_layout()
    st.pyplot(fig5)
    plt.close()


# ── PAGE 6: NETWORK MAP ───────────────────────────────────────────────────────

def page_network_map(df):
    st.header("🌐 Network Map")

    if df.empty:
        st.warning("No data loaded.")
        return

    col1, col2 = st.columns([1, 2])
    with col1:
        carriers = ['All'] + sorted(df['Carrier'].unique())
        selected_carrier = st.selectbox("Filter by Carrier", carriers,
                                         key="network_carrier")
    with col2:
        top_n = st.slider("Top N airports to show", 10, 50, 25)

    if selected_carrier != 'All':
        df = df[df['Carrier'] == selected_carrier]

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Top {top_n} Airports by Traffic")
        visits = pd.concat([df['Origin'], df['Dest']]).value_counts().head(top_n)

        fig, ax = plt.subplots(figsize=(6, top_n * 0.3 + 1))
        style_fig(fig); style_ax(ax)
        max_v = visits.values[0]
        colors_ap = [COLOR_CRIT if v >= max_v * 0.8
                     else COLOR_BAD if v >= max_v * 0.5
                     else COLOR_WARN if v >= max_v * 0.25
                     else COLOR_GOOD for v in visits.values]
        ax.barh(visits.index[::-1], visits.values[::-1],
                color=colors_ap[::-1], zorder=3)
        for i, (ap, count) in enumerate(
                zip(visits.index[::-1], visits.values[::-1])):
            ax.text(count + max_v * 0.005, i, f"{count:,}",
                    va='center', color=WHITE, fontsize=7)
        ax.set_xlabel('Total Visits (dep + arr)', color=TEXT_COLOR)
        ax.tick_params(colors=TEXT_COLOR, labelsize=8)
        ax.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
        fig.tight_layout()
        st.pyplot(fig)
        plt.close()

    with col2:
        st.subheader("Route Performance — Most Flown Routes")
        operated = df[df['Cancelled'] == 0].copy()
        operated['Route'] = operated['Origin'] + ' → ' + operated['Dest']

        route_perf = operated.groupby('Route').agg(
            Flights      = ('ArrDelay', 'count'),
            Avg_Delay    = ('ArrDelay', 'mean'),
            On_Time_Rate = ('ArrDelay', lambda x: (x <= 15).mean() * 100),
        ).sort_values('Flights', ascending=False).head(30).reset_index()

        fig2, ax2 = plt.subplots(figsize=(6, 8))
        style_fig(fig2); style_ax(ax2)
        colors_r = [COLOR_CRIT if d > 15 else COLOR_WARN if d > 5
                    else COLOR_GOOD for d in route_perf['Avg_Delay']]
        ax2.barh(route_perf['Route'][::-1],
                 route_perf['Avg_Delay'][::-1],
                 color=colors_r[::-1], zorder=3)
        ax2.axvline(0,  color=WHITE,    linewidth=0.8, linestyle='--', alpha=0.4)
        ax2.axvline(15, color=COLOR_CRIT, linewidth=0.8, linestyle=':', alpha=0.5)
        ax2.set_xlabel('Avg Arrival Delay (mins)', color=TEXT_COLOR)
        ax2.tick_params(colors=TEXT_COLOR, labelsize=7)
        ax2.xaxis.grid(True, color=GRID_COLOR, linewidth=0.5)
        fig2.tight_layout()
        st.pyplot(fig2)
        plt.close()

    st.markdown("---")

    # Route performance table
    st.subheader("Full Route Performance Table")
    route_table = operated.groupby('Route').agg(
        Flights      = ('ArrDelay', 'count'),
        On_Time_Rate = ('ArrDelay', lambda x: f"{(x <= 15).mean()*100:.1f}%"),
        Avg_Delay    = ('ArrDelay', lambda x: f"{x.mean():.1f}m"),
        Max_Delay    = ('ArrDelay', lambda x: f"{x.max():.0f}m"),
    ).sort_values('Flights', ascending=False).reset_index()

    df2 = df.copy()
    df2['Route'] = df2['Origin'] + ' → ' + df2['Dest']
    cancel_rates = df2.groupby('Route')['Cancelled'].mean() * 100
    route_table['Cancel_Rate'] = route_table['Route'].map(
        lambda r: f"{cancel_rates.get(r, 0):.2f}%"
    )

    route_table['Flights'] = route_table['Flights'].apply(lambda x: f"{x:,}")

    st.dataframe(
        route_table.rename(columns={
            'On_Time_Rate': 'On-Time %',
            'Avg_Delay'   : 'Avg Delay',
            'Max_Delay'   : 'Max Delay',
            'Cancel_Rate' : 'Cancel %',
        }),
        use_container_width=True, hide_index=True
    )

def page_hub_analysis(df):
    st.header("🏢 Hub Analysis")
    
    # Top airports by total visits
    visits = pd.concat([df['Origin'], df['Dest']]).value_counts().head(20)
    
    # Hub concentration (top 10 airports handle what % of traffic?)
    total = len(df) * 2  # each flight counted twice (origin + dest)
    concentration = (visits.head(10).sum() / total) * 100
    
    # Route density (how many routes per airport?)
    routes_per_origin = df.groupby('Origin')['Dest'].nunique()
    
    # Visualize
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(visits.index[::-1], visits.values[::-1])
    st.pyplot(fig)
    
    # Metrics
    st.metric("Hub Concentration (Top 10)", f"{concentration:.1f}%")
    st.metric("Total Unique Routes", f"{df.groupby(['Origin', 'Dest']).ngroups:,}")

def page_seasonal_trends(df):
    st.header("🍂 Seasonal Trends")
    
    # Add season column
    df['Month'] = df['FlightDate'].dt.month
    df['Season'] = df['Month'].apply(lambda m: 
        'Winter' if m in [12, 1, 2] else
        'Spring' if m in [3, 4, 5] else
        'Summer' if m in [6, 7, 8] else 'Fall'
    )
    
    # Seasonal metrics
    seasonal = df.groupby('Season').agg({
        'ArrDelay': ['mean', lambda x: (x <= 15).mean() * 100],
        'Cancelled': lambda x: x.mean() * 100,
        'FlightDate': 'count'
    })
    
    # Charts
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    seasonal_data = df.groupby('Season')['ArrDelay'].mean()
    ax1.bar(seasonal_data.index, seasonal_data.values)
    ax1.set_title('Avg Delay by Season')
    
    # Table
    st.dataframe(seasonal)

def page_route_optimization(df):
    st.header("🛫 Route Optimization")
    
    df['Route'] = df['Origin'] + ' → ' + df['Dest']
    
    # Route performance ranking
    route_stats = df.groupby('Route').agg({
        'FlightDate': 'count',
        'ArrDelay': 'mean',
        'Cancelled': lambda x: x.mean() * 100,
        'Distance': 'first'
    }).rename(columns={'FlightDate': 'Flights'})
    
    route_stats['OnTimeRate'] = (df.groupby('Route')['ArrDelay'].apply(
        lambda x: (x <= 15).mean() * 100
    ))
    
    # Sort by worst performing
    worst = route_stats[route_stats['Flights'] > 100].sort_values('ArrDelay', ascending=False).head(20)
    
    st.subheader("Worst Performing Routes (>100 flights)")
    st.dataframe(worst)
    
    # Distance vs delay scatter
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(route_stats['Distance'], route_stats['ArrDelay'], s=route_stats['Flights']/10)
    ax.set_xlabel('Distance (miles)')
    ax.set_ylabel('Avg Delay (min)')
    st.pyplot(fig)

def page_aircraft_utilization(df):
    st.header("✈️ Aircraft Utilization")
    
    # Utilization metrics per tail number
    utilization = df.groupby('TailNumber').agg({
        'FlightDate': ['count', 'nunique'],
        'ArrDelay': 'mean',
        'Distance': 'sum'
    }).round(2)
    
    utilization.columns = ['TotalFlights', 'UniqueDays', 'AvgDelay', 'TotalMiles']
    utilization['FlightsPerDay'] = (
        utilization['TotalFlights'] / utilization['UniqueDays']
    ).round(2)
    
    # Identify underutilized
    underutilized = utilization[utilization['FlightsPerDay'] < 2]
    
    st.metric("Total Aircraft", len(utilization))
    st.metric("Avg Flights/Day", f"{utilization['FlightsPerDay'].mean():.1f}")
    st.metric("Underutilized (<2 flights/day)", len(underutilized))
    
    # Top performers
    st.subheader("Most Utilized Aircraft")
    st.dataframe(utilization.nlargest(20, 'FlightsPerDay'))
    
    # Histogram
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(utilization['FlightsPerDay'], bins=20, edgecolor='black')
    ax.set_xlabel('Flights per Day')
    ax.set_ylabel('Number of Aircraft')
    st.pyplot(fig)

def page_crew_efficiency(df):
    st.header("👨‍✈️ Crew & Aircraft Efficiency")
    
    # Turnaround time calculation (fix: convert times to datetime format first)
    df_sorted = df.sort_values(['TailNumber', 'FlightDate', 'SchedArr']).copy()
    
    # Convert integer times (0900) to timedelta for calculation
    def time_to_minutes(time_int):
        """Convert HHMM format to minutes since midnight"""
        if pd.isna(time_int):
            return None
        hours = int(time_int) // 100
        minutes = int(time_int) % 100
        return hours * 60 + minutes
    
    # Get next departure and arrival times
    df_sorted['NextDepartureTime'] = df_sorted.groupby('TailNumber')['SchedDep'].shift(-1)
    df_sorted['ArrivalMinutes'] = df_sorted['SchedArr'].apply(time_to_minutes)
    df_sorted['NextDepartureMinutes'] = df_sorted['NextDepartureTime'].apply(time_to_minutes)
    
    # Calculate turnaround (next departure - current arrival)
    # Handle day boundary (if next flight is next day, add 1440 minutes)
    df_sorted['TurnaroundMinutes'] = df_sorted.apply(
        lambda row: row['NextDepartureMinutes'] - row['ArrivalMinutes']
        if pd.notna(row['NextDepartureMinutes']) and pd.notna(row['ArrivalMinutes'])
        else None,
        axis=1
    )
    
    # Recovery rate: DepDelay > 0 AND ArrDelay <= 15
    recovered = df[(df['DepDelay'] > 0) & (df['ArrDelay'] <= 15)]
    recovery_rate = (len(recovered) / len(df[df['DepDelay'] > 0])) * 100 if len(df[df['DepDelay'] > 0]) > 0 else 0
    
    # Metrics
    valid_turnaround = df_sorted['TurnaroundMinutes'].dropna()
    if len(valid_turnaround) > 0:
        st.metric("Avg Turnaround Time", f"{valid_turnaround.mean():.0f} min")
    st.metric("Recovery Rate", f"{recovery_rate:.1f}%")
    
    # By carrier
    st.subheader("Recovery Rate by Carrier")
    carrier_recovery = df.groupby('Carrier').apply(
        lambda x: (len(x[(x['DepDelay'] > 0) & (x['ArrDelay'] <= 15)]) / len(x[x['DepDelay'] > 0])) * 100 
        if len(x[x['DepDelay'] > 0]) > 0 else 0
    ).sort_values(ascending=False)
    
    fig, ax = plt.subplots(figsize=(10, 5))
    style_fig(fig); style_ax(ax)
    carrier_recovery.head(10).plot(kind='barh', ax=ax, color=COLOR_GOOD)
    ax.set_xlabel('Recovery Rate (%)')
    ax.tick_params(colors=TEXT_COLOR)
    st.pyplot(fig)
    plt.close()
    
    # Turnaround distribution
    st.subheader("Turnaround Time Distribution")
    fig, ax = plt.subplots(figsize=(10, 5))
    style_fig(fig); style_ax(ax)
    valid_turnaround_filtered = valid_turnaround[(valid_turnaround > 0) & (valid_turnaround < 500)]
    if len(valid_turnaround_filtered) > 0:
        ax.hist(valid_turnaround_filtered, bins=30, edgecolor='black', color=COLOR_WARN)
        ax.set_xlabel('Minutes')
        ax.set_ylabel('Frequency')
    st.pyplot(fig)
    plt.close()


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    st.title("✈ US Airline On-Time Performance Dashboard")
    st.caption("Source: BTS Marketing Carrier On-Time Performance | 2018–2026")

    env, clean_dir = detect_environment()

    if env == "cloud":
        # ── CLOUD MODE ────────────────────────────────────────────────────────
        available_months = AVAILABLE_MONTHS
        
        st.sidebar.title("✈ Filters")
        st.sidebar.markdown("---")
        
        month_options = [f"{MONTH_NAMES[m]} {y}" for y, m in sorted(available_months, reverse=True)]
        
        selected_labels = st.sidebar.multiselect(
            "Select Months to Load",
            options=month_options,
            default=[]
        )
        
        if selected_labels:
            st.session_state.selected_months = []
            for label in selected_labels:
                parts = label.split()
                month_name = parts[0]
                year = int(parts[1])
                month_num = [k for k, v in MONTH_NAMES.items() if v == month_name][0]
                st.session_state.selected_months.append((year, month_num))
        
        st.sidebar.caption(f"Selected: {len(st.session_state.get('selected_months', []))} months")
        st.sidebar.markdown("---")
        
        if st.sidebar.button("Load Data", use_container_width=True):
            if st.session_state.get('selected_months'):
                with st.spinner(f"Loading {len(st.session_state.selected_months)} months..."):
                    df = load_months_hf(tuple(st.session_state.selected_months))
                    if not df.empty:
                        st.session_state.df = df
                        st.session_state.load_counter = st.session_state.get("load_counter", 0) + 1
                        st.rerun()
            else:
                st.error("Select at least one month first")
        
        if hasattr(st.session_state, 'df') and not st.session_state.df.empty:
            df = st.session_state.df
        else:
            st.info("👆 Pick months above, click Load Data")
            st.stop()

    else:
        # ── LOCAL MODE ────────────────────────────────────────────────────────
        if clean_dir is None:
            st.error("Data directory not found.")
            st.stop()
        available_months = get_available_months(clean_dir)
        if not available_months:
            st.error("No clean data files found.")
            st.stop()
        
        years = sorted(set(y for y, m in available_months))
        st.sidebar.caption(
            f"Local mode | {len(available_months)} months available | {years[0]}–{years[-1]}"
        )
        
        # Default: Jan 2025 to Jun 2026 (17 months)
        default_months = [
            (2025, 1), (2025, 2), (2025, 3), (2025, 4), (2025, 5), (2025, 6),
            (2025, 7), (2025, 8), (2025, 9), (2025, 10), (2025, 11), (2025, 12),
            (2026, 1), (2026, 2), (2026, 3), (2026, 4), (2026, 5),
        ]
        
        month_options = [f"{MONTH_NAMES[m]} {y}" for y, m in sorted(available_months, reverse=True)]
        default_labels = [f"{MONTH_NAMES[m]} {y}" for y, m in sorted(default_months)]
        
        selected_labels = st.sidebar.multiselect(
            "Select Months (default: Jan 2025–May 2026)",
            options=month_options,
            default=default_labels
        )
        
        selected_months_local = []
        for label in selected_labels:
            parts = label.split()
            month_name = parts[0]
            year = int(parts[1])
            month_num = [k for k, v in MONTH_NAMES.items() if v == month_name][0]
            selected_months_local.append((year, month_num))
        
        st.sidebar.caption(f"Loading: {len(selected_months_local)} months")
        st.sidebar.markdown("---")
        
        # ── PIPELINE SECTION ──────────────────────────────────────────────────
        st.sidebar.subheader("🔄 Pipeline")
        
        local_state_file = r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines\Data\pipeline_state.json"
        if os.path.exists(local_state_file):
            try:
                with open(local_state_file) as f:
                    state = json.load(f)
                last_checked = state.get("last_checked", "Never")[:19] if state.get("last_checked") else "Never"
                latest = state.get("last_known_latest", "Unknown")
                st.sidebar.caption(f"Last checked: {last_checked}")
                st.sidebar.caption(f"Latest on BTS: {latest}")
            except Exception as e:
                st.sidebar.caption(f"Pipeline state error: {str(e)[:50]}")
        else:
            st.sidebar.caption("No pipeline state found.")

        if st.sidebar.button("▶ Run Pipeline Update", use_container_width=True):
            with st.sidebar:
                with st.spinner("Running pipeline update..."):
                    try:
                        result = subprocess.run(
                            [sys.executable, "run_pipeline.py"],
                            capture_output=True, text=True, timeout=600,
                            cwd=r"C:\Users\abish\OneDrive\New\OneDrive\Desktop\Airlines"
                        )
                        if result.returncode == 0:
                            st.success("Pipeline update complete!")
                            st.cache_data.clear()
                        else:
                            st.error(f"Pipeline error: {result.stderr[:200]}")
                    except Exception as e:
                        st.error(f"Failed: {e}")
        
        st.sidebar.markdown("---")
        
        # Load data automatically
        with st.spinner(f"Loading {len(selected_months_local)} months..."):
            df = load_months(clean_dir, tuple(selected_months_local))
            if not df.empty:
                st.session_state.df = df
                st.session_state.load_counter = st.session_state.get("load_counter", 0) + 1

    if df.empty:
        st.warning("No data found for selected filters.")
        st.stop()

    st.sidebar.success(f"Loaded {len(df):,} flights")
    
    # Global date filter - PERSISTENT with session_state
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Date Range Filter")
    min_date = df['FlightDate'].min().date()
    max_date = df['FlightDate'].max().date()
    
    # Initialize session state for dates
    if 'start_date' not in st.session_state:
        st.session_state.start_date = min_date
    if 'end_date' not in st.session_state:
        st.session_state.end_date = max_date
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "From",
            value=st.session_state.start_date,
            min_value=min_date,
            max_value=max_date,
            key="start_date_picker"
        )
        st.session_state.start_date = start_date
    
    with col2:
        end_date = st.date_input(
            "To",
            value=st.session_state.end_date,
            min_value=min_date,
            max_value=max_date,
            key="end_date_picker"
        )
        st.session_state.end_date = end_date
    
    # Validate and filter
    if start_date > end_date:
        st.sidebar.error("Start date must be before end date")
        st.stop()
    
    df = df[(df['FlightDate'].dt.date >= start_date) & 
            (df['FlightDate'].dt.date <= end_date)]
    
    st.sidebar.caption(f"Filtered: {start_date} to {end_date}")

    # Navigation
    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")
    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Route Explorer", "Carrier Comparison",
        "Aircraft Tracker", "Delay Analysis", "Network Map",
        "Hub Analysis", "Seasonal Trends", "Route Optimization",
        "Aircraft Utilization", "Crew Efficiency"]
    )

    if page == "Overview":
        page_overview(df)
    elif page == "Route Explorer":
        page_routes(df)
    elif page == "Carrier Comparison":
        page_carrier_comparison(df)
    elif page == "Aircraft Tracker":
        page_aircraft_tracker(df)
    elif page == "Delay Analysis":
        page_delay_analysis(df)
    elif page == "Network Map":
        page_network_map(df)
    elif page == "Hub Analysis":
        page_hub_analysis(df)
    elif page == "Seasonal Trends":
        page_seasonal_trends(df)
    elif page == "Route Optimization":
        page_route_optimization(df)
    elif page == "Aircraft Utilization":
        page_aircraft_utilization(df)
    elif page == "Crew Efficiency":
        page_crew_efficiency(df)


    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Built by Abishek Singanur Aswan Kumar\n"
        "M.S. Industrial Engineering, UIUC"
    )


if __name__ == '__main__':
    main()