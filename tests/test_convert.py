"""
tests/test_convert.py

Checks that data/recorded_game_game_1.json was produced correctly.
Run after scripts/convert_raw_game.py has been executed.
"""

import json
import os
import pytest

OUT_FILE = "data/recorded_game_game_1.json"

REQUIRED_FIELDS = [
    "type", "game_id", "event_id", "sequence",
    "event_type", "team", "points",
    "home_score", "away_score", "period", "clock",
    "description", "source",
]

VALID_EVENT_TYPES = {"score", "half_end", "game_end", "other"}


@pytest.fixture(scope="module")
def events():
    assert os.path.exists(OUT_FILE), f"{OUT_FILE} not found. Run scripts/convert_raw_game.py first."
    with open(OUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def test_events_is_list(events):
    assert isinstance(events, list)
    assert len(events) > 0


def test_sequence_numbers_in_order(events):
    """Sequence must start at 1 and increase by 1 each step."""
    seqs = [e["sequence"] for e in events]
    assert seqs[0] == 1, f"First sequence should be 1, got {seqs[0]}"
    for i in range(1, len(seqs)):
        assert seqs[i] == seqs[i - 1] + 1, (
            f"Sequence gap at index {i}: {seqs[i-1]} -> {seqs[i]}"
        )


def test_exactly_one_game_end(events):
    """There must be exactly one game_end event."""
    game_ends = [e for e in events if e["event_type"] == "game_end"]
    assert len(game_ends) == 1, f"Expected 1 game_end, got {len(game_ends)}"


def test_game_end_is_last(events):
    """The game_end event must be the last event."""
    assert events[-1]["event_type"] == "game_end", (
        "Last event is not game_end"
    )


def test_every_event_has_required_fields(events):
    """Every event must have all required fields present (value may be None)."""
    for e in events:
        for field in REQUIRED_FIELDS:
            assert field in e, f"Event seq={e.get('sequence')} missing field '{field}'"


def test_event_types_are_valid(events):
    """event_type must be one of the four allowed values."""
    for e in events:
        assert e["event_type"] in VALID_EVENT_TYPES, (
            f"Event seq={e['sequence']} has unknown event_type '{e['event_type']}'"
        )


def test_event_count_in_range(events):
    """Total events should be between 20 and 80."""
    assert 20 <= len(events) <= 80, f"Event count {len(events)} not in [20, 80]"


def test_at_least_one_half_end(events):
    """There must be at least one half_end event."""
    half_ends = [e for e in events if e["event_type"] == "half_end"]
    assert len(half_ends) >= 1, "No half_end event found"


def test_scores_never_go_down(events):
    """home_score and away_score must never decrease as we go through events."""
    prev_home = 0
    prev_away = 0
    for e in events:
        h = e["home_score"]
        a = e["away_score"]
        assert h >= prev_home, (
            f"home_score went down at seq={e['sequence']}: {prev_home} -> {h}"
        )
        assert a >= prev_away, (
            f"away_score went down at seq={e['sequence']}: {prev_away} -> {a}"
        )
        prev_home = h
        prev_away = a


def test_score_events_have_team_and_points(events):
    """score events must have a non-null team and points > 0."""
    for e in events:
        if e["event_type"] == "score":
            assert e["team"] is not None, f"score event seq={e['sequence']} has null team"
            assert isinstance(e["points"], int) and e["points"] > 0, (
                f"score event seq={e['sequence']} has bad points: {e['points']}"
            )


def test_game_id_is_game_1(events):
    """All events must use game_id 'game_1'."""
    for e in events:
        assert e["game_id"] == "game_1", (
            f"Event seq={e['sequence']} has wrong game_id '{e['game_id']}'"
        )
