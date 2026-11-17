"""
tests/test_rulings.py

Tests for tools/get_leaderboard.py, tools/list_rulings.py,
and tools/override_ruling.py.

Uses FakeCloudant and monkey-patching so no network calls are made.
All player names and team names are made up.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tools.get_leaderboard as gl
import tools.list_rulings as lr
import tools.override_ruling as ovr
from tests.fakes import FakeCloudant

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = "Riverside Rockets"
AWAY = "Lakeside Lions"
GAME_ID = "game_1"
GAME_ID_2 = "game_2"
GROUP_ID = "group_a"
OTHER_GROUP = "group_b"
DB = "rivalry_watch_party"
ORGANIZER = "Morgan"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _game_state(game_id: str = GAME_ID, organizer: str = ORGANIZER) -> dict:
    return {
        "_id": f"game_state:{game_id}",
        "type": "game_state",
        "game_id": game_id,
        "sport": "basketball",
        "home_team": HOME,
        "away_team": AWAY,
        "source": "recorded",
        "status": "final",
        "last_sequence": 10,
        "home_score": 21,
        "away_score": 18,
        "period": 2,
        "organizer": organizer,
        "updated_at": "2025-01-01T12:00:00Z",
    }


def _ruling(
    pred_short_id: str,
    player: str = "Alex",
    status: str = "right",
    points: int = 1,
    group_id: str = GROUP_ID,
    game_id: str = GAME_ID,
    prediction_type: str = "game_winner",
    team: str = HOME,
    changes: list | None = None,
) -> dict:
    pred_id = f"prediction:{game_id}:{pred_short_id}"
    ruling_id = f"ruling:{pred_id}"
    return {
        "_id": ruling_id,
        "type": "ruling",
        "ruling_id": ruling_id,
        "prediction_id": pred_id,
        "game_id": game_id,
        "group_id": group_id,
        "player": player,
        "prediction_type": prediction_type,
        "team": team,
        "status": status,
        "reason": "Test reason.",
        "points": points,
        "event_id": "evt_001",
        "decided_at": "2025-01-01T12:00:00Z",
        "changes": changes if changes is not None else [],
    }


# ---------------------------------------------------------------------------
# Monkey-patch helpers — get_leaderboard
# ---------------------------------------------------------------------------

def _apply_gl_patches(monkeypatch, fake: FakeCloudant):
    def fake_get_creds():
        return "http://fake", "fake-apikey", DB

    def fake_get_iam_token(apikey):
        return "fake-token"

    def fake_all_docs_by_prefix(base_url, db, prefix, token):
        return fake.all_docs_by_prefix(db, prefix)

    monkeypatch.setattr(gl, "_get_creds", fake_get_creds)
    monkeypatch.setattr(gl, "_get_iam_token", fake_get_iam_token)
    monkeypatch.setattr(gl, "_all_docs_by_prefix", fake_all_docs_by_prefix)


# ---------------------------------------------------------------------------
# Monkey-patch helpers — list_rulings
# ---------------------------------------------------------------------------

def _apply_lr_patches(monkeypatch, fake: FakeCloudant):
    def fake_get_creds():
        return "http://fake", "fake-apikey", DB

    def fake_get_iam_token(apikey):
        return "fake-token"

    def fake_all_docs_by_prefix(base_url, db, prefix, token):
        return fake.all_docs_by_prefix(db, prefix)

    monkeypatch.setattr(lr, "_get_creds", fake_get_creds)
    monkeypatch.setattr(lr, "_get_iam_token", fake_get_iam_token)
    monkeypatch.setattr(lr, "_all_docs_by_prefix", fake_all_docs_by_prefix)


# ---------------------------------------------------------------------------
# Monkey-patch helpers — override_ruling
# ---------------------------------------------------------------------------

def _apply_ovr_patches(monkeypatch, fake: FakeCloudant):
    def fake_get_creds():
        return "http://fake", "fake-apikey", DB

    def fake_get_iam_token(apikey):
        return "fake-token"

    def fake_get_doc(base_url, db, doc_id, token):
        return fake.get_doc(db, doc_id)

    def fake_put_doc(base_url, db, doc_id, body, token):
        return fake.put_doc(db, doc_id, body)

    monkeypatch.setattr(ovr, "_get_creds", fake_get_creds)
    monkeypatch.setattr(ovr, "_get_iam_token", fake_get_iam_token)
    monkeypatch.setattr(ovr, "_get_doc", fake_get_doc)
    monkeypatch.setattr(ovr, "_put_doc", fake_put_doc)


# ===========================================================================
# Tests: get_leaderboard
# ===========================================================================

class TestGetLeaderboard:

    def test_single_game_totals_correct(self, monkeypatch):
        """Points and counts are right for a single game."""
        fake = FakeCloudant()
        # Alex: 2 right (2 pts), Taylor: 1 wrong (0 pts), Jordan: 1 not_counted (0 pts)
        fake.seed(DB, _ruling("p1", player="Alex", status="right", points=1))
        fake.seed(DB, _ruling("p2", player="Alex", status="right", points=1))
        fake.seed(DB, _ruling("p3", player="Taylor", status="wrong", points=0))
        fake.seed(DB, _ruling("p4", player="Jordan", status="not_counted", points=0))
        _apply_gl_patches(monkeypatch, fake)

        result = gl.get_leaderboard.fn(game_id=GAME_ID, group_id="all")

        assert result["ok"] is True
        lb = {row["player"]: row for row in result["leaderboard"]}
        assert lb["Alex"]["points"] == 2
        assert lb["Alex"]["right"] == 2
        assert lb["Alex"]["wrong"] == 0
        assert lb["Alex"]["not_counted"] == 0
        assert lb["Taylor"]["points"] == 0
        assert lb["Taylor"]["wrong"] == 1
        assert lb["Jordan"]["not_counted"] == 1

    def test_sorted_high_to_low(self, monkeypatch):
        """The leaderboard is sorted by points descending."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", player="Casey", status="right", points=1))
        fake.seed(DB, _ruling("p2", player="Riley", status="right", points=1))
        fake.seed(DB, _ruling("p3", player="Riley", status="right", points=1))
        fake.seed(DB, _ruling("p4", player="Sam", status="wrong", points=0))
        _apply_gl_patches(monkeypatch, fake)

        result = gl.get_leaderboard.fn(game_id=GAME_ID, group_id="all")

        assert result["ok"] is True
        points = [row["points"] for row in result["leaderboard"]]
        assert points == sorted(points, reverse=True)
        assert result["leaderboard"][0]["player"] == "Riley"

    def test_all_games_combines_scores(self, monkeypatch):
        """game_id="all" totals across both games."""
        fake = FakeCloudant()
        # Alex: 1 right in game_1 and 1 right in game_2 → 2 total points
        fake.seed(DB, _ruling("p1", player="Alex", status="right", points=1, game_id=GAME_ID))
        fake.seed(DB, _ruling("p2", player="Alex", status="right", points=1, game_id=GAME_ID_2))
        # Taylor: 1 right in game_1 → 1 total point
        fake.seed(DB, _ruling("p3", player="Taylor", status="right", points=1, game_id=GAME_ID))
        _apply_gl_patches(monkeypatch, fake)

        result = gl.get_leaderboard.fn(game_id="all", group_id="all")

        assert result["ok"] is True
        lb = {row["player"]: row for row in result["leaderboard"]}
        assert lb["Alex"]["points"] == 2
        assert lb["Alex"]["right"] == 2
        assert lb["Taylor"]["points"] == 1

    def test_single_game_excludes_other_game(self, monkeypatch):
        """Filtering by game_id excludes rulings from other games."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", player="Alex", status="right", points=1, game_id=GAME_ID))
        fake.seed(DB, _ruling("p2", player="Alex", status="right", points=1, game_id=GAME_ID_2))
        _apply_gl_patches(monkeypatch, fake)

        result = gl.get_leaderboard.fn(game_id=GAME_ID, group_id="all")

        assert result["ok"] is True
        lb = {row["player"]: row for row in result["leaderboard"]}
        assert lb["Alex"]["points"] == 1

    def test_group_filter(self, monkeypatch):
        """Filtering by group_id excludes other groups."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", player="Alex", status="right", points=1, group_id=GROUP_ID))
        fake.seed(DB, _ruling("p2", player="Taylor", status="right", points=1, group_id=OTHER_GROUP))
        _apply_gl_patches(monkeypatch, fake)

        result = gl.get_leaderboard.fn(game_id=GAME_ID, group_id=GROUP_ID)

        assert result["ok"] is True
        players = [row["player"] for row in result["leaderboard"]]
        assert "Alex" in players
        assert "Taylor" not in players

    def test_empty_leaderboard_when_no_rulings(self, monkeypatch):
        """Returns an empty leaderboard when there are no rulings."""
        fake = FakeCloudant()
        _apply_gl_patches(monkeypatch, fake)

        result = gl.get_leaderboard.fn(game_id=GAME_ID, group_id="all")

        assert result["ok"] is True
        assert result["leaderboard"] == []

    def test_all_games_default(self, monkeypatch):
        """Default arguments return all games and all groups."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", player="Alex", status="right", points=1, game_id=GAME_ID))
        fake.seed(DB, _ruling("p2", player="Taylor", status="right", points=1, game_id=GAME_ID_2))
        _apply_gl_patches(monkeypatch, fake)

        result = gl.get_leaderboard.fn()

        assert result["ok"] is True
        players = {row["player"] for row in result["leaderboard"]}
        assert "Alex" in players
        assert "Taylor" in players


# ===========================================================================
# Tests: list_rulings
# ===========================================================================

class TestListRulings:

    def test_returns_rulings_for_game(self, monkeypatch):
        """All rulings for the requested game are returned."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", game_id=GAME_ID, group_id=GROUP_ID))
        fake.seed(DB, _ruling("p2", game_id=GAME_ID, group_id=GROUP_ID))
        _apply_lr_patches(monkeypatch, fake)

        result = lr.list_rulings.fn(game_id=GAME_ID, group_id="all")

        assert result["ok"] is True
        assert len(result["rulings"]) == 2

    def test_excludes_other_game(self, monkeypatch):
        """Rulings from a different game are not included."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", game_id=GAME_ID))
        fake.seed(DB, _ruling("p2", game_id=GAME_ID_2))
        _apply_lr_patches(monkeypatch, fake)

        result = lr.list_rulings.fn(game_id=GAME_ID, group_id="all")

        assert result["ok"] is True
        assert len(result["rulings"]) == 1
        assert result["rulings"][0]["game_id"] == GAME_ID

    def test_group_filter(self, monkeypatch):
        """Filtering by group_id excludes other groups."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", group_id=GROUP_ID))
        fake.seed(DB, _ruling("p2", group_id=OTHER_GROUP))
        _apply_lr_patches(monkeypatch, fake)

        result = lr.list_rulings.fn(game_id=GAME_ID, group_id=GROUP_ID)

        assert result["ok"] is True
        assert len(result["rulings"]) == 1
        assert result["rulings"][0]["group_id"] == GROUP_ID

    def test_all_groups_returned_by_default(self, monkeypatch):
        """group_id="all" returns rulings from every group."""
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", group_id=GROUP_ID))
        fake.seed(DB, _ruling("p2", group_id=OTHER_GROUP))
        _apply_lr_patches(monkeypatch, fake)

        result = lr.list_rulings.fn(game_id=GAME_ID, group_id="all")

        assert result["ok"] is True
        assert len(result["rulings"]) == 2

    def test_ruling_includes_changes(self, monkeypatch):
        """The changes list is returned as part of the ruling."""
        change = {"changed_by": ORGANIZER, "old_status": "wrong", "new_status": "right",
                  "reason": "Referee error.", "changed_at": "2025-01-01T13:00:00Z"}
        fake = FakeCloudant()
        fake.seed(DB, _ruling("p1", status="right", changes=[change]))
        _apply_lr_patches(monkeypatch, fake)

        result = lr.list_rulings.fn(game_id=GAME_ID)

        assert result["ok"] is True
        assert len(result["rulings"][0]["changes"]) == 1
        assert result["rulings"][0]["changes"][0]["old_status"] == "wrong"

    def test_empty_when_no_rulings(self, monkeypatch):
        """Returns an empty list when there are no rulings for the game."""
        fake = FakeCloudant()
        _apply_lr_patches(monkeypatch, fake)

        result = lr.list_rulings.fn(game_id=GAME_ID)

        assert result["ok"] is True
        assert result["rulings"] == []


