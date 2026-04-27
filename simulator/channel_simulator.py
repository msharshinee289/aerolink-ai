import random
import numpy as np
from datetime import datetime
from .weather_engine import WeatherEngine


class Channel:
    """
    Represents a single communication channel (WiFi, 5G, or Satellite).
    Each channel has base characteristics and can enter degradation events.
    """

    # Base ranges per channel type
    BASE_PROFILES = {
        "WiFi": {
            "signal": (70, 95),    # strong but limited range
            "latency": (10, 40),   # low latency
            "loss": (0, 3),        # low packet loss
        },
        "5G": {
            "signal": (60, 90),
            "latency": (15, 50),
            "loss": (0, 4),
        },
        "Satellite": {
            "signal": (50, 80),    # weaker but always available
            "latency": (200, 400), # high latency by nature
            "loss": (1, 6),
        },
    }

    def __init__(self, name):
        self.name = name
        self.profile = self.BASE_PROFILES[name]
        self.is_degrading = False
        self.degradation_ticks = 0
        self.degradation_duration = 0

    def _maybe_start_degradation(self):
        """3% chance each tick to start a degradation event."""
        if not self.is_degrading and random.random() < 0.03:
            self.is_degrading = True
            self.degradation_ticks = 0
            self.degradation_duration = random.randint(8, 20)  # lasts 8-20 ticks

    def _degradation_factor(self):
        """
        Returns a worsening multiplier during a degradation event.
        Signal drops progressively — simulates real-world gradual failure.
        """
        if not self.is_degrading:
            return 1.0
        progress = self.degradation_ticks / self.degradation_duration
        return max(0.2, 1.0 - (progress * 0.8))  # drops to 20% at worst

    def read(self, weather_multipliers):
        """
        Generate one tick of channel readings.
        Returns a dict of signal, latency, packet_loss.
        """
        self._maybe_start_degradation()

        sig_mult, lat_mult, loss_mult = weather_multipliers
        deg_factor = self._degradation_factor()

        # Base values with random noise
        sig_min, sig_max = self.profile["signal"]
        lat_min, lat_max = self.profile["latency"]
        los_min, los_max = self.profile["loss"]

        signal = random.uniform(sig_min, sig_max) * sig_mult * deg_factor
        latency = random.uniform(lat_min, lat_max) * lat_mult / deg_factor
        loss = random.uniform(los_min, los_max) * loss_mult / deg_factor

        # Add small Gaussian noise for realism
        signal = max(0, min(100, signal + np.random.normal(0, 1.5)))
        latency = max(0, latency + np.random.normal(0, 2))
        loss = max(0, min(100, loss + np.random.normal(0, 0.3)))

        # Advance or end degradation
        if self.is_degrading:
            self.degradation_ticks += 1
            if self.degradation_ticks >= self.degradation_duration:
                self.is_degrading = False
                self.degradation_ticks = 0

        return {
            "signal_strength": round(signal, 2),
            "latency": round(latency, 2),
            "packet_loss": round(loss, 2),
            "is_degrading": self.is_degrading,
        }


class ChannelSimulator:
    """
    Manages all three channels and the weather engine.
    On each tick, produces a full snapshot of all channel readings.
    """

    def __init__(self):
        self.weather = WeatherEngine()
        self.channels = {
            "WiFi": Channel("WiFi"),
            "5G": Channel("5G"),
            "Satellite": Channel("Satellite"),
        }
        self.tick_count = 0

    def tick(self):
        """
        Advance simulation by one step.
        Returns a dict with readings from all channels + metadata.
        """
        self.tick_count += 1
        weather = self.weather.update()

        readings = {}
        for name, channel in self.channels.items():
            multipliers = self.weather.get_multipliers(name)
            data = channel.read(multipliers)
            data["channel"] = name
            data["weather"] = weather
            data["timestamp"] = datetime.now().isoformat()
            data["tick"] = self.tick_count
            readings[name] = data

        return readings

    def get_weather(self):
        return self.weather.get_current_weather()