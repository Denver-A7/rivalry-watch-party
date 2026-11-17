"""
scripts/run_prediction_check.py

Loads the recorded game into the fake Cloudant client, saves each prediction
from tests/predictions_20.csv, feeds all events, runs the Scoring tool, and
prints a table of expected versus actual status.

No language model is used. No network calls are made.
Run from the repo root:
  python scripts/run_prediction_check.py
"""

import sys
import os
import csv
import json
import copy

# Allow imports from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.fakes import FakeCloudant
import tools.save_prediction as sp
import tools.get_next_game_events as gne
import tools.score_open_predictions as sop

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GAME_ID = "game_1"
GROUP_ID = "group_a"
DB = "rivalry_watch_party"
HOME_TEAM = "KC"
AWAY_TEAM = "BAL"

EVENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "recorded_game_game_1.json")
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "predictions_20.csv")


# ---------------------------------------------------------------------------
# Patch helpers: replace HTTP calls with FakeCloudant methods
# ---------------------------------------------------------------------------

def _apply_patches(fake: FakeCloudant) -> None:
    """Monkey-patch all three tool modules to use the fake in-memory store."""

    def fake_get_creds():
        return "http://fake", "fake-apikey", DB

    def fake_get_iam_token(apikey):
        return "fake-token"

    def fake_get_doc(base_url, db, doc_id, token):
        return fake.get_doc(db, doc_id)

    def fake_put_doc(base_url, db, doc_id, body, token):
        return fake.put_doc(db, doc_id, body)

    def fake_all_docs_by_prefix(base_url, db, prefix, token):
        return fake.all_docs_by_prefix(db, prefix)

    for module in (sp, gne, sop):
        module._get_creds = fake_get_creds
        module._get_iam_token = fake_get_iam_token
        module._get_doc = fake_get_doc
        module._put_doc = fake_put_doc
        module._all_docs_by_prefix = fake_all_docs_by_prefix


# ---------------------------------------------------------------------------
# Setup: seed game_state and events into the fake store
# ---------------------------------------------------------------------------

def _build_game_state(last_sequence: int = 0) -> dict:
    """Build a game_state document with the given last_sequence."""
    return {
        "_id": f"game_state:{GAME_ID}",
        "type": "game_state",
        "game_id": GAME_ID,
        "sport": "american_football",
        "home_team": HOME_TEAM,
        "away_team": AWAY_TEAM,
        "source": "recorded",
        "status": "not_started",
        "last_sequence": last_sequence,
        "home_score": 0,
        "away_score": 0,
        "period": 1,
        "organizer": "Nadia Osei",
        "updated_at": "2025-01-01T00:00:00Z",
    }


def _load_events() -> list[dict]:
    """Load events from the recorded game JSON file."""
    with open(EVENTS_PATH) as f:
        events = json.load(f)
    # Add home_team and away_team to each event so the scoring tool can read them.
    for ev in events:
        ev["home_team"] = HOME_TEAM
        ev["away_team"] = AWAY_TEAM
    return events


def _seed_events(fake: FakeCloudant, events: list[dict]) -> None:
    """Seed all game events into the fake store."""
    for ev in events:
        doc_id = f"game_event:{GAME_ID}:{ev['sequence']:05d}"
        doc = copy.deepcopy(ev)
        doc["_id"] = doc_id
        fake.seed(DB, doc)


# ---------------------------------------------------------------------------
# Save one prediction by temporarily adjusting game_state.last_sequence
# ---------------------------------------------------------------------------

def _save_prediction_at(fake: FakeCloudant, row: dict) -> str:
    """
    Set game_state.last_sequence to the value in the CSV row, then call
    save_prediction. Returns the prediction_id or raises on failure.
    """
    made_after = int(row["made_after_sequence"])

    # Read the current game_state from the fake store.
    state = fake.get_doc(DB, f"game_state:{GAME_ID}")
    state["last_sequence"] = made_after
    # Put it back so save_prediction reads the right sequence.
    fake.put_doc(DB, f"game_state:{GAME_ID}", state)

    result = sp.save_prediction.fn(
        game_id=GAME_ID,
        group_id=GROUP_ID,
        player=row["player"],
        prediction_type=row["prediction_type"],
        team=row["team"],
        original_text=row["text"],
    )
    if not result.get("ok"):
        raise RuntimeError(f"save_prediction failed for row {row['id']}: {result}")
    return result["prediction_id"]


