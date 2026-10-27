# AGENTS.md: Rivalry Watch Party Agent

## 1. What we are building
Rivalry Watch Party Agent is a prototype for the IBM SkillsBuild AI Experiential Learning Lab (Track 3, Fan Centric Sports and Entertainment). Friends who watch the same game from different places type predictions in a chat. Two agents in IBM watsonx Orchestrate check the predictions against game events, rule each one right, wrong or not counted with a short reason, and keep the score. It is a fun tool for friends. It is not a betting tool. The design works for a group of friends of any size. Never write a fixed number of friends anywhere.

The two agents:
- prediction_agent: reads a friend's message, turns it into a checkable prediction, saves it, asks one short question if the message is unclear, shows open predictions and the leaderboard.
- referee_agent: checks each new game event, calls the Scoring tool, explains each ruling, updates the score, writes a recap, handles disputes.
Both agents share one IBM Cloudant database.

Game data: live game data is our goal. We have not confirmed a live source that allows commercial use. Until then we test with a recorded game, and we keep a recorded game as the backup for the demo. Always call it a "recorded game". Never claim the data is live unless a live source is confirmed.

## 2. Hard rules. Never break these.
1. No betting, no payments, no prizes with cash value.
2. Use only made up player names. No real personal information. No data from social media. No client data.
3. Only use data whose terms allow commercial use. Every data source goes in data/data_sources.md with: name, link, license, date checked.
4. Never put a key, password or token in code, tests, logs, README or chat. Locally use environment variables. In Orchestrate use the connection named cloudant_creds.
5. Rulings come from code (the Scoring tool). The language model never decides right or wrong. The player name is never an input to scoring.
6. Do not invent facts, field names, library functions or API behavior. If you are not sure, write CHECK and ask me.
7. Do not add a dependency, rename a tool, or change a tool signature without asking me first.
8. Do not run any command that changes the Orchestrate instance (orchestrate tools import, agents import, connections, remove, delete) unless my prompt says to.
9. Do not delete files unless my prompt says to.

## 3. Fixed names. Use exactly these.
- Agents: prediction_agent, referee_agent
- Tools (one Python file each in tools/): save_prediction, list_open_predictions, get_next_game_events, score_open_predictions, get_leaderboard, list_rulings, override_ruling
- The Game Data tool is get_next_game_events. The Scoring tool is score_open_predictions.
- Orchestrate connection app id: cloudant_creds (kind key_value, keys: url, apikey, and optional database)
- Cloudant database name: rivalry_watch_party (default; can be overridden by the optional database key)
- Game ids: game_1, game_2, game_3
- Prediction types: game_winner, scores_before_half, next_score
- Statuses: open, right, wrong, not_counted
- Language model for both agents: groq/openai/gpt-oss-120b

## 4. Database design (one Cloudant database, documents have a "type" field)
Dates are ISO 8601 strings in UTC.

game_state (one per game). _id = "game_state:{game_id}"
  type, game_id, sport, home_team, away_team, source ("recorded" or "live"), status ("not_started", "in_progress", "final"), last_sequence (int, starts at 0), home_score, away_score, period, organizer (made up name of the person who set up the watch party), updated_at

game_event. _id = "game_event:{game_id}:{sequence as 5 digits}"
  type, game_id, event_id, sequence (int, 1, 2, 3...), event_type ("score", "half_end", "game_end", "other"), team (team name or null), points (int or null), home_score, away_score, period, clock, description, source

prediction. _id = "prediction:{game_id}:{short random id}"
  type, game_id, group_id, player, prediction_type, team, original_text, made_after_sequence (the game_state.last_sequence when it was saved), status ("open"), created_at

ruling. _id = "ruling:{prediction_id}"  (one ruling per prediction)
  type, ruling_id, prediction_id, game_id, group_id, player, prediction_type, team, status ("right", "wrong", "not_counted"), reason (plain sentence), points (int), event_id (the event that decided it), decided_at, changes (list; each item has changed_by, old_status, new_status, reason, changed_at)

Cloudant needs _rev to update a document. Read the document first, then write with its _rev. If you get a conflict (HTTP 409), read again and retry once.
The leaderboard is calculated from ruling documents. We do not store a separate score document.

## 5. Prediction types and scoring rules (the Scoring tool)
Points: right = 1. wrong = 0. not_counted = 0. Keep POINTS_RIGHT = 1 as one named constant in score_open_predictions.py. Only the team lead approves a change to scoring rules.

1. game_winner (team = the team the friend says will win)
   Decided by the first event with event_type "game_end". The winner is the team with the higher final score. Right if team equals the winner. Wrong if not. If the final score is a tie, status is not_counted with the reason "The game ended in a tie."
2. scores_before_half (team = the team the friend says will score before the half ends)
   Decided by the first event that is either a "score" event by that team in the first half (right) or a "half_end" event (wrong, if that team has not scored in the first half). Use the period field to know the first half.
3. next_score (team = the team the friend says will score next)
   Decided by the first "score" event with sequence greater than made_after_sequence. Right if the event team equals the prediction team. Wrong if not. If a "game_end" event comes first, status is not_counted with the reason "The game ended before another score."

General rules for all types:
- An event can decide a prediction only if its sequence is greater than made_after_sequence. If the deciding event already happened before the prediction was saved, status is not_counted with the reason "The prediction was made after the answer was already known."
- If a prediction is not decided yet, leave it open.
- Every ruling has a reason written as a short plain sentence that names the event.
- The functions that decide must not receive the player name.
(Add up to two more types only after the team picks the dataset, and only if the data supports them. Ask me first.)