# ===========================================================================
# Tests: override_ruling
# ===========================================================================

class TestOverrideRuling:

    def _setup(self, fake: FakeCloudant, ruling: dict) -> None:
        """Seed the database with a game_state and a ruling."""
        fake.seed(DB, _game_state())
        fake.seed(DB, ruling)

    def test_organizer_can_override(self, monkeypatch):
        """The organizer can change a wrong ruling to right."""
        fake = FakeCloudant()
        r = _ruling("p1", status="wrong", points=0)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        result = ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="right",
            requested_by=ORGANIZER,
            reason="The scorer made an error.",
        )

        assert result["ok"] is True
        saved = fake.get_doc(DB, r["_id"])
        assert saved["status"] == "right"
        assert saved["points"] == 1

    def test_override_adds_to_changes_list(self, monkeypatch):
        """An accepted override adds one item to the changes list."""
        fake = FakeCloudant()
        r = _ruling("p1", status="wrong", points=0)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="right",
            requested_by=ORGANIZER,
            reason="Scorer error.",
        )

        saved = fake.get_doc(DB, r["_id"])
        assert len(saved["changes"]) == 1
        change = saved["changes"][0]
        assert change["old_status"] == "wrong"
        assert change["new_status"] == "right"
        assert change["changed_by"] == ORGANIZER
        assert change["reason"] == "Scorer error."

    def test_override_records_old_status(self, monkeypatch):
        """The changes entry preserves the old status before the override."""
        fake = FakeCloudant()
        r = _ruling("p1", status="not_counted", points=0)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="wrong",
            requested_by=ORGANIZER,
            reason="Clerical mistake.",
        )

        saved = fake.get_doc(DB, r["_id"])
        assert saved["changes"][0]["old_status"] == "not_counted"

    def test_override_updates_points_to_zero_for_wrong(self, monkeypatch):
        """Overriding to wrong sets points to 0."""
        fake = FakeCloudant()
        r = _ruling("p1", status="right", points=1)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="wrong",
            requested_by=ORGANIZER,
            reason="Reversed.",
        )

        saved = fake.get_doc(DB, r["_id"])
        assert saved["status"] == "wrong"
        assert saved["points"] == 0

    def test_override_updates_points_to_zero_for_not_counted(self, monkeypatch):
        """Overriding to not_counted sets points to 0."""
        fake = FakeCloudant()
        r = _ruling("p1", status="right", points=1)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="not_counted",
            requested_by=ORGANIZER,
            reason="Voided.",
        )

        saved = fake.get_doc(DB, r["_id"])
        assert saved["status"] == "not_counted"
        assert saved["points"] == 0

    def test_non_organizer_refused(self, monkeypatch):
        """A person who is not the organizer cannot override a ruling."""
        fake = FakeCloudant()
        r = _ruling("p1", status="wrong", points=0)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        result = ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="right",
            requested_by="RandomPerson",
            reason="I disagree.",
        )

        assert result["ok"] is False
        assert "organizer" in result["error"].lower()

    def test_refused_override_changes_nothing(self, monkeypatch):
        """A refused override does not modify the ruling document."""
        fake = FakeCloudant()
        r = _ruling("p1", status="wrong", points=0)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="right",
            requested_by="RandomPerson",
            reason="I disagree.",
        )

        saved = fake.get_doc(DB, r["_id"])
        assert saved["status"] == "wrong"
        assert saved["points"] == 0
        assert saved["changes"] == []

    def test_invalid_new_status_refused(self, monkeypatch):
        """An invalid new_status returns ok=False before touching the database."""
        fake = FakeCloudant()
        r = _ruling("p1", status="wrong", points=0)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        result = ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="open",
            requested_by=ORGANIZER,
            reason="Trying something invalid.",
        )

        assert result["ok"] is False
        # Document must be unchanged.
        saved = fake.get_doc(DB, r["_id"])
        assert saved["status"] == "wrong"

    def test_ruling_not_found_returns_error(self, monkeypatch):
        """Returns ok=False when the ruling_id does not exist."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_ovr_patches(monkeypatch, fake)

        result = ovr.override_ruling.fn(
            ruling_id="ruling:prediction:game_1:nonexistent",
            new_status="right",
            requested_by=ORGANIZER,
            reason="Does not matter.",
        )

        assert result["ok"] is False
        assert "not found" in result["error"].lower()

    def test_second_override_appends_to_changes(self, monkeypatch):
        """A second override appends a second item to the changes list."""
        fake = FakeCloudant()
        r = _ruling("p1", status="wrong", points=0)
        self._setup(fake, r)
        _apply_ovr_patches(monkeypatch, fake)

        # First override: wrong → right
        ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="right",
            requested_by=ORGANIZER,
            reason="First correction.",
        )

        # Second override: right → not_counted
        ovr.override_ruling.fn(
            ruling_id=r["_id"],
            new_status="not_counted",
            requested_by=ORGANIZER,
            reason="Second correction.",
        )

        saved = fake.get_doc(DB, r["_id"])
        assert len(saved["changes"]) == 2
        assert saved["changes"][0]["old_status"] == "wrong"
        assert saved["changes"][1]["old_status"] == "right"
        assert saved["status"] == "not_counted"
        assert saved["points"] == 0
