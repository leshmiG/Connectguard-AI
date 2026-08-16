"""
agents/connect_guard_agents.py
--------------------------------
Two agents, same ToolAgent loop used throughout this conversation's builds:

  RiskAgent      - reads live inbound flight status + hub weather, judges
                    missed-connection probability with reasoning (not just
                    a raw threshold check — it can weigh "15 min delay but
                    storm at the hub" differently from "15 min delay, clear
                    skies").
  RebookingAgent  - for flagged itineraries, searches alternatives and
                     drafts a recommendation. The actual booking-change
                     action is gated behind human approval.
"""

from agents.base import Tool, ToolAgent
from connectors import sources
from config import config
from guardrails import ApprovalPolicy, BudgetTracker
from tracing import Tracer


def _tool(name, description, schema, fn) -> Tool:
    return Tool(name=name, description=description, input_schema=schema, handler=fn)


RISK_TOOLS = [
    _tool(
        "get_flight_status", "Get live status (delay, ETA) for a flight number.",
        {"type": "object", "properties": {"flight_number": {"type": "string"}}, "required": ["flight_number"]},
        lambda flight_number: sources.fetch_flight_status(flight_number).__dict__,
    ),
    _tool(
        "get_hub_weather", "Get current weather conditions at an airport.",
        {"type": "object", "properties": {"airport_iata": {"type": "string"}}, "required": ["airport_iata"]},
        lambda airport_iata: sources.fetch_weather(airport_iata),
    ),
]

REBOOKING_TOOLS = [
    _tool(
        "search_alternatives", "Search alternative flights on a route departing after a given time.",
        {"type": "object", "properties": {
            "route_from": {"type": "string"}, "route_to": {"type": "string"}, "after_time": {"type": "string"},
        }, "required": ["route_from", "route_to", "after_time"]},
        lambda route_from, route_to, after_time: [o.__dict__ for o in sources.search_alternative_flights(route_from, route_to, after_time)],
    ),
    Tool(
        name="rebook_passenger",
        description="Actually change the passenger's booking and notify them. Irreversible — only call after confirming the best alternative.",
        input_schema={"type": "object", "properties": {
            "passenger_name": {"type": "string"}, "itinerary_id": {"type": "string"}, "new_flight": {"type": "string"},
        }, "required": ["passenger_name", "itinerary_id", "new_flight"]},
        handler=sources.notify_passenger_rebooking,
        sensitive=True,
    ),
]


def build_risk_agent(budget: BudgetTracker, tracer: Tracer) -> ToolAgent:
    return ToolAgent(
        name="risk_agent",
        model=config.model,
        system_prompt=(
            "You assess missed-connection risk for a passenger itinerary at a hub airport. "
            "Call get_flight_status on the inbound flight, and get_hub_weather on the hub airport. "
            "Weigh the delay against the scheduled connection buffer, AND factor in weather — "
            "a 15-minute delay with a storm at the hub is riskier than a 15-minute delay in clear "
            "weather, because storms cause secondary delays. End with a final answer in exactly "
            "this format on one line: RISK_SCORE=<0.0-1.0> BUFFER_MINUTES=<int> REASON=<short text>"
        ),
        tools=RISK_TOOLS,
        budget=budget,
        tracer=tracer,
        max_steps=4,
    )


def build_rebooking_agent(budget: BudgetTracker, tracer: Tracer, approval_policy: ApprovalPolicy) -> ToolAgent:
    return ToolAgent(
        name="rebooking_agent",
        model=config.model,
        system_prompt=(
            "A passenger's connection is at high risk of being missed. Search for alternative "
            "flights on their route, pick the best option (soonest with seats available), and "
            "call rebook_passenger with that option. Explain your choice briefly before calling it."
        ),
        tools=REBOOKING_TOOLS,
        budget=budget,
        tracer=tracer,
        approval_policy=approval_policy,
        max_steps=4,
    )
