# Technology Statement

## What we built

Rivalry Watch Party is a prototype prediction game. Friends watch a game from
different places and type predictions in a chat. Two AI agents check each
prediction against game events and keep score. We built this with IBM watsonx
Orchestrate, IBM Cloudant, and IBM Bob.

## IBM watsonx Orchestrate

Orchestrate runs both agents and routes each chat message to the right tools.
We imported two agents and seven tools into Orchestrate.

The first agent is prediction_agent. It reads a message, turns it into a
checkable prediction, saves it, and shows open predictions and the leaderboard.
It asks one short question if a message is unclear.

The second agent is referee_agent. It fetches game events, scores predictions,
explains each ruling, updates the score, writes a recap, and handles disputes.

## The language model

Both agents use groq/openai/gpt-oss-120b. The model reads messages, calls
tools, and writes replies. The model never decides whether a prediction is
right or wrong. All rulings come from the Scoring tool in code.

## The seven tools

1. save_prediction saves a friend's prediction and records the game sequence
   at the time it was saved.
2. list_open_predictions returns all undecided predictions.
3. get_next_game_events reads the next events, checks each one is new and
   valid, and updates the game state.
4. score_open_predictions applies the scoring rules to every open prediction
   and saves a ruling for each one that can be decided.
5. get_leaderboard returns points per player, sorted high to low.
6. list_rulings returns the full ruling log including any overrides.
7. override_ruling lets the organizer change a ruling and records the old
   status in a changes list.

## IBM Cloudant

Cloudant is the shared database. It stores the game state, game events,
predictions, and rulings. Credentials are kept in an Orchestrate connection
named cloudant_creds. No key is stored in code or logs.

## IBM Bob

We used IBM Bob to write and review the Python tool files, agent YAML files,
test files, scripts, and all documentation for this project.

## Game data

The demo uses a recorded game. The source is nflverse play-by-play data
(BAL at KC, 2024-09-05, CC BY 4.0, commercial use allowed). We have not
confirmed a live data source. The demo will use the recorded game until a live
source with a compatible license is confirmed.

## What we tested

104 unit tests pass across five suites: scoring, game data, predictions,
rulings, and data conversion. A prediction check ran 20 predictions through
the Scoring tool on the recorded game and matched 20 of 20 against
hand-worked expected results. CHECK: chat tests in Orchestrate are not
finished yet.

## Limits

The live data mode is not built and returns an error until a source is
confirmed. The HTTP 409 conflict retry has not been tested end to end. The
scoring rules cover three prediction types. New types can be added after the
team confirms the dataset.
