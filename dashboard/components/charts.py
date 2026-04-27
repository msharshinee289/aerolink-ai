"""
AeroLink AI - Charts Component
---------------------------------
Renders live Plotly charts for:
  - Signal Strength over time (all 3 channels)
  - Latency over time (all 3 channels)
  - Packet Loss over time (all 3 channels)
"""

import streamlit as st
import plotly.graph_objects as go
from collections import deque

# How many ticks to show on the chart x-axis
MAX_HISTORY = 60

CHANNEL_COLORS = {
    "WiFi":      "#4a9eff",
    "5G":        "#00e676",
    "Satellite": "#ff9100",
}

CHANNEL_FILL_COLORS = {
    "WiFi":      "rgba(74,158,255,0.05)",
    "5G":        "rgba(0,230,118,0.05)",
    "Satellite": "rgba(255,145,0,0.05)",
}

# Shared chart history — persisted in Streamlit session state
def _init_history():
    if "chart_history" not in st.session_state:
        st.session_state.chart_history = {
            ch: {
                "signal":  deque(maxlen=MAX_HISTORY),
                "latency": deque(maxlen=MAX_HISTORY),
                "loss":    deque(maxlen=MAX_HISTORY),
                "ticks":   deque(maxlen=MAX_HISTORY),
            }
            for ch in ["WiFi", "5G", "Satellite"]
        }


def update_history(readings: dict, tick: int):
    """Push latest readings into chart history."""
    _init_history()
    for channel, data in readings.items():
        h = st.session_state.chart_history[channel]
        h["signal"].append(data.get("signal_strength", 0))
        h["latency"].append(data.get("latency", 0))
        h["loss"].append(data.get("packet_loss", 0))
        h["ticks"].append(tick)


def _base_layout(title: str, y_label: str, y_range=None) -> dict:
    """Shared dark-theme Plotly layout."""
    layout = dict(
        title=dict(
            text=title,
            font=dict(color="#4a9eff", size=13, family="Courier New"),
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(10,15,30,0.6)",
        font=dict(color="#8899aa", family="Courier New"),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.04)",
            title="Tick",
            color="#4a6080",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.04)",
            title=y_label,
            color="#4a6080",
        ),
        legend=dict(
            bgcolor="rgba(10,15,30,0.0)",
            bordercolor="rgba(74,158,255,0.1)",
            borderwidth=1,
            font=dict(color="#7a858f", size=11, family="Courier New"),
        ),
        margin=dict(l=50, r=20, t=40, b=40),
        height=240,
    )
    if y_range:
        layout["yaxis"]["range"] = y_range
    return layout


def render_charts():
    """Render all three live charts."""
    _init_history()
    hist = st.session_state.chart_history

    # ── Signal Strength ───────────────────────────────────────────────────────
    fig_sig = go.Figure()
    for ch, color in CHANNEL_COLORS.items():
        ticks  = list(hist[ch]["ticks"])
        values = list(hist[ch]["signal"])
        if not ticks:
            continue
        fig_sig.add_trace(go.Scatter(
            x=ticks, y=values,
            name=ch,
            line=dict(color=color, width=2),
            fill="tozeroy",
            fillcolor=CHANNEL_FILL_COLORS[ch],
            mode="lines",
        ))

    # Danger zone line at 40%
    fig_sig.add_hline(
        y=40, line_dash="dash",
        line_color="rgba(255,23,68,0.4)",
        annotation_text="CRITICAL",
        annotation_font_color="rgba(255,23,68,0.6)",
        annotation_font_size=10,
    )
    fig_sig.update_layout(**_base_layout("SIGNAL STRENGTH (%)", "%", [0, 100]))
    st.plotly_chart(fig_sig, use_container_width=True, config={"displayModeBar": False})

    # ── Latency + Packet Loss side by side ────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        fig_lat = go.Figure()
        for ch, color in CHANNEL_COLORS.items():
            ticks  = list(hist[ch]["ticks"])
            values = list(hist[ch]["latency"])
            if not ticks:
                continue
            fig_lat.add_trace(go.Scatter(
                x=ticks, y=values,
                name=ch,
                line=dict(color=color, width=2),
                mode="lines",
            ))
        fig_lat.update_layout(**_base_layout("LATENCY (ms)", "ms"))
        st.plotly_chart(fig_lat, use_container_width=True, config={"displayModeBar": False})

    with col2:
        fig_loss = go.Figure()
        for ch, color in CHANNEL_COLORS.items():
            ticks  = list(hist[ch]["ticks"])
            values = list(hist[ch]["loss"])
            if not ticks:
                continue
            fig_loss.add_trace(go.Scatter(
                x=ticks, y=values,
                name=ch,
                line=dict(color=color, width=2),
                mode="lines",
            ))
        fig_loss.add_hline(
            y=12, line_dash="dash",
            line_color="rgba(255,23,68,0.4)",
            annotation_text="CRITICAL",
            annotation_font_color="rgba(255,23,68,0.6)",
            annotation_font_size=10,
        )
        fig_loss.update_layout(**_base_layout("PACKET LOSS (%)", "%", [0, 25]))
        st.plotly_chart(fig_loss, use_container_width=True, config={"displayModeBar": False})
