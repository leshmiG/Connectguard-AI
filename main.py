"""
main.py
-------
Setup:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=sk-ant-...

Run a demo cycle (sample itineraries, connector stubs):
    python main.py --demo

Then view the dashboard:
    streamlit run dashboard.py
"""

import logging
import sys

from models import Itinerary
from pipeline import run_monitoring_cycle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def console_approver(tool_name: str, tool_input: dict) -> bool:
    print(f"\n[APPROVAL REQUIRED] {tool_name}({tool_input})")
    return input("Approve? [y/N]: ").strip().lower() == "y"


SAMPLE_ITINERARIES = [
    Itinerary("IT-001", "A. Al Mansoori", "EK231", "EK568", "2026-08-16T14:30:00", "DXB"),
    Itinerary("IT-002", "J. Chen", "EK002", "EK524", "2026-08-16T15:10:00", "DXB"),
    Itinerary("IT-003", "M. Silva", "EK073", "EK355", "2026-08-16T13:45:00", "DXB"),
]


def main():
    if "--demo" in sys.argv:
        summary = run_monitoring_cycle(SAMPLE_ITINERARIES, approver=console_approver)
        print(f"\n=== CYCLE SUMMARY ===\n{summary}")
        print("\nRun `streamlit run dashboard.py` to view results.")
    else:
        print("Usage: python main.py --demo")


if __name__ == "__main__":
    main()
