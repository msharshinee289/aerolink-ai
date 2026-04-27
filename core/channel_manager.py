"""
AeroLink AI - Channel Manager
--------------------------------
Acts as the central state store for the entire system.
Tracks:
  - Which channel is currently active
  - Health scores for all 3 channels
  - Full history of switch events
  - Latest readings snapshot

Everything else (switch logic, dashboard) reads from here.
"""

from datetime import datetime
from collections import deque


# Health score weights — how much each metric contributes to channel score
SIGNAL_WEIGHT = 0.50
LATENCY_WEIGHT = 0.30
LOSS_WEIGHT = 0.20

# Per-channel latency normalization ceiling
# Satellite naturally has high latency — we normalize against a higher ceiling
LATENCY_CEILING = {
    "WiFi":      200.0,
    "5G":        200.0,
    "Satellite": 600.0,
}

MAX_LOG_ENTRIES = 100   # keep last 100 events in the log


class ChannelManager:
    """
    Central state manager for AeroLink.
    The dashboard and switch logic both read/write through this class.
    """

    CHANNELS = ["WiFi", "5G", "Satellite"]

    def __init__(self):
        # Start on WiFi by default
        self.active_channel: str = "WiFi"

        # Latest raw readings snapshot { channel: {signal, latency, loss, ...} }
        self.latest_readings: dict = {}

        # Latest AI failure probabilities { channel: float }
        self.failure_probs: dict = {ch: 0.0 for ch in self.CHANNELS}

        # Computed health scores 0-100 { channel: float }
        self.health_scores: dict = {ch: 100.0 for ch in self.CHANNELS}

        # Event log — each entry is a dict
        self.event_log: deque = deque(maxlen=MAX_LOG_ENTRIES)

        # Timestamp of the last switch (used for cooldown)
        self.last_switch_time: datetime | None = None

        # Total number of switches performed
        self.switch_count: int = 0

        # Log the startup event
        self._log_event("system", f"AeroLink started. Active channel: {self.active_channel}")

    # ── State Updates ──────────────────────────────────────────────────────────

    def update_readings(self, readings: dict):
        """
        Called every tick with fresh simulator output.
        Stores readings and recomputes health scores.
        """
        self.latest_readings = readings
        for channel, data in readings.items():
            self.health_scores[channel] = self._compute_health(channel, data)

    def update_failure_probs(self, probs: dict):
        """Store latest AI predictions { channel: probability }."""
        self.failure_probs = probs

    def perform_switch(self, to_channel: str, reason: str, explanation: str = ""):
        """
        Execute a channel switch.
        Logs the event and updates state.
        """
        from_channel = self.active_channel
        self.active_channel = to_channel
        self.last_switch_time = datetime.now()
        self.switch_count += 1

        self._log_event(
            event_type="switch",
            message=(
                f"Switched {from_channel} → {to_channel}. "
                f"Reason: {reason}"
            ),
            extra={
                "from":        from_channel,
                "to":          to_channel,
                "reason":      reason,
                "explanation": explanation,
                "prob_at_switch": self.failure_probs.get(from_channel, 0.0),
            }
        )

    def log_warning(self, channel: str, message: str):
        """Log a degradation warning (yellow event)."""
        self._log_event("warning", f"[{channel}] {message}")

    def log_prediction(self, channel: str, prob: float):
        """Log an AI high-confidence failure prediction (red event)."""
        self._log_event(
            "prediction",
            f"AI predicted {channel} failure (confidence: {prob * 100:.1f}%)"
        )

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_best_alternative(self) -> str | None:
        """
        Returns the channel (excluding active) with the highest health score.
        Returns None if no alternative is available.
        """
        alternatives = {
            ch: score
            for ch, score in self.health_scores.items()
            if ch != self.active_channel
        }
        if not alternatives:
            return None
        return max(alternatives, key=alternatives.get)

    def get_active_reading(self) -> dict:
        """Returns the latest reading for the currently active channel."""
        return self.latest_readings.get(self.active_channel, {})

    def get_event_log(self) -> list:
        """Returns event log as a list, newest first."""
        return list(reversed(self.event_log))

    def get_snapshot(self) -> dict:
        """
        Full state snapshot used by the dashboard.
        Returns everything needed to render the UI in one call.
        """
        return {
            "active_channel":  self.active_channel,
            "health_scores":   self.health_scores.copy(),
            "failure_probs":   self.failure_probs.copy(),
            "latest_readings": self.latest_readings.copy(),
            "switch_count":    self.switch_count,
            "event_log":       self.get_event_log(),
            "last_switch":     (
                self.last_switch_time.isoformat()
                if self.last_switch_time else None
            ),
        }

    # ── Internal ───────────────────────────────────────────────────────────────

    def _compute_health(self, channel: str, data: dict) -> float:
        """
        Compute a 0–100 health score for a channel.

        Formula:
            score = (signal_norm * 0.5) +
                    (latency_norm * 0.3) +
                    (loss_norm * 0.2)

        Each metric is normalized to 0–1 then multiplied by 100.
        """
        signal  = data.get("signal_strength", 0)
        latency = data.get("latency", 0)
        loss    = data.get("packet_loss", 0)

        # Signal: higher is better → normalize directly
        signal_norm = max(0.0, min(1.0, signal / 100.0))

        # Latency: lower is better → invert
        lat_ceil = LATENCY_CEILING.get(channel, 200.0)
        latency_norm = max(0.0, 1.0 - (latency / lat_ceil))

        # Packet loss: lower is better → invert (max meaningful loss = 20%)
        loss_norm = max(0.0, 1.0 - (loss / 20.0))

        score = (
            signal_norm  * SIGNAL_WEIGHT  +
            latency_norm * LATENCY_WEIGHT +
            loss_norm    * LOSS_WEIGHT
        ) * 100

        return round(score, 2)

    def _log_event(self, event_type: str, message: str, extra: dict = None):
        """Append a structured event to the log."""
        entry = {
            "timestamp":  datetime.now().isoformat(),
            "type":       event_type,   # "system" | "warning" | "prediction" | "switch"
            "message":    message,
        }
        if extra:
            entry.update(extra)
        self.event_log.append(entry)
