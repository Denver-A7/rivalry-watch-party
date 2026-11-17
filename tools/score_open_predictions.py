"""
tools/score_open_predictions.py

Scoring tool for Rivalry Watch Party.
Reads all open predictions and all accepted game events for a game,
applies the prediction rules, saves a ruling for each decided prediction,
updates each prediction status, and returns the result.

Rulings come from code, not from the language model.
The player name is never an input to the decide() function.
"""

import os
import datetime

import requests

from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

# Points awarded for a right prediction.
# Only the team lead may change this constant.
POINTS_RIGHT = 1


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
        # Conflict: return the error so the caller can retry.
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
# Pure decision logic — no database, no player name
# ---------------------------------------------------------------------------

def decide(prediction: dict, events: list[dict]) -> dict | None:
    """
    Decide a single prediction given a list of accepted game events.

    Args:
        prediction: A prediction document (without the player name used in logic).
        events: Accepted game_event documents ordered by sequence, ascending.

    Returns:
        A dict with keys: status, reason, points, event_id.
        Returns None when the prediction cannot be decided yet (stays open).
    """
    ptype = prediction["prediction_type"]
    team = prediction["team"]
    made_after = prediction["made_after_sequence"]

    # Events that could decide this prediction must have sequence > made_after.
    # We also need to detect when a deciding event happened before made_after
    # (the late-prediction rule).

    if ptype == "game_winner":
        return _decide_game_winner(team, made_after, events)
    if ptype == "scores_before_half":
        return _decide_scores_before_half(team, made_after, events)
    if ptype == "next_score":
        return _decide_next_score(team, made_after, events)
    # Unknown type: not_counted.
    return {
        "status": "not_counted",
        "reason": f"Unknown prediction type '{ptype}'.",
        "points": 0,
        "event_id": None,
    }


def _decide_game_winner(team: str, made_after: int, events: list[dict]) -> dict | None:
    """Decide a game_winner prediction."""
    # Find the first game_end event in the full event list.
    game_end = next((e for e in events if e["event_type"] == "game_end"), None)
    if game_end is None:
        return None  # Game not over yet.

    # Late prediction: the game_end happened before the prediction was saved.
    if game_end["sequence"] <= made_after:
        return {
            "status": "not_counted",
            "reason": "The prediction was made after the answer was already known.",
            "points": 0,
            "event_id": game_end["event_id"],
        }

    home_score = game_end["home_score"]
    away_score = game_end["away_score"]
    home_team = game_end.get("home_team")  # may be absent in event; resolved below
    away_team = game_end.get("away_team")

    # Tie.
    if home_score == away_score:
        return {
            "status": "not_counted",
            "reason": "The game ended in a tie.",
            "points": 0,
            "event_id": game_end["event_id"],
        }

    # Determine winner from score. The event carries home_score / away_score.
    # We need to know which team is home and which is away.
    # The game_event document has team=null for game_end; we use home_team/away_team
    # fields that get_next_game_events copies from game_state onto each event.
    if home_team is None or away_team is None:
        # Fallback: we cannot determine winner without team names.
        return {
            "status": "not_counted",
            "reason": "Could not determine winner because team names are missing from the game_end event.",
            "points": 0,
            "event_id": game_end["event_id"],
        }

    winner = home_team if home_score > away_score else away_team
    if team == winner:
        return {
            "status": "right",
            "reason": f"{winner} won the game.",
            "points": POINTS_RIGHT,
            "event_id": game_end["event_id"],
        }
    return {
        "status": "wrong",
        "reason": f"{winner} won the game, not {team}.",
        "points": 0,
        "event_id": game_end["event_id"],
    }


def _decide_scores_before_half(team: str, made_after: int, events: list[dict]) -> dict | None:
    """Decide a scores_before_half prediction."""
    for event in events:
        # Only events with event_type score or half_end in the first half matter.
        if event["event_type"] == "score" and event.get("period") == 1:
            if event["sequence"] <= made_after:
                # Deciding event already happened.
                return {
                    "status": "not_counted",
                    "reason": "The prediction was made after the answer was already known.",
                    "points": 0,
                    "event_id": event["event_id"],
                }
            if event["team"] == team:
                return {
                    "status": "right",
                    "reason": f"{team} scored before the half ended.",
                    "points": POINTS_RIGHT,
                    "event_id": event["event_id"],
                }
        elif event["event_type"] == "half_end":
            if event["sequence"] <= made_after:
                return {
                    "status": "not_counted",
                    "reason": "The prediction was made after the answer was already known.",
                    "points": 0,
                    "event_id": event["event_id"],
                }
            return {
                "status": "wrong",
                "reason": f"{team} did not score before the half ended.",
                "points": 0,
                "event_id": event["event_id"],
            }
    return None  # No decision yet.


