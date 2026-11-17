# Chat Test Reasoning

This file shows the step-by-step logic used to work out the expected rulings in
`docs/chat_test_script.md`. The scoring rules come from AGENTS.md section 5.
No scoring tool code was read to produce these answers.

---

## Game data summary

Source file: `data/recorded_game_game_1.json`
Teams: KC (home), BAL (away)
Total events: 20

| seq | event_type | team | period | home | away | description                      |
|-----|------------|------|--------|------|------|----------------------------------|
|  1  | other      | null |   1    |   0  |   0  | Game start                       |
|  2  | score      | BAL  |   1    |   0  |   6  | BAL touchdown                    |
|  3  | score      | BAL  |   1    |   0  |   7  | BAL extra point                  |
|  4  | score      | KC   |   1    |   6  |   7  | KC touchdown                     |
|  5  | score      | KC   |   1    |   7  |   7  | KC extra point                   |
|  6  | other      | null |   1    |   7  |   7  | END QUARTER 1                    |
|  7  | score      | KC   |   2    |  10  |   7  | KC field goal                    |
|  8  | score      | KC   |   2    |  13  |   7  | KC field goal                    |
|  9  | score      | BAL  |   2    |  13  |  10  | BAL field goal                   |
| 10  | half_end   | null |   2    |  13  |  10  | End of first half                |
| 11  | other      | null |   3    |  13  |  10  | Start of second half             |
| 12  | score      | KC   |   3    |  19  |  10  | KC touchdown                     |
| 13  | score      | KC   |   3    |  20  |  10  | KC extra point                   |
| 14  | other      | null |   3    |  20  |  10  | END QUARTER 3                    |
| 15  | score      | BAL  |   4    |  20  |  16  | BAL touchdown                    |
| 16  | score      | BAL  |   4    |  20  |  17  | BAL extra point                  |
| 17  | score      | KC   |   4    |  26  |  17  | KC touchdown                     |
| 18  | score      | KC   |   4    |  27  |  17  | KC extra point                   |
| 19  | score      | BAL  |   4    |  27  |  20  | BAL field goal                   |
| 20  | game_end   | null |   4    |  27  |  20  | Game over. Final: KC 27, BAL 20  |

First half = periods 1 and 2 (sequences 1 through 10).
Second half starts at sequence 11.

---

## Predictions made at game start (last_sequence = 0)

All three predictions have made_after_sequence = 0.
Any event with sequence > 0 can decide them.

### Prediction A: Maya, game_winner, team = KC

Rule: decided by the first event with event_type "game_end".

Scan through events:
- seq 1 to 19: none are game_end.
- seq 20: event_type = "game_end". Final home_score = 27 (KC), away_score = 20 (BAL).
  KC has the higher score. Winner = KC.
  Maya's team = KC. KC equals the winner.

**Result: right**
Reason: KC won with a final score of KC 27 to BAL 20.

This prediction stays open until seq 20 is processed.

### Prediction B: Leo, scores_before_half, team = BAL

Rule: decided by the first event that is either:
  (a) a score event by BAL in the first half (period 1 or 2), with seq > 0, OR
  (b) a half_end event, if BAL has not scored in the first half.

Scan:
- seq 1: other. Skip.
- seq 2: score, team = BAL, period = 1. Seq 2 > 0. BAL scored in the first half.

**Result: right**
Reason: BAL scored in the first half at sequence 2.

This prediction is decided as soon as seq 2 is processed.

### Prediction C: Ana, next_score, team = BAL

Rule: decided by the first score event with sequence greater than made_after_sequence (0).

Scan:
- seq 1: other. Not a score. Skip.
- seq 2: score, team = BAL, period = 1. Seq 2 > 0. This is the first score event.
  Ana's team = BAL. BAL equals the event team.

**Result: right**
Reason: BAL scored next at sequence 2.

This prediction is decided as soon as seq 2 is processed.

---

## Which update batch decides which prediction

The chat script processes events in four batches.

### Batch 1: sequences 1 to 5 (Q1 plays)

Events: game start, BAL TD, BAL XP, KC TD, KC XP.
- Prediction B (Leo, scores_before_half, BAL): seq 2 is score by BAL in period 1 → decided right.
- Prediction C (Ana, next_score, BAL): seq 2 is first score event → decided right.
- Prediction A (Maya, game_winner): no game_end yet → still open.

After scoring: 2 new rulings. Leo: right. Ana: right. Maya: still open.

### Batch 2: sequences 6 to 10 (end Q1 through half)

Events: END Q1, KC FG, KC FG, BAL FG, half_end.
- Prediction B: already decided. No change.
- Prediction C: already decided. No change.
- Prediction A: no game_end yet → still open.

After scoring: 0 new rulings. Maya: still open.

### Batch 3: sequences 11 to 14 (second half start through end Q3)

Events: second half start, KC TD, KC XP, END Q3.
- Prediction A: no game_end yet → still open.

After scoring: 0 new rulings. Maya: still open.

### Batch 4: sequences 15 to 20 (Q4 through game end)

Events: BAL TD, BAL XP, KC TD, KC XP, BAL FG, game_end.
- Prediction A (Maya, game_winner, KC): seq 20 game_end. KC 27 > BAL 20. Winner = KC.
  Maya's team = KC → decided right.

After scoring: 1 new ruling. Maya: right.

---

## Leaderboard after the game (all predictions from first run)

All three players scored right on their predictions.

| player | points | right | wrong | not_counted |
|--------|--------|-------|-------|-------------|
| Maya   |   1    |   1   |   0   |      0      |
| Leo    |   1    |   1   |   0   |      0      |
| Ana    |   1    |   1   |   0   |      0      |

Sorted by points high to low. All tied at 1 point.
The agent may show them in any order since all have equal points.

---

## Dispute scenario

After the game, Ana's next_score ruling is "right".
Leo is not the organizer. Maya is the organizer (this matches the organizer field in
game_state; the seed script in run_prediction_check.py uses "Nadia Osei" but the chat
test uses Maya as the organizer for the purpose of this test).

Leo tries to override Ana's ruling. The override_ruling tool checks requested_by
against game_state.organizer. Leo is not the organizer. Result: refused.

Maya overrides Ana's ruling from right to wrong.
The tool saves the new status as "wrong", points updated to 0, and adds an entry
to the changes list showing old_status = "right".

After the override:
- Ana: 0 points, 0 right, 1 wrong, 0 not_counted.
- Maya and Leo: unchanged, 1 point each.

list_rulings shows Ana's ruling with status "wrong" and a changes entry with
old_status "right", changed_by "Maya".

---

## Section 9: same prediction under three names after reset

Reset: game_state set to not_started, last_sequence = 0. All prediction and ruling
documents for game_1 deleted.

Three players each type a next_score prediction for BAL at the same game state
(last_sequence = 0). All three have made_after_sequence = 0.

When seq 2 is processed (score, team = BAL, period = 1, seq 2 > 0):
- All three predictions have the same type, same team, same made_after_sequence.
- The first score event team (BAL) equals BAL for every prediction.
- All three are decided right at the same event.

**Result for all three: right**
Reason (for each): BAL scored next at sequence 2.

This shows that the ruling depends only on the prediction type, team, and
made_after_sequence — not on the player name.
