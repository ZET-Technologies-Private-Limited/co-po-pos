#!/usr/bin/env python3
"""
train_rasa.py – Train the Rasa NLU model for the OBE chatbot.

Run from the backend/ directory (with the project venv active):
    python scripts/train_rasa.py
"""
import subprocess
import sys
from pathlib import Path

RASA_DIR = Path(__file__).parent.parent / "rasa"


def main() -> None:
    print("=" * 60)
    print("Training Rasa NLU model for OBE Chatbot")
    print(f"Rasa project dir: {RASA_DIR}")
    print("=" * 60)

    result = subprocess.run(
        [sys.executable, "-m", "rasa", "train", "--data", "data",
         "--config", "config.yml", "--domain", "domain.yml",
         "--out", "models"],
        cwd=str(RASA_DIR),
    )

    if result.returncode == 0:
        print("\n[OK] Rasa model trained successfully.")
        print("     Models saved to: backend/rasa/models/")
        print("\nTo start the Rasa NLU server run:")
        print("    python scripts/start_rasa.py")
    else:
        print("\n[ERROR] Rasa training failed.")
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
