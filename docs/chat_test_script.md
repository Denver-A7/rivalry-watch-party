# Chat Test Script: Rivalry Watch Party

This file lists the exact messages to type into the Orchestrate chat, in order.
The expected result follows each message.

**Game:** game_1 (recorded game)
**Teams:** KC (home) vs BAL (away)
**Group:** friends1
**Organizer:** Maya
**Players:** Maya, Leo, Ana
**Total events in the recorded game:** 20

Before starting: the game state must be seeded (run `scripts/seed_recorded_game.py`
for game_1). The game_state must be set to `not_started` with `last_sequence = 0`.

---

## Part 1: Three normal predictions

### Message 1 — Maya, game_winner

**Agent to use:** prediction_agent

**You type:**
```
Hi, I am Maya. For game_1 in group friends1, I predict KC will win the game.
```

**Expected result:**
The agent calls `save_prediction` with:
- game_id = "game_1"
- group_id = "friends1"
- player = "Maya"
- prediction_type = "game_winner"
- team = "KC"
- original_text = the message above

The agent replies with something like:

> Got it, Maya! I saved your prediction: KC will win game_1. Good luck!

The prediction is stored with `status = "open"` and `made_after_sequence = 0`.

---

### Message 2 — Leo, scores_before_half

**Agent to use:** prediction_agent

**You type:**
```
Hi, I am Leo. For game_1 in group friends1, I predict BAL will score before the half ends.
```

**Expected result:**
The agent calls `save_prediction` with:
- prediction_type = "scores_before_half"
- team = "BAL"

The agent replies with something like:

> Saved, Leo! Your prediction: BAL will score before the half. Let's see!

The prediction is stored with `status = "open"` and `made_after_sequence = 0`.

---

### Message 3 — Ana, next_score

**Agent to use:** prediction_agent

**You type:**
```
Hi, I am Ana. For game_1 in group friends1, I predict BAL will score next.
```

**Expected result:**
The agent calls `save_prediction` with:
- prediction_type = "next_score"
- team = "BAL"

The agent replies with something like:

> Saved, Ana! Your prediction: BAL will score next. Watch closely!

The prediction is stored with `status = "open"` and `made_after_sequence = 0`.

---

## Part 2: One unclear prediction

### Message 4 — unclear prediction

**Agent to use:** prediction_agent

**You type:**
```
Hi, I am Leo. For game_1 in group friends1, I predict they will dominate.
```

**Expected result:**
The agent cannot build a checkable prediction because "they" does not name a team
and "dominate" does not match any of the three prediction types.
The agent asks one short question before saving anything, for example:

> Which team do you mean, KC or BAL, and what are you predicting: that they will
> win the game, score before the half, or score next?

The agent does NOT save a prediction yet. It waits for Leo's answer.

---

## Part 3: Question about betting or money

### Message 5 — betting question

**Agent to use:** prediction_agent (or referee_agent, either will reject the request)

**You type:**
```
Can I bet money on KC winning? What is the prize if I am right?
```

**Expected result:**
The agent replies politely and clearly. It does not give betting or prize
information. For example:

> This is a fun prediction game for friends. We do not support betting or prizes
> with cash value. Make a prediction and see how you do on the leaderboard!

No prediction is saved. No tool is called.

---

## Part 4: List open predictions

### Message 6 — list open predictions

**Agent to use:** prediction_agent

**You type:**
```
What predictions are open for game_1 in group friends1?
```

**Expected result:**
The agent calls `list_open_predictions` with game_id = "game_1" and
group_id = "friends1".

The agent replies with the three open predictions saved above, for example:

> Here are the open predictions for game_1 in group friends1:
> 1. Maya — KC will win the game (game_winner)
> 2. Leo — BAL will score before the half ends (scores_before_half)
> 3. Ana — BAL will score next (next_score)

(The unclear prediction from message 4 was never saved, so it does not appear.)

---

## Part 5: Check game events and rulings

The referee_agent fetches events and then scores predictions.
Type each "Check" message to the **referee_agent**.

---

### Update 1: sequences 1 to 5 (Q1 plays, up to KC extra point)

**You type:**
```
Check game_1, next update.
```

**Expected result — event fetch:**
The agent calls `get_next_game_events` one or more times and accepts sequences
1 through 5:
- seq 1: other — Game start
- seq 2: score — BAL touchdown (BAL 6, KC 0)
- seq 3: score — BAL extra point (BAL 7, KC 0)
- seq 4: score — KC touchdown (KC 6, BAL 7)
- seq 5: score — KC extra point (KC 7, BAL 7)

game_state is now: last_sequence = 5, home (KC) = 7, away (BAL) = 7, period = 1.

**Expected result — scoring:**
The agent calls `score_open_predictions` for game_1.

Two predictions are decided:

