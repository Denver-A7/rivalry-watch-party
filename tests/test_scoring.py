"""
tests/test_scoring.py

Unit tests for the decide() function and the score_open_predictions @tool.

Tests cover:
  - game_winner: right, wrong, not_counted (tie)
  - scores_before_half: right, wrong
  - next_score: right, wrong, not_counted (game_end before score)
  - Late prediction rule (made_after_sequence >= deciding event sequence)
  - Prediction that stays open (no deciding event yet)
  - Fairness: same prediction by three different player names gets the
    same status and points (player name must not affect scoring)

The @tool function is tested through the _run_tool helper, which monkey-
patches the HTTP helpers with the FakeCloudant from tests/fakes.py.
No network calls are made.
"""

import sys
import os
import copy
import datetime

import pytest

# Allow imports from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.fakes import FakeCloudant
import tools.score_open_predictions as sop

# ---------------------------------------------------------------------------
# Shared fake data builders
# ---------------------------------------------------------------------------

HOME = "Riverside Rockets"
AWAY = "Lakeside Lions"
GAME_ID = "game_1"
GROUP_ID = "group_a"
DB = "rivalry_watch_party"


def _game_state(last_sequence: int = 0) -> dict:
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
        "home_score": 0,
        "away_score": 0,
        "period": 1,
        "organizer": "Alex",
        "updated_at": "2025-01-01T00:00:00Z",
    }


def _event(
    seq: int,
    event_type: str,
    team: str | None = None,
    points: int | None = None,
    home_score: int = 0,
    away_score: int = 0,
    period: int = 1,
) -> dict:
    return {
        "_id": f"game_event:{GAME_ID}:{seq:05d}",
        "type": "game_event",
        "game_id": GAME_ID,
        "event_id": f"evt_{seq}",
        "sequence": seq,
        "event_type": event_type,
        "team": team,
        "points": points,
        "home_score": home_score,
        "away_score": away_score,
        "home_team": HOME,
        "away_team": AWAY,
        "period": period,
        "clock": "10:00",
        "description": f"Event {seq}",
        "source": "recorded",
    }


def _prediction(
    pred_id: str,
    prediction_type: str,
    team: str,
    made_after_sequence: int = 0,
    player: str = "Jordan",
) -> dict:
    return {
        "_id": f"prediction:{GAME_ID}:{pred_id}",
        "type": "prediction",
        "game_id": GAME_ID,
        "group_id": GROUP_ID,
        "player": player,
        "prediction_type": prediction_type,
        "team": team,
        "original_text": f"I think {team}",
        "made_after_sequence": made_after_sequence,
        "status": "open",
        "created_at": "2025-01-01T00:00:00Z",
    }


# ---------------------------------------------------------------------------
# Monkey-patch helper: replace HTTP helpers with FakeCloudant methods
# ---------------------------------------------------------------------------

def _make_patch(fake: FakeCloudant):
    """Return a context-like patch dict. Applied with monkeypatch.setattr."""
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
        monkeypatch.setattr(sop, name, fn)


# ===========================================================================
# Tests for the pure decide() function
# ===========================================================================

