"""
dashboard.py
------------
Run: streamlit run dashboard.py
Deploy free: push to GitHub, connect the repo at share.streamlit.io — no
server to provision, SQLite file ships with the deploy.
"""

import streamlit as st

import db
from config import config

st.set_page_config(page_title="ConnectGuard - Emirates Connection Risk Monitor", layout="wide")
st.title("Flight ConnectGuard")
st.caption("Missed-connection risk monitoring for hub itineraries - public-data prototype")

db.init_db()
rows = db.get_latest_risk_view()

if not rows:
    st.info("No itineraries monitored yet. Run `python main.py --demo` to load sample data.")
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
st.caption(
    "Architecture: risk agent reads live flight status + hub weather, produces a confidence-scored "
    "risk assessment, then a rebooking agent drafts alternatives for high-risk itineraries - gated "
    "behind human approval before any booking actually changes."
)
