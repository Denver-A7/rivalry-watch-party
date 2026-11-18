"""
tools/get_next_game_events.py

Game Data tool for Rivalry Watch Party.
Reads the next count game events from Cloudant (recorded mode only).
Validates each event for newness and reliability before accepting it.
Accepted events update game_state. Rejected events do not change state.

Live mode is not built yet. Returns an error if source is "live".
"""

import os
import datetime

import requests

from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

# Required fields that every game_event document must have.
REQUIRED_EVENT_FIELDS = [
    "event_id", "sequence", "event_type", "home_score", "away_score", "period",
]


# ---------------------------------------------------------------------------
# Credential helper
# ---------------------------------------------------------------------------

def _get_creds() -> tuple[str, str, str]:
    """Return (url, apikey, database) from Orchestrate or environment variables."""
    try:
        from ibm_watsonx_orchestrate.run import connections
        creds = connections.key_value("cloudant_creds")
        url = creds["url"]
        apikey = creds["apikey"]
        database = creds.get("database", "rivalry_watch_party")
    except Exception:
        url = os.environ["CLOUDANT_URL"]
        apikey = os.environ["CLOUDANT_APIKEY"]
        database = os.environ.get("CLOUDANT_DB", "rivalry_watch_party")
    return url, apikey, database


# ---------------------------------------------------------------------------
# IAM token helper
# ---------------------------------------------------------------------------

def _get_iam_token(apikey: str) -> str:
    """Exchange an IAM API key for a bearer token."""
    resp = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey", "apikey": apikey},
        headers={"Accept": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# Cloudant HTTP helpers
# ---------------------------------------------------------------------------

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _get_doc(base_url: str, db: str, doc_id: str, token: str) -> dict | None:
    """Return the document or None if it does not exist."""
    resp = requests.get(
        f"{base_url}/{db}/{doc_id}",
        headers=_headers(token),
        timeout=15,
    )
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.json()


def _put_doc(base_url: str, db: str, doc_id: str, body: dict, token: str) -> dict:
    """Create or update a document. body must include _rev when updating."""
    resp = requests.put(
        f"{base_url}/{db}/{doc_id}",
        json=body,
        headers=_headers(token),
        timeout=15,
    )
    if resp.status_code == 409:
        return {"ok": False, "error": "conflict"}
    resp.raise_for_status()
    return resp.json()


def _all_docs_by_prefix(base_url: str, db: str, prefix: str, token: str) -> list[dict]:
    """Return all documents whose _id starts with prefix, ordered by _id."""
    resp = requests.get(
        f"{base_url}/{db}/_all_docs",
        params={
            "startkey": f'"{prefix}"',
            "endkey": f'"{prefix}\uffff"',
            "include_docs": "true",
        },
        headers=_headers(token),
        timeout=15,
    )
    resp.raise_for_status()
    rows = resp.json().get("rows", [])
    return [row["doc"] for row in rows if "doc" in row]


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------

def _validate_event(event: dict, game_state: dict, seen_event_ids: set) -> str | None:
    """
    Check whether an event is new and reliable.

    Returns None if the event is accepted.
    Returns a short reason string if the event is rejected.
    """
    # Check required fields.
    for field in REQUIRED_EVENT_FIELDS:
        if field not in event:
            return f"Missing required field '{field}'."

    # sequence must be an integer.
    if not isinstance(event["sequence"], int):
        return "Field 'sequence' must be an integer."

    # New: sequence must be greater than last_sequence.
    if event["sequence"] <= game_state["last_sequence"]:
        return "Not new: sequence is not greater than last_sequence."

    # New: event_id must not have been seen before.
    if event["event_id"] in seen_event_ids:
        return "Not new: duplicate event_id."

    # Reliable: team must be one of the two game teams or null.
    allowed_teams = {game_state["home_team"], game_state["away_team"], None}
    if event.get("team") not in allowed_teams:
        return f"Unknown team '{event.get('team')}': not one of the game teams."

    # Reliable: scores must not go down.
    if event["home_score"] < game_state["home_score"]:
        return "home_score went down."
    if event["away_score"] < game_state["away_score"]:
        return "away_score went down."

    return None  # Accepted.


# ---------------------------------------------------------------------------
# @tool entry point
# ---------------------------------------------------------------------------

expected_credentials = [
    {"app_id": "cloudant_creds", "type": ConnectionType.KEY_VALUE}
]

# Maximum events returned in one call. Prevents a single call from draining
# all remaining events and leaving nothing for later checks.
MAX_COUNT = 5


@tool
def get_next_game_events(game_id: str, count: int = 1) -> dict:
    """Read the next game events from Cloudant for a recorded game.

    Validates each event for newness and reliability. Accepted events update
    game_state. Rejected events do not change the state. Live mode is not
    supported yet.

    Args:
        game_id: The game identifier (e.g. game_1).
        count: Number of events to fetch. Defaults to 1. Capped at 5.

    Returns:
        A dict with ok, accepted (list), rejected (list of event+reason),
        and game_state (updated copy).
    """
    try:
        base_url, apikey, database = _get_creds()
        token = _get_iam_token(apikey)

        # Cap count so one call cannot drain all remaining events at once.
        count = min(count, MAX_COUNT)

        # Read game_state.
        state_id = f"game_state:{game_id}"
        game_state = _get_doc(base_url, database, state_id, token)
        if game_state is None:
            return {"ok": False, "error": f"game_state not found for {game_id}."}

        # Live mode is not supported yet.
        if game_state.get("source") == "live":
            return {"ok": False, "error": "Live source not enabled yet."}

        last_seq = game_state["last_sequence"]

        # Read all events for this game.
        all_events = _all_docs_by_prefix(base_url, database, f"game_event:{game_id}:", token)

        # seen_event_ids tracks event_ids already accepted (sequence <= last_seq).
        # Candidates have not been accepted yet, so they are not in this set.
        seen_event_ids = {
            e["event_id"] for e in all_events if e.get("sequence", 0) <= last_seq
        }

        # Find the next count events: sequences > last_seq, ordered by sequence.
        candidates = sorted(
            [e for e in all_events if e.get("sequence", 0) > last_seq],
            key=lambda e: e["sequence"],
        )[:count]

        accepted = []
        rejected = []

        for event in candidates:
            reason = _validate_event(event, game_state, seen_event_ids)
            if reason is not None:
                rejected.append({"event": event, "reason": reason})
                continue

            # Accept: mark event_id as seen and update game_state.
            seen_event_ids.add(event["event_id"])
            game_state["last_sequence"] = event["sequence"]
            game_state["home_score"] = event["home_score"]
            game_state["away_score"] = event["away_score"]
            game_state["period"] = event["period"]

            # Update game status when the game ends.
            if event.get("event_type") == "game_end":
                game_state["status"] = "final"
            elif game_state.get("status") == "not_started":
                game_state["status"] = "in_progress"

            game_state["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            accepted.append(event)

        # Save updated game_state if anything was accepted (retry once on conflict).
        if accepted:
            result = _put_doc(base_url, database, state_id, game_state, token)
            if not result.get("ok") and result.get("error") == "conflict":
                fresh = _get_doc(base_url, database, state_id, token)
                if fresh:
                    game_state["_rev"] = fresh["_rev"]
                _put_doc(base_url, database, state_id, game_state, token)

        return {
            "ok": True,
            "accepted": accepted,
            "rejected": rejected,
            "game_state": game_state,
        }

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
