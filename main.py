"""
AeroLink AI - Entry Point
---------------------------
This file is the single command to start the entire system.

Usage:
    python main.py

What it does:
    1. Checks that the trained model exists
    2. Verifies the .env file has required keys
    3. Launches the Streamlit dashboard
"""

import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()


def check_model():
    """Make sure the trained model file exists."""
    model_path = os.path.join("model", "saved_model.pkl")
    if not os.path.exists(model_path):
        print("\n❌ Trained model not found!")
        print("   Please run this first:")
        print("   python -m model.train_model\n")
        sys.exit(1)
    print("✅ Model found.")


def check_env():
    """Verify required environment variables are set."""
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or api_key == "your_gemini_api_key_here":
        print("\n⚠️  Warning: GEMINI_API_KEY not set in .env")
        print("   Gemini explanations will be disabled.")
        print("   Get your key at: https://aistudio.google.com/app/apikey\n")
    else:
        print("✅ Gemini API key found.")


def launch_dashboard():
    """Launch the Streamlit dashboard."""
    dashboard_path = os.path.join("dashboard", "app.py")
    print("\n🚀 Launching AeroLinkDashboard...")
    print("   Open your browser at: http://localhost:8501\n")
    print("   Press Ctrl+C to stop.\n")
    print("=" * 50)

    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", dashboard_path],
        check=True,
    )


if __name__ == "__main__":
    print("\n✈️  AeroLink AI — System Check")
    print("=" * 50)
    check_model()
    check_env()
    launch_dashboard()