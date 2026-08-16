"""
connectors/sources.py
-----------------------
All public-data connectors. Each has a real free-tier API it maps to — fill
in the TODO to go live. Every function works as a stub today so the whole
pipeline is runnable and testable with zero API keys.
"""

import logging
import random
from datetime import datetime, timedelta

from config import config
from models import FlightStatus, RebookingOption

logger = logging.getLogger("connectors")


def fetch_flight_status(flight_number: str) -> FlightStatus:
    """Real implementation: AviationStack /flights endpoint (free tier,
    100 req/month) or OpenSky Network (fully free, no key, less flight-
    number-friendly — better for raw position data than scheduled status).
        GET {aviationstack_base_url}/flights?access_key=...&flight_iata={flight_number}
    """
    # --- TODO: replace with the real AviationStack call ---
    logger.info(f"Fetching status for {flight_number} (stub)")
    delay = random.choice([0, 0, 5, 15, 45, 90])  # weighted toward on-time, occasional big delay
    now = datetime.utcnow()
    scheduled = now + timedelta(hours=2)
    return FlightStatus(
        flight_number=flight_number,
        scheduled_arrival=scheduled.isoformat(),
        estimated_arrival=(scheduled + timedelta(minutes=delay)).isoformat(),
        delay_minutes=delay,
        status="on_time" if delay == 0 else ("cancelled" if delay > 999 else "delayed"),
    )


def fetch_weather(airport_iata: str) -> dict:
    """Real implementation: Open-Meteo — free, no API key required at all.
        GET {weather_base_url}?latitude=..&longitude=..&current=precipitation,wind_speed_10m
    (airport lat/long lookup needed first — a small static IATA->coords table is enough)
    """
    # --- TODO: replace with the real Open-Meteo call ---
    logger.info(f"Fetching weather for {airport_iata} (stub)")
    conditions = random.choice(["clear", "clear", "clear", "rain", "storm"])
    return {"airport": airport_iata, "condition": conditions, "wind_kmh": random.randint(5, 40)}


def search_alternative_flights(route_from: str, route_to: str, after_time: str) -> list[RebookingOption]:
    """Real implementation: the same flight-status API's schedule search,
    or the airline's own inventory API if you have partner/GDS access.
    """
    # --- TODO: replace with a real schedule search ---
    logger.info(f"Searching alternatives {route_from}->{route_to} after {after_time} (stub)")
    base = datetime.fromisoformat(after_time)
    options = []
    for i in range(1, 4):
        dep = base + timedelta(hours=i * 2)
        options.append(RebookingOption(
            flight_number=f"EK{500 + i}",
            departure_time=dep.isoformat(),
            arrival_time=(dep + timedelta(hours=4)).isoformat(),
            seats_available=random.random() > 0.2,
        ))
    return options


def notify_passenger_rebooking(passenger_name: str, itinerary_id: str, new_flight: str) -> str:
    """The irreversible, externally-visible action — actually changing a
    passenger's booking and notifying them. Gated behind approval in the
    agent layer, never called directly.
    """
    # --- TODO: replace with the real booking-change + notification call ---
    logger.info(f"[SIMULATED] Rebooked {passenger_name} ({itinerary_id}) onto {new_flight}")
    return f"[SIMULATED] {passenger_name} rebooked onto {new_flight}, notification sent."
