"""
AeroLink AI - Simulator Tests
--------------------------------
Tests that the simulator generates valid data
and that weather correctly affects channel readings.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from simulator.channel_simulator import ChannelSimulator
from simulator.weather_engine import WeatherEngine


class TestWeatherEngine:

    def test_initial_weather_is_clear(self):
        engine = WeatherEngine()
        assert engine.get_current_weather() == "clear"

    def test_weather_states_are_valid(self):
        engine = WeatherEngine()
        valid_states = {"clear", "cloudy", "rainy", "stormy"}
        # Run many updates and ensure only valid states appear
        for _ in range(200):
            engine.update()
            assert engine.get_current_weather() in valid_states

    def test_multipliers_exist_for_all_channels(self):
        engine = WeatherEngine()
        for channel in ["WiFi", "5G", "Satellite"]:
            mults = engine.get_multipliers(channel)
            assert len(mults) == 3  # signal, latency, loss

    def test_stormy_weakens_satellite_most(self):
        engine = WeatherEngine()
        engine.current_weather = "stormy"
        sat_sig_mult = engine.get_multipliers("Satellite")[0]
        wifi_sig_mult = engine.get_multipliers("WiFi")[0]
        # Satellite should be weaker than WiFi in a storm
        assert sat_sig_mult < wifi_sig_mult


class TestChannelSimulator:

    def setup_method(self):
        self.sim = ChannelSimulator()

    def test_tick_returns_all_three_channels(self):
        readings = self.sim.tick()
        assert set(readings.keys()) == {"WiFi", "5G", "Satellite"}

    def test_signal_in_valid_range(self):
        for _ in range(50):
            readings = self.sim.tick()
            for ch, data in readings.items():
                assert 0 <= data["signal_strength"] <= 100, \
                    f"{ch} signal out of range: {data['signal_strength']}"

    def test_latency_is_positive(self):
        for _ in range(50):
            readings = self.sim.tick()
            for ch, data in readings.items():
                assert data["latency"] >= 0, \
                    f"{ch} latency is negative: {data['latency']}"

    def test_packet_loss_in_valid_range(self):
        for _ in range(50):
            readings = self.sim.tick()
            for ch, data in readings.items():
                assert 0 <= data["packet_loss"] <= 100, \
                    f"{ch} packet loss out of range: {data['packet_loss']}"

    def test_satellite_has_higher_latency_than_wifi_on_average(self):
        wifi_lats = []
        sat_lats  = []
        for _ in range(100):
            readings = self.sim.tick()
            wifi_lats.append(readings["WiFi"]["latency"])
            sat_lats.append(readings["Satellite"]["latency"])
        assert sum(sat_lats) / len(sat_lats) > sum(wifi_lats) / len(wifi_lats)

    def test_tick_count_increments(self):
        for i in range(1, 6):
            readings = self.sim.tick()
            for ch, data in readings.items():
                assert data["tick"] == i

    def test_readings_contain_required_keys(self):
        readings = self.sim.tick()
        required = {"signal_strength", "latency", "packet_loss",
                    "is_degrading", "channel", "weather", "timestamp", "tick"}
        for ch, data in readings.items():
            assert required.issubset(data.keys()), \
                f"{ch} missing keys: {required - data.keys()}"
