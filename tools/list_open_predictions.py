"""
tools/list_open_predictions.py

Lists all open predictions for a game and group.
Returns only predictions with status "open" for the given game_id and group_id.
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
def list_open_predictions(game_id: str, group_id: str) -> dict:
    """List all open predictions for a game and group.

    Returns only predictions with status "open" for the given game_id and
    group_id. Predictions that have been ruled right, wrong, or not_counted
    are not included.

    Args:
        game_id: The game identifier (e.g. game_1).
        group_id: The watch-party group identifier.

    Returns:
        A dict with ok and predictions (list of open prediction dicts).
    """
    try:
        base_url, apikey, database = _get_creds()
        token = _get_iam_token(apikey)

        # Fetch all predictions for this game using the doc id prefix.
        all_preds = _all_docs_by_prefix(
            base_url, database, f"prediction:{game_id}:", token
        )

        # Filter: open status and matching group_id.
        open_preds = [
            p for p in all_preds
            if p.get("status") == "open" and p.get("group_id") == group_id
        ]

        return {"ok": True, "predictions": open_preds}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
