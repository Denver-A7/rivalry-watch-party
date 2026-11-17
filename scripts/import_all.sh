#!/usr/bin/env bash
# import_all.sh
# Imports all 7 Python tools, then referee_agent, then prediction_agent.
# Ends by listing all tools and agents in the active Orchestrate environment.
# Run this from the project root directory.
#
# Commands verified with --help before use.
# orchestrate tools import: flags --kind/-k, --file/-f, --requirements-file/-r, --app-id/-a
# orchestrate agents import: flag --file/-f
# orchestrate tools list: no required flags
# orchestrate agents list: no required flags

set -euo pipefail

echo "=== Importing tools ==="

orchestrate tools import \
  -k python \
  -f tools/save_prediction.py \
  -r requirements.txt \
  -a cloudant_creds

orchestrate tools import \
  -k python \
  -f tools/list_open_predictions.py \
  -r requirements.txt \
  -a cloudant_creds

orchestrate tools import \
  -k python \
  -f tools/get_next_game_events.py \
  -r requirements.txt \
  -a cloudant_creds

orchestrate tools import \
  -k python \
  -f tools/score_open_predictions.py \
  -r requirements.txt \
  -a cloudant_creds

orchestrate tools import \
  -k python \
  -f tools/get_leaderboard.py \
  -r requirements.txt \
  -a cloudant_creds

orchestrate tools import \
  -k python \
  -f tools/list_rulings.py \
  -r requirements.txt \
  -a cloudant_creds

orchestrate tools import \
  -k python \
  -f tools/override_ruling.py \
  -r requirements.txt \
  -a cloudant_creds

echo "=== Importing agents ==="

# Import referee_agent first because prediction_agent lists it as a collaborator.
orchestrate agents import -f agents/referee_agent.yaml

orchestrate agents import -f agents/prediction_agent.yaml

echo "=== Listing tools ==="
orchestrate tools list

echo "=== Listing agents ==="
orchestrate agents list

echo "Done."
