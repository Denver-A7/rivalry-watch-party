# Video Script: Rivalry Watch Party

Length: 3 minutes
Format: Say / Show
Slides are not required. Record the demo screen and say the Say text as the voiceover. Show the architecture diagram during The Solution.

---

## 0:00 to 0:25 — The Problem

**Say:**

Friends watch the same game from different places.
They text predictions to each other all game long.
Nobody keeps score and nobody gets a reason.
The fun fades fast.

**Show:**

A group chat on screen. Messages arrive:
"I predict KC will win the game."
"I think BAL will score before the half."
"I called that three messages ago!"
Scroll the chat to show it getting messy. No score. No rulings. No record.

---

## 0:25 to 0:45 — The User

**Say:**

Our users are friends who watch the same game from different places.
They want to make predictions and find out if they were right.
They do not want to manage a spreadsheet.
They do not want to wait until the game ends.
Group chats and spreadsheets do not check predictions against the game, and they do not explain a result.
They want a ruling and a reason right away.
This is a fun tool. It is not a betting tool. No money is involved.

**Show:**

Two or three people on separate screens or phones watching the same game.
One types a prediction. Another checks the leaderboard.
Keep it casual. Show friends, not gamblers.

---

## 0:45 to 1:05 — The Solution

**Say:**

We built Rivalry Watch Party using IBM watsonx Orchestrate.
Two agents work together.
The Prediction Agent takes a friend's message, turns it into a checkable prediction, and saves it.
The Referee Agent reads each new game event, runs the scoring rules in code, and gives a ruling with a plain reason.
Seven tools connect the agents to one IBM Cloudant database.
The scoring rules live in code. The language model never decides right or wrong.
Every ruling is fair and explainable.
Only the organizer can change a ruling, and the old ruling is kept.
There is no betting, and the game data is open and credited.

**Show:**

A simple diagram. Two boxes: Prediction Agent and Referee Agent.
Seven tool names arranged around them: save_prediction, list_open_predictions, get_next_game_events, score_open_predictions, get_leaderboard, list_rulings, override_ruling.
One cylinder below both agents labeled: IBM Cloudant.
Draw a line from each agent to the tools it uses. Keep the diagram clean.

---

## 1:05 to 2:35 — The Demo

**Note to presenter:** This demo uses a recorded game. The game data is not live. We replay events one at a time from a recorded game stored in the database. The game moves forward by one event each time you say "Check game_1, next update." For this video we skip ahead to show the final outcome.

---

### 1:05 to 1:25 — Three friends type predictions

**Say:**

Maya, Leo and Ana are watching game_1 together in group friends1.
Each one types a prediction into the Orchestrate chat.
The Prediction Agent reads each message, turns it into a checkable prediction, and saves it.

**Show:**

The Orchestrate chat window open. Type each message in turn and show the agent reply after each one.

Message 1: "Hi, I am Maya. For game_1 in group friends1, I predict KC will win the game."
Agent reply: prediction saved, type is game_winner, team is KC.

Message 2: "Hi, I am Leo. For game_1 in group friends1, I predict BAL will score before the half ends."
Agent reply: prediction saved, type is scores_before_half, team is BAL.

Message 3: "Hi, I am Ana. For game_1 in group friends1, I predict BAL will score next."
Agent reply: prediction saved, type is next_score, team is BAL.

---

### 1:25 to 1:50 — The game moves forward

**Say:**

We are using a recorded game for this demo.
The game data comes from nflverse, under the CC BY 4.0 license.
Each check moves the game forward by one event.
We skip ahead to the end of the game.
The Referee Agent reads each event, checks that it is new and complete, and updates the game state.
When all predictions are decided it shows the rulings.

**Show:**

The Orchestrate chat window. Type:
"Check game_1, next update."
Show the agent reply: event accepted, game state updated.
Then show a brief pause or cut. Add text on screen: "Video skips ahead to the end of the game."
Type "Check game_1, next update." one more time to show the final event processed and the game state showing status: final.

---

### 1:50 to 2:10 — The rulings and the recap

**Say:**

The game is final. KC won. The scoring tool decided each prediction.
Maya predicted KC would win. That is right.
Leo predicted BAL would score before the half. That is right.
Ana predicted BAL would score next. The ruling shows right as well.
Each ruling has a plain reason that names the event that decided it.

**Show:**

The Orchestrate chat window. Type:
"Give me a recap of game_1 for group friends1."
Show the Referee Agent reply. It lists all three rulings with their reasons.
Then show the leaderboard: Ana 1 point, Leo 1 point, Maya 1 point.

---

### 2:10 to 2:35 — A dispute

**Say:**

The organizer of the watch party can override a ruling.
Only the organizer can do this.
Maya is the organizer.
She asks to change Ana's next_score ruling.
The old ruling is kept in the record. Nothing is deleted.
Every change has a reason.
This keeps the game fair and transparent.

**Show:**

The Orchestrate chat window. Type:
"I am Maya, the organizer. Please change Ana's next_score ruling from right to wrong. The reason is: prediction was made after the answer was known."
Show the Referee Agent look up the ruling, then call override_ruling.
Show the result: status changed to wrong, old status right is in the changes log.

Then type:
"Show the ruling log for game_1 in group friends1, including the change history."
Show the agent reply. It lists all three rulings. Ana's ruling shows the change: who changed it, when and why.

---

## 2:35 to 3:00 — What Is Next and How We Built It

**Say:**

This prototype works with a recorded game.
Our next step is to connect a live game data source.
Try it with your own friends.
We also want to add more prediction types when the data supports them.

IBM Bob helped us plan the agent design, write the tool code, and run all 108 tests.
The chat test in watsonx Orchestrate found three problems the unit tests missed. We fixed all three with Bob.
IBM watsonx Orchestrate connected the agents and tools in one place.
IBM Cloudant stored every prediction, event, and ruling.
We built this in a short time because the platform handled the hard parts.
Rivalry Watch Party: fair rulings, clear reasons, and a lot more fun.

**Show:**

Split screen. Left side: a terminal showing "108 tests passed". Right side: the Orchestrate agent builder with both agents visible.
Then show the full architecture diagram one more time: Prediction Agent, Referee Agent, seven tools, one Cloudant database.
End on the project name: Rivalry Watch Party.

---

## Presenter Notes

1. Use made up player names throughout. Do not use real names.
2. Say "recorded game" every time you refer to the game data. Do not say "live" unless a live source is confirmed.
3. The game data comes from nflverse. Credit nflverse if asked about the data source.
4. The scoring rules live in code. Say this clearly in the demo section. The language model explains the ruling but does not make the decision.
5. No betting language. No prizes. No money. This is a fun tool for friends.
6. The dispute section shows override_ruling. Make clear that only the organizer can do this and that the old ruling is preserved.
7. The 108 tests cover all three prediction types, bad event rejection, dispute logic, leaderboard sorting, and the live source error. You can mention any of these if a question comes up.
8. The chat test found three problems: the agent asked for more than one event and the game got stuck; the game winner was not counted because the final event had no team names; the organizer change failed because the agent had no ruling ID. All three were fixed before the demo.
