"""
config.py
---------
Public-data-only configuration — no Sulb/Foulath systems involved. Fill in
free-tier API keys to run against live data; the pipeline works fully
against the connector stubs for demoing/testing without any keys at all.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    # --- Flight status (AviationStack free tier: 100 requests/month, or
    # swap for OpenSky Network which is fully free with no key) ---
    aviationstack_api_key: str = os.environ.get("AVIATIONSTACK_API_KEY", "")
    aviationstack_base_url: str = "http://api.aviationstack.com/v1"

    # --- Weather (Open-Meteo: free, no API key required at all) ---
    weather_base_url: str = "https://api.open-meteo.com/v1/forecast"

    # --- Hub airport this system watches connections through ---
    hub_airport: str = os.environ.get("HUB_AIRPORT", "DXB")

    # --- Storage ---
    db_path: str = os.environ.get("DB_PATH", "./data/connect_guard.db")

    # --- Model / guardrails ---
    model: str = "claude-sonnet-5"
    max_budget_usd_per_run: float = float(os.environ.get("MAX_BUDGET_USD_PER_RUN", "0.50"))

    # --- Risk thresholds ---
    high_risk_threshold: float = float(os.environ.get("HIGH_RISK_THRESHOLD", "0.6"))  # 0-1 scale
    min_connection_buffer_minutes: int = 60  # below this, risk rises sharply regardless of delay

    # --- Monitoring cadence ---
    monitor_interval_minutes: int = int(os.environ.get("MONITOR_INTERVAL_MINUTES", "20"))


config = Config()
