"""
AeroLink AI - Status Panel Component
"""

import streamlit as st

CHANNEL_ICONS = {"WiFi": "📶", "5G": "🗼", "Satellite": "🛰️"}
WEATHER_ICONS = {"clear": "☀️", "cloudy": "⛅", "rainy": "🌧️", "stormy": "⛈️"}


def _health_color(score):
    if score >= 70: return "#00e676"
    elif score >= 40: return "#ffea00"
    else: return "#ff1744"


def _prob_color(prob):
    if prob < 0.40: return "#00e676"
    elif prob < 0.70: return "#ffea00"
    else: return "#ff1744"


def _card(channel, is_active, score, prob, signal, lat, loss, theme="dark"):
    border = "#4a9eff" if is_active else "#1e3a6e"
    bg     = "rgba(74,158,255,0.07)" if is_active else "rgba(255,255,255,0.02)"
    badge  = '<span style="background:#4a9eff;color:#000;font-size:10px;padding:2px 8px;border-radius:20px;font-weight:700;margin-left:8px;">ACTIVE</span>' if is_active else ""
    hc     = _health_color(score)
    pc     = _prob_color(prob)
    icon   = CHANNEL_ICONS.get(channel, "")
    text_col = "#0a1a2a" if theme == "light" else "#ffffff"


    st.markdown(f'<div style="font-size:18px;font-weight:700;color:#8899aa;margin-bottom:14px;">{icon} {channel}{badge}</div>', unsafe_allow_html=True)

    st.markdown(f'''
    <div style="margin-bottom:10px;">
        <div style="color:#8899aa;font-size:11px;letter-spacing:2px;margin-bottom:4px;">HEALTH SCORE</div>
        <div style="background:#111827;border-radius:6px;height:8px;overflow:hidden;">
            <div style="width:{min(score,100)}%;height:100%;background:{hc};border-radius:6px;"></div>
        </div>
        <div style="color:{hc};font-size:20px;font-weight:800;margin-top:4px;">{score:.1f}</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f'''
    <div style="margin-bottom:10px;">
        <div style="color:#8899aa;font-size:11px;letter-spacing:2px;margin-bottom:4px;">FAILURE PROBABILITY</div>
        <div style="background:#111827;border-radius:6px;height:8px;overflow:hidden;">
            <div style="width:{min(prob*100,100):.1f}%;height:100%;background:{pc};border-radius:6px;"></div>
        </div>
        <div style="color:{pc};font-size:20px;font-weight:800;margin-top:4px;">{prob*100:.1f}%</div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown(f'''
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:12px;">
        <div style="text-align:center;">
            <div style="color:#8899aa;font-size:10px;">SIG</div>
            <div style="color:#8899aa;font-size:13px;font-weight:700;">{signal:.0f}%</div>
        </div>
        <div style="text-align:center;">
            <div style="color:#8899aa;font-size:10px;">LAT</div>
            <div style="color:#8899aa;font-size:13px;font-weight:700;">{lat:.0f}ms</div>
        </div>
        <div style="text-align:center;">
            <div style="color:#8899aa;font-size:10px;">LOSS</div>
            <div style="color:#8899aa;font-size:13px;font-weight:700;">{loss:.1f}%</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_status_panel(snapshot: dict, theme: str = "dark"):
    is_light = (theme == "light")
    hero_bg  = "linear-gradient(135deg,#dce8f5 0%,#c8ddf0 100%)" if is_light else "linear-gradient(135deg,#0a0f1e 0%,#0d1b3e 100%)"
    hero_border = "#7ab0d8" if is_light else "#1e3a6e"
    text_color  = "#0a1a2a" if is_light else "#ffffff"
    label_color = "#1a5a9a" if is_light else "#4a9eff"
    active   = snapshot["active_channel"]
    scores   = snapshot["health_scores"]
    probs    = snapshot["failure_probs"]
    readings = snapshot["latest_readings"]
    switches = snapshot["switch_count"]
    weather  = readings.get(active, {}).get("weather", "clear")
    w_icon   = WEATHER_ICONS.get(weather, "🌤️")
    ch_icon  = CHANNEL_ICONS.get(active, "")

    # ── Hero banner ───────────────────────────────────────────────────────────
    st.markdown(f'''
    <div style="background:{hero_bg};border:1px solid {hero_border};border-radius:16px;padding:28px 36px;margin-bottom:24px;display:flex;align-items:center;justify-content:space-between;">
        <div>
            <div style="color:#4a9eff;font-size:13px;letter-spacing:3px;font-family:Courier New,monospace;margin-bottom:6px;">ACTIVE CHANNEL</div>
            <div style="color:{text_color};font-size:42px;font-weight:800;line-height:1;">{ch_icon} {active}</div>
            <div style="color:#4a9eff;font-size:13px;margin-top:8px;font-family:Courier New,monospace;">{w_icon} WEATHER: {weather.upper()}</div>
        </div>
        <div style="text-align:right;">
            <div style="color:#4a9eff;font-size:13px;letter-spacing:3px;font-family:Courier New,monospace;margin-bottom:6px;">TOTAL SWITCHES</div>
            <div style="color:{text_color};font-size:48px;font-weight:800;">{switches}</div>
            <div style="color:#4a9eff;font-size:12px;font-family:Courier New,monospace;">CHANNEL HANDOFFS</div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # ── Channel cards ─────────────────────────────────────────────────────────
    cols = st.columns(3)
    for i, channel in enumerate(["WiFi", "5G", "Satellite"]):
        data = readings.get(channel, {})
        with cols[i]:
            _card(
                channel=channel,
                is_active=(channel == active),
                score=scores.get(channel, 0),
                prob=probs.get(channel, 0),
                signal=data.get("signal_strength", 0),
                lat=data.get("latency", 0),
                loss=data.get("packet_loss", 0),
            )
