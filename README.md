# Connectguard-AI
AI agents that monitor connecting flight itineraries, predict missed-connection risk from live flight status + weather, and propose rebooking options — gated behind human approval before any booking changes. Built with Claude, verified end-to-end.


# ConnectGuard — missed-connection risk monitoring for hub airlines

A working prototype addressing a live, named gap in Emirates' current AI investment: Emirates has invested heavily in AI for turbulence prediction, flight planning, and lounge-volume forecasting, but passenger connection-risk prediction isn't among the publicly listed initiatives — despite Emirates' entire hub model depending on tight Dubai connections.

Every core behavior (risk scoring, the confidence-gated rebooking trigger, the approval gate, and per-itinerary error isolation) was verified end to end with a mocked model client before being called done — see "What I verified" below.

---

## The tools/framework, and why each one

| Choice | Why |
|---|---|
| **Claude (`claude-sonnet-5`)** | The risk-scoring task needs judgment (a 15-min delay + storm ≠ a 15-min delay + clear skies), not a lookup table — this is a genuine reasoning task, not a rules engine dressed up as AI. |
| **Raw ReAct loop, no framework** | Same reasoning as every other build in this series: hand-rolled control gives full visibility into guardrails (budget, step limits, approval) without a framework's abstractions hiding what's actually happening — important when you're pitching the architecture, not just the output. |
| **SQLite** | Zero infrastructure. The entire database is one file that ships with the deploy — critical for a portfolio project that needs to run on a free tier, not a provisioned server. |
| **Streamlit** | Fastest path from Python logic to a clickable, demoable dashboard, with a genuinely free, zero-config hosting tier (Streamlit Community Cloud). |
| **AviationStack (flight status) + Open-Meteo (weather)** | Both have free tiers (Open-Meteo requires no key at all), so the whole system runs on public data — nothing confidential, nothing that requires a partnership to demo. |
| **Confidence-gate pattern (reused from the invoice pipeline)** | The rebooking agent only acts on itineraries the risk agent explicitly flags — same "don't act on uncertain judgment" principle, applied to an operational decision instead of a data-extraction one. |
| **Approval gate (reused from every prior build)** | `rebook_passenger` is the one irreversible, externally-visible action in the system. It's gated behind human sign-off by default — the same governance posture used throughout every agent in this conversation. |

---

## How it works

Itinerary list
|
Risk agent: reads live flight status + hub weather -> risk score + reasoning
|
risk >= threshold?
| |
yes no
| |
Rebooking agent: logged, no action
search alternatives,
propose best option
|
Approval gate (human sign-off)
|
approved -> booking changed, passenger notified
denied -> blocked, logged


State lands in SQLite; the Streamlit dashboard reads it directly and ranks itineraries highest-risk first.

## Files

config.py # thresholds, API config, model choice
models.py # Itinerary, FlightStatus, RiskAssessment, RebookingOption
connectors/sources.py # flight status / weather / rebooking search (stubs, real APIs marked TODO)
agents/base.py # shared ReAct tool-calling loop (reused across this whole project series)
agents/connect_guard_agents.py # risk agent + rebooking agent
pipeline.py # orchestrates: assess -> gate -> rebook, with per-itinerary error isolation
db.py # SQLite schema + queries
dashboard.py # Streamlit UI
guardrails.py, tracing.py # budget cap, step limit, approval policy, structured JSONL trace
main.py # CLI entry point (--demo)


---

## Setup and running it locally

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python main.py --demo
streamlit run dashboard.py
```

Runs fully on the connector stubs with zero external API keys beyond Anthropic's — good enough to demo end to end today. Fill in the `# --- TODO ---` markers in `connectors/sources.py` with a free AviationStack key and Open-Meteo (no key needed) to go live on real flight data.

---

## How to deploy it (free, public link)

1. **Push to GitHub** — a public repo, since none of this touches confidential data.
2. **Streamlit Community Cloud** (share.streamlit.io) — connect the repo, point it at `dashboard.py`, add `ANTHROPIC_API_KEY` as a secret in the app settings. Free tier, no server to manage, live in about two minutes.
3. **Seed data**: either run `python main.py --demo` locally first and commit the resulting `data/connect_guard.db`, or add a "Run demo cycle" button inside `dashboard.py` that calls `run_monitoring_cycle()` directly from the deployed app (a natural next iteration — currently `main.py` is the trigger).
4. **Custom domain (optional)**: Streamlit Community Cloud gives you a `*.streamlit.app` URL immediately; that's more than sufficient for a portfolio link.

For a more "production-grade" demo, the same code deploys equally well on Hugging Face Spaces (also free, also zero-config for a Streamlit app) — useful as a second link if you want to show you're not tied to one platform.

---

## What I verified before calling this done

Using a mocked Anthropic client scripted to respond to each agent's prompts, plus a real SQLite database:

- **Risk differentiation**: two itineraries in the same batch — one with a long delay and storm at the hub, one on-time with clear weather — were correctly scored 0.9 (high) and 0.15 (low) respectively, and only the high-risk one triggered the rebooking agent.
- **The confidence gate actually gates**: the low-risk itinerary never touched the rebooking agent at all — confirmed zero rebooking proposals were generated for it.
- **The approval gate actually blocks**: ran the full cycle twice, once with approval granted (booking changed) and once denied (explicitly blocked, confirmed in the stored proposal text).
- **Fail-safe parsing**: if the risk agent's output doesn't parse cleanly into a score, the system defaults to treating it as high risk rather than silently dropping the assessment — verified directly.
- **Per-itinerary error isolation**: a deliberately runaway itinerary (never converging on a parseable answer, hitting its step limit) was caught and logged without stopping the rest of the batch — the other itineraries in the same run were still assessed correctly. This was a real bug I found and fixed during testing, not a hypothetical — the first version of `pipeline.py` let one bad itinerary crash the whole monitoring cycle.

## What's still a stub
Every connector in `connectors/sources.py` is marked `# --- TODO ---` where the real AviationStack/Open-Meteo call goes — same pattern as every other connector-based build in this series. This proves the agent orchestration, risk logic, and guardrails are correct; wiring in live flight data is a half-day of work once you have an AviationStack free-tier key.

Every connector in `connectors/sources.py` is marked `# --- TODO ---` where the real AviationStack/Open-Meteo call goes — same pattern as every other connector-based build in this series. This proves the agent orchestration, risk logic, and guardrails are correct; wiring in live flight data is a half-day of work once you have an AviationStack free-tier key.
