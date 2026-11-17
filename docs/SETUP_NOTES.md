# SETUP_NOTES.md

Setup notes for the Rivalry Watch Party project.

---

## 1. Create the virtual environment

You only need to do this once.

### Mac

```bash
python3 -m venv .venv
```

### Windows

```bat
python -m venv .venv
```

---

## 2. Activate the virtual environment

You must do this every time you open a new terminal.

### Mac

```bash
source .venv/bin/activate
```

### Windows (Command Prompt)

```bat
.venv\Scripts\activate.bat
```

### Windows (PowerShell)

```powershell
.venv\Scripts\Activate.ps1
```

---

## 3. Upgrade pip

Run this after activating the virtual environment.

```bash
pip install --upgrade pip
```

---

## 4. Install ibm-watsonx-orchestrate

This installs the Orchestrate CLI and SDK.

```bash
pip install --upgrade ibm-watsonx-orchestrate
```

Version installed: **2.20.0**

---

## 5. Install development dependencies

```bash
pip install -r requirements-dev.txt
```

This installs pytest for local testing.

---

## 6. orchestrate subcommands

Run `orchestrate --help` to see the top-level commands.

| Command | What it does |
|---|---|
| env | Add, remove, or select the active environment |
| agents | Interact with agents in the active env |
| tools | Interact with tools in the active env |
| skills | Interact with skills in the active env |
| toolkits | Interact with toolkits in the active env |
| knowledge-bases | Upload knowledge your agents can search |
| connections | Manage authentication connections |
| voice-configs | Configure voice providers |
| server | Manage your local Developer Edition server |
| chat | Launch the chat UI and CLI interface |
| models | List available large language models |
| channels | Configure channels (webchat, WhatsApp, etc.) |
| phone | Manage phone configurations |
| evaluations | Evaluate agent performance |
| settings | Configure settings for the active env |
| partners | Generate a submission-ready agent artifact package |
| observability | Search and export trace data |
| controls | Configure controls for AI assets |

### orchestrate agents subcommands

| Command | What it does |
|---|---|
| import | Import an agent definition from a file |
| create | Create and import an agent |
| list | List all agents |
| remove | Remove an agent |
| export | Export an agent to a zip or yaml |
| escalation-prompt | Show the escalation prompt for a native agent |
| deploy | Deploy an agent |
| undeploy | Undeploy an agent |
| connect | Add application connections to a custom agent |
| copy | Copy an agent to a different workspace |
| discover | Discover and import agents from A2A or an external provider |
| ai-builder | AI tools to help create and refine agents |

### orchestrate tools subcommands

| Command | What it does |
|---|---|
| import | Import a tool into the active environment |
| list | List imported tools |
| remove | Remove a tool |
| export | Export a tool to a zip file |
| auto-discover | Annotate and generate docstring for a Python tool |
| translation-export | Retrieve translations for a flow tool |
| translation-import | Import translations for a flow tool from a CSV file |
