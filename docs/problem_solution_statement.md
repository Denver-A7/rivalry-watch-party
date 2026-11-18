# Problem and Solution Statement

## The problem

Friends who watch the same game from different places often type predictions
during the game. They track them by hand in separate messages or notes. There
is no shared record. When the game ends, it is hard to check who was right.

## The user

A group of friends of any size who watch the same game from different locations.

## The solution

Rivalry Watch Party is a prototype prediction game built on IBM watsonx
Orchestrate. Friends type predictions in a chat. Two AI agents handle
everything else.

The first agent reads each message and saves it as a checkable prediction. The
second agent fetches game events, checks every open prediction against those
events, and issues a ruling for each one. All rulings come from code. The
language model never decides right or wrong. A leaderboard keeps score across
games.

Both agents share one IBM Cloudant database that stores predictions, events,
rulings, and the game state.

## Key features

Friends can predict who will win the game, which team will score before the
half ends, or which team will score next. Each prediction is checked against
events that happen after it was saved. A prediction made after the answer was
known is marked not counted. The organizer can override any ruling and the old
status is saved in the log. The demo uses a recorded game from nflverse
(BAL at KC, 2024-09-05, CC BY 4.0).

## What we tested and the results

108 unit tests pass across five suites: scoring, game data, predictions,
rulings, and data conversion.

A prediction check ran 20 predictions through the Scoring tool on the recorded
game and matched all 20 against expected results worked out by hand. The
predictions cover all three types and include right, wrong, and not counted
outcomes.

The pass or fail checklist confirms:

- The same prediction under three player names gives the same ruling.
- Duplicate and old game events are rejected.
- An event where the score goes down is rejected.
- A late prediction is marked not counted.
- A non-organizer dispute is refused.
- An organizer dispute changes the ruling and logs the old status.
- A tie game gives not counted for a game_winner prediction.

We ran a chat test in Orchestrate with prediction_agent using the recorded game
game_1. Three predictions were saved. An unclear prediction got one short
question. A betting question got a polite refusal. The open predictions list
worked. Repeated checks moved the game forward until it ended. All three
players were ruled correctly: Leo right, Maya right (KC won), Ana right. The
leaderboard showed Ana 1, Leo 1, Maya 1. The recap and ruling log worked with
a reason for each ruling. Organizer Maya changed Ana's ruling to wrong and the
log shows who changed it, when, and why.

## Limits

The live data mode is not built. It returns an error until a source is
confirmed. The HTTP 409 conflict retry in Cloudant has not been tested end to
end. The system supports three prediction types. We have not tested it with a
large number of simultaneous friends.
