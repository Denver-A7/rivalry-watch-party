# Test Results

Last updated: 2026-11-17

---

## Unit test counts

| Test suite         | Passing |
|--------------------|---------|
| Scoring            | 28      |
| Game data          | 22      |
| Predictions        | 20      |
| Rulings            | 23      |
| Convert            | 11      |
| **Total**          | **104** |

All 104 tests pass.

---

## Prediction check against the recorded game

Script: `scripts/run_prediction_check.py`
Game: recorded game `2024_01_BAL_KC`
Final score: KC 27, BAL 20

We ran 20 predictions through the scoring tool and compared each result to the expected status we worked out by hand before running the script.

**Result: 20 of 20 matched.**

The 20 predictions cover all three prediction types across a range of `made_after_sequence` values:

- `game_winner` (8 predictions): right, wrong, and not counted (late).
- `scores_before_half` (6 predictions): right, not counted (late).
- `next_score` (6 predictions): right, wrong, and not counted (game ended first or late).

---

## Pass or fail checklist

| Check | Result |
|-------|--------|
| Same prediction under three different player names gives the same ruling | PASS |
| Duplicate event (same event_id seen twice) is rejected | PASS |
| Old event (sequence not greater than last_sequence) is rejected | PASS |
| Event where score goes down is rejected | PASS |
| Late prediction (made after the answer was already known) is not counted | PASS |
| Dispute by a non-organizer is refused | PASS |
| Dispute by the organizer changes the ruling and logs the old status | PASS |
| Tie game gives not_counted for game_winner | PASS (test_scoring.py::TestDecideGameWinner::test_not_counted_tie, test_scoring.py::TestScoreOpenPredictions::test_game_winner_tie) |
| game_end arrives before any score for a next_score prediction | PASS |
| Live source returns an error (not enabled yet) | PASS (test_game_data.py::TestLiveMode::test_live_mode_returns_error) |
| Leaderboard sorts by points high to low across multiple games | PASS (test_rulings.py::TestGetLeaderboard::test_sorted_high_to_low, test_rulings.py::TestGetLeaderboard::test_all_games_combines_scores) |
| HTTP 409 conflict on Cloudant write triggers one retry | NOT TESTED |

---

## Notes

- "Same prediction under three names gives the same ruling" confirms that the player name is not an input to scoring, as required.
- Bad event tests use made up events from `data/test_bad_events.json`. That file is test data only.
- Items marked NOT TESTED have not been run yet. We do not claim they pass.
