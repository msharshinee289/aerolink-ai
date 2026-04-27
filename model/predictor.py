"""
AeroLink AI - Real-Time Predictor
-----------------------------------
Loads the trained Random Forest model and exposes a simple
predict() function that the switch logic calls every tick.
"""

import os
import joblib
import numpy as np
import pandas as pd
from collections import deque

MODEL_PATH = os.path.join(os.path.dirname(__file__), "saved_model.pkl")

# How many past readings to keep per channel for rolling features
HISTORY_SIZE = 10


class Predictor:
    """
    Wraps the trained model and maintains a short history
    of readings per channel so rolling features can be computed
    in real time (mirrors what train_model.py does at training time).
    """

    WEATHER_MAP  = {"clear": 0, "cloudy": 1, "rainy": 2, "stormy": 3}
    CHANNEL_MAP  = {"WiFi": 0, "5G": 1, "Satellite": 2}
    WINDOW_SIZE  = 5

    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}.\n"
                "Please run:  python -m model.train_model"
            )

        payload          = joblib.load(MODEL_PATH)
        self.model       = payload["model"]
        self.feature_cols = payload["features"]

        # Circular buffer: stores last HISTORY_SIZE readings per channel
        self.history: dict[str, deque] = {
            "WiFi":      deque(maxlen=HISTORY_SIZE),
            "5G":        deque(maxlen=HISTORY_SIZE),
            "Satellite": deque(maxlen=HISTORY_SIZE),
        }

        print("✓ Predictor loaded model successfully.")

    # ── Public API ─────────────────────────────────────────────────────────────

    def predict(self, channel_name: str, reading: dict) -> float:
        """
        Given one fresh reading for a channel, return the
        probability (0.0 → 1.0) that the channel will fail soon.

        Parameters
        ----------
        channel_name : str
            "WiFi", "5G", or "Satellite"
        reading : dict
            Keys: signal_strength, latency, packet_loss,
                  weather, is_degrading

        Returns
        -------
        float
            Failure probability between 0.0 and 1.0
        """
        self.history[channel_name].append(reading)
        features = self._build_features(channel_name, reading)
        prob = self.model.predict_proba(features)[0][1]  # prob of class 1
        return round(float(prob), 4)

    def predict_all(self, readings: dict) -> dict:
        """
        Convenience wrapper — predict for all 3 channels at once.

        Parameters
        ----------
        readings : dict
            Output of ChannelSimulator.tick()

        Returns
        -------
        dict  { "WiFi": 0.12, "5G": 0.85, "Satellite": 0.03 }
        """
        return {
            name: self.predict(name, data)
            for name, data in readings.items()
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _build_features(self, channel_name: str, reading: dict) -> pd.DataFrame:
        """
        Reconstruct the same feature vector that was used during training.
        Uses the channel's rolling history for window-based features.
        """
        hist = list(self.history[channel_name])

        signals  = [r["signal_strength"] for r in hist]
        latencies = [r["latency"]         for r in hist]
        losses   = [r["packet_loss"]      for r in hist]

        # Rolling means
        sig_mean = np.mean(signals[-self.WINDOW_SIZE:])
        lat_mean = np.mean(latencies[-self.WINDOW_SIZE:])
        los_mean = np.mean(losses[-self.WINDOW_SIZE:])

        # Rate of change (last vs second-to-last)
        sig_delta = signals[-1] - signals[-2]  if len(signals) >= 2 else 0.0
        lat_delta = latencies[-1] - latencies[-2] if len(latencies) >= 2 else 0.0
        los_delta = losses[-1] - losses[-2]    if len(losses) >= 2 else 0.0

        # Rolling std
        sig_std = np.std(signals[-self.WINDOW_SIZE:]) if len(signals) > 1 else 0.0

        row = {
            "signal_strength":  reading["signal_strength"],
            "latency":          reading["latency"],
            "packet_loss":      reading["packet_loss"],
            "signal_roll_mean": sig_mean,
            "latency_roll_mean": lat_mean,
            "loss_roll_mean":   los_mean,
            "signal_delta":     sig_delta,
            "latency_delta":    lat_delta,
            "loss_delta":       los_delta,
            "signal_std":       sig_std,
            "weather_score":    self.WEATHER_MAP.get(reading.get("weather", "clear"), 0),
            "channel_id":       self.CHANNEL_MAP.get(channel_name, 0),
            "is_degrading":     int(reading.get("is_degrading", False)),
        }

        return pd.DataFrame([row])[self.feature_cols]
