"""
AeroLink AI - Event Log Component
"""

import streamlit as st
from datetime import datetime

EVENT_STYLES = {
    "system":     {"icon": "🟢", "color": "#00e676", "bg": "rgba(0,230,118,0.06)",   "border": "rgba(0,230,118,0.2)"},
    "warning":    {"icon": "🟡", "color": "#ffea00", "bg": "rgba(255,234,0,0.06)",   "border": "rgba(255,234,0,0.2)"},
    "prediction": {"icon": "🔴", "color": "#ff1744", "bg": "rgba(255,23,68,0.06)",   "border": "rgba(255,23,68,0.2)"},
    "switch":     {"icon": "🔵", "color": "#4a9eff", "bg": "rgba(74,158,255,0.08)",  "border": "rgba(74,158,255,0.3)"},
}
DEFAULT_STYLE = EVENT_STYLES["system"]


def _fmt_time(iso_str: str) -> str:
    try:
        return datetime.fromisoformat(iso_str).strftime("%H:%M:%S")
    except Exception:
        return iso_str


def render_event_log(event_log: list, max_entries: int = 12):
    st.markdown(
        '<div style="color:#4a9eff;font-size:12px;letter-spacing:3px;font-family:Courier New,monospace;margin-bottom:12px;">SYSTEM EVENT LOG</div>',
        unsafe_allow_html=True,
    )

    if not event_log:
        st.markdown('<div style="color:#4a6080;font-family:Courier New;font-size:13px;">No events yet...</div>', unsafe_allow_html=True)
        return

    for entry in event_log[:max_entries]:
        s           = EVENT_STYLES.get(entry.get("type", "system"), DEFAULT_STYLE)
        time_s      = _fmt_time(entry.get("timestamp", ""))
        message     = entry.get("message", "")
        explanation = entry.get("explanation", "")

        # Main event row
        st.markdown(f'''
<div style="background:{s['bg']};border:1px solid {s['border']};border-radius:8px;padding:10px 14px;margin-bottom:8px;font-family:Courier New,monospace;">
    <div style="display:flex;justify-content:space-between;align-items:flex-start;">
        <div style="color:{s['color']};font-size:12px;font-weight:700;flex:1;">{s['icon']} {message}</div>
        <div style="color:#4a6080;font-size:11px;white-space:nowrap;margin-left:12px;">{time_s}</div>
    </div>
</div>''', unsafe_allow_html=True)

        # Gemini explanation as a separate block underneath
        if explanation:
            st.markdown(f'''
<div style="color:#8899aa;font-size:11px;margin:-4px 0 8px 12px;padding:6px 12px;border-left:2px solid {s['border']};font-style:italic;line-height:1.5;font-family:Courier New,monospace;">
    💬 {explanation}
</div>''', unsafe_allow_html=True)
