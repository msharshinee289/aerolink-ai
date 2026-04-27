"""
AeroLink AI - Switch Logic Tests
-----------------------------------
Tests that the switching engine:
  - Switches when failure probability exceeds threshold
  - Respects the cooldown timer (flap prevention)
  - Always picks the healthiest alternative channel
  - Does NOT switch when probability is below threshold
"""

import sys
import os
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core.channel_manager import ChannelManager
from core.switch_logic import SwitchLogic


def make_readings(
    wifi_sig=85, wifi_lat=20, wifi_loss=1,
    g5_sig=80,  g5_lat=30,  g5_loss=2,
    sat_sig=70, sat_lat=300, sat_loss=3,
    weather="clear",
):
    """Helper to build a fake readings dict."""
    def _make(sig, lat, loss):
        return {
            "signal_strength": sig,
            "latency": lat,
            "packet_loss": loss,
            "weather": weather,
            "is_degrading": False,
            "timestamp": "2026-01-01T00:00:00",
            "tick": 1,
        }
    return {
        "WiFi":      _make(wifi_sig, wifi_lat, wifi_loss),
        "5G":        _make(g5_sig,   g5_lat,   g5_loss),
        "Satellite": _make(sat_sig,  sat_lat,  sat_loss),
    }


@pytest.fixture
def manager():
    return ChannelManager()


@pytest.fixture
def logic(manager):
    return SwitchLogic(channel_manager=manager, explainer=None)


class TestSwitchLogic:

    def test_no_switch_below_threshold(self, manager, logic):
        """Should NOT switch when all probabilities are low."""
        readings = make_readings()
        probs = {"WiFi": 0.10, "5G": 0.05, "Satellite": 0.03}
        logic.evaluate(readings, probs)
        assert manager.active_channel == "WiFi"
        assert manager.switch_count == 0

    def test_switches_when_above_threshold(self, manager, logic):
        """Should switch when active channel probability exceeds 70%."""
        readings = make_readings(wifi_sig=20, wifi_lat=400, wifi_loss=15)
        probs = {"WiFi": 0.90, "5G": 0.10, "Satellite": 0.05}
        logic.evaluate(readings, probs)
        assert manager.active_channel != "WiFi"
        assert manager.switch_count == 1

    def test_switches_to_healthiest_channel(self, manager, logic):
        """Should pick the channel with the highest health score."""
        # Make 5G clearly healthier than Satellite
        readings = make_readings(
            wifi_sig=10, wifi_lat=500, wifi_loss=20,   # WiFi failing
            g5_sig=90,  g5_lat=15,   g5_loss=0.5,     # 5G very healthy
            sat_sig=40, sat_lat=350, sat_loss=8,        # Satellite mediocre
        )
        probs = {"WiFi": 0.95, "5G": 0.02, "Satellite": 0.10}
        logic.evaluate(readings, probs)
        assert manager.active_channel == "5G"

    def test_cooldown_prevents_rapid_switching(self, manager, logic):
        """Should not switch twice within the cooldown window."""
        readings = make_readings(wifi_sig=10, wifi_lat=500, wifi_loss=20)
        probs    = {"WiFi": 0.95, "5G": 0.90, "Satellite": 0.05}

        # First switch should happen
        logic.evaluate(readings, probs)
        first_channel = manager.active_channel
        count_after_first = manager.switch_count

        # Immediate second evaluation — cooldown should block it
        logic.evaluate(readings, probs)
        assert manager.switch_count == count_after_first  # no extra switch
        assert manager.active_channel == first_channel

    def test_switch_is_logged_in_event_log(self, manager, logic):
        """Switch events must appear in the event log."""
        readings = make_readings(wifi_sig=10, wifi_lat=500, wifi_loss=20)
        probs    = {"WiFi": 0.92, "5G": 0.05, "Satellite": 0.03}
        logic.evaluate(readings, probs)

        log = manager.get_event_log()
        event_types = [e["type"] for e in log]
        assert "switch" in event_types

    def test_warning_logged_below_threshold(self, manager, logic):
        """Warning events should appear when prob is between 45% and 70%."""
        readings = make_readings()
        probs    = {"WiFi": 0.55, "5G": 0.10, "Satellite": 0.05}
        logic.evaluate(readings, probs)

        log   = manager.get_event_log()
        types = [e["type"] for e in log]
        assert "warning" in types
        # But no switch should have happened
        assert manager.switch_count == 0

    def test_health_scores_update_each_tick(self, manager, logic):
        """Health scores must be recomputed on every evaluate() call."""
        readings1 = make_readings(wifi_sig=90)
        probs1    = {"WiFi": 0.05, "5G": 0.05, "Satellite": 0.05}
        logic.evaluate(readings1, probs1)
        score_high = manager.health_scores["WiFi"]

        readings2 = make_readings(wifi_sig=20)
        probs2    = {"WiFi": 0.30, "5G": 0.05, "Satellite": 0.05}
        logic.evaluate(readings2, probs2)
        score_low = manager.health_scores["WiFi"]

        assert score_high > score_low
