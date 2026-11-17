"""
tests/test_predictions.py

Tests for tools/save_prediction.py and tools/list_open_predictions.py.

Uses FakeCloudant and monkey-patching so no network calls are made.
All player names and team names are made up.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import tools.save_prediction as sp
import tools.list_open_predictions as lop
from tests.fakes import FakeCloudant

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

HOME = "Riverside Rockets"
AWAY = "Lakeside Lions"
GAME_ID = "game_1"
GROUP_ID = "group_a"
OTHER_GROUP = "group_b"
OTHER_GAME = "game_2"
DB = "rivalry_watch_party"


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _game_state(last_sequence: int = 3) -> dict:
    return {
        "_id": f"game_state:{GAME_ID}",
        "type": "game_state",
        "game_id": GAME_ID,
        "sport": "basketball",
        "home_team": HOME,
        "away_team": AWAY,
        "source": "recorded",
        "status": "in_progress",
        "last_sequence": last_sequence,
        "home_score": 7,
        "away_score": 3,
        "period": 1,
        "organizer": "Morgan",
        "updated_at": "2025-01-01T00:00:00Z",
    }


def _prediction(
    pred_id: str,
    prediction_type: str = "game_winner",
    team: str = HOME,
    status: str = "open",
    group_id: str = GROUP_ID,
    game_id: str = GAME_ID,
    player: str = "Alex",
    made_after_sequence: int = 0,
) -> dict:
    return {
        "_id": f"prediction:{game_id}:{pred_id}",
        "type": "prediction",
        "game_id": game_id,
        "group_id": group_id,
        "player": player,
        "prediction_type": prediction_type,
        "team": team,
        "original_text": f"I think {team} will win",
        "made_after_sequence": made_after_sequence,
        "status": status,
        "created_at": "2025-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Monkey-patch helpers — save_prediction
# ---------------------------------------------------------------------------

def _make_sp_patch(fake: FakeCloudant):
    def fake_get_creds():
        return "http://fake", "fake-apikey", DB

    def fake_get_iam_token(apikey):
        return "fake-token"

    def fake_get_doc(base_url, db, doc_id, token):
        return fake.get_doc(db, doc_id)

    def fake_put_doc(base_url, db, doc_id, body, token):
        return fake.put_doc(db, doc_id, body)

    return {
        "_get_creds": fake_get_creds,
        "_get_iam_token": fake_get_iam_token,
        "_get_doc": fake_get_doc,
        "_put_doc": fake_put_doc,
    }


def _apply_sp_patches(monkeypatch, fake: FakeCloudant):
    for name, fn in _make_sp_patch(fake).items():
        monkeypatch.setattr(sp, name, fn)


# ---------------------------------------------------------------------------
# Monkey-patch helpers — list_open_predictions
# ---------------------------------------------------------------------------

def _make_lop_patch(fake: FakeCloudant):
    def fake_get_creds():
        return "http://fake", "fake-apikey", DB

    def fake_get_iam_token(apikey):
        return "fake-token"

    def fake_all_docs_by_prefix(base_url, db, prefix, token):
        return fake.all_docs_by_prefix(db, prefix)

    return {
        "_get_creds": fake_get_creds,
        "_get_iam_token": fake_get_iam_token,
        "_all_docs_by_prefix": fake_all_docs_by_prefix,
    }


def _apply_lop_patches(monkeypatch, fake: FakeCloudant):
    for name, fn in _make_lop_patch(fake).items():
        monkeypatch.setattr(lop, name, fn)


# ===========================================================================
# Tests: save_prediction
# ===========================================================================

class TestSavePrediction:

    def test_valid_prediction_saved_with_status_open(self, monkeypatch):
        """A valid prediction is saved and returned with status open."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=3))
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Alex", "game_winner", HOME, "I think Rockets win"
        )

        assert result["ok"] is True
        pred_id = result["prediction_id"]
        saved = fake.get_doc(DB, pred_id)
        assert saved is not None
        assert saved["status"] == "open"

    def test_made_after_sequence_set_from_game_state(self, monkeypatch):
        """made_after_sequence equals game_state.last_sequence at save time."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state(last_sequence=5))
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Taylor", "next_score", AWAY, "Lions score next"
        )

        assert result["ok"] is True
        saved = fake.get_doc(DB, result["prediction_id"])
        assert saved["made_after_sequence"] == 5

    def test_all_required_fields_present(self, monkeypatch):
        """The saved document contains all required prediction fields."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Jordan", "scores_before_half", HOME, "Rockets score first"
        )

        saved = fake.get_doc(DB, result["prediction_id"])
        for field in [
            "type", "game_id", "group_id", "player", "prediction_type",
            "team", "original_text", "made_after_sequence", "status", "created_at",
        ]:
            assert field in saved, f"Missing field: {field}"

    def test_prediction_id_contains_game_id(self, monkeypatch):
        """The prediction_id contains the game_id as a prefix."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Sam", "game_winner", HOME, "Rockets all the way"
        )

        assert result["prediction_id"].startswith(f"prediction:{GAME_ID}:")

    def test_correct_fields_stored(self, monkeypatch):
        """game_id, group_id, player, prediction_type, team and original_text match inputs."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Casey", "next_score", AWAY, "Lions going next"
        )

        saved = fake.get_doc(DB, result["prediction_id"])
        assert saved["game_id"] == GAME_ID
        assert saved["group_id"] == GROUP_ID
        assert saved["player"] == "Casey"
        assert saved["prediction_type"] == "next_score"
        assert saved["team"] == AWAY
        assert saved["original_text"] == "Lions going next"

    # --- unknown prediction_type ---

    def test_unknown_prediction_type_refused(self, monkeypatch):
        """An unknown prediction_type returns ok=False with a clear error."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Alex", "coin_flip", HOME, "I flip a coin"
        )

        assert result["ok"] is False
        assert "coin_flip" in result["error"]

    def test_unknown_prediction_type_not_saved(self, monkeypatch):
        """No document is written to Cloudant when prediction_type is invalid."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_sp_patches(monkeypatch, fake)

        sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Alex", "coin_flip", HOME, "I flip a coin"
        )

        # No prediction documents should exist.
        preds = fake.all_docs_by_prefix(DB, f"prediction:{GAME_ID}:")
        assert preds == []

    def test_all_three_valid_types_accepted(self, monkeypatch):
        """Each of the three valid prediction types is accepted."""
        for ptype in ("game_winner", "scores_before_half", "next_score"):
            fake = FakeCloudant()
            fake.seed(DB, _game_state())
            _apply_sp_patches(monkeypatch, fake)

            result = sp.save_prediction.fn(
                GAME_ID, GROUP_ID, "Robin", ptype, HOME, f"Testing {ptype}"
            )

            assert result["ok"] is True, f"Expected ok for type '{ptype}'"

    # --- team not in game ---

    def test_unknown_team_refused(self, monkeypatch):
        """A team not in game_state returns ok=False with a clear error."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Alex", "game_winner", "UNKNOWN_FC", "Bad team"
        )

        assert result["ok"] is False
        assert "UNKNOWN_FC" in result["error"]

    def test_unknown_team_not_saved(self, monkeypatch):
        """No document is written to Cloudant when the team is not in the game."""
        fake = FakeCloudant()
        fake.seed(DB, _game_state())
        _apply_sp_patches(monkeypatch, fake)

        sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Alex", "game_winner", "UNKNOWN_FC", "Bad team"
        )

        preds = fake.all_docs_by_prefix(DB, f"prediction:{GAME_ID}:")
        assert preds == []

    def test_both_teams_accepted(self, monkeypatch):
        """Both home and away teams are valid."""
        for team in (HOME, AWAY):
            fake = FakeCloudant()
            fake.seed(DB, _game_state())
            _apply_sp_patches(monkeypatch, fake)

            result = sp.save_prediction.fn(
                GAME_ID, GROUP_ID, "Drew", "game_winner", team, f"I pick {team}"
            )

            assert result["ok"] is True, f"Expected ok for team '{team}'"

    # --- game_state not found ---

    def test_missing_game_state_returns_error(self, monkeypatch):
        """Returns ok=False when game_state does not exist for the game."""
        fake = FakeCloudant()
        # No game_state seeded.
        _apply_sp_patches(monkeypatch, fake)

        result = sp.save_prediction.fn(
            GAME_ID, GROUP_ID, "Alex", "game_winner", HOME, "Any text"
        )

        assert result["ok"] is False
        assert "game_state not found" in result["error"]


# ===========================================================================
# Tests: list_open_predictions
# ===========================================================================

class TestListOpenPredictions:

    def test_returns_open_predictions_for_game_and_group(self, monkeypatch):
        """Open predictions for the requested game and group are returned."""
        fake = FakeCloudant()
        fake.seed(DB, _prediction("p1", status="open", group_id=GROUP_ID))
        fake.seed(DB, _prediction("p2", status="open", group_id=GROUP_ID))
        _apply_lop_patches(monkeypatch, fake)

        result = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)

        assert result["ok"] is True
        assert len(result["predictions"]) == 2

    def test_excludes_ruled_predictions(self, monkeypatch):
        """Predictions with status right, wrong, or not_counted are excluded."""
        fake = FakeCloudant()
        fake.seed(DB, _prediction("p1", status="open"))
        fake.seed(DB, _prediction("p2", status="right"))
        fake.seed(DB, _prediction("p3", status="wrong"))
        fake.seed(DB, _prediction("p4", status="not_counted"))
        _apply_lop_patches(monkeypatch, fake)

        result = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)

        assert result["ok"] is True
        assert len(result["predictions"]) == 1
        assert result["predictions"][0]["_id"] == f"prediction:{GAME_ID}:p1"

    def test_excludes_other_group(self, monkeypatch):
        """Predictions from a different group are not included."""
        fake = FakeCloudant()
        fake.seed(DB, _prediction("p1", status="open", group_id=GROUP_ID))
        fake.seed(DB, _prediction("p2", status="open", group_id=OTHER_GROUP))
        _apply_lop_patches(monkeypatch, fake)

        result = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)

        assert result["ok"] is True
        assert len(result["predictions"]) == 1
        assert result["predictions"][0]["group_id"] == GROUP_ID

    def test_excludes_other_game(self, monkeypatch):
        """Predictions from a different game are not included."""
        fake = FakeCloudant()
        fake.seed(DB, _prediction("p1", status="open", game_id=GAME_ID, group_id=GROUP_ID))
        fake.seed(DB, _prediction("p2", status="open", game_id=OTHER_GAME, group_id=GROUP_ID))
        _apply_lop_patches(monkeypatch, fake)

        result = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)

        assert result["ok"] is True
        assert len(result["predictions"]) == 1
        assert result["predictions"][0]["game_id"] == GAME_ID

    def test_empty_when_no_open_predictions(self, monkeypatch):
        """Returns an empty list when there are no open predictions."""
        fake = FakeCloudant()
        _apply_lop_patches(monkeypatch, fake)

        result = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)

        assert result["ok"] is True
        assert result["predictions"] == []

    def test_empty_when_all_predictions_ruled(self, monkeypatch):
        """Returns an empty list when all predictions have been decided."""
        fake = FakeCloudant()
        fake.seed(DB, _prediction("p1", status="right"))
        fake.seed(DB, _prediction("p2", status="wrong"))
        _apply_lop_patches(monkeypatch, fake)

        result = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)

        assert result["ok"] is True
        assert result["predictions"] == []

    def test_prediction_fields_preserved(self, monkeypatch):
        """All prediction fields are returned unchanged."""
        fake = FakeCloudant()
        pred = _prediction("p1", prediction_type="next_score", team=AWAY, player="Riley")
        fake.seed(DB, pred)
        _apply_lop_patches(monkeypatch, fake)

        result = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)

        assert len(result["predictions"]) == 1
        returned = result["predictions"][0]
        assert returned["player"] == "Riley"
        assert returned["prediction_type"] == "next_score"
        assert returned["team"] == AWAY

    def test_multiple_groups_independent(self, monkeypatch):
        """Querying group_b does not return group_a predictions and vice versa."""
        fake = FakeCloudant()
        fake.seed(DB, _prediction("p1", status="open", group_id=GROUP_ID))
        fake.seed(DB, _prediction("p2", status="open", group_id=OTHER_GROUP))
        _apply_lop_patches(monkeypatch, fake)

        result_a = lop.list_open_predictions.fn(GAME_ID, GROUP_ID)
        result_b = lop.list_open_predictions.fn(GAME_ID, OTHER_GROUP)

        assert len(result_a["predictions"]) == 1
        assert result_a["predictions"][0]["group_id"] == GROUP_ID
        assert len(result_b["predictions"]) == 1
        assert result_b["predictions"][0]["group_id"] == OTHER_GROUP
