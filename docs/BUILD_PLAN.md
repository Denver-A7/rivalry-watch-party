# BUILD_PLAN.md

One-page build plan for the Rivalry Watch Party tools.

---

## Build order

We build in dependency order. Each tool depends only on the tools above it.

| Step | Tool file | Why this order |
|------|-----------|----------------|
| 1 | `get_next_game_events` | Populates game_event and updates game_state. All other tools depend on data being in the database. |
| 2 | `save_prediction` | Needs game_state to exist so it can validate the team name and read last_sequence. |
| 3 | `list_open_predictions` | Read-only. Needs predictions to exist. |
| 4 | `score_open_predictions` | Needs game_events and open predictions. Writes rulings. |
| 5 | `get_leaderboard` | Read-only. Needs rulings to exist. |
| 6 | `list_rulings` | Read-only. Needs rulings to exist. |
| 7 | `override_ruling` | Needs a ruling to exist and game_state to check the organizer. Build last because it modifies existing rulings. |

---

## Cloudant documents each tool reads and writes

### 1. get_next_game_events
- Reads: `game_state:{game_id}` (to get last_sequence, home/away teams, source, scores)
- Reads: `game_event:{game_id}:*` (in recorded mode, to fetch the next count events by sequence)
- Writes: `game_state:{game_id}` (updates last_sequence, home_score, away_score, period, status)
- Does NOT write game_event documents (they are seeded by `seed_recorded_game.py`)

### 2. save_prediction
- Reads: `game_state:{game_id}` (to validate team name and read last_sequence)
- Writes: `prediction:{game_id}:{short random id}` (new document, status "open")

### 3. list_open_predictions
- Reads: `prediction:{game_id}:*` where status is "open" and group_id matches
- Writes: nothing

### 4. score_open_predictions
- Reads: `prediction:{game_id}:*` where status is "open"
- Reads: `game_event:{game_id}:*` (all accepted events, ordered by sequence)
- Writes: `ruling:{prediction_id}` (new document for each decided prediction)
- Writes: `prediction:{game_id}:{id}` (updates status from "open" to right/wrong/not_counted; needs _rev)

### 5. get_leaderboard
- Reads: `ruling:*` filtered by game_id (or all games) and group_id (or all groups)
- Writes: nothing

### 6. list_rulings
- Reads: `ruling:*` filtered by game_id and group_id
- Writes: nothing

### 7. override_ruling
- Reads: `game_state:{game_id}` (to check organizer name matches requested_by)
- Reads: `ruling:{ruling_id}` (to get current status and _rev)
- Writes: `ruling:{ruling_id}` (updates status, points, appends to changes list; needs _rev)

---

## Tests needed (short list)

### get_next_game_events
- [ ] Returns next event in sequence from recorded game
- [ ] Advances game_state.last_sequence after accept
- [ ] Rejects duplicate event_id (reason "Not new")
- [ ] Rejects event with sequence <= last_sequence (reason "Not new")
- [ ] Rejects event where home_score goes down
- [ ] Rejects event with a missing required field
- [ ] Returns error when source is "live"

### save_prediction
- [ ] Saves prediction with correct made_after_sequence and status "open"
- [ ] Rejects unknown prediction_type
- [ ] Rejects team not in game_state
- [ ] Returns error when game_state does not exist

### list_open_predictions
- [ ] Returns only open predictions for the given game_id and group_id
- [ ] Returns empty list when none exist

### score_open_predictions
- [ ] game_winner: right when team matches winner at game_end
- [ ] game_winner: wrong when team does not match winner
- [ ] game_winner: not_counted when game ends in a tie
- [ ] scores_before_half: right when team scores before half_end
- [ ] scores_before_half: wrong when half_end arrives and team has not scored
- [ ] next_score: right when next score event matches team
- [ ] next_score: wrong when next score event is the other team
- [ ] next_score: not_counted when game_end arrives before any score
- [ ] not_counted when deciding event sequence <= made_after_sequence
- [ ] Does not use player name anywhere in scoring logic
- [ ] Leaves prediction open when no deciding event exists yet

### get_leaderboard
- [ ] Correct points, right, wrong, not_counted per player
- [ ] Sorted by points high to low
- [ ] game_id="all" aggregates across all games
- [ ] group_id="all" aggregates across all groups

### list_rulings
- [ ] Returns rulings with reason and changes list
- [ ] Filters correctly by game_id and group_id

### override_ruling
- [ ] Updates status and points when requested_by equals organizer
- [ ] Rejects request when requested_by does not equal organizer
- [ ] Old status is saved in the changes list
- [ ] Rejects new_status values not in {right, wrong, not_counted}

---

## Decisions and resolved CHECK items

**Decision: use `requests` for all Cloudant calls (resolved CHECK-1 and CHECK-2)**
We do not use ibmcloudant in any tool file. All Cloudant HTTP calls use the `requests` package. `requirements.txt` will pin a single `requests` version. The Cloudant base URL and IAM API key come from the `cloudant_creds` connection (or environment variables in local tests). Authentication uses an IAM token exchange call to `https://iam.cloud.ibm.com/identity/token` with the apikey, then passes the bearer token in the `Authorization` header.

**Decision: use `_all_docs` key-prefix scans (resolved CHECK-3)**
No Mango indexes. All queries use `GET /{db}/_all_docs?startkey="prefix:"&endkey="prefix:\uffff"&include_docs=true`. This works because every document ID is prefixed with its type and game_id.

**Resolved CHECK-4 (connections import in local pytest)**
Confirmed locally: `from ibm_watsonx_orchestrate.run import connections` imports without error in the `.venv`. The fallback helper can use a simple try/except around `connections.key_value(...)`, not around the import.

**Resolved CHECK-5 (default parameter values in @tool functions)**
Confirmed locally: the `@tool` decorator captures Python default values in its JSON schema (`default=1`, `default='all'`) and marks only parameters without defaults as required. Default values work as expected.
