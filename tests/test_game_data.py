"""
tests/test_game_data.py

Tests for tools/get_next_game_events.py.

Uses FakeCloudant and monkey-patching so no network calls are made.
All events and player names are made up.
"""

import sys
import os
import pytest

# Allow importing from tools/ directly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tools.get_next_game_events as gne
from tests.fakes import FakeCloudant

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = "KC"
AWAY = "BAL"
GAME_ID = "game_1"
DB = "rivalry_watch_party"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _game_state(
    last_sequence: int = 0,
    home_score: int = 0,
    away_score: int = 0,
    source: str = "recorded",
    status: str = "in_progress",
) -> dict:
    return {
        "_id": f"game_state:{GAME_ID}",
        "type": "game_state",
        "game_id": GAME_ID,
        "sport": "football",
        "home_team": HOME,
        "away_team": AWAY,
        "source": source,
        "status": status,
        "last_sequence": last_sequence,
        "home_score": home_score,
        "away_score": away_score,
        "period": 1,
        "organizer": "Casey",
        "updated_at": "2025-01-01T00:00:00Z",
    }


def _event(
    seq: int,
    event_type: str = "score",
    team: str | None = HOME,
    home_score: int = 7,
    away_score: int = 0,
    period: int = 1,
    event_id: str | None = None,
) -> dict:
    """Make a minimal valid game_event document."""
    return {
        "_id": f"game_event:{GAME_ID}:{seq:05d}",
        "type": "game_event",
        "game_id": GAME_ID,
        "event_id": event_id or f"evt_{seq:05d}",
        "sequence": seq,
        "event_type": event_type,
        "team": team,
        "points": 7 if team else None,
        "home_score": home_score,
        "away_score": away_score,
        "period": period,
        "clock": "10:00",
        "description": f"Made-up event {seq}",
        "source": "recorded",
    }


# ---------------------------------------------------------------------------
# Monkey-patch helpers
# ---------------------------------------------------------------------------

def _make_patch(fake: FakeCloudant):
    """Return functions that replace the HTTP helpers with FakeCloudant."""

    def fake_get_creds():
        return "http://fake", "fake-apikey", DB

    def fake_get_iam_token(apikey: str) -> str:
        return "fake-token"

    def fake_get_doc(base_url, db, doc_id, token):
        return fake.get_doc(db, doc_id)

    def fake_put_doc(base_url, db, doc_id, body, token):
        return fake.put_doc(db, doc_id, body)

    def fake_all_docs_by_prefix(base_url, db, prefix, token):
        return fake.all_docs_by_prefix(db, prefix)

    return {
        "_get_creds": fake_get_creds,
        "_get_iam_token": fake_get_iam_token,
        "_get_doc": fake_get_doc,
        "_put_doc": fake_put_doc,
        "_all_docs_by_prefix": fake_all_docs_by_prefix,
    }


def _apply_patches(monkeypatch, fake: FakeCloudant):
    patches = _make_patch(fake)
    for name, fn in patches.items():
        monkeypatch.setattr(gne, name, fn)


# ===========================================================================
# Tests: normal events are accepted and update game_state
# ===========================================================================

