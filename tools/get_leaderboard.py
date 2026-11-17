"""
tools/get_leaderboard.py

Returns the leaderboard for a game or for all games.
Leaderboard is calculated from ruling documents. No separate score document.
Per player: points, right, wrong, not_counted. Sorted by points high to low.
"""

import os

import requests

from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType


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
# @tool entry point
# ---------------------------------------------------------------------------

expected_credentials = [
    {"app_id": "cloudant_creds", "type": ConnectionType.KEY_VALUE}
]


@tool
def get_leaderboard(game_id: str = "all", group_id: str = "all") -> dict:
    """Return the leaderboard with points per player.

    Calculates points from ruling documents. Sorted by points high to low.
    Use game_id="all" to include every game. Use group_id="all" for every group.

    Args:
        game_id: The game identifier (e.g. game_1) or "all" for every game.
        group_id: The group identifier or "all" for every group.

    Returns:
        A dict with ok and leaderboard (list of player entries sorted by points).
    """
    try:
        base_url, apikey, database = _get_creds()
        token = _get_iam_token(apikey)

        # Read all ruling documents. prefix "ruling:" covers every game.
        rulings = _all_docs_by_prefix(base_url, database, "ruling:", token)

        # Filter by game and group.
        if game_id != "all":
            rulings = [r for r in rulings if r.get("game_id") == game_id]
        if group_id != "all":
            rulings = [r for r in rulings if r.get("group_id") == group_id]

        # Tally per player.
        totals: dict[str, dict] = {}
        for r in rulings:
            player = r.get("player", "unknown")
            if player not in totals:
                totals[player] = {"player": player, "points": 0, "right": 0, "wrong": 0, "not_counted": 0}
            status = r.get("status", "")
            totals[player]["points"] += r.get("points", 0)
            if status in ("right", "wrong", "not_counted"):
                totals[player][status] += 1

        # Sort by points descending, then by player name for a stable order.
        leaderboard = sorted(totals.values(), key=lambda x: (-x["points"], x["player"]))

        return {"ok": True, "leaderboard": leaderboard}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