class TestDecideGameWinner:
    def test_right(self):
        pred = _prediction("p1", "game_winner", HOME)
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0),
            _event(2, "game_end", None, None, home_score=3, away_score=0),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "right"
        assert result["points"] == sop.POINTS_RIGHT
        assert result["event_id"] == "evt_2"

    def test_wrong(self):
        pred = _prediction("p1", "game_winner", HOME)
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3),
            _event(2, "game_end", None, None, home_score=0, away_score=3),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "wrong"
        assert result["points"] == 0

    def test_not_counted_tie(self):
        pred = _prediction("p1", "game_winner", HOME)
        events = [
            _event(1, "game_end", None, None, home_score=3, away_score=3),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "not_counted"
        assert "tie" in result["reason"].lower()
        assert result["points"] == 0

    def test_stays_open_no_game_end(self):
        pred = _prediction("p1", "game_winner", HOME)
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0),
        ]
        result = sop.decide(pred, events)
        assert result is None

    def test_late_prediction(self):
        """game_end already happened before the prediction was saved."""
        pred = _prediction("p1", "game_winner", HOME, made_after_sequence=5)
        events = [
            _event(3, "game_end", None, None, home_score=5, away_score=2),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "not_counted"
        assert "already known" in result["reason"]


class TestDecideScoresBeforeHalf:
    def test_right(self):
        pred = _prediction("p1", "scores_before_half", HOME)
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0, period=1),
            _event(2, "half_end", period=1),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "right"
        assert result["points"] == sop.POINTS_RIGHT
        assert result["event_id"] == "evt_1"

    def test_wrong(self):
        pred = _prediction("p1", "scores_before_half", HOME)
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3, period=1),
            _event(2, "half_end", period=1),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "wrong"
        assert result["points"] == 0
        assert result["event_id"] == "evt_2"

    def test_stays_open(self):
        pred = _prediction("p1", "scores_before_half", HOME)
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3, period=1),
        ]
        result = sop.decide(pred, events)
        assert result is None

    def test_late_prediction(self):
        """Score event already happened before the prediction was saved."""
        pred = _prediction("p1", "scores_before_half", HOME, made_after_sequence=3)
        events = [
            _event(2, "score", HOME, 3, home_score=3, away_score=0, period=1),
            _event(4, "half_end", period=1),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "not_counted"
        assert "already known" in result["reason"]


class TestDecideNextScore:
    def test_right(self):
        pred = _prediction("p1", "next_score", HOME, made_after_sequence=0)
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "right"
        assert result["points"] == sop.POINTS_RIGHT

    def test_wrong(self):
        pred = _prediction("p1", "next_score", HOME, made_after_sequence=0)
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "wrong"
        assert result["points"] == 0

    def test_not_counted_game_end_before_score(self):
        pred = _prediction("p1", "next_score", HOME, made_after_sequence=0)
        events = [
            _event(1, "game_end", None, None, home_score=0, away_score=0),
        ]
        result = sop.decide(pred, events)
        assert result["status"] == "not_counted"
        assert "game ended" in result["reason"].lower()

    def test_ignores_events_before_made_after(self):
        """Events at or before made_after_sequence must not decide next_score."""
        pred = _prediction("p1", "next_score", HOME, made_after_sequence=2)
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0),
            _event(2, "score", HOME, 3, home_score=6, away_score=0),
            _event(3, "score", AWAY, 3, home_score=6, away_score=3),
        ]
        result = sop.decide(pred, events)
        # Seq 3 is the first event after made_after=2; team is AWAY, so wrong.
        assert result["status"] == "wrong"

    def test_stays_open(self):
        pred = _prediction("p1", "next_score", HOME, made_after_sequence=5)
        events = [
            _event(3, "score", HOME, 3),
            _event(4, "score", HOME, 3),
        ]
        result = sop.decide(pred, events)
        assert result is None


# ===========================================================================
# Fairness test: player name must not change the outcome
# ===========================================================================

class TestFairness:
    def test_same_prediction_different_players(self):
        """Three players making the same prediction get the same status and points."""
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3),
            _event(2, "game_end", None, None, home_score=0, away_score=3),
        ]
        players = ["Jordan", "Taylor", "Morgan"]
        results = []
        for name in players:
            pred = _prediction("px", "game_winner", HOME, player=name)
            outcome = sop.decide(pred, events)
            results.append(outcome)

        statuses = {r["status"] for r in results}
        points_set = {r["points"] for r in results}
        assert len(statuses) == 1, f"Different statuses for same prediction: {statuses}"
        assert len(points_set) == 1, f"Different points for same prediction: {points_set}"


# ===========================================================================
# Integration tests: score_open_predictions @tool with fake Cloudant
# ===========================================================================