class TestNormalEvents:
    def test_single_event_accepted(self, monkeypatch):
        """A valid score event is accepted and game_state is updated."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=0))
        fake.seed(DB, _event(seq=1, home_score=7, away_score=0))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is True
        assert len(result["accepted"]) == 1
        assert len(result["rejected"]) == 0
        assert result["accepted"][0]["sequence"] == 1

    def test_game_state_updated_after_accept(self, monkeypatch):
        """Accepted event updates last_sequence, scores, and period in game_state."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=0))
        fake.seed(DB, _event(seq=1, home_score=7, away_score=0, period=2))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        gs = result["game_state"]
        assert gs["last_sequence"] == 1
        assert gs["home_score"] == 7
        assert gs["away_score"] == 0
        assert gs["period"] == 2

    def test_game_state_persisted_in_cloudant(self, monkeypatch):
        """game_state in Cloudant reflects the update after a successful call."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=0))
        fake.seed(DB, _event(seq=1, home_score=7, away_score=0))
        _apply_patches(monkeypatch, fake)

        gne.get_next_game_events.fn(GAME_ID, count=1)

        stored = fake.get_doc(DB, f"game_state:{GAME_ID}")
        assert stored["last_sequence"] == 1
        assert stored["home_score"] == 7

    def test_multiple_events_accepted_in_order(self, monkeypatch):
        """count=2 returns events in sequence order."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=0))
        fake.seed(DB, _event(seq=1, home_score=7, away_score=0))
        fake.seed(DB, _event(seq=2, home_score=7, away_score=7, team=AWAY))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=2)

        assert result["ok"] is True
        assert len(result["accepted"]) == 2
        assert result["accepted"][0]["sequence"] == 1
        assert result["accepted"][1]["sequence"] == 2

    def test_only_next_count_events_returned(self, monkeypatch):
        """With count=1, only the first new event is returned even if more exist."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=0))
        fake.seed(DB, _event(seq=1, home_score=7, away_score=0))
        fake.seed(DB, _event(seq=2, home_score=14, away_score=0))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert len(result["accepted"]) == 1
        assert result["accepted"][0]["sequence"] == 1

    def test_game_end_sets_status_final(self, monkeypatch):
        """A game_end event changes game_state.status to 'final'."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=0))
        fake.seed(DB, _event(seq=1, event_type="game_end", team=None, home_score=14, away_score=7))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["game_state"]["status"] == "final"

    def test_null_team_allowed(self, monkeypatch):
        """An event with team=null (e.g. game_end, other) is valid."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=0))
        fake.seed(DB, _event(seq=1, event_type="other", team=None, home_score=0, away_score=0))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is True
        assert len(result["accepted"]) == 1
        assert len(result["rejected"]) == 0

    def test_no_new_events_returns_empty(self, monkeypatch):
        """When all events are at or below last_sequence, nothing is returned."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=5))
        fake.seed(DB, _event(seq=3))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is True
        assert result["accepted"] == []
        assert result["rejected"] == []

    def test_missing_game_state_returns_error(self, monkeypatch):
        """Returns ok=False if game_state does not exist."""
        fake = FakeCloudant()
        # No game_state seeded.
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is False
        assert "game_state not found" in result["error"]


# ===========================================================================
# Tests: bad events are rejected with a clear reason and do not change state
# ===========================================================================

