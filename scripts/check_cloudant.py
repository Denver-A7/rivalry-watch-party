"""
check_cloudant.py

Checks the Cloudant connection. Steps:
  1. Load .env if it exists, then read CLOUDANT_URL and CLOUDANT_APIKEY.
  2. Get an IAM bearer token.
  3. Print the database names (never prints the URL or key).
  4. Create the database rivalry_watch_party if it does not exist.
  5. Create a test document, read it back, delete it, and print OK.
"""

import os
import sys
import uuid

import requests
from dotenv import load_dotenv

DB_NAME = "rivalry_watch_party"
IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"


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
        print(f"ERROR: Could not get IAM token. Status {resp.status_code}: {resp.text}")
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


def list_databases(token, url):
    """Print all database names."""
    resp = cloudant_request("GET", "/_all_dbs", token, url)
    if resp.status_code != 200:
        print(f"ERROR listing databases: {resp.status_code} {resp.text}")
        sys.exit(1)
    dbs = resp.json()
    print(f"Databases ({len(dbs)}):")
    for name in dbs:
        print(f"  {name}")


def ensure_database(token, url):
    """Create rivalry_watch_party if it does not exist."""
    resp = cloudant_request("HEAD", f"/{DB_NAME}", token, url)
    if resp.status_code == 200:
        print(f"Database '{DB_NAME}' already exists.")
        return
    if resp.status_code == 404:
        put = cloudant_request("PUT", f"/{DB_NAME}", token, url)
        if put.status_code in (201, 202):
            print(f"Database '{DB_NAME}' created.")
        else:
            print(f"ERROR creating database: {put.status_code} {put.text}")
            sys.exit(1)
    else:
        print(f"ERROR checking database: {resp.status_code} {resp.text}")
        sys.exit(1)


def test_document(token, url):
    """Create, read, and delete one test document. Print OK if all steps pass."""
    doc_id = f"check_test_{uuid.uuid4().hex}"

    # Create
    create = cloudant_request(
        "PUT", f"/{DB_NAME}/{doc_id}", token, url,
        json={"type": "check_test", "note": "temporary test document"},
    )
    if create.status_code not in (201, 202):
        print(f"ERROR creating test document: {create.status_code} {create.text}")
        sys.exit(1)
    rev = create.json()["rev"]

    # Read back
    read = cloudant_request("GET", f"/{DB_NAME}/{doc_id}", token, url)
    if read.status_code != 200:
        print(f"ERROR reading test document: {read.status_code} {read.text}")
        sys.exit(1)

    # Delete
    delete = cloudant_request(
        "DELETE", f"/{DB_NAME}/{doc_id}?rev={rev}", token, url,
    )
    if delete.status_code not in (200, 202):
        print(f"ERROR deleting test document: {delete.status_code} {delete.text}")
        sys.exit(1)

    print("Test document: OK")


def main():
    url, apikey = load_credentials()
    print("Getting IAM token...")
    token = get_iam_token(apikey)
    print("IAM token obtained.")
    list_databases(token, url)
    ensure_database(token, url)
    test_document(token, url)


if __name__ == "__main__":
    main()
