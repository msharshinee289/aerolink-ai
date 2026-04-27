"""
AeroLink AI - Model Tests
----------------------------
Tests that the trained model loads correctly
and returns valid predictions.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from model.predictor import Predictor
from simulator.channel_simulator import ChannelSimulator


@pytest.fixture(scope="module")
def predictor():
    """Load predictor once for all tests in this module."""
    return Predictor()


@pytest.fixture(scope="module")
def simulator():
    return ChannelSimulator()


class TestPredictor:

    def test_model_loads_without_error(self, predictor):
        assert predictor.model is not None

    def test_feature_cols_are_set(self, predictor):
        assert isinstance(predictor.feature_cols, list)
        assert len(predictor.feature_cols) > 0

    def test_predict_returns_float(self, predictor, simulator):
        readings = simulator.tick()
        for ch, data in readings.items():
            prob = predictor.predict(ch, data)
            assert isinstance(prob, float), \
                f"Expected float, got {type(prob)} for {ch}"

    def test_predict_returns_valid_probability(self, predictor, simulator):
        readings = simulator.tick()
        for ch, data in readings.items():
            prob = predictor.predict(ch, data)
            assert 0.0 <= prob <= 1.0, \
                f"{ch} probability out of range: {prob}"

    def test_predict_all_returns_all_channels(self, predictor, simulator):
        readings = simulator.tick()
        probs = predictor.predict_all(readings)
        assert set(probs.keys()) == {"WiFi", "5G", "Satellite"}

    def test_predict_all_probabilities_are_valid(self, predictor, simulator):
        readings = simulator.tick()
        probs = predictor.predict_all(readings)
        for ch, prob in probs.items():
            assert 0.0 <= prob <= 1.0, \
                f"{ch} probability out of range: {prob}"

    def test_history_builds_up_per_channel(self, predictor, simulator):
        """Ensure rolling history grows correctly."""
        for _ in range(10):
            readings = simulator.tick()
            predictor.predict_all(readings)
        # History should have entries for each channel
        for ch in ["WiFi", "5G", "Satellite"]:
            assert len(predictor.history[ch]) > 0

    def test_degrading_channel_scores_higher_probability(self, predictor):
        """
        A reading with critically low signal should score
        a higher failure probability than a healthy one.
        """
        healthy_reading = {
            "signal_strength": 90.0,
            "latency": 20.0,
            "packet_loss": 1.0,
            "weather": "clear",
            "is_degrading": False,
        }
        failing_reading = {
            "signal_strength": 15.0,
            "latency": 450.0,
            "packet_loss": 18.0,
            "weather": "stormy",
            "is_degrading": True,
        }

        # Feed some history first so rolling features are meaningful
        for _ in range(6):
            predictor.predict("WiFi", healthy_reading)

        healthy_prob = predictor.predict("WiFi", healthy_reading)

        for _ in range(6):
            predictor.predict("5G", failing_reading)

        failing_prob = predictor.predict("5G", failing_reading)

        assert failing_prob > healthy_prob, (
            f"Expected failing ({failing_prob:.3f}) > "
            f"healthy ({healthy_prob:.3f})"
        )
