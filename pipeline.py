"""
pipeline.py
-----------
Runs the risk agent over every monitored itinerary, and for anything flagged
high-risk, runs the rebooking agent to draft (and, if approved, execute) an
alternative.
"""

import logging
import re

import db
from agents.connect_guard_agents import build_rebooking_agent, build_risk_agent
from config import config
from guardrails import ApprovalPolicy, BudgetExceeded, BudgetTracker, StepLimitExceeded
from models import Itinerary, RiskAssessment
from tracing import Tracer

logger = logging.getLogger("pipeline")

RISK_LINE_RE = re.compile(r"RISK_SCORE=([\d.]+)\s+BUFFER_MINUTES=(-?\d+)\s+REASON=(.*)", re.DOTALL)


def parse_risk_output(text: str, itinerary_id: str) -> RiskAssessment:
    match = RISK_LINE_RE.search(text)
    if not match:
        logger.warning(f"Could not parse risk agent output for {itinerary_id}, defaulting to high risk")
        return RiskAssessment(itinerary_id=itinerary_id, risk_score=1.0, buffer_minutes=0,
                               reasoning=f"UNPARSEABLE OUTPUT: {text[:200]}", recommend_rebooking=True)
    score = float(match.group(1))
    buffer_min = int(match.group(2))
    reason = match.group(3).strip()
    return RiskAssessment(itinerary_id=itinerary_id, risk_score=score, buffer_minutes=buffer_min,
                           reasoning=reason, recommend_rebooking=score >= config.high_risk_threshold)


def run_monitoring_cycle(itineraries: list, approver=None, db_path: str = None) -> dict:
    db.init_db(db_path)
    for it in itineraries:
        db.upsert_itinerary(it, db_path)

    budget = BudgetTracker(max_usd=config.max_budget_usd_per_run, model=config.model)
    tracer = Tracer()
    approval_policy = ApprovalPolicy(sensitive_tools={"rebook_passenger"}, approver=approver)

    summary = {"assessed": 0, "high_risk": 0, "rebooking_proposed": 0, "errors": 0}

    for it in itineraries:
        # Each itinerary is isolated: a budget/step-limit hit or any other
        # failure on one itinerary must not stop the rest of the batch from
        # being assessed — same principle as the invoice pipeline's
        # per-attachment error isolation.
        try:
            risk_agent = build_risk_agent(budget, tracer)
            raw = risk_agent.run(
                f"Itinerary {it.itinerary_id}: inbound flight {it.inbound_flight} connecting to "
                f"{it.connecting_flight} at {it.hub_airport}, scheduled connection departure "
                f"{it.scheduled_connection_time}."
            )
            assessment = parse_risk_output(raw, it.itinerary_id)
            db.record_risk_assessment(assessment, db_path)
            summary["assessed"] += 1
            logger.info(f"{it.itinerary_id}: risk={assessment.risk_score:.2f} buffer={assessment.buffer_minutes}min")

            if assessment.recommend_rebooking:
                summary["high_risk"] += 1
                rebooking_agent = build_rebooking_agent(budget, tracer, approval_policy)
                result = rebooking_agent.run(
                    f"Passenger {it.passenger_name} (itinerary {it.itinerary_id}) is at risk of missing "
                    f"their connection ({it.connecting_flight} from {it.hub_airport}). "
                    f"Find and book an alternative departing after {it.scheduled_connection_time}."
                )
                db.record_rebooking_proposal(it.itinerary_id, result, db_path=db_path)
                summary["rebooking_proposed"] += 1

        except BudgetExceeded as e:
            logger.warning(f"Budget cap hit during {it.itinerary_id} — stopping the whole cycle: {e}")
            summary["errors"] += 1
            break  # a blown budget applies to the whole run, not just this itinerary — stop here
        except StepLimitExceeded as e:
            logger.error(f"{it.itinerary_id} hit its step limit: {e} — skipping this itinerary, continuing batch")
            db.record_rebooking_proposal(it.itinerary_id, f"ERROR: {e}", status="error", db_path=db_path)
            summary["errors"] += 1
            continue
        except Exception as e:
            logger.exception(f"Unexpected error processing {it.itinerary_id} — skipping, continuing batch")
            summary["errors"] += 1
            continue

    tracer.close()
    logger.info(f"Monitoring cycle complete: {summary} (spent ${budget.spent_usd:.4f})")
    return summary