## 6. Game Data tool rules (get_next_game_events)
Reads the next count events for the game. In "recorded" mode the events come from game_event documents in Cloudant. In "live" mode they would come from the live source. Live mode is not built until the team confirms a source: if source is "live", return {"ok": false, "error": "Live source not enabled yet."}.
For every event, check that it is new and reliable:
- New: sequence is greater than game_state.last_sequence and the event_id was not seen before. Otherwise reject with the reason "Not new".
- Reliable: all required fields are present; team is one of the two game teams or null; home_score and away_score never go down compared to game_state; sequence is an integer. Otherwise reject with a clear reason.
Accepted events update game_state (last_sequence, scores, period, status). Rejected events never change the state and never decide a prediction.
Return: {"ok": true, "accepted": [...], "rejected": [{"event": ..., "reason": ...}], "game_state": {...}}

## 7. Tool signatures
All tools return a plain dictionary that can be turned into JSON. On a problem return {"ok": false, "error": "short plain message"}. Never raise an unhandled error to the agent.
- save_prediction(game_id: str, group_id: str, player: str, prediction_type: str, team: str, original_text: str) -> dict
  Checks that prediction_type is one of the three types and team is one of the two teams in game_state. Sets made_after_sequence and status "open".
- list_open_predictions(game_id: str, group_id: str) -> dict
- get_next_game_events(game_id: str, count: int = 1) -> dict
- score_open_predictions(game_id: str) -> dict
  Reads all open predictions and all accepted events, applies section 5, saves a ruling for each decided prediction, and updates the prediction status. Returns {"ok": true, "new_rulings": [...], "still_open": number}.
- get_leaderboard(game_id: str = "all", group_id: str = "all") -> dict
  Per player: points, right, wrong, not_counted. Sorted by points high to low. "all" means every game, so scores carry over across games.
- list_rulings(game_id: str, group_id: str = "all") -> dict
  The ruling log. Every ruling with its reason and its changes.
- override_ruling(ruling_id: str, new_status: str, requested_by: str, reason: str) -> dict
  Only works if requested_by equals game_state.organizer. new_status must be right, wrong or not_counted. Updates points, keeps the old status in the changes list.

## 8. Rules for Orchestrate Python tools (Docs)
- Import: from ibm_watsonx_orchestrate.agent_builder.tools import tool
- One @tool function per file. The file name equals the tool name.
- The tool description comes from the docstring. Use Google style with Args: and Returns: sections.
- Keep inputs simple: str and int only. No nested types. Few parameters.
- Credentials: declare expected_credentials with app_id "cloudant_creds" and type ConnectionType.KEY_VALUE (from ibm_watsonx_orchestrate.agent_builder.connections import ConnectionType). Read them with connections.key_value("cloudant_creds") (from ibm_watsonx_orchestrate.run import connections). Keys: url, apikey, optional database.
- Local testing fallback: if the connection is not available, read the environment variables CLOUDANT_URL and CLOUDANT_APIKEY. Put this in one small helper function inside each tool file (a tool file cannot import another file unless packaged).
- Build the Cloudant client explicitly: CloudantV1(authenticator=IAMAuthenticator(apikey)) then set_service_url(url). CHECK the exact import names against the ibmcloudant package before using them.
- requirements.txt lists only third party packages the tools need, each pinned to an exact version. Never put ibm-watsonx-orchestrate in requirements.txt. Orchestrate checks packages against an allowlist at import time. CHECK that ibmcloudant is allowed. If it is not, use the requests package and the Cloudant HTTP API instead, and tell me first.
- Tool names are lowercase with underscores. No spaces.
- Agent names are lowercase with underscores.

## 9. Repository layout
AGENTS.md, README.md, .gitignore, .bobignore, .env.example, requirements.txt (tool packages, pinned), requirements-dev.txt (pytest and local tools), tools/ (7 tool files), agents/ (prediction_agent.yaml, referee_agent.yaml), scripts/ (check_cloudant.py, convert_raw_game.py, seed_recorded_game.py, setup_connection.sh, import_all.sh, run_prediction_check.py), data/ (data_sources.md, recorded_game_game_1.json, test_bad_events.json), tests/, docs/ (BUILD_PLAN.md, IMPORT_COMMANDS.md, test_results.md, bobcoin_log.md, technology_statement.md, problem_solution_statement.md, video_script.md, plus the team notes check_point_1.md, check_point_3.md, orchestrate_models.md, bob_model_note.md), bob_sessions/ (screenshots only). data/ also holds live_source_test.md.
.env, any key file, .venv/, scratch/ and data/raw/ must be in both .gitignore and .bobignore.
data/test_bad_events.json holds made up bad events (duplicate, old, score going down) used only for failure tests. Label it clearly as test data.

## 10. How you work with me
- You may run terminal commands in this project folder. I approve each one. Use the virtual environment in .venv. Before you run any orchestrate command, check it with --help.
- Never print or read the contents of .env. Scripts may read it. Never show its values.
- Start every task by reading this file and only the files my prompt names.
- Work in small steps. Run the tests you write. Do not say a task is done until the tests pass or you tell me exactly which fail.
- End every task with a report of at most 6 short lines: files created or changed, tests run and the result, what is not finished, any CHECK items, and the question you need answered.
- Ask before: adding a dependency, changing names or signatures in section 3 and 7, running orchestrate commands that change Orchestrate, deleting files.
- Keep code simple. Short functions. Plain names. Comments in simple English.
- All documentation (README, statements, scripts for the video) uses simple English: short sentences, no dashes, no metaphors, no claims we cannot prove.
- Do not read large files in full. Use the file names I give you.
- If my prompt conflicts with this file, tell me before you act.
