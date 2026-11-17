"""
tests/fakes.py

In-memory fake Cloudant client for local testing.
Stores documents in a plain dictionary. Supports get, put, and
prefix-scan (_all_docs), just like the real Cloudant HTTP calls
used in the tool files.

This module does NOT touch the network. Tests import functions
from tool files and monkey-patch the HTTP helpers.
"""

import copy
import json


class FakeCloudant:
    """
    Minimal in-memory store that mimics the Cloudant HTTP behaviour
    used by the tool files.

    Documents are stored in self.docs[db][doc_id] as plain dicts.
    Every put increments a fake _rev.
    """

    def __init__(self):
        # db_name -> {doc_id: doc_dict}
        self.docs: dict[str, dict[str, dict]] = {}
        self._rev_counters: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def seed(self, db: str, doc: dict) -> None:
        """Insert a document. Adds _rev = "1-fake" if missing."""
        self.docs.setdefault(db, {})
        d = copy.deepcopy(doc)
        if "_rev" not in d:
            d["_rev"] = "1-fake"
        self.docs[db][d["_id"]] = d

    # ------------------------------------------------------------------
    # HTTP-like interface (mirrors the tool helper functions)
    # ------------------------------------------------------------------

    def get_doc(self, db: str, doc_id: str) -> dict | None:
        """Return a deep copy of the document, or None if missing."""
        db_docs = self.docs.get(db, {})
        doc = db_docs.get(doc_id)
        if doc is None:
            return None
        return copy.deepcopy(doc)

    def put_doc(self, db: str, doc_id: str, body: dict) -> dict:
        """
        Create or update a document.

        Returns {"ok": True} on success.
        Returns {"ok": False, "error": "conflict"} when _rev does not match.
        """
        self.docs.setdefault(db, {})
        existing = self.docs[db].get(doc_id)

        if existing is not None:
            # Update: _rev must match.
            if body.get("_rev") != existing["_rev"]:
                return {"ok": False, "error": "conflict"}

        # Bump _rev.
        counter_key = f"{db}/{doc_id}"
        n = self._rev_counters.get(counter_key, 1) + 1
        self._rev_counters[counter_key] = n

        d = copy.deepcopy(body)
        d["_id"] = doc_id
        d["_rev"] = f"{n}-fake"
        self.docs[db][doc_id] = d
        return {"ok": True, "id": doc_id, "rev": d["_rev"]}

    def all_docs_by_prefix(self, db: str, prefix: str) -> list[dict]:
        """Return all docs whose _id starts with prefix, sorted by _id."""
        db_docs = self.docs.get(db, {})
        result = [
            copy.deepcopy(v)
            for k, v in db_docs.items()
            if k.startswith(prefix)
        ]
        result.sort(key=lambda d: d["_id"])
        return result
