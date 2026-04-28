"""
AeroLink AI - Main Dashboard
------------------------------
Run with:
    streamlit run dashboard/app.py

Ties together:
  - ChannelSimulator   (fake network data)
  - Predictor          (AI failure prediction)
  - SwitchLogic        (switching decisions)
  - Gemini Explainer   (human-readable explanations)
  - All visual components
"""

import sys
import os
import time
import streamlit as st

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.channel_simulator import ChannelSimulator
from model.predictor import Predictor
from core.channel_manager import ChannelManager
from core.switch_logic import SwitchLogic
from gemini.explainer import Explainer
from dashboard.components.status_panel import render_status_panel
from dashboard.components.charts import render_charts, update_history
from dashboard.components.event_log import render_event_log

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AeroLink AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Global Styles ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

    /* Dark cockpit theme */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #060b18 !important;
        color: #c8d8e8;
    }s
    [data-testid="stAppViewContainer"] {
        background:
            radial-gradient(ellipse at 20% 20%, rgba(0,60,120,0.15) 0%, transparent 60%),
            radial-gradient(ellipse at 80% 80%, rgba(0,30,80,0.10) 0%, transparent 60%),
            #060b18;
    }
    [data-testid="stHeader"] { background: transparent !important; }
    [data-testid="stSidebar"] { background: #090f1f !important; }

    /* Remove Streamlit padding */
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-track { background: #0a0f1e; }
    ::-webkit-scrollbar-thumb { background: #1e3a6e; border-radius: 4px; }

    /* Hide Streamlit branding */
    #MainMenu, footer, header { visibility: hidden; }

    /* Plotly chart background */
    .js-plotly-plot { border-radius: 12px; overflow: hidden; }

    div[data-testid="stHorizontalBlock"] { gap: 16px; }
    /* Sidebar text colors */
    [data-testid="stSidebar"] h3 { color: #4a9eff !important; }
    [data-testid="stSidebar"] p  { color: #c8d8e8 !important; }
    [data-testid="stSidebar"] label { color: #c8d8e8 !important; }
    [data-testid="stSidebar"] .stSlider p { color: #c8d8e8 !important; }
</style>
""", unsafe_allow_html=True)


# ── Session State Init ────────────────────────────────────────────────────────
def init_session():
    """Initialize all objects once and store in Streamlit session state."""
    if "initialized" not in st.session_state:
        with st.spinner("Initializing AeroLink AI systems..."):
            st.session_state.simulator = ChannelSimulator()
            st.session_state.predictor = Predictor()
            st.session_state.manager   = ChannelManager()

            # Try to init Gemini — gracefully skip if key missing
            try:
                explainer = Explainer()
            except ValueError as e:
                st.warning(f"⚠️ Gemini disabled: {e}")
                explainer = None

            st.session_state.switch_logic = SwitchLogic(
                channel_manager=st.session_state.manager,
                explainer=explainer,
            )
            st.session_state.tick = 0
            st.session_state.initialized = True


# ── Header ────────────────────────────────────────────────────────────────────
def render_header(theme: str = "dark"):
    is_light    = (theme == "light")
    title_color = "#0a1a2a" if is_light else "#ffffff"
    sub_color   = "#1a5a9a" if is_light else "#6b7e9b"
    hr_color    = "#7ab0d8" if is_light else "#1e3a6e"
    dot_color   = "#00aa44" if is_light else "#00e676"
    st.markdown(f"""
    <div style="display:flex; align-items:center; justify-content:space-between;
                margin-bottom:8px;">
        <div>
            <div style="font-family:'Rajdhani',sans-serif; font-size:32px;
                        font-weight:700; color:{title_color}; letter-spacing:2px;
                        line-height:1;">
                ✈️ AEROLINK <span style="color:#4a9eff;">AI</span>
            </div>
            <div style="font-family:'Share Tech Mono',monospace; font-size:12px;
                        color:{sub_color}; letter-spacing:3px; margin-top:2px;">
                <span style="color:#4a9eff;">🛰️ Switch ON Monitoring in the controls Panel</span><br>        
                PREDICTIVE AIRCRAFT COMMUNICATION SYSTEM
            </div>
        </div>
        <div style="font-family:'Share Tech Mono',monospace; font-size:11px;
                    color:{sub_color}; text-align:right; line-height:1.8;">
            <span style="color:{dot_color};">●</span> SIMULATION ACTIVE<br>
            POWERED BY GEMINI AI + RANDOM FOREST
        </div>
    </div>
    <hr style="border:none; border-top:1px solid {hr_color}; margin-bottom:20px;">
    """, unsafe_allow_html=True)

# ── Sidebar Controls ──────────────────────────────────────────────────────────
def render_sidebar(theme: str = "dark"):
    is_light    = (theme == "light")
    title_color = "#0a1a2a" if is_light else "#ffffff"
    sub_color   = "#1a5a9a" if is_light else "#4a6080"
    hr_color    = "#7ab0d8" if is_light else "#1e3a6e"
    dot_color   = "#00aa44" if is_light else "#00e676"
    with st.sidebar:
        st.markdown("### ⚙️ Controls")

        speed = st.slider(
            "Simulation Speed (seconds/tick)",
            min_value=0.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
        )

        st.markdown("---")
        st.markdown("### 📊 Thresholds")
        st.markdown(f"""
        <div style="font-family:monospace; font-size:12px; color:#8899aa;">
            Failure threshold: <b style="color:{sub_color};">70%</b><br>
            Warning threshold: <b style="color:{sub_color};">45%</b><br>
            Switch cooldown:   <b style="color:{sub_color};">5s</b>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 🔗 About")
        st.markdown(f"""
        <div style="font-size:12px; color:{sub_color};">
            AeroLink AI monitors WiFi, 5G, and Satellite
            channels simultaneously, using Random Forest ML
            to predict failures and Gemini AI to explain
            every switching decision.<br><br>
            Built for <b>Google Solution Challenge 2026</b>.
        </div>
        """, unsafe_allow_html=True)
        if "running" not in st.session_state:
            st.session_state.running = False

        st.session_state.running = st.toggle(
            "🛰️ Switch ON Monitoring",
            value=False
        )
        st.markdown("Theme")
        is_light = st.toggle("Light Mode", value=False)
        st.session_state.theme = "light" if is_light else "dark"
        st.markdown("---")
        return speed


# ── Main Loop ─────────────────────────────────────────────────────────────────
def main():
    init_session()
    speed = render_sidebar(theme=st.session_state.get("theme", "dark"))
    theme = st.session_state.get("theme", "dark")
    render_header(theme=theme)

    if st.session_state.get("theme") == "light":
        st.markdown("""
        <style>
            html, body, [data-testid="stAppViewContainer"] {
                background-color: #f0f4f8 !important;
                color: #1a2a3a !important;
            }
            [data-testid="stAppViewContainer"] {
                background: #f0f4f8 !important;
            }
            [data-testid="stSidebar"] {
                background: #e2eaf2 !important;
            }
            [data-testid="stSidebar"] h3 { color: #1a4a8a !important; }
            [data-testid="stSidebar"] p  { color: #1a2a3a !important; }
        </style>
        """, unsafe_allow_html=True)


    sim    = st.session_state.simulator
    pred   = st.session_state.predictor
    mgr    = st.session_state.manager
    logic  = st.session_state.switch_logic

    # Always run one tick so UI has data to display
    readings = sim.tick()
    probs    = pred.predict_all(readings)
    logic.evaluate(readings, probs)

    st.session_state.tick += 1
    tick = st.session_state.tick

    update_history(readings, tick)
    snapshot = mgr.get_snapshot()

    # ── Render UI ──────────────────────────────────────────────────────────
    render_status_panel(snapshot, theme=theme)

    st.markdown("""
    <div style="color:#4a9eff; font-size:12px; letter-spacing:3px;
                font-family:'Courier New',monospace; margin-bottom:8px;">
        LIVE TELEMETRY
    </div>
    """, unsafe_allow_html=True)

    render_charts()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    hr_color = "#7ab0d8" if theme == "light" else "#1e3a6e"
    st.markdown(f"""
    <hr style="border:none; border-top:1px solid {hr_color}; margin:8px 0 20px 0;">
    """, unsafe_allow_html=True)

    render_event_log(snapshot["event_log"])

    st.markdown(f"""
    <div style="text-align:center; font-family:'Share Tech Mono',monospace;
                font-size:11px; color:#2a4060; margin-top:24px;">
        TICK #{tick} &nbsp;|&nbsp; AEROLINK AI &nbsp;|&nbsp;
        GOOGLE SOLUTION CHALLENGE 2026
    </div>
    """, unsafe_allow_html=True)

    # Only auto-refresh if monitoring toggle is ON
    if st.session_state.get("running"):
        time.sleep(speed)
        st.rerun()


if __name__ == "__main__":
    main()