**Leo — scores_before_half, BAL → right**
Reason: BAL scored in the first half at sequence 2.
Points: 1

**Ana — next_score, BAL → right**
Reason: BAL scored next at sequence 2.
Points: 1

Maya's game_winner prediction is still open (no game_end event yet).

The agent reports the two new rulings. For example:

> Two predictions have been ruled:
> - Leo: RIGHT. BAL scored in the first half at sequence 2. (+1 point)
> - Ana: RIGHT. BAL scored next at sequence 2. (+1 point)
> Maya's game_winner prediction is still open.

---

### Update 2: sequences 6 to 10 (end Q1 through half end)

**You type:**
```
Check game_1, next update.
```

**Expected result — event fetch:**
The agent accepts sequences 6 through 10:
- seq 6: other — END QUARTER 1
- seq 7: score — KC field goal (KC 10, BAL 7)
- seq 8: score — KC field goal (KC 13, BAL 7)
- seq 9: score — BAL field goal (KC 13, BAL 10)
- seq 10: half_end — End of first half (KC 13, BAL 10)

game_state is now: last_sequence = 10, KC = 13, BAL = 10, period = 2.

**Expected result — scoring:**
The agent calls `score_open_predictions`. No new rulings. Maya's game_winner
prediction is still open.

The agent reports something like:

> Updated through sequence 10. Half time: KC 13, BAL 10.
> No new rulings. Maya's game_winner prediction is still waiting for the final score.

---

### Update 3: sequences 11 to 14 (second half start through end Q3)

**You type:**
```
Check game_1, next update.
```

**Expected result — event fetch:**
The agent accepts sequences 11 through 14:
- seq 11: other — Start of second half
- seq 12: score — KC touchdown (KC 19, BAL 10)
- seq 13: score — KC extra point (KC 20, BAL 10)
- seq 14: other — END QUARTER 3

game_state is now: last_sequence = 14, KC = 20, BAL = 10, period = 3.

**Expected result — scoring:**
The agent calls `score_open_predictions`. No new rulings. Maya's game_winner
prediction is still open.

The agent reports something like:

> Updated through sequence 14. After three quarters: KC 20, BAL 10.
> No new rulings. Maya's game_winner prediction is still waiting for the final score.

---

### Update 4: sequences 15 to 20 (Q4 through game end)

**You type:**
```
Check game_1, next update.
```

**Expected result — event fetch:**
The agent accepts sequences 15 through 20:
- seq 15: score — BAL touchdown (KC 20, BAL 16)
- seq 16: score — BAL extra point (KC 20, BAL 17)
- seq 17: score — KC touchdown (KC 26, BAL 17)
- seq 18: score — KC extra point (KC 27, BAL 17)
- seq 19: score — BAL field goal (KC 27, BAL 20)
- seq 20: game_end — Final: KC 27, BAL 20

game_state is now: last_sequence = 20, KC = 27, BAL = 20, period = 4,
status = "final".

**Expected result — scoring:**
The agent calls `score_open_predictions`. One new ruling:

**Maya — game_winner, KC → right**
Reason: KC won with a final score of KC 27 to BAL 20.
Points: 1

The agent reports something like:

> Game over! Final score: KC 27, BAL 20.
> New ruling:
> - Maya: RIGHT. KC won with a final score of KC 27 to BAL 20. (+1 point)
> All predictions have been decided.

---

## Part 6: Leaderboard after the game

### Message 11 — get leaderboard

**Agent to use:** prediction_agent or referee_agent

**You type:**
```
Show the leaderboard for game_1 in group friends1.
```

**Expected result:**
The agent calls `get_leaderboard` with game_id = "game_1" and
group_id = "friends1".

All three players scored right on their one prediction. Each has 1 point.

The agent replies with something like:

> Leaderboard for game_1, group friends1:
> 1. Maya — 1 point (1 right, 0 wrong, 0 not counted)
> 2. Leo — 1 point (1 right, 0 wrong, 0 not counted)
> 3. Ana — 1 point (1 right, 0 wrong, 0 not counted)

(The order of tied players may vary.)

---

## Part 7: Disputes

### Message 12 — dispute by someone who is not the organizer

**Agent to use:** referee_agent

**You type:**
```
I am Leo. Please change Ana's next_score ruling from right to wrong. She made her
prediction after the play already happened.
```

**Expected result:**
The agent calls `override_ruling` with requested_by = "Leo".
The tool checks game_state.organizer. The organizer is "Maya". Leo is not Maya.

The tool returns `{"ok": false, "error": "..."}` and the agent replies politely,
for example:

> Sorry, Leo. Only the organizer can change a ruling. The organizer for game_1
> is Maya.

No ruling is changed.

---

### Message 13 — dispute by the organizer

**Agent to use:** referee_agent

