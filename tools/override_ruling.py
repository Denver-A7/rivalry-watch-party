"""
tools/override_ruling.py

Allows the organizer of a watch party to override a ruling.
Only the organizer named in game_state may request an override.
The old status is kept in the ruling's changes list.
"""

import os
import datetime

import requests

from ibm_watsonx_orchestrate.agent_builder.tools import tool
from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType

# Valid final statuses a ruling may have.
VALID_STATUSES = {"right", "wrong", "not_counted"}

# Points for a right ruling.
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
def override_ruling(ruling_id: str, new_status: str, requested_by: str, reason: str) -> dict:
    """Override a ruling. Only the game organizer may do this.

    Updates the ruling status and points. Keeps the old status in the changes list.
    new_status must be right, wrong, or not_counted.

    Args:
        ruling_id: The ruling identifier (e.g. ruling:prediction:game_1:abc123).
        new_status: The new status: right, wrong, or not_counted.
        requested_by: The name of the person requesting the override.
        reason: A short plain sentence explaining why the ruling is being changed.

    Returns:
        A dict with ok and the updated ruling, or ok=False with an error message.
    """
    try:
        if new_status not in VALID_STATUSES:
            return {"ok": False, "error": f"new_status must be one of {sorted(VALID_STATUSES)}."}

        base_url, apikey, database = _get_creds()
        token = _get_iam_token(apikey)

        # Read the ruling.
        ruling = _get_doc(base_url, database, ruling_id, token)
        if ruling is None:
            return {"ok": False, "error": f"Ruling '{ruling_id}' not found."}

        # Find the game_state to check the organizer.
        game_id = ruling.get("game_id")
        game_state = _get_doc(base_url, database, f"game_state:{game_id}", token)
        if game_state is None:
            return {"ok": False, "error": f"game_state not found for game '{game_id}'."}

        organizer = game_state.get("organizer", "")
        if requested_by != organizer:
            return {"ok": False, "error": f"Only the organizer '{organizer}' may override a ruling."}

        old_status = ruling["status"]

        # Record the change.
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        change = {
            "changed_by": requested_by,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
            "changed_at": now,
        }
        ruling.setdefault("changes", []).append(change)

        # Update status and points.
        ruling["status"] = new_status
        ruling["points"] = POINTS_RIGHT if new_status == "right" else 0

        # Save with retry on conflict.
        result = _put_doc(base_url, database, ruling_id, ruling, token)
        if not result.get("ok") and result.get("error") == "conflict":
            # Re-read and retry once.
            fresh = _get_doc(base_url, database, ruling_id, token)
            if fresh is None:
                return {"ok": False, "error": "Ruling disappeared during update."}
            # Apply changes onto the fresh document.
            fresh["status"] = new_status
            fresh["points"] = ruling["points"]
            fresh.setdefault("changes", []).append(change)
            result = _put_doc(base_url, database, ruling_id, fresh, token)

        return {"ok": True, "ruling": ruling}

    except Exception as exc:
        return {"ok": False, "error": str(exc)}
