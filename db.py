"""
db.py
-----
SQLite specifically because this needs to run on free-tier deployment
(Streamlit Community Cloud / Hugging Face Spaces) with zero infrastructure —
no server to provision, the whole database is one file.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import config
from models import Itinerary, RiskAssessment

SCHEMA = """
CREATE TABLE IF NOT EXISTS itineraries (
    itinerary_id TEXT PRIMARY KEY,
    passenger_name TEXT,
    inbound_flight TEXT,
    connecting_flight TEXT,
    scheduled_connection_time TEXT,
    hub_airport TEXT
);

CREATE TABLE IF NOT EXISTS risk_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id TEXT,
    risk_score REAL,
    buffer_minutes INTEGER,
    reasoning TEXT,
    recommend_rebooking INTEGER,
    assessed_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rebooking_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id TEXT,
    proposal_text TEXT,
    status TEXT DEFAULT 'pending',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def get_conn(db_path: str = None):
    path = db_path or config.db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = None):
    with get_conn(db_path) as conn:
        conn.executescript(SCHEMA)


def upsert_itinerary(itinerary: Itinerary, db_path: str = None):
    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT INTO itineraries VALUES (?,?,?,?,?,?)
               ON CONFLICT(itinerary_id) DO UPDATE SET
               passenger_name=excluded.passenger_name, inbound_flight=excluded.inbound_flight,
               connecting_flight=excluded.connecting_flight,
               scheduled_connection_time=excluded.scheduled_connection_time,
               hub_airport=excluded.hub_airport""",
            (itinerary.itinerary_id, itinerary.passenger_name, itinerary.inbound_flight,
             itinerary.connecting_flight, itinerary.scheduled_connection_time, itinerary.hub_airport),
        )


def record_risk_assessment(assessment: RiskAssessment, db_path: str = None):
    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT INTO risk_assessments (itinerary_id, risk_score, buffer_minutes, reasoning, recommend_rebooking)
               VALUES (?,?,?,?,?)""",
            (assessment.itinerary_id, assessment.risk_score, assessment.buffer_minutes,
             assessment.reasoning, int(assessment.recommend_rebooking)),
        )


def record_rebooking_proposal(itinerary_id: str, proposal_text: str, status: str = "pending", db_path: str = None):
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO rebooking_proposals (itinerary_id, proposal_text, status) VALUES (?,?,?)",
            (itinerary_id, proposal_text, status),
        )


def get_latest_risk_view(db_path: str = None) -> list[dict]:
    """The dashboard's main query: every itinerary with its most recent risk
    assessment, ranked highest-risk first."""
    with get_conn(db_path) as conn:
        rows = conn.execute(
            """SELECT i.itinerary_id, i.passenger_name, i.inbound_flight, i.connecting_flight,
                      i.scheduled_connection_time, r.risk_score, r.buffer_minutes, r.reasoning,
                      r.recommend_rebooking, r.assessed_at
               FROM itineraries i
               LEFT JOIN risk_assessments r ON r.id = (
                   SELECT id FROM risk_assessments WHERE itinerary_id = i.itinerary_id
                   ORDER BY assessed_at DESC LIMIT 1
               )
               ORDER BY r.risk_score DESC"""
        ).fetchall()
        return [dict(row) for row in rows]