**You type:**
```
I am Maya, the organizer. Please change Ana's next_score ruling from right to wrong.
Ana made her prediction after seq 2 had already been processed. The reason is:
prediction was made after the answer was known.
```

**Expected result:**
The agent calls `override_ruling` with:
- ruling_id = Ana's next_score ruling id
- new_status = "wrong"
- requested_by = "Maya"
- reason = the reason given

The tool verifies requested_by == game_state.organizer. Maya matches. The tool:
- Sets the ruling status to "wrong".
- Sets points to 0.
- Adds an entry to the changes list with old_status = "right", new_status = "wrong",
  changed_by = "Maya", and the reason.

The agent replies something like:

> Done, Maya. Ana's next_score ruling has been changed to wrong.
> The old status (right) is saved in the ruling log.

---

### Message 14 — verify the ruling log

**Agent to use:** referee_agent

**You type:**
```
Show the ruling log for game_1 in group friends1.
```

**Expected result:**
The agent calls `list_rulings` with game_id = "game_1" and group_id = "friends1".

The reply shows all three rulings. Ana's ruling shows the override:

> Rulings for game_1, group friends1:
> - Maya: game_winner, KC — right (1 pt). Reason: KC won with a final score of KC 27 to BAL 20.
> - Leo: scores_before_half, BAL — right (1 pt). Reason: BAL scored in the first half at sequence 2.
> - Ana: next_score, BAL — wrong (0 pts). Reason: BAL scored next at sequence 2.
>   Override: changed from right to wrong by Maya. Reason: prediction was made after the answer was known.

---

## Part 8: Recap

### Message 15 — recap

**Agent to use:** referee_agent

**You type:**
```
Give me a recap of game_1 for group friends1.
```

**Expected result:**
The agent reads the rulings and game_state and writes a short plain recap. For example:

> Recap of game_1 — KC vs BAL (recorded game):
> Final score: KC 27, BAL 20. KC wins.
>
> Predictions:
> - Maya predicted KC to win the game — RIGHT. (+1 point)
> - Leo predicted BAL to score before the half — RIGHT. (+1 point)
> - Ana predicted BAL to score next — overridden to WRONG. (0 points)
>
> Final standings: Maya 1 pt, Leo 1 pt, Ana 0 pts.

---

## Part 9: Same prediction, three names, after reset

### Step A — run the reset script (do not run this in chat)

Before this part, run from the terminal:

```
python scripts/reset_game.py game_1
```

This deletes all prediction and ruling documents for game_1 and sets game_state
back to `not_started` with `last_sequence = 0`. See `scripts/reset_game.py` for
details. Do not run the reset script during the chat demo — run it in a terminal
first.

After the reset, game_state is:
- status = "not_started"
- last_sequence = 0
- home_score = 0
- away_score = 0
- period = 1

---

### Message 16 — Maya makes a next_score prediction for BAL

**Agent to use:** prediction_agent

**You type:**
```
Hi, I am Maya. For game_1 in group friends1, I predict BAL will score next.
```

**Expected result:**
Saved with made_after_sequence = 0, status = "open".

---

### Message 17 — Leo makes the same prediction

**Agent to use:** prediction_agent

**You type:**
```
Hi, I am Leo. For game_1 in group friends1, I predict BAL will score next.
```

**Expected result:**
Saved with made_after_sequence = 0, status = "open".

---

### Message 18 — Ana makes the same prediction

**Agent to use:** prediction_agent

**You type:**
```
Hi, I am Ana. For game_1 in group friends1, I predict BAL will score next.
```

**Expected result:**
Saved with made_after_sequence = 0, status = "open".

---

### Message 19 — check the first update

**Agent to use:** referee_agent

**You type:**
```
Check game_1, next update.
```

**Expected result:**
Sequences 1 through 5 are accepted (same as Update 1 above).
Sequence 2 is a score event by BAL, period 1, seq 2 > 0.

The Scoring tool decides all three next_score predictions at sequence 2 because
all three have team = BAL and made_after_sequence = 0.

**All three: right**
Reason for each: BAL scored next at sequence 2.

The agent reports three new rulings with the same outcome, for example:

> Three predictions have been ruled:
> - Maya: RIGHT. BAL scored next at sequence 2. (+1 point)
> - Leo: RIGHT. BAL scored next at sequence 2. (+1 point)
> - Ana: RIGHT. BAL scored next at sequence 2. (+1 point)

This confirms that the ruling depends only on the prediction type, team, and
made_after_sequence — not on the player name.

---

## Notes

- The agents may phrase replies differently. What matters is that the tool calls
  match and the ruling status values match what this script shows.
- The organizer name in game_state must be "Maya" for the dispute in Part 7 to
  work. If the seed script sets a different organizer, update game_state manually
  before testing Part 7.
- For the dispute test, you need the actual ruling_id of Ana's next_score ruling.
  Read it from the list_rulings output or from the database before typing
  message 13.
