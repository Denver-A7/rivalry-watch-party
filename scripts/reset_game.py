"""
scripts/reset_game.py

Deletes all prediction and ruling documents for a game and resets game_state
to not_started with last_sequence = 0.

Use this before re-running the chat test script from the beginning.
Do NOT use this on a game that is in progress during a demo.

Usage:
  python scripts/reset_game.py game_1

Credentials: reads CLOUDANT_URL and CLOUDANT_APIKEY from the environment
(the same method used by the tool files). The database name defaults to
rivalry_watch_party and can be overridden with CLOUDANT_DB.

This script does not change scripts/seed_recorded_game.py.
"""

import os
import sys
import requests
from dotenv import load_dotenv


# ---------------------------------------------------------------------------
# Credentials helper (same pattern as check_cloudant.py)
# ---------------------------------------------------------------------------

def _get_creds() -> tuple[str, str, str]:
    """Load URL, API key, and database from .env then environment."""
    if os.path.exists(".env"):
        load_dotenv(".env", override=False)
    url = os.environ.get("CLOUDANT_URL", "").strip().rstrip("/")
    apikey = os.environ.get("CLOUDANT_APIKEY", "").strip()
    if not url or not apikey:
        print("ERROR: CLOUDANT_URL or CLOUDANT_APIKEY is not set.")
        sys.exit(1)
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


def _put_doc(base_url: str, db: str, doc_id: str, body: dict, token: str) -> None:
    """Create or update a document. body must include _rev when updating."""
    resp = requests.put(
        f"{base_url}/{db}/{doc_id}",
        json=body,
        headers=_headers(token),
        timeout=15,
    )
    resp.raise_for_status()


def _delete_doc(base_url: str, db: str, doc_id: str, rev: str, token: str) -> None:
    """Delete a document by id and _rev."""
    resp = requests.delete(
        f"{base_url}/{db}/{doc_id}",
        params={"rev": rev},
        headers=_headers(token),
        timeout=15,
    )
    resp.raise_for_status()


def _all_docs_by_prefix(base_url: str, db: str, prefix: str, token: str) -> list[dict]:
    """Return all documents whose _id starts with prefix."""
    resp = requests.get(
        f"{base_url}/{db}/_all_docs",
        params={
            "startkey": f'"{prefix}"',
            "endkey": f'"{prefix}\uffff"',
            "include_docs": "true",
        },
        headers=_headers(token),
        timeout=30,
    )
    resp.raise_for_status()
    rows = resp.json().get("rows", [])
    return [row["doc"] for row in rows if "doc" in row]


# ---------------------------------------------------------------------------
# Reset logic
# ---------------------------------------------------------------------------

def reset_game(game_id: str) -> None:
    """
    Delete all prediction and ruling documents for game_id and reset
    game_state to not_started with last_sequence = 0.
    """
    base_url, apikey, database = _get_creds()
    token = _get_iam_token(apikey)

    # 1. Delete all prediction documents for this game.
    prediction_prefix = f"prediction:{game_id}:"
    predictions = _all_docs_by_prefix(base_url, database, prediction_prefix, token)
    print(f"Found {len(predictions)} prediction document(s) for {game_id}.")
    for doc in predictions:
        _delete_doc(base_url, database, doc["_id"], doc["_rev"], token)
        print(f"  Deleted {doc['_id']}")

    # 2. Delete all ruling documents for this game.
    # Ruling ids are "ruling:prediction:{game_id}:{short_id}".
    ruling_prefix = f"ruling:prediction:{game_id}:"
    rulings = _all_docs_by_prefix(base_url, database, ruling_prefix, token)
    print(f"Found {len(rulings)} ruling document(s) for {game_id}.")
    for doc in rulings:
        _delete_doc(base_url, database, doc["_id"], doc["_rev"], token)
        print(f"  Deleted {doc['_id']}")

    # 3. Reset game_state.
    state_id = f"game_state:{game_id}"
    state = _get_doc(base_url, database, state_id, token)
    if state is None:
        print(f"game_state not found for {game_id}. Nothing to reset.")
        return

    state["status"] = "not_started"
    state["last_sequence"] = 0
    state["home_score"] = 0
    state["away_score"] = 0
    state["period"] = 1
    _put_doc(base_url, database, state_id, state, token)
    print(f"game_state for {game_id} reset to not_started, last_sequence = 0.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/reset_game.py <game_id>")
        print("Example: python scripts/reset_game.py game_1")
        sys.exit(1)

    game_id = sys.argv[1]
    print(f"Resetting {game_id} ...")
    reset_game(game_id)
    print("Done.")
