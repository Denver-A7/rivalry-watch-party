# Rivalry Watch Party Agent

This is a prototype for the IBM SkillsBuild AI Experiential Learning Lab, Track 3: Fan Centric Sports and Entertainment.

Friends watch the same game from different places and type predictions in a chat. Two AI agents in IBM watsonx Orchestrate check those predictions against game events, rule each one right or wrong or not counted, and keep score. It is a fun tool for friends. It is not a betting tool.

## The two agents

**prediction_agent** reads a friend's message and turns it into a checkable prediction. It saves the prediction, asks one short question if the message is unclear, and can show open predictions and the current leaderboard.

**referee_agent** checks each new game event, scores all open predictions, explains each ruling, updates the score, and writes a recap. It can also handle disputes from the organizer.

## The seven tools

| Tool | What it does |
|------|--------------|
| save_prediction | Saves a new prediction for a player |
| list_open_predictions | Lists all predictions that have not been ruled yet |
| get_next_game_events | Reads the next events from the recorded game |
| score_open_predictions | Checks open predictions against events and saves rulings |
| get_leaderboard | Shows points for each player, sorted high to low |
| list_rulings | Shows all rulings with reasons and any changes |
| override_ruling | Lets the organizer change a ruling with a reason |

## Game data

We test with a recorded game. We do not have a confirmed live data source at this time.

## Credentials

Copy `.env.example` to `.env` and fill in your IBM Cloudant URL and API key. Do not commit `.env`.

## Setup

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```
