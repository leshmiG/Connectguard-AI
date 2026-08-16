"""
models.py
---------
"""

from dataclasses import dataclass


@dataclass
class Itinerary:
    itinerary_id: str
    passenger_name: str
    inbound_flight: str       # e.g. "EK231" JFK -> DXB
    connecting_flight: str    # e.g. "EK568" DXB -> BOM
    scheduled_connection_time: str  # ISO timestamp of the connecting flight's departure
    hub_airport: str = "DXB"


@dataclass
class FlightStatus:
    flight_number: str
    scheduled_arrival: str
    estimated_arrival: str
    delay_minutes: int
    status: str  # "on_time" | "delayed" | "cancelled" | "diverted"


@dataclass
class RiskAssessment:
    itinerary_id: str
    risk_score: float          # 0.0 (safe) - 1.0 (will almost certainly miss it)
    buffer_minutes: int        # time between actual/estimated arrival and connecting departure
    reasoning: str
    recommend_rebooking: bool


@dataclass
class RebookingOption:
    flight_number: str
    departure_time: str
    arrival_time: str
    seats_available: bool