class TestScoreOpenPredictions:
    def _setup(self, fake: FakeCloudant, predictions: list[dict], events: list[dict]):
        """Seed fake Cloudant with game_state, predictions, and events."""
        last_seq = max((e["sequence"] for e in events), default=0)
        gs = _game_state(last_sequence=last_seq)
        fake.seed(DB, gs)
        for pred in predictions:
            fake.seed(DB, pred)
        for evt in events:
            fake.seed(DB, evt)

    def test_game_winner_right(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "game_winner", HOME)]
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0),
            _event(2, "game_end", None, None, home_score=3, away_score=0),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["ok"] is True
        assert len(result["new_rulings"]) == 1
        assert result["new_rulings"][0]["status"] == "right"
        assert result["still_open"] == 0

    def test_game_winner_wrong(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "game_winner", HOME)]
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3),
            _event(2, "game_end", None, None, home_score=0, away_score=3),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["ok"] is True
        assert result["new_rulings"][0]["status"] == "wrong"
        assert result["new_rulings"][0]["points"] == 0

    def test_game_winner_tie(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "game_winner", HOME)]
        events = [
            _event(1, "game_end", None, None, home_score=3, away_score=3),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["new_rulings"][0]["status"] == "not_counted"

    def test_scores_before_half_right(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "scores_before_half", AWAY)]
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3, period=1),
            _event(2, "half_end", period=1),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["new_rulings"][0]["status"] == "right"

    def test_scores_before_half_wrong(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "scores_before_half", HOME)]
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3, period=1),
            _event(2, "half_end", period=1),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["new_rulings"][0]["status"] == "wrong"

    def test_next_score_right(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "next_score", HOME, made_after_sequence=0)]
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["new_rulings"][0]["status"] == "right"

    def test_next_score_wrong(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "next_score", HOME, made_after_sequence=0)]
        events = [
            _event(1, "score", AWAY, 3, home_score=0, away_score=3),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["new_rulings"][0]["status"] == "wrong"

    def test_next_score_not_counted_game_end(self, monkeypatch):
        fake = FakeCloudant()
        predictions = [_prediction("p1", "next_score", HOME, made_after_sequence=0)]
        events = [
            _event(1, "game_end", None, None, home_score=0, away_score=0),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["new_rulings"][0]["status"] == "not_counted"

    def test_late_prediction_not_counted(self, monkeypatch):
        """Prediction saved after the deciding event: not_counted."""
        fake = FakeCloudant()
        # made_after_sequence=5 but game_end is at sequence=2.
        predictions = [_prediction("p1", "game_winner", HOME, made_after_sequence=5)]
        events = [
            _event(2, "game_end", None, None, home_score=3, away_score=0),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["new_rulings"][0]["status"] == "not_counted"
        assert "already known" in result["new_rulings"][0]["reason"]

    def test_prediction_stays_open(self, monkeypatch):
        """No deciding event yet: prediction must stay open."""
        fake = FakeCloudant()
        predictions = [_prediction("p1", "game_winner", HOME)]
        events = [
            _event(1, "score", HOME, 3, home_score=3, away_score=0),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["ok"] is True
        assert result["new_rulings"] == []
        assert result["still_open"] == 1

    def test_no_open_predictions(self, monkeypatch):
        """No open predictions: returns empty rulings and zero still_open."""
        fake = FakeCloudant()
        gs = _game_state(last_sequence=0)
        fake.seed(DB, gs)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["ok"] is True
        assert result["new_rulings"] == []
        assert result["still_open"] == 0

    def test_ruling_saved_with_correct_fields(self, monkeypatch):
        """Ruling document in fake DB must have all required fields."""
        fake = FakeCloudant()
        predictions = [_prediction("p1", "next_score", HOME, made_after_sequence=0)]
        events = [_event(1, "score", HOME, 3, home_score=3, away_score=0)]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        sop.score_open_predictions.fn(GAME_ID)

        pred_id = f"prediction:{GAME_ID}:p1"
        ruling = fake.get_doc(DB, f"ruling:{pred_id}")
        assert ruling is not None
        for field in ("type", "ruling_id", "prediction_id", "game_id",
                      "group_id", "player", "prediction_type", "team",
                      "status", "reason", "points", "event_id",
                      "decided_at", "changes"):
            assert field in ruling, f"Ruling missing field '{field}'"

    def test_fairness_via_tool(self, monkeypatch):
        """Same prediction by three players gets the same status and points."""
        fake = FakeCloudant()
        players = ["Jordan", "Taylor", "Morgan"]
        predictions = [
            _prediction(f"p{i}", "game_winner", HOME, player=p)
            for i, p in enumerate(players)
        ]
        events = [
            _event(1, "game_end", None, None, home_score=5, away_score=3),
        ]
        self._setup(fake, predictions, events)
        _apply_patches(monkeypatch, fake)

        result = sop.score_open_predictions.fn(GAME_ID)
        assert result["ok"] is True
        assert len(result["new_rulings"]) == 3
        statuses = {r["status"] for r in result["new_rulings"]}
        points_set = {r["points"] for r in result["new_rulings"]}
        assert len(statuses) == 1, f"Players got different statuses: {statuses}"
        assert len(points_set) == 1, f"Players got different points: {points_set}"
