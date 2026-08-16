"""
tracing.py
----------
Structured, machine-readable observability. Every event in a run is written
as one JSON line to a trace file, so a full run can be replayed, audited, or
loaded into a dashboard later — this is the difference between "print
statements" and real observability.
"""

import json
import time
import uuid
from pathlib import Path


class Tracer:
    def __init__(self, trace_dir: str = "./traces"):
        Path(trace_dir).mkdir(parents=True, exist_ok=True)
        self.run_id = uuid.uuid4().hex[:12]
        self.path = Path(trace_dir) / f"run_{self.run_id}.jsonl"
        self._file = open(self.path, "a")

    def event(self, event_type: str, **fields):
        record = {
            "run_id": self.run_id,
            "ts": time.time(),
            "type": event_type,
            **fields,
        }
        self._file.write(json.dumps(record) + "\n")
        self._file.flush()
        return record

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
