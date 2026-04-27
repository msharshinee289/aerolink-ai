"""
AeroLink AI - Switch Logic
-----------------------------
Reads AI predictions from the Predictor and decides
whether to trigger a channel switch.

Key features:
  - Configurable failure threshold (default 70%)
  - Flap prevention via cooldown timer
  - Reasons logged for every switch
  - Calls Gemini explainer after every switch
"""

import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

FAILURE_THRESHOLD = float(os.getenv("FAILURE_THRESHOLD", 0.70))
SWITCH_COOLDOWN   = int(os.getenv("SWITCH_COOLDOWN", 5))     # seconds

# Warning threshold — log a yellow warning before a full switch
WARNING_THRESHOLD = 0.45


class SwitchLogic:
    """
    Evaluates AI predictions each tick and triggers channel
    switches when necessary.

    Works alongside ChannelManager (state) and Predictor (AI).
    Optionally calls the Gemini Explainer for human-readable logs.
    """

    def __init__(self, channel_manager, explainer=None):
        """
        Parameters
        ----------
        channel_manager : ChannelManager
            The shared state manager.
        explainer : Explainer | None
            Gemini explainer. If None, switches still work
            but without AI-generated explanations.
        """
        self.manager   = channel_manager
        self.explainer = explainer
        self._last_switch_ts: float = 0.0   # Unix timestamp of last switch

    # ── Main Entry Point ───────────────────────────────────────────────────────

    def evaluate(self, readings: dict, probs: dict):
        """
        Called every tick by main.py.

        Parameters
        ----------
        readings : dict
            Latest channel readings from ChannelSimulator.tick()
        probs : dict
            Failure probabilities from Predictor.predict_all()
        """
        # 1. Push new data into the state manager
        self.manager.update_readings(readings)
        self.manager.update_failure_probs(probs)

        active = self.manager.active_channel
        active_prob = probs.get(active, 0.0)

        # 2. Log warnings for channels approaching threshold
        self._check_warnings(probs)

        # 3. Decide whether to switch
        if active_prob >= FAILURE_THRESHOLD:
            self._attempt_switch(active, active_prob, readings)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _check_warnings(self, probs: dict):
        """Log yellow warnings for channels between warning and failure threshold."""
        for channel, prob in probs.items():
            if WARNING_THRESHOLD <= prob < FAILURE_THRESHOLD:
                self.manager.log_warning(
                    channel,
                    f"Signal degrading — failure probability {prob * 100:.1f}%"
                )

    def _attempt_switch(self, from_channel: str, prob: float, readings: dict):
        """
        Try to switch away from a failing channel.
        Respects the cooldown timer (flap prevention).
        """
        now = time.time()
        seconds_since_last = now - self._last_switch_ts

        # Flap prevention — don't switch if cooldown hasn't elapsed
        if seconds_since_last < SWITCH_COOLDOWN:
            remaining = SWITCH_COOLDOWN - seconds_since_last
            self.manager.log_warning(
                from_channel,
                f"Switch suppressed — cooldown active ({remaining:.1f}s remaining)"
            )
            return

        # Find the best alternative channel
        to_channel = self.manager.get_best_alternative()

        if to_channel is None:
            self.manager.log_warning(
                from_channel,
                "No alternative channel available — staying on current channel."
            )
            return

        # Log the AI prediction event
        self.manager.log_prediction(from_channel, prob)

        # Build a short human reason (used even without Gemini)
        reason = self._build_reason(from_channel, prob, readings)

        # Get Gemini explanation if available
        explanation = ""
        if self.explainer:
            try:
                explanation = self.explainer.explain_switch(
                    from_channel=from_channel,
                    to_channel=to_channel,
                    readings=readings,
                    prob=prob,
                )
            except Exception as e:
                explanation = f"(Explanation unavailable: {e})"

        # Execute the switch
        self.manager.perform_switch(
            to_channel=to_channel,
            reason=reason,
            explanation=explanation,
        )

        self._last_switch_ts = now

    def _build_reason(self, channel: str, prob: float, readings: dict) -> str:
        """
        Build a short, structured reason string for the switch.
        This appears in the event log even without Gemini.
        """
        data    = readings.get(channel, {})
        signal  = data.get("signal_strength", 0)
        latency = data.get("latency", 0)
        loss    = data.get("packet_loss", 0)
        weather = data.get("weather", "unknown")

        parts = []

        if signal < 45:
            parts.append(f"signal critically low ({signal:.1f}%)")
        if latency > 250:
            parts.append(f"latency spiked ({latency:.0f}ms)")
        if loss > 10:
            parts.append(f"packet loss high ({loss:.1f}%)")
        if weather in ("rainy", "stormy"):
            parts.append(f"weather: {weather}")

        if not parts:
            parts.append(f"AI failure confidence {prob * 100:.1f}%")

        return "; ".join(parts).capitalize()