def _decide_next_score(team: str, made_after: int, events: list[dict]) -> dict | None:
    """Decide a next_score prediction."""
    for event in events:
        if event["sequence"] <= made_after:
            continue  # Only look at events after the prediction was saved.
        if event["event_type"] == "score":
            if event["team"] == team:
                return {
                    "status": "right",
                    "reason": f"{team} scored next.",
                    "points": POINTS_RIGHT,
                    "event_id": event["event_id"],
                }
            return {
                "status": "wrong",
                "reason": f"{event['team']} scored next, not {team}.",
                "points": 0,
                "event_id": event["event_id"],
            }
        if event["event_type"] == "game_end":
            return {
                "status": "not_counted",
                "reason": "The game ended before another score.",
                "points": 0,
                "event_id": event["event_id"],
            }
    return None  # No decision yet.


# ---------------------------------------------------------------------------
# @tool entry point
# ---------------------------------------------------------------------------

expected_credentials = [
    {"app_id": "cloudant_creds", "type": ConnectionType.KEY_VALUE}
]


@tool
def score_open_predictions(game_id: str) -> dict:
    """Score all open predictions for a game.

    Reads every open prediction and every accepted game event for the game,
    applies the prediction rules, saves a ruling for each decided prediction,
    updates the prediction status, and returns a summary.

    Args:
        game_id: The game identifier (e.g. game_1).

    Returns:
        A dict with ok, new_rulings (list of ruling summaries), and still_open (count).
    """
    try:
        base_url, apikey, database = _get_creds()
        token = _get_iam_token(apikey)

        # Read all open predictions for this game.
        all_predictions = _all_docs_by_prefix(base_url, database, f"prediction:{game_id}:", token)
        open_predictions = [p for p in all_predictions if p.get("status") == "open"]

        if not open_predictions:
            return {"ok": True, "new_rulings": [], "still_open": 0}

        # Read all accepted game events for this game, ordered by sequence.
        all_events = _all_docs_by_prefix(base_url, database, f"game_event:{game_id}:", token)
        events = sorted(all_events, key=lambda e: e["sequence"])

        new_rulings = []
        still_open = 0

        for pred in open_predictions:
            pred_id = pred["_id"]
            outcome = decide(pred, events)

            if outcome is None:
                still_open += 1
                continue

            now = datetime.datetime.now(datetime.timezone.utc).isoformat()

            # Build ruling document.
            ruling_id = f"ruling:{pred_id}"
            ruling = {
                "_id": ruling_id,
                "type": "ruling",
                "ruling_id": ruling_id,
                "prediction_id": pred_id,
                "game_id": pred["game_id"],
                "group_id": pred["group_id"],
                "player": pred["player"],
                "prediction_type": pred["prediction_type"],
                "team": pred["team"],
                "status": outcome["status"],
                "reason": outcome["reason"],
                "points": outcome["points"],
                "event_id": outcome["event_id"],
                "decided_at": now,
                "changes": [],
            }

            # Save ruling (retry once on conflict).
            existing_ruling = _get_doc(base_url, database, ruling_id, token)
            if existing_ruling:
                ruling["_rev"] = existing_ruling["_rev"]
            result = _put_doc(base_url, database, ruling_id, ruling, token)
            if not result.get("ok") and result.get("error") == "conflict":
                existing_ruling = _get_doc(base_url, database, ruling_id, token)
                if existing_ruling:
                    ruling["_rev"] = existing_ruling["_rev"]
                _put_doc(base_url, database, ruling_id, ruling, token)

            # Update prediction status (retry once on conflict).
            pred["status"] = outcome["status"]
            update_result = _put_doc(base_url, database, pred_id, pred, token)
            if not update_result.get("ok") and update_result.get("error") == "conflict":
                fresh = _get_doc(base_url, database, pred_id, token)
                if fresh:
                    pred["_rev"] = fresh["_rev"]
                    pred["status"] = outcome["status"]
                    _put_doc(base_url, database, pred_id, pred, token)

            new_rulings.append({
                "ruling_id": ruling_id,
                "prediction_id": pred_id,
                "player": pred["player"],
                "prediction_type": pred["prediction_type"],
                "team": pred["team"],
                "status": outcome["status"],
                "reason": outcome["reason"],
                "points": outcome["points"],
            })

        return {"ok": True, "new_rulings": new_rulings, "still_open": still_open}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