# ---------------------------------------------------------------------------
# Feed all events using get_next_game_events
# ---------------------------------------------------------------------------

def _feed_all_events(fake: FakeCloudant, total_events: int) -> None:
    """
    Reset game_state.last_sequence to 0 and feed every event one at a time.
    This lets get_next_game_events validate and accept each event.
    """
    # Reset game_state to last_sequence=0 so all events are "new".
    state = fake.get_doc(DB, f"game_state:{GAME_ID}")
    state["last_sequence"] = 0
    state["home_score"] = 0
    state["away_score"] = 0
    state["period"] = 1
    state["status"] = "not_started"
    fake.put_doc(DB, f"game_state:{GAME_ID}", state)

    # Feed events one at a time.
    for _ in range(total_events):
        result = gne.get_next_game_events.fn(game_id=GAME_ID, count=1)
        if not result.get("ok"):
            print(f"  Warning: get_next_game_events returned error: {result}")
            break
        if not result["accepted"]:
            break  # No more events.


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # 1. Set up fake store.
    fake = FakeCloudant()
    _apply_patches(fake)

    # 2. Seed game_state (last_sequence=0 to start).
    state = _build_game_state(last_sequence=0)
    fake.seed(DB, state)

    # 3. Load and seed all events.
    events = _load_events()
    _seed_events(fake, events)

    # 4. Load the CSV.
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    # 5. Save each prediction. game_state.last_sequence is set to
    #    made_after_sequence before each save so the prediction gets
    #    the right made_after_sequence value.
    pred_ids = []
    for row in rows:
        pred_id = _save_prediction_at(fake, row)
        pred_ids.append(pred_id)

    # 6. Feed all events (resets last_sequence to 0 first, then advances
    #    through every event one at a time).
    _feed_all_events(fake, len(events))

    # 7. Run the Scoring tool.
    scoring_result = sop.score_open_predictions.fn(game_id=GAME_ID)
    if not scoring_result.get("ok"):
        print(f"score_open_predictions failed: {scoring_result}")
        return

    # 8. Build a map of prediction_id -> actual status from rulings.
    actual_by_pred_id = {}
    for ruling in scoring_result.get("new_rulings", []):
        actual_by_pred_id[ruling["prediction_id"]] = ruling["status"]

    # Also read any rulings already in the store (in case the tool returned
    # them in a previous run). Check the fake store directly.
    all_rulings = fake.all_docs_by_prefix(DB, "ruling:")
    for r in all_rulings:
        pid = r.get("prediction_id")
        if pid and pid not in actual_by_pred_id:
            actual_by_pred_id[pid] = r.get("status", "unknown")

    # 9. Print the results table.
    col_w = [4, 20, 20, 10, 10, 8]
    header = (
        f"{'ID':<{col_w[0]}} "
        f"{'Player':<{col_w[1]}} "
        f"{'Type':<{col_w[2]}} "
        f"{'Team':<{col_w[3]}} "
        f"{'Expected':<{col_w[4]}} "
        f"{'Actual':<{col_w[5]}} "
        f"Match"
    )
    separator = "-" * len(header)
    print()
    print("Prediction Check Results")
    print(separator)
    print(header)
    print(separator)

    matches = 0
    for row, pred_id in zip(rows, pred_ids):
        expected = row["expected_status"]
        actual = actual_by_pred_id.get(pred_id, "open")
        match = "YES" if actual == expected else "NO "
        if actual == expected:
            matches += 1
        print(
            f"{row['id']:<{col_w[0]}} "
            f"{row['player']:<{col_w[1]}} "
            f"{row['prediction_type']:<{col_w[2]}} "
            f"{row['team']:<{col_w[3]}} "
            f"{expected:<{col_w[4]}} "
            f"{actual:<{col_w[5]}} "
            f"{match}"
        )

    print(separator)
    print(f"Matches: {matches} / {len(rows)}")
    print()


if __name__ == "__main__":
    main()
