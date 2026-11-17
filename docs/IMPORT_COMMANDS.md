# IMPORT_COMMANDS.md

This document explains what `setup_connection.sh` and `import_all.sh` do and
how to run them.

---

## Before you start

1. Make sure you have a `.env` file in the project root with these two lines:

   ```
   CLOUDANT_URL=<your Cloudant URL>
   CLOUDANT_APIKEY=<your Cloudant API key>
   ```

2. Make sure you are logged in to your Orchestrate environment. Run
   `orchestrate env list` to check.

3. Run all commands from the project root directory.

4. If you are using a virtual environment, activate it first:

   ```bash
   source .venv/bin/activate
   ```

---

## setup_connection.sh

**What it does**

This script creates the Cloudant connection in Orchestrate. The connection is
named `cloudant_creds`. The tools use it to reach the Cloudant database.

The script does these steps in order:

1. Reads `CLOUDANT_URL` and `CLOUDANT_APIKEY` from `.env`. It never prints the
   values.
2. Creates the connection with `orchestrate connections add`.
3. Configures it for the `draft` environment with type `team` and kind
   `key_value`.
4. Configures it for the `live` environment with the same settings.
5. Sets the `url` and `apikey` credentials for both environments.

**How to run on a Mac**

```bash
bash scripts/setup_connection.sh
```

**How to run on Windows**

The script is a bash script. It will not run directly in Command Prompt or
PowerShell. Use one of these options:

- **Git Bash or WSL:** open Git Bash or Windows Subsystem for Linux, go to the
  project folder, and run:

  ```bash
  bash scripts/setup_connection.sh
  ```

- **Run the commands manually:** copy and paste each command below into your
  terminal. Replace `<your URL>` and `<your API key>` with the actual values
  from your `.env` file. Do not share or print those values.

  ```
  orchestrate connections add -a cloudant_creds

  orchestrate connections configure -a cloudant_creds --env draft -t team -k key_value

  orchestrate connections configure -a cloudant_creds --env live -t team -k key_value

  orchestrate connections set-credentials -a cloudant_creds --env draft -e "url=<your URL>" -e "apikey=<your API key>"

  orchestrate connections set-credentials -a cloudant_creds --env live -e "url=<your URL>" -e "apikey=<your API key>"
  ```

---

## import_all.sh

**What it does**

This script imports all tools and agents into the active Orchestrate
environment.

The script does these steps in order:

1. Imports each of the 7 Python tools one by one. Each import command uses:
   - `--kind python` because the tools are Python files.
   - `--file` pointing to the tool file in `tools/`.
   - `--requirements-file requirements.txt` to install the needed packages.
   - `--app-id cloudant_creds` to link the connection.
2. Imports `referee_agent` from `agents/referee_agent.yaml`.
3. Imports `prediction_agent` from `agents/prediction_agent.yaml`.
   `referee_agent` is imported first because `prediction_agent` lists it as a
   collaborator.
4. Runs `orchestrate tools list` and `orchestrate agents list` to confirm the
   imports.

**How to run on a Mac**

```bash
bash scripts/import_all.sh
```

**How to run on Windows**

The script is a bash script. Use Git Bash or WSL as described above, or run
each command manually:

```
orchestrate tools import -k python -f tools/save_prediction.py -r requirements.txt -a cloudant_creds

orchestrate tools import -k python -f tools/list_open_predictions.py -r requirements.txt -a cloudant_creds

orchestrate tools import -k python -f tools/get_next_game_events.py -r requirements.txt -a cloudant_creds

orchestrate tools import -k python -f tools/score_open_predictions.py -r requirements.txt -a cloudant_creds

orchestrate tools import -k python -f tools/get_leaderboard.py -r requirements.txt -a cloudant_creds

orchestrate tools import -k python -f tools/list_rulings.py -r requirements.txt -a cloudant_creds

orchestrate tools import -k python -f tools/override_ruling.py -r requirements.txt -a cloudant_creds

orchestrate agents import -f agents/referee_agent.yaml

orchestrate agents import -f agents/prediction_agent.yaml

orchestrate tools list

orchestrate agents list
```

---

## Order matters

Run `setup_connection.sh` before `import_all.sh`. The tools need the
`cloudant_creds` connection to exist before they are imported.
