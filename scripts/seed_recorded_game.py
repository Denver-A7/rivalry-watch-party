"""
seed_recorded_game.py

Uploads data/recorded_game_game_1.json to Cloudant as game_event documents.
Also creates one game_state document for game_1.

Safe to run more than once. Existing documents are not changed and no
duplicates are created.

Credentials: reads CLOUDANT_URL and CLOUDANT_APIKEY from .env then
environment. Never prints the key or the URL.
"""

import json
import os
import sys

import requests
from dotenv import load_dotenv

DB_NAME = "rivalry_watch_party"
GAME_ID = "game_1"
DATA_FILE = "data/recorded_game_game_1.json"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"

# Known teams from recorded_game_game_1.json
HOME_TEAM = "KC"
AWAY_TEAM = "BAL"
SPORT = "football"
ORGANIZER = "Maya"


def load_credentials():
    """Load URL and API key from .env then environment. Return (url, apikey)."""
    if os.path.exists(".env"):
        load_dotenv(".env", override=False)
    url = os.environ.get("CLOUDANT_URL", "").strip().rstrip("/")
    apikey = os.environ.get("CLOUDANT_APIKEY", "").strip()
    if not url or not apikey:
        print("ERROR: CLOUDANT_URL or CLOUDANT_APIKEY is not set.")
        sys.exit(1)
    return url, apikey


def get_iam_token(apikey):
    """Exchange the API key for an IAM bearer token. Return the token string."""
    resp = requests.post(
        IAM_TOKEN_URL,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": apikey,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"ERROR: Could not get IAM token. Status {resp.status_code}.")
        sys.exit(1)
    return resp.json()["access_token"]


def cloudant_request(method, path, token, url_base, **kwargs):
    """Make a Cloudant HTTP request. Return the Response object."""
    full_url = f"{url_base}{path}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    return requests.request(method, full_url, headers=headers, timeout=30, **kwargs)


def upsert_document(doc_id, doc, token, url):
    """Write doc to Cloudant. Skip if it already exists. Return 'created' or 'skipped'."""
    # Try to read the existing document to get its _rev.
    get_resp = cloudant_request("GET", f"/{DB_NAME}/{doc_id}", token, url)
    if get_resp.status_code == 200:
        # Document already exists. Do not overwrite it.
        return "skipped"
    if get_resp.status_code != 404:
        print(f"ERROR reading {doc_id}: {get_resp.status_code} {get_resp.text}")
        sys.exit(1)

    # Document does not exist. Create it.
    put_resp = cloudant_request("PUT", f"/{DB_NAME}/{doc_id}", token, url, json=doc)
    if put_resp.status_code not in (201, 202):
        print(f"ERROR writing {doc_id}: {put_resp.status_code} {put_resp.text}")
        sys.exit(1)
    return "created"


def seed_game_state(token, url):
    """Create the game_state document for game_1 if it does not exist."""
    from datetime import datetime, timezone

    doc_id = f"game_state:{GAME_ID}"
    doc = {
        "type": "game_state",
        "game_id": GAME_ID,
        "sport": SPORT,
        "home_team": HOME_TEAM,
        "away_team": AWAY_TEAM,
        "source": "recorded",
        "status": "not_started",
        "last_sequence": 0,
        "home_score": 0,
        "away_score": 0,
        "period": 0,
        "organizer": ORGANIZER,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = upsert_document(doc_id, doc, token, url)
    print(f"game_state:{GAME_ID} -> {result}")
    return result


def seed_game_events(token, url):
    """Upload each event from the JSON file as a game_event document."""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        events = json.load(f)

    created = 0
    skipped = 0
    for event in events:
        seq_str = str(event["sequence"]).zfill(5)
        doc_id = f"game_event:{GAME_ID}:{seq_str}"
        result = upsert_document(doc_id, event, token, url)
        if result == "created":
            created += 1
        else:
            skipped += 1

    print(f"game_event documents: {created} created, {skipped} skipped")
    return created, skipped


def count_by_type(token, url):
    """Count documents by type using _find. Print the totals."""
    for doc_type in ("game_state", "game_event"):
        resp = cloudant_request(
            "POST",
            f"/{DB_NAME}/_find",
            token,
            url,
            json={
                "selector": {"type": {"$eq": doc_type}},
                "fields": ["_id"],
                "limit": 1000,
            },
        )
        if resp.status_code != 200:
            print(f"ERROR querying type={doc_type}: {resp.status_code} {resp.text}")
            continue
        count = len(resp.json().get("docs", []))
        print(f"  type={doc_type}: {count} document(s)")


def main():
    url, apikey = load_credentials()
    print("Getting IAM token...")
    token = get_iam_token(apikey)
    print("IAM token obtained.")

    seed_game_state(token, url)
    seed_game_events(token, url)

    print("\nDocument counts in database:")
    count_by_type(token, url)


if __name__ == "__main__":
    main()