class TestBadEvents:
    """
    Each bad event from data/test_bad_events.json is tested individually.
    game_state has last_sequence=5, home_score=14, away_score=14.
    One event with event_id 'evt_dup_001' is already in Cloudant.
    """

    def _setup_base_state(self, fake: FakeCloudant):
        """Seed game_state at sequence 5 with scores 14-14."""
        fake.seed(DB, _game_state(last_sequence=5, home_score=14, away_score=14))
        # Seed an existing event that introduced 'evt_dup_001'.
        existing = _event(seq=5, home_score=14, away_score=14, event_id="evt_dup_001")
        fake.seed(DB, existing)

    def _assert_state_unchanged(self, fake: FakeCloudant):
        """Check that game_state has not been modified."""
        gs = fake.get_doc(DB, f"game_state:{GAME_ID}")
        assert gs["last_sequence"] == 5
        assert gs["home_score"] == 14
        assert gs["away_score"] == 14

    # --- duplicate event_id ---

    def test_duplicate_event_id_rejected(self, monkeypatch):
        """An event whose event_id was already seen is rejected as 'Not new'."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        # Insert a new document with a NEW sequence but a DUPLICATE event_id.
        dup = _event(seq=6, home_score=21, away_score=14, event_id="evt_dup_001")
        fake.seed(DB, dup)
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is True
        assert result["accepted"] == []
        assert len(result["rejected"]) == 1
        assert "Not new" in result["rejected"][0]["reason"]
        assert "duplicate" in result["rejected"][0]["reason"].lower()

    def test_duplicate_event_id_does_not_change_state(self, monkeypatch):
        """game_state is not modified when the only candidate is a duplicate."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        dup = _event(seq=6, home_score=21, away_score=14, event_id="evt_dup_001")
        fake.seed(DB, dup)
        _apply_patches(monkeypatch, fake)

        gne.get_next_game_events.fn(GAME_ID, count=1)

        self._assert_state_unchanged(fake)

    # --- old sequence ---

    def test_old_sequence_not_fetched(self, monkeypatch):
        """An event with sequence <= last_sequence is never a candidate."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        # seq=3 is already below last_sequence=5.
        old = _event(seq=3, home_score=14, away_score=14, event_id="evt_old_002")
        fake.seed(DB, old)
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        # The old event is never a candidate; nothing to accept or reject.
        assert result["ok"] is True
        assert result["accepted"] == []
        assert result["rejected"] == []

    def test_old_sequence_does_not_change_state(self, monkeypatch):
        """game_state is not modified when the only available event is old."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        old = _event(seq=3, home_score=14, away_score=14, event_id="evt_old_002")
        fake.seed(DB, old)
        _apply_patches(monkeypatch, fake)

        gne.get_next_game_events.fn(GAME_ID, count=1)

        self._assert_state_unchanged(fake)

    # --- missing required field ---

    def test_missing_field_rejected(self, monkeypatch):
        """An event missing 'home_score' is rejected with a clear reason."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        bad = _event(seq=7, home_score=21, away_score=14, event_id="evt_missing_003")
        # Remove the required field.
        del bad["home_score"]
        fake.seed(DB, bad)
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is True
        assert result["accepted"] == []
        assert len(result["rejected"]) == 1
        reason = result["rejected"][0]["reason"]
        assert "home_score" in reason
        assert "Missing" in reason

    def test_missing_field_does_not_change_state(self, monkeypatch):
        """game_state is not modified when the only candidate has a missing field."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        bad = _event(seq=7, home_score=21, away_score=14, event_id="evt_missing_003")
        del bad["home_score"]
        fake.seed(DB, bad)
        _apply_patches(monkeypatch, fake)

        gne.get_next_game_events.fn(GAME_ID, count=1)

        self._assert_state_unchanged(fake)

    # --- unknown team ---

    def test_unknown_team_rejected(self, monkeypatch):
        """An event with a team not in the game is rejected with a clear reason."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        bad = _event(seq=8, home_score=14, away_score=14, event_id="evt_badteam_004")
        bad["team"] = "UNKNOWN_FC"
        fake.seed(DB, bad)
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is True
        assert result["accepted"] == []
        assert len(result["rejected"]) == 1
        reason = result["rejected"][0]["reason"]
        assert "UNKNOWN_FC" in reason

    def test_unknown_team_does_not_change_state(self, monkeypatch):
        """game_state is not modified when the only candidate has an unknown team."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        bad = _event(seq=8, home_score=14, away_score=14, event_id="evt_badteam_004")
        bad["team"] = "UNKNOWN_FC"
        fake.seed(DB, bad)
        _apply_patches(monkeypatch, fake)

        gne.get_next_game_events.fn(GAME_ID, count=1)

        self._assert_state_unchanged(fake)

    # --- score going down ---

    def test_score_down_rejected(self, monkeypatch):
        """An event where away_score drops is rejected with a clear reason."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        bad = _event(seq=9, home_score=21, away_score=7, event_id="evt_scoredown_005")
        fake.seed(DB, bad)
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is True
        assert result["accepted"] == []
        assert len(result["rejected"]) == 1
        reason = result["rejected"][0]["reason"]
        assert "away_score" in reason
        assert "down" in reason.lower()

    def test_score_down_does_not_change_state(self, monkeypatch):
        """game_state is not modified when the only candidate has a score going down."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        bad = _event(seq=9, home_score=21, away_score=7, event_id="evt_scoredown_005")
        fake.seed(DB, bad)
        _apply_patches(monkeypatch, fake)

        gne.get_next_game_events.fn(GAME_ID, count=1)

        self._assert_state_unchanged(fake)

    # --- mixed: one good and one bad event ---

    def test_good_event_accepted_bad_rejected_in_same_call(self, monkeypatch):
        """With count=2, a good event at seq=6 is accepted and a bad one at seq=7 is rejected."""
        fake = FakeCloudant()
        self._setup_base_state(fake)
        good = _event(seq=6, home_score=21, away_score=14, event_id="evt_good_006")
        bad = _event(seq=7, home_score=21, away_score=14, event_id="evt_missing_003")
        del bad["home_score"]
        fake.seed(DB, good)
        fake.seed(DB, bad)
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=2)

        assert result["ok"] is True
        assert len(result["accepted"]) == 1
        assert result["accepted"][0]["event_id"] == "evt_good_006"
        assert len(result["rejected"]) == 1
        assert result["rejected"][0]["event"]["event_id"] == "evt_missing_003"
        # State updated by the good event only.
        assert result["game_state"]["last_sequence"] == 6


# ===========================================================================
# Tests: live mode returns the error message
# ===========================================================================

class TestLiveMode:
    def test_live_mode_returns_error(self, monkeypatch):
        """If game_state.source is 'live', the tool returns the expected error."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(source="live"))
        _apply_patches(monkeypatch, fake)

        result = gne.get_next_game_events.fn(GAME_ID, count=1)

        assert result["ok"] is False
        assert result["error"] == "Live source not enabled yet."

    def test_live_mode_does_not_change_state(self, monkeypatch):
        """game_state is not modified when source is 'live'."""
        fake = FakeCloudant()
        gs = _game_state(source="live", last_sequence=3)
        fake.seed(DB, gs)
        _apply_patches(monkeypatch, fake)

        gne.get_next_game_events.fn(GAME_ID, count=1)

        stored = fake.get_doc(DB, f"game_state:{GAME_ID}")
        assert stored["last_sequence"] == 3
