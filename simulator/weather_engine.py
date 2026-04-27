import random

class WeatherEngine:
    """
    Simulates weather conditions and applies realistic
    degradation multipliers to each channel type.

    Weather States: clear, cloudy, rainy, stormy
    """

    WEATHER_STATES = ["clear", "cloudy", "rainy", "stormy"]

    # How likely weather is to change each tick (5% chance)
    CHANGE_PROBABILITY = 0.05

    # Multipliers: 1.0 = no effect, lower = worse signal
    # Format: { weather: { channel: (signal_mult, latency_mult, loss_mult) } }
    EFFECTS = {
        "clear": {
            "WiFi":     (1.0,  1.0,  1.0),
            "5G":       (1.0,  1.0,  1.0),
            "Satellite":(1.0,  1.0,  1.0),
        },
        "cloudy": {
            "WiFi":     (0.95, 1.05, 1.1),
            "5G":       (0.97, 1.03, 1.0),
            "Satellite":(0.90, 1.10, 1.2),
        },
        "rainy": {
            "WiFi":     (0.80, 1.20, 1.5),
            "5G":       (0.90, 1.15, 1.2),
            "Satellite":(0.60, 1.50, 2.0),  # satellite worst in rain
        },
        "stormy": {
            "WiFi":     (0.55, 1.80, 3.0),
            "5G":       (0.70, 1.50, 2.0),
            "Satellite":(0.30, 2.50, 4.0),  # satellite nearly unusable
        },
    }

    def __init__(self):
        self.current_weather = "clear"

    def update(self):
        """Randomly transition to a new weather state."""
        if random.random() < self.CHANGE_PROBABILITY:
            self.current_weather = random.choice(self.WEATHER_STATES)
        return self.current_weather

    def get_multipliers(self, channel_name):
        """
        Returns (signal_mult, latency_mult, loss_mult)
        for the given channel under current weather.
        """
        return self.EFFECTS[self.current_weather][channel_name]

    def get_current_weather(self):
        return self.current_weather