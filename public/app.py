"""
EcoFlight AI - Aviation-Themed Flight Management System
Dark cockpit avionics aesthetic with radar-style map
"""

import streamlit as st
import requests
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import json

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="EcoFlight AI | Flight Management System",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== AVIATION COCKPIT CSS ====================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Orbitron:wght@400;500;700;900&display=swap');

    /* Global dark cockpit background */
    .stApp {
        background: #0a0e17;
        color: #c8d6e5;
    }

    /* Sidebar - instrument panel */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #0a0e17 100%);
        border-right: 1px solid #1a3a4a;
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stRadio label,
    section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #00e5ff !important;
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-size: 0.8rem !important;
    }

    /* Main title - avionics display */
    .fms-header {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.4rem;
        font-weight: 900;
        color: #00e5ff;
        text-shadow: 0 0 20px rgba(0, 229, 255, 0.4), 0 0 40px rgba(0, 229, 255, 0.1);
        letter-spacing: 4px;
        margin-bottom: 0;
        padding: 10px 0;
    }
    .fms-subtitle {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #4a6a7a;
        letter-spacing: 3px;
        text-transform: uppercase;
        margin-top: -5px;
    }

    /* Instrument panel cards */
    .instrument {
        background: linear-gradient(145deg, #0d1520, #111b2a);
        border: 1px solid #1a3a4a;
        border-radius: 8px;
        padding: 16px;
        margin: 4px 0;
        position: relative;
        overflow: hidden;
    }
    .instrument::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00e5ff, transparent);
    }
    .instrument-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        color: #4a7a8a;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 4px;
    }
    .instrument-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        color: #00ff88;
        text-shadow: 0 0 10px rgba(0, 255, 136, 0.3);
    }
    .instrument-value.warning {
        color: #ffb300;
        text-shadow: 0 0 10px rgba(255, 179, 0, 0.3);
    }
    .instrument-value.danger {
        color: #ff4444;
        text-shadow: 0 0 10px rgba(255, 68, 68, 0.3);
    }
    .instrument-delta {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #00ff88;
        margin-top: 2px;
    }

    /* Route info bar */
    .route-bar {
        background: linear-gradient(90deg, #0d1520, #111b2a, #0d1520);
        border: 1px solid #1a3a4a;
        border-radius: 8px;
        padding: 15px 25px;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 20px;
        margin: 10px 0;
    }
    .route-airport {
        font-family: 'Orbitron', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        color: #00e5ff;
        letter-spacing: 3px;
    }
    .route-arrow {
        font-size: 1.5rem;
        color: #2a4a5a;
    }
    .route-detail {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.7rem;
        color: #4a6a7a;
        text-align: center;
    }

    /* Insight box - caution/advisory style */
    .advisory {
        background: linear-gradient(145deg, #1a1a00, #1a2000);
        border: 1px solid #4a4a00;
        border-left: 3px solid #ffb300;
        border-radius: 4px;
        padding: 12px 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        color: #ffb300;
        line-height: 1.6;
    }

    /* Override Streamlit metrics */
    div[data-testid="stMetricValue"] {
        font-family: 'Orbitron', sans-serif !important;
        color: #00ff88 !important;
    }
    div[data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
    }
    div[data-testid="stMetricLabel"] {
        font-family: 'JetBrains Mono', monospace !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.7rem !important;
    }

    /* Section headers */
    .section-header {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #00e5ff;
        text-transform: uppercase;
        letter-spacing: 3px;
        border-bottom: 1px solid #1a3a4a;
        padding-bottom: 8px;
        margin: 20px 0 15px 0;
    }

    /* Table styling */
    .stTable, table {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.8rem;
    }

    /* Override streamlit info/success/warning boxes */
    .stAlert {
        background: #0d1520 !important;
        border-color: #1a3a4a !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0a0e17; }
    ::-webkit-scrollbar-thumb { background: #1a3a4a; border-radius: 3px; }

    /* Status indicator */
    .status-online {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #00ff88;
        border-radius: 50%;
        box-shadow: 0 0 6px #00ff88;
        margin-right: 8px;
    }

    /* Hide default streamlit header/footer */
    header[data-testid="stHeader"] { background: #0a0e17; }
    .stDeployButton { display: none; }

    /* Button styling */
    .stButton > button {
        background: linear-gradient(145deg, #003344, #004455) !important;
        color: #00e5ff !important;
        border: 1px solid #00e5ff !important;
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 2px;
        text-transform: uppercase;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        background: linear-gradient(145deg, #004455, #005566) !important;
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.3) !important;
    }

    /* Contrail badge */
    .contrail-tag {
        background: #ff6b35;
        color: white;
        padding: 2px 10px;
        border-radius: 3px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.65rem;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
    }
</style>
""", unsafe_allow_html=True)


# ==================== HELPER FUNCTIONS ====================

def fetch(endpoint):
    try:
        return requests.get(f"{API_URL}{endpoint}", timeout=5).json()
    except:
        return None


def optimize(origin, dest, aircraft, priority):
    try:
        r = requests.post(f"{API_URL}/optimize", json={
            "origin": origin, "destination": dest,
            "aircraft_type": aircraft, "priority": priority
        }, timeout=10)
        return r.json()
    except Exception as e:
        st.error(f"SYSTEM FAULT: {e}")
        return None


def create_radar_map(result):
    """Aviation radar-style dark map with glowing route lines"""
    origin = result["metadata"]["origin"]
    dest = result["metadata"]["destination"]
    std_wps = result["routes"]["standard"]["waypoints"]
    clim_wps = result["routes"]["climate_optimized"]["waypoints"]
    contrails = result.get("contrail_heatmap", [])

    center_lat = (origin["lat"] + dest["lat"]) / 2
    center_lon = (origin["lon"] + dest["lon"]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=4,
        tiles="CartoDB dark_matter",
        control_scale=False,
        zoom_control=False,
    )

    # Contrail risk zones as shaded circles
    for c in contrails:
        if c.get("contrail_probability", 0) > 0.15:
            prob = c["contrail_probability"]
            color = "#ff4444" if prob > 0.5 else "#ff8800" if prob > 0.3 else "#ffcc00"
            folium.CircleMarker(
                [c["lat"], c["lon"]],
                radius=prob * 25,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.15,
                weight=1,
                opacity=0.3,
                popup=f"Contrail Risk: {prob:.0%}"
            ).add_to(m)

    # Standard route - dim red dashed
    std_coords = [[w["lat"], w["lon"]] for w in std_wps]
    folium.PolyLine(
        std_coords,
        color="#cc3333",
        weight=2,
        opacity=0.4,
        dash_array="8, 12",
    ).add_to(m)

    # Optimized route - bright cyan animated (like a moving radar blip)
    clim_coords = [[w["lat"], w["lon"]] for w in clim_wps]
    AntPath(
        clim_coords,
        color="#00e5ff",
        weight=3,
        opacity=0.9,
        pulse_color="#00ff88",
        delay=1200,
        dash_array=[15, 30],
    ).add_to(m)

    # Solid line underneath for clarity
    folium.PolyLine(
        clim_coords,
        color="#00e5ff",
        weight=2,
        opacity=0.5,
    ).add_to(m)

    # Contrail avoidance points (where altitude was adjusted)
    for w in clim_wps:
        if w.get("contrail_avoidance"):
            folium.CircleMarker(
                [w["lat"], w["lon"]],
                radius=6,
                color="#ffb300",
                fill=True,
                fill_color="#ffb300",
                fill_opacity=0.8,
                weight=2,
                popup=f"ALT ADJUST: FL{int(w['altitude']/100)}"
            ).add_to(m)

    # Waypoint markers along optimized route (every few points)
    step = max(1, len(clim_wps) // 8)
    for i, w in enumerate(clim_wps):
        if i % step == 0 and 0 < i < len(clim_wps) - 1:
            folium.CircleMarker(
                [w["lat"], w["lon"]],
                radius=3,
                color="#00e5ff",
                fill=True,
                fill_color="#00e5ff",
                fill_opacity=0.6,
                weight=1,
                popup=f"WPT {i} | FL{int(w['altitude']/100)} | {w['distance_cumulative']:.0f}NM"
            ).add_to(m)

    # Origin marker
    folium.Marker(
        [origin["lat"], origin["lon"]],
        popup=f"DEP: {origin['code']}",
        icon=folium.DivIcon(html=f"""
            <div style="
                font-family: 'Courier New', monospace;
                font-size: 11px;
                font-weight: bold;
                color: #00ff88;
                text-shadow: 0 0 8px rgba(0,255,136,0.6);
                background: rgba(0,0,0,0.7);
                padding: 2px 6px;
                border: 1px solid #00ff88;
                border-radius: 2px;
            ">{origin['code']}</div>
        """)
    ).add_to(m)

    # Destination marker
    folium.Marker(
        [dest["lat"], dest["lon"]],
        popup=f"ARR: {dest['code']}",
        icon=folium.DivIcon(html=f"""
            <div style="
                font-family: 'Courier New', monospace;
                font-size: 11px;
                font-weight: bold;
                color: #00e5ff;
                text-shadow: 0 0 8px rgba(0,229,255,0.6);
                background: rgba(0,0,0,0.7);
                padding: 2px 6px;
                border: 1px solid #00e5ff;
                border-radius: 2px;
            ">{dest['code']}</div>
        """)
    ).add_to(m)

    return m


def create_altitude_profile(result):
    """Aviation instrument-style altitude profile"""
    std = result["routes"]["standard"]["waypoints"]
    clim = result["routes"]["climate_optimized"]["waypoints"]
    contrails = result.get("contrail_heatmap", [])

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.65, 0.35],
        subplot_titles=("VERTICAL PROFILE", "CONTRAIL THREAT"),
        vertical_spacing=0.12
    )

    # Standard route altitude
    fig.add_trace(go.Scatter(
        x=[w["distance_cumulative"] for w in std],
        y=[w["altitude"] for w in std],
        name="STD ROUTE",
        line=dict(color="#cc3333", width=1.5, dash="dash"),
        opacity=0.5
    ), row=1, col=1)

    # Optimized route altitude
    fig.add_trace(go.Scatter(
        x=[w["distance_cumulative"] for w in clim],
        y=[w["altitude"] for w in clim],
        name="ECO ROUTE",
        line=dict(color="#00e5ff", width=2.5),
        fill="tozeroy",
        fillcolor="rgba(0,229,255,0.05)"
    ), row=1, col=1)

    # Contrail avoidance markers
    avoid_pts = [(w["distance_cumulative"], w["altitude"])
                 for w in clim if w.get("contrail_avoidance")]
    if avoid_pts:
        fig.add_trace(go.Scatter(
            x=[p[0] for p in avoid_pts],
            y=[p[1] for p in avoid_pts],
            name="ALT ADJUST",
            mode="markers",
            marker=dict(color="#ffb300", size=10, symbol="diamond",
                        line=dict(color="#ffb300", width=1))
        ), row=1, col=1)

    # Contrail risk bars
    if contrails:
        risks = [c.get("contrail_probability", 0) for c in contrails]
        colors = ["#ff4444" if r > 0.5 else "#ff8800" if r > 0.2 else "#1a3a4a"
                  for r in risks]
        fig.add_trace(go.Bar(
            x=list(range(len(risks))),
            y=risks,
            name="CONTRAIL RISK",
            marker_color=colors,
            opacity=0.7
        ), row=2, col=1)

        fig.add_hline(y=0.5, line_dash="dash", line_color="#ff4444",
                      line_width=1, row=2, col=1)
        fig.add_hline(y=0.2, line_dash="dot", line_color="#ff8800",
                      line_width=1, row=2, col=1)

    fig.update_layout(
        height=450,
        template="plotly_dark",
        paper_bgcolor="rgba(10,14,23,1)",
        plot_bgcolor="rgba(13,21,32,1)",
        font=dict(family="JetBrains Mono, monospace", color="#4a7a8a", size=10),
        legend=dict(orientation="h", y=1.15, font=dict(size=9)),
        margin=dict(l=50, r=20, t=40, b=30)
    )

    fig.update_xaxes(title_text="DISTANCE (NM)", gridcolor="#1a2a3a",
                     zerolinecolor="#1a2a3a", row=1, col=1)
    fig.update_yaxes(title_text="ALTITUDE (FT)", gridcolor="#1a2a3a",
                     zerolinecolor="#1a2a3a", row=1, col=1)
    fig.update_xaxes(title_text="WAYPOINT", gridcolor="#1a2a3a", row=2, col=1)
    fig.update_yaxes(title_text="RISK", gridcolor="#1a2a3a", row=2, col=1)

    return fig


def create_warming_chart(result):
    """Stacked bar: CO2 vs Contrail warming"""
    routes = result["routes"]

    categories = ["STANDARD", "FUEL-ONLY", "ECOFLIGHT"]
    co2 = [routes["standard"]["co2_kg"], routes["fuel_optimized"]["co2_kg"],
           routes["climate_optimized"]["co2_kg"]]
    contrail = [routes["standard"]["contrail_warming_co2eq"],
                routes["fuel_optimized"]["contrail_warming_co2eq"],
                routes["climate_optimized"]["contrail_warming_co2eq"]]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="CO2 (FUEL)", x=categories, y=co2,
        marker_color="#1a6aaa",
        text=[f"{v:.0f}" for v in co2], textposition="inside",
        textfont=dict(family="JetBrains Mono", size=10, color="white")
    ))
    fig.add_trace(go.Bar(
        name="CONTRAIL WARMING", x=categories, y=contrail,
        marker_color="#ff6b35",
        text=[f"{v:.0f}" for v in contrail], textposition="inside",
        textfont=dict(family="JetBrains Mono", size=10, color="white")
    ))

    fig.update_layout(
        barmode="stack",
        height=350,
        template="plotly_dark",
        paper_bgcolor="rgba(10,14,23,1)",
        plot_bgcolor="rgba(13,21,32,1)",
        font=dict(family="JetBrains Mono, monospace", color="#4a7a8a", size=10),
        legend=dict(orientation="h", y=1.12, font=dict(size=9)),
        yaxis_title="CO2-EQUIVALENT (KG)",
        margin=dict(l=50, r=20, t=30, b=30)
    )
    fig.update_xaxes(gridcolor="#1a2a3a")
    fig.update_yaxes(gridcolor="#1a2a3a")

    return fig


# ==================== MAIN UI ====================

# Header
st.markdown('<p class="fms-header">ECOFLIGHT AI</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="fms-subtitle">'
    '<span class="status-online"></span>'
    'Flight Management System &mdash; Dual Climate Optimization '
    '<span class="contrail-tag">CONTRAIL AWARE</span>'
    '</p>',
    unsafe_allow_html=True
)

# ---- Sidebar: Instrument Panel ----
st.sidebar.markdown("### ✈ FLIGHT PLAN")

airports_data = fetch("/airports")
aircraft_data = fetch("/aircraft")

airports = airports_data["airports"] if airports_data else [
    {"code": "KJFK", "name": "New York JFK", "city": "New York"},
    {"code": "KLAX", "name": "Los Angeles Intl", "city": "Los Angeles"},
    {"code": "KORD", "name": "Chicago O'Hare", "city": "Chicago"},
    {"code": "KDFW", "name": "Dallas/Fort Worth", "city": "Dallas"},
    {"code": "KDEN", "name": "Denver Intl", "city": "Denver"},
    {"code": "KSFO", "name": "San Francisco", "city": "San Francisco"},
    {"code": "KSEA", "name": "Seattle Tacoma", "city": "Seattle"},
    {"code": "KATL", "name": "Atlanta Hartsfield", "city": "Atlanta"},
    {"code": "KMIA", "name": "Miami Intl", "city": "Miami"},
    {"code": "KBOS", "name": "Boston Logan", "city": "Boston"},
]
aircraft_list = aircraft_data["aircraft"] if aircraft_data else [
    {"type": "B737", "name": "Boeing 737-800"},
    {"type": "A320", "name": "Airbus A320neo"},
]

airport_map = {f"{a['code']} - {a.get('city', a['name'])}": a["code"] for a in airports}
aircraft_map = {f"{a['type']} ({a['name']})": a["type"] for a in aircraft_list}

origin_sel = st.sidebar.selectbox("DEPARTURE", list(airport_map.keys()), index=0)
dest_sel = st.sidebar.selectbox("ARRIVAL", list(airport_map.keys()), index=1)
aircraft_sel = st.sidebar.selectbox("AIRCRAFT", list(aircraft_map.keys()), index=0)

st.sidebar.markdown("---")
st.sidebar.markdown("### OPT MODE")
priority = st.sidebar.radio(
    "Select optimization target:",
    ["climate", "fuel", "balanced"],
    format_func=lambda x: {
        "climate": "CLIMATE (FUEL + CONTRAILS)",
        "fuel": "FUEL ONLY",
        "balanced": "BALANCED"
    }[x]
)

st.sidebar.markdown("---")
go_btn = st.sidebar.button("COMPUTE ROUTE", type="primary", use_container_width=True)

if go_btn:
    with st.spinner("COMPUTING OPTIMAL 4D TRAJECTORY..."):
        result = optimize(
            airport_map[origin_sel], airport_map[dest_sel],
            aircraft_map[aircraft_sel], priority
        )
        if result:
            st.session_state["result"] = result

# ==================== RESULTS ====================
if "result" in st.session_state:
    result = st.session_state["result"]
    savings = result["savings"]
    meta = result["metadata"]

    # Route bar
    st.markdown(f"""
    <div class="route-bar">
        <div>
            <div class="route-airport">{meta['origin']['code']}</div>
            <div class="route-detail">{meta['origin']['name']}</div>
        </div>
        <div class="route-arrow">
            ━━━ ✈ ━━━▶
        </div>
        <div>
            <div class="route-airport">{meta['destination']['code']}</div>
            <div class="route-detail">{meta['destination']['name']}</div>
        </div>
        <div style="margin-left: 30px;">
            <div class="route-detail">DISTANCE</div>
            <div style="font-family: Orbitron; color: #00e5ff; font-size: 1.2rem;">{meta['distance_nm']:.0f} NM</div>
        </div>
        <div>
            <div class="route-detail">AIRCRAFT</div>
            <div style="font-family: Orbitron; color: #00e5ff; font-size: 1.2rem;">{meta['aircraft']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Advisory/Insight
    st.markdown(f'<div class="advisory">ADVISORY: {result["insight"]}</div>',
                unsafe_allow_html=True)
    st.markdown("")

    # Instrument panels - key metrics
    st.markdown('<div class="section-header">OPTIMIZATION RESULTS</div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Fuel Saved</div>
            <div class="instrument-value">{savings['fuel_saved_kg']:.0f}</div>
            <div class="instrument-delta">KG | {savings['fuel_saved_percent']:.1f}%</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">CO2 Avoided</div>
            <div class="instrument-value">{savings['co2_saved_kg']:.0f}</div>
            <div class="instrument-delta">KG (FROM FUEL)</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        val = savings['contrail_warming_avoided_kg']
        cls = "warning" if val < 50 else ""
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Contrail Warming Avoided</div>
            <div class="instrument-value {cls}">{val:.0f}</div>
            <div class="instrument-delta">KG CO2-EQ</div>
        </div>""", unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Total Warming Saved</div>
            <div class="instrument-value">{savings['total_warming_saved_kg']:.0f}</div>
            <div class="instrument-delta">KG | {savings['total_warming_saved_percent']:.1f}%</div>
        </div>""", unsafe_allow_html=True)

    with c5:
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Cost Saved</div>
            <div class="instrument-value">${savings['cost_saved_usd']:.0f}</div>
            <div class="instrument-delta">PER FLIGHT</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # Map + Charts
    map_col, data_col = st.columns([3, 2])

    with map_col:
        st.markdown('<div class="section-header">RADAR / ROUTE MAP</div>',
                    unsafe_allow_html=True)
        radar_map = create_radar_map(result)
        st_folium(radar_map, width=700, height=480, returned_objects=[])

        st.markdown("""
        <div style="font-family: JetBrains Mono; font-size: 0.7rem; color: #4a6a7a; margin-top: 5px;">
        <span style="color: #00e5ff;">━━</span> ECO ROUTE &nbsp;
        <span style="color: #cc3333;">- - -</span> STD ROUTE &nbsp;
        <span style="color: #ffb300;">&#9670;</span> ALT ADJUST &nbsp;
        <span style="color: #ff4444;">&#9679;</span> CONTRAIL ZONE
        </div>
        """, unsafe_allow_html=True)

    with data_col:
        st.markdown('<div class="section-header">CLIMATE IMPACT BREAKDOWN</div>',
                    unsafe_allow_html=True)
        warming_fig = create_warming_chart(result)
        st.plotly_chart(warming_fig, use_container_width=True)

        # Comparison insight
        std_total = result["routes"]["standard"]["total_warming_co2eq"]
        clim_total = result["routes"]["climate_optimized"]["total_warming_co2eq"]
        fuel_total = result["routes"]["fuel_optimized"]["total_warming_co2eq"]

        if std_total > 0:
            fuel_pct = (std_total - fuel_total) / std_total * 100
            clim_pct = (std_total - clim_total) / std_total * 100
            multiplier = clim_pct / max(fuel_pct, 0.1)

            st.markdown(f"""
            <div class="instrument">
                <div class="instrument-label">Fuel-Only Optimization</div>
                <div class="instrument-value warning">{fuel_pct:.1f}%</div>
                <div class="instrument-delta">WARMING REDUCTION</div>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div class="instrument">
                <div class="instrument-label">EcoFlight Climate Optimization</div>
                <div class="instrument-value">{clim_pct:.1f}%</div>
                <div class="instrument-delta">WARMING REDUCTION | {multiplier:.1f}x MORE EFFECTIVE</div>
            </div>
            """, unsafe_allow_html=True)

    # Altitude Profile
    st.markdown('<div class="section-header">VERTICAL NAV / CONTRAIL THREAT</div>',
                unsafe_allow_html=True)
    alt_fig = create_altitude_profile(result)
    st.plotly_chart(alt_fig, use_container_width=True)

    # Three-route comparison
    st.markdown('<div class="section-header">ROUTE COMPARISON TABLE</div>',
                unsafe_allow_html=True)

    routes = result["routes"]
    comp = pd.DataFrame({
        "METRIC": ["Fuel Burn (kg)", "CO2 (kg)", "Contrail Warming (kg CO2-eq)",
                    "TOTAL WARMING (kg CO2-eq)", "Contrail Distance (km)", "Cost ($)"],
        "STANDARD": [
            f"{routes['standard']['fuel_kg']:.0f}",
            f"{routes['standard']['co2_kg']:.0f}",
            f"{routes['standard']['contrail_warming_co2eq']:.0f}",
            f"{routes['standard']['total_warming_co2eq']:.0f}",
            f"{routes['standard']['contrail_km']:.0f}",
            f"${routes['standard']['fuel_kg'] * 0.8:.0f}"
        ],
        "FUEL-ONLY": [
            f"{routes['fuel_optimized']['fuel_kg']:.0f}",
            f"{routes['fuel_optimized']['co2_kg']:.0f}",
            f"{routes['fuel_optimized']['contrail_warming_co2eq']:.0f}",
            f"{routes['fuel_optimized']['total_warming_co2eq']:.0f}",
            f"{routes['fuel_optimized']['contrail_km']:.0f}",
            f"${routes['fuel_optimized']['fuel_kg'] * 0.8:.0f}"
        ],
        "ECOFLIGHT": [
            f"{routes['climate_optimized']['fuel_kg']:.0f}",
            f"{routes['climate_optimized']['co2_kg']:.0f}",
            f"{routes['climate_optimized']['contrail_warming_co2eq']:.0f}",
            f"{routes['climate_optimized']['total_warming_co2eq']:.0f}",
            f"{routes['climate_optimized']['contrail_km']:.0f}",
            f"${routes['climate_optimized']['fuel_kg'] * 0.8:.0f}"
        ]
    })
    st.table(comp)

    # Scale impact
    st.markdown('<div class="section-header">FLEET-WIDE IMPACT PROJECTION</div>',
                unsafe_allow_html=True)

    annual = 10_000_000
    s1, s2, s3, s4 = st.columns(4)

    with s1:
        val = savings['total_warming_saved_kg'] * annual / 1e9
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Annual Warming Avoided</div>
            <div class="instrument-value">{val:.1f}M</div>
            <div class="instrument-delta">TONS CO2-EQ / YEAR</div>
        </div>""", unsafe_allow_html=True)
    with s2:
        cars = savings['total_warming_saved_kg'] * annual / 4600 / 1000
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Equivalent Cars Removed</div>
            <div class="instrument-value">{cars:.0f}K</div>
            <div class="instrument-delta">VEHICLES / YEAR</div>
        </div>""", unsafe_allow_html=True)
    with s3:
        cost = savings['cost_saved_usd'] * annual / 1e9
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Industry Savings</div>
            <div class="instrument-value">${cost:.1f}B</div>
            <div class="instrument-delta">USD / YEAR</div>
        </div>""", unsafe_allow_html=True)
    with s4:
        trees = savings['total_warming_saved_kg'] * annual / 21 / 1e6
        st.markdown(f"""
        <div class="instrument">
            <div class="instrument-label">Equivalent Trees</div>
            <div class="instrument-value">{trees:.0f}M</div>
            <div class="instrument-delta">PLANTED / YEAR</div>
        </div>""", unsafe_allow_html=True)

else:
    # ---- Landing page ----
    st.markdown("")

    lc, rc = st.columns(2)

    with lc:
        st.markdown("""
        <div class="section-header">THE PROBLEM NOBODY SEES</div>
        <div class="instrument" style="line-height: 1.8;">
            <p style="color: #c8d6e5; font-family: JetBrains Mono; font-size: 0.85rem;">
            Every other team optimizes for <b style="color:#ff4444;">fuel only</b>.<br><br>
            But <b style="color:#ff6b35;">contrails</b> -- those white lines behind planes --
            cause <b style="color:#ffb300;">35% of aviation's total warming</b>.<br><br>
            Nearly as much as all the CO2 from jet fuel combined.<br><br>
            Google & American Airlines proved in 2025:
            <b style="color:#00ff88;">62% contrail reduction</b> with only
            <b style="color:#00e5ff;">0.11% fuel penalty</b>.
            </p>
        </div>
        """, unsafe_allow_html=True)

    with rc:
        st.markdown("""
        <div class="section-header">ECOFLIGHT ADVANTAGE</div>
        <div class="instrument" style="line-height: 1.8;">
            <p style="color: #c8d6e5; font-family: JetBrains Mono; font-size: 0.85rem;">
            <b style="color:#00e5ff;">4D Trajectory</b> -- lat, lon, altitude, time<br>
            <b style="color:#00e5ff;">Contrail Prediction</b> -- Schmidt-Appleman physics<br>
            <b style="color:#00e5ff;">Dual Optimization</b> -- fuel AND contrails<br>
            <b style="color:#00e5ff;">CDO Descent</b> -- continuous descent ops<br>
            <b style="color:#00e5ff;">Wind-Aware</b> -- jet stream exploitation<br><br>
            <span style="color:#00ff88; font-size:1rem;">
            Fuel-only: ~4% warming reduction<br>
            EcoFlight: up to 60%+ warming reduction<br>
            <b>That's 15x more effective.</b>
            </span>
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")
    st.markdown("""
    <div class="advisory">
    SELECT FLIGHT PARAMETERS AND CLICK COMPUTE ROUTE TO BEGIN
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="font-family: JetBrains Mono; font-size: 0.65rem; color: #2a3a4a; text-align: center; letter-spacing: 2px;">
ECOFLIGHT AI v2.0 | UNH HACKATHON 2026 | TEAM: GUNNY & SHRUTI |
RESEARCH: GOOGLE/BREAKTHROUGH ENERGY 2025, LEE ET AL. 2021
</div>
""", unsafe_allow_html=True)
