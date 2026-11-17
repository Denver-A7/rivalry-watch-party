"""
tools/list_rulings.py

Returns all rulings for a game, optionally filtered by group.
Each ruling includes its reason and the history of any changes.
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
def list_rulings(game_id: str, group_id: str = "all") -> dict:
    """Return the ruling log for a game.

    Lists every ruling with its reason and the history of any override changes.
    Use group_id="all" to include every group.

    Args:
        game_id: The game identifier (e.g. game_1).
        group_id: The group identifier or "all" for every group.

    Returns:
        A dict with ok and rulings (list of ruling documents).
    """
    try:
        base_url, apikey, database = _get_creds()
        token = _get_iam_token(apikey)

        # All rulings for this game share the prefix "ruling:prediction:{game_id}:".
        prefix = f"ruling:prediction:{game_id}:"
        rulings = _all_docs_by_prefix(base_url, database, prefix, token)

        # Filter by group when requested.
        if group_id != "all":
            rulings = [r for r in rulings if r.get("group_id") == group_id]

        return {"ok": True, "rulings": rulings}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
