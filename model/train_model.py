"""
AeroLink AI - Model Training Script
------------------------------------
Run this ONCE before starting the app:
    python -m model.train_model

What this script does:
1. Simulates thousands of channel readings using ChannelSimulator
2. Engineers features (rolling averages, rate of change)
3. Labels each reading: 0 = Good, 1 = Failing Soon
4. Trains a Random Forest classifier
5. Saves the trained model to model/saved_model.pkl
"""

import os
import sys
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

# Add project root to path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.channel_simulator import ChannelSimulator

# ── Config ────────────────────────────────────────────────────────────────────
NUM_TICKS         = 3000        # total simulation ticks to generate
WINDOW_SIZE       = 5           # rolling window for feature engineering
FAILURE_SIG       = 40.0        # signal below this = failing
FAILURE_LAT       = 300.0       # latency above this = failing (WiFi/5G)
FAILURE_LOSS      = 12.0        # packet loss above this = failing
LOOKAHEAD         = 10          # ticks ahead to check for failure (label window)
OUTPUT_CSV        = os.path.join(os.path.dirname(__file__), "data", "training_data.csv")
OUTPUT_MODEL      = os.path.join(os.path.dirname(__file__), "saved_model.pkl")
# ──────────────────────────────────────────────────────────────────────────────


def generate_raw_data(num_ticks: int) -> pd.DataFrame:
    """Run the simulator and collect raw readings into a DataFrame."""
    print(f"[1/5] Generating {num_ticks} ticks of simulation data...")

    sim = ChannelSimulator()
    records = []

    for _ in range(num_ticks):
        readings = sim.tick()
        for channel_name, data in readings.items():
            records.append({
                "tick":            data["tick"],
                "channel":         channel_name,
                "signal_strength": data["signal_strength"],
                "latency":         data["latency"],
                "packet_loss":     data["packet_loss"],
                "weather":         data["weather"],
                "is_degrading":    int(data["is_degrading"]),
            })

    df = pd.DataFrame(records)
    print(f"    ✓ Generated {len(df)} rows across 3 channels.")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add rolling and rate-of-change features per channel.
    These give the model time-awareness without needing LSTM.
    """
    print("[2/5] Engineering features...")

    enhanced = []

    for channel in df["channel"].unique():
        ch_df = df[df["channel"] == channel].copy().reset_index(drop=True)

        # Rolling means (last N readings)
        ch_df["signal_roll_mean"] = (
            ch_df["signal_strength"].rolling(WINDOW_SIZE, min_periods=1).mean()
        )
        ch_df["latency_roll_mean"] = (
            ch_df["latency"].rolling(WINDOW_SIZE, min_periods=1).mean()
        )
        ch_df["loss_roll_mean"] = (
            ch_df["packet_loss"].rolling(WINDOW_SIZE, min_periods=1).mean()
        )

        # Rate of change (how fast is signal dropping?)
        ch_df["signal_delta"] = ch_df["signal_strength"].diff().fillna(0)
        ch_df["latency_delta"] = ch_df["latency"].diff().fillna(0)
        ch_df["loss_delta"]   = ch_df["packet_loss"].diff().fillna(0)

        # Rolling standard deviation (instability indicator)
        ch_df["signal_std"] = (
            ch_df["signal_strength"].rolling(WINDOW_SIZE, min_periods=1).std().fillna(0)
        )

        # Encode weather as a numeric score (clear=0, cloudy=1, rainy=2, stormy=3)
        weather_map = {"clear": 0, "cloudy": 1, "rainy": 2, "stormy": 3}
        ch_df["weather_score"] = ch_df["weather"].map(weather_map)

        # Encode channel as numeric (for the model)
        channel_map = {"WiFi": 0, "5G": 1, "Satellite": 2}
        ch_df["channel_id"] = channel_map[channel]

        enhanced.append(ch_df)

    result = pd.concat(enhanced).reset_index(drop=True)
    print(f"    ✓ Features engineered. Total columns: {len(result.columns)}")
    return result


def label_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Label each row as:
        0 = Good (channel is healthy)
        1 = Failing Soon (will fail within LOOKAHEAD ticks)

    Logic: look ahead LOOKAHEAD ticks per channel.
    If signal drops below threshold OR latency/loss spikes, label = 1.
    """
    print("[3/5] Labeling data (Good vs Failing Soon)...")

    labeled = []

    for channel in df["channel"].unique():
        ch_df = df[df["channel"] == channel].copy().reset_index(drop=True)
        labels = []

        for i in range(len(ch_df)):
            # Look at the next LOOKAHEAD rows
            window = ch_df.iloc[i: i + LOOKAHEAD]

            will_fail = (
                (window["signal_strength"] < FAILURE_SIG).any() or
                (window["packet_loss"] > FAILURE_LOSS).any() or
                # Satellite has naturally high latency — use a higher bar
                (
                    (channel != "Satellite") and
                    (window["latency"] > FAILURE_LAT).any()
                )
            )
            labels.append(1 if will_fail else 0)

        ch_df["label"] = labels
        labeled.append(ch_df)

    result = pd.concat(labeled).reset_index(drop=True)

    good    = (result["label"] == 0).sum()
    failing = (result["label"] == 1).sum()
    print(f"    ✓ Labels assigned → Good: {good} | Failing Soon: {failing}")
    return result


def train(df: pd.DataFrame):
    """Train a Random Forest classifier and print evaluation metrics."""
    print("[4/5] Training Random Forest model...")

    feature_cols = [
        "signal_strength", "latency", "packet_loss",
        "signal_roll_mean", "latency_roll_mean", "loss_roll_mean",
        "signal_delta", "latency_delta", "loss_delta",
        "signal_std", "weather_score", "channel_id", "is_degrading",
    ]

    X = df[feature_cols]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=150,
        max_depth=12,
        min_samples_split=5,
        class_weight="balanced",   # handles imbalanced good/failing ratio
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n    ✓ Accuracy: {acc * 100:.1f}%")
    print("\n" + classification_report(y_test, y_pred,
                                       target_names=["Good", "Failing Soon"]))

    return model, feature_cols


def save_artifacts(df: pd.DataFrame, model, feature_cols: list):
    """Save CSV and trained model to disk."""
    print("[5/5] Saving artifacts...")

    # Save CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"    ✓ Training data saved → {OUTPUT_CSV}")

    # Save model + feature column list together
    joblib.dump({"model": model, "features": feature_cols}, OUTPUT_MODEL)
    print(f"    ✓ Model saved → {OUTPUT_MODEL}")


def main():
    print("\n🛰️  AeroLink AI — Model Training\n" + "=" * 40)

    df       = generate_raw_data(NUM_TICKS)
    df       = engineer_features(df)
    df       = label_data(df)
    model, feature_cols = train(df)
    save_artifacts(df, model, feature_cols)

    print("\n✅ Training complete! You can now run the app.\n")


if __name__ == "__main__":
    main()
