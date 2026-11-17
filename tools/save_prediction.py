"""
tools/save_prediction.py

Saves a friend's prediction for a game.
Checks that prediction_type is one of the three known types and that the team
is one of the two teams in game_state. Sets made_after_sequence to the current
game_state.last_sequence and status to "open".
"""

import os
import datetime
import uuid

import requests

from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

# The three allowed prediction types.
VALID_PREDICTION_TYPES = {"game_winner", "scores_before_half", "next_score"}


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


# ---------------------------------------------------------------------------
# @tool entry point
# ---------------------------------------------------------------------------

expected_credentials = [
    {"app_id": "cloudant_creds", "type": ConnectionType.KEY_VALUE}
]


@tool
def save_prediction(
    game_id: str,
    group_id: str,
    player: str,
    prediction_type: str,
    team: str,
    original_text: str,
) -> dict:
    """Save a friend's prediction for a game.

    Checks that prediction_type is one of the three known types and that the
    team is one of the two teams in game_state. Sets made_after_sequence to
    the current game_state.last_sequence and status to "open".

    Args:
        game_id: The game identifier (e.g. game_1).
        group_id: The watch-party group identifier.
        player: The name of the friend making the prediction.
        prediction_type: One of game_winner, scores_before_half, next_score.
        team: The team the friend is predicting for.
        original_text: The friend's original message text.

    Returns:
        A dict with ok and prediction_id on success, or ok and error on failure.
    """
    try:
        # Validate prediction_type first so we give a clear error early.
        if prediction_type not in VALID_PREDICTION_TYPES:
            return {
                "ok": False,
                "error": (
                    f"Unknown prediction type '{prediction_type}'. "
                    f"Use one of: {', '.join(sorted(VALID_PREDICTION_TYPES))}."
                ),
            }

        base_url, apikey, database = _get_creds()
        token = _get_iam_token(apikey)

        # Read game_state to validate the team and get the current sequence.
        state_id = f"game_state:{game_id}"
        game_state = _get_doc(base_url, database, state_id, token)
        if game_state is None:
            return {"ok": False, "error": f"game_state not found for {game_id}."}

        allowed_teams = {game_state["home_team"], game_state["away_team"]}
        if team not in allowed_teams:
            return {
                "ok": False,
                "error": (
                    f"Unknown team '{team}'. "
                    f"Use one of: {', '.join(sorted(allowed_teams))}."
                ),
            }

        # Build the prediction document.
        short_id = uuid.uuid4().hex[:8]
        pred_id = f"prediction:{game_id}:{short_id}"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        prediction = {
            "_id": pred_id,
            "type": "prediction",
            "game_id": game_id,
            "group_id": group_id,
            "player": player,
            "prediction_type": prediction_type,
            "team": team,
            "original_text": original_text,
            "made_after_sequence": game_state["last_sequence"],
            "status": "open",
            "created_at": now,
        }

        result = _put_doc(base_url, database, pred_id, prediction, token)
        if not result.get("ok") and result.get("error") == "conflict":
            # Retry once; a new UUID means this should not conflict again.
            short_id = uuid.uuid4().hex[:8]
            pred_id = f"prediction:{game_id}:{short_id}"
            prediction["_id"] = pred_id
            result = _put_doc(base_url, database, pred_id, prediction, token)

        return {"ok": True, "prediction_id": pred_id}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
