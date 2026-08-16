"""
dashboard.py
------------
Run: streamlit run dashboard.py
Deploy free: push to GitHub, connect the repo at share.streamlit.io -- no
server to provision, SQLite file ships with the deploy.

For the deployed version, this reads ANTHROPIC_API_KEY from Streamlit's
secrets manager (Settings -> Secrets on share.streamlit.io) and makes it
available as a normal environment variable, since the underlying agent code
expects it there.
"""

import os

import streamlit as st

os.environ.setdefault("ANTHROPIC_API_KEY", st.secrets.get("ANTHROPIC_API_KEY", ""))

import db
from config import config
from models import Itinerary
from pipeline import run_monitoring_cycle

st.set_page_config(page_title="ConnectGuard - Emirates Connection Risk Monitor", layout="wide")
st.title("Flight ConnectGuard")
st.caption("Missed-connection risk monitoring for hub itineraries - public-data prototype")

SAMPLE_ITINERARIES = [
    Itinerary("IT-001", "A. Al Mansoori", "EK231", "EK568", "2026-08-16T14:30:00", "DXB"),
    Itinerary("IT-002", "J. Chen", "EK002", "EK524", "2026-08-16T15:10:00", "DXB"),
    Itinerary("IT-003", "M. Silva", "EK073", "EK355", "2026-08-16T13:45:00", "DXB"),
]

db.init_db()

with st.sidebar:
    st.subheader("Run the agents")
    st.caption("This calls the real risk agent and rebooking agent against the sample itineraries (connector stubs, since this is a public-data demo, no real flight or airline systems are touched). The rebooking action is auto-approved for this deployed demo; in a real deployment, rebook_passenger pauses for a human to approve, as shown in the codebase's main.py.")
    if st.button("Run demo cycle", type="primary"):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.error("No ANTHROPIC_API_KEY configured -- add it under this app's Settings -> Secrets.")
        else:
            with st.spinner("Running risk agent + rebooking agent..."):
                try:
                    summary = run_monitoring_cycle(SAMPLE_ITINERARIES, approver=lambda name, inp: True)
                    st.success(f"Cycle complete: {summary}")
                except Exception as e:
                    st.error(f"Run failed: {e}")

rows = db.get_latest_risk_view()

if not rows:
    st.info("No itineraries monitored yet. Click Run demo cycle in the sidebar to generate live results.")
else:
    high_risk = [r for r in rows if (r["risk_score"] or 0) >= config.high_risk_threshold]
    col1, col2, col3 = st.columns(3)
    col1.metric("Itineraries monitored", len(rows))
    col2.metric("High risk", len(high_risk))
    col3.metric("Risk threshold", f"{config.high_risk_threshold:.0%}")

    st.subheader("At-risk itineraries")
    for r in rows:
        risk = r["risk_score"] or 0
        marker = "[HIGH]" if risk >= config.high_risk_threshold else ("[MED]" if risk >= 0.3 else "[OK]")
        with st.expander(f"{marker} {r['passenger_name']} - {r['inbound_flight']} to {r['connecting_flight']} (risk: {risk:.0%})"):
            st.write(f"**Scheduled connection:** {r['scheduled_connection_time']}")
            st.write(f"**Buffer:** {r['buffer_minutes']} minutes")
            st.write(f"**Reasoning:** {r['reasoning']}")
            if r["recommend_rebooking"]:
                st.warning("Rebooking recommended")

st.divider()
st.caption("Architecture: risk agent reads live flight status and hub weather, produces a confidence-scored risk assessment, then a rebooking agent drafts alternatives for high-risk itineraries, gated behind human approval before any booking actually changes.")
