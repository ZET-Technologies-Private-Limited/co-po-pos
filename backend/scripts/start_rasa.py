#!/usr/bin/env python3
"""
start_rasa.py – Start the Rasa NLU server so the OBE backend can call it.

Run from the backend/ directory (with the project venv active):
    python scripts/start_rasa.py

The Rasa server listens on http://localhost:5005 by default.
Override the port via the RASA_PORT environment variable:
    RASA_PORT=5010 python scripts/start_rasa.py
"""
import os
import subprocess
import sys
from pathlib import Path

RASA_DIR = Path(__file__).parent.parent / "rasa"
RASA_PORT = os.getenv("RASA_PORT", "5005")


def main() -> None:
    models_dir = RASA_DIR / "models"
    if not models_dir.exists() or not any(models_dir.iterdir()):
        print("[WARN] No trained model found in backend/rasa/models/")
        print("       Run   python scripts/train_rasa.py   first.")
        sys.exit(1)

    print("=" * 60)
    print(f"Starting Rasa NLU server on port {RASA_PORT}")
    print(f"Rasa project dir: {RASA_DIR}")
    print("=" * 60)

    subprocess.run(
        [
            sys.executable, "-m", "rasa", "run",
            "--enable-api",
            "--cors", "*",
            "--port", RASA_PORT,
        ],
        cwd=str(RASA_DIR),
    )


if __name__ == "__main__":
    main()
