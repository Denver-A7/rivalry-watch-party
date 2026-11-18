# Technology Statement

## What we built

Rivalry Watch Party is a prototype prediction game. Friends watch a game from
different places and type predictions in a chat. Two AI agents check each
prediction against game events and keep score. We used IBM watsonx Orchestrate,
IBM Cloudant, and IBM Bob.

## IBM Bob

IBM Bob was our main development tool. We used Bob to plan the work, build
each tool, write the agent YAML files, run the prediction check, and write all
documentation. A teammate ran a separate Bob session to fix the dispute lookup.

Bob generated 108 unit tests across five suites. For each tool it read the
rules, wrote the logic, and wrote tests covering many cases including ties and
late predictions. All 108 pass.

After the chat test we described three problems to Bob and it found and fixed
each one.

The first problem was that the agent fetched too many events at once and the
game got stuck. Bob told the agent to always fetch one event at a time and
added a limit on the batch size in the tool.

The second problem was that game winner predictions were not counted because
the final game_end event carried no team names. Bob changed the scoring tool
to read the team names from the game state instead.

The third problem was that the organizer override failed because the agent had
no ruling ID. A teammate used Bob to update the agent instructions to look up
the ruling ID first.

## IBM watsonx Orchestrate

Orchestrate runs both agents and routes each message to the right tools.
Both agents use groq/openai/gpt-oss-120b. The model calls tools and writes
replies. It never decides rulings. All rulings come from the Scoring tool.

## The seven tools

There are seven tools, one Python file each. The Scoring tool decides all
three prediction types and saves a ruling for each one.

## IBM Cloudant

Cloudant stores the game state, events, predictions, and rulings. Credentials
are in an Orchestrate connection named cloudant_creds. No key is in code or logs.

## Game data

The demo uses a recorded game. The source is nflverse play-by-play data
(BAL at KC, 2024-09-05, CC BY 4.0, commercial use allowed). We will use the
recorded game until a live source with a compatible license is confirmed.

## What we tested

108 unit tests pass. A prediction check ran 20 predictions through the Scoring
tool on the recorded game and all 20 matched. A chat test with prediction_agent
on the recorded game game_1 ran from the first prediction to the final ruling.
The game ended, all three players were ruled correctly, and an organizer change
was logged. A request from a non-organizer got a question and no change, not
the planned refusal sentence. Three problems the chat test found were fixed
with Bob.

## Limits

Live data mode is not built. It returns an error until a source is confirmed.
The HTTP 409 retry has not been tested end to end.
