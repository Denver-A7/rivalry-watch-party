# Video Script: Rivalry Watch Party

Length: 3 minutes
Format: Say / Show

---

## 0:00 to 0:25 — The Problem

**Say:**

Friends watch the same game from different places.
They text predictions to each other all game long.
Who said what? Who was right?
Nobody keeps score. The fun fades fast.
There is no easy way to track predictions, check them against what actually happened, and give everyone a fair result with a reason.

**Show:**

A group chat on screen. Messages arrive:
"I think the Royals score next."
"No way, the Knights will win this half."
"I called that three messages ago!"
Scroll the chat to show it getting messy. No score. No rulings. No record.

---

## 0:25 to 0:45 — The User

**Say:**

Our users are friends who watch the same game from different places.
They want to make predictions and find out if they were right.
They do not want to manage a spreadsheet.
They do not want to wait until the game ends.
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

**Show:**

A simple diagram. Two boxes: Prediction Agent and Referee Agent.
Seven tool names arranged around them: save_prediction, list_open_predictions, get_next_game_events, score_open_predictions, get_leaderboard, list_rulings, override_ruling.
One cylinder below both agents labeled: IBM Cloudant.
Draw a line from each agent to the tools it uses. Keep the diagram clean.

---

## 1:05 to 2:35 — The Demo

**Note to presenter:** This demo uses a recorded game. The game data is not live. We replay events from a recorded game stored in the database.

---

### 1:05 to 1:20 — A friend types a prediction

**Say:**

A friend named Sam types: "I think the Knights will score next."
The Prediction Agent reads the message.
It saves the prediction and confirms it is recorded.
Sam can see her open predictions at any time.

**Show:**

The Orchestrate chat window open. Type:
"I think the Knights will score next."
Show the Prediction Agent reply: prediction saved, type is next_score, team is Knights.
Then show the list of open predictions returned by the agent.

---

### 1:20 to 1:40 — A game event arrives

**Say:**

We are using a recorded game for this demo.
The next event in the recording is a score by the Knights.
The Referee Agent reads the event.
It checks that the event is new and that all required fields are present.
It accepts the event and updates the game state.

**Show:**

The Orchestrate chat window. Type:
"Get the next game event."
Show the Referee Agent reply. Display the accepted event:
event type: score, team: Knights, home score and away score updated.
Point out the words "source: recorded" in the game state.

---

### 1:40 to 2:00 — The referee rules

**Say:**

The Referee Agent runs the scoring tool on all open predictions.
Sam predicted the Knights would score next.
The Knights just scored.
The ruling is: right.
The reason is a plain sentence that names the event.
Sam gets one point.

**Show:**

The Orchestrate chat window. Show the ruling returned:
Player: Sam. Prediction: next_score, Knights. Status: right.
Reason: "The Knights scored on event game_event:game_1:00005, which was the next score after this prediction was made."
Then show the leaderboard with Sam at the top with 1 point.

---

### 2:00 to 2:20 — The leaderboard

**Say:**

The leaderboard shows every player, their points, and how many predictions were right, wrong, or not counted.
It updates automatically after each ruling.
Scores carry over across games.
The organizer can filter by game or see all games together.

**Show:**

The leaderboard output in the chat:
Sam: 1 point, 1 right, 0 wrong, 0 not counted.
Show a second player with 0 points for contrast.
Then show the same leaderboard filtered to game_1 only.

---

### 2:20 to 2:35 — A dispute

**Say:**

The organizer of the watch party can override a ruling.
Only the organizer can do this.
The old ruling is kept in the record. Nothing is deleted.
Every change has a reason.
This keeps the game fair and transparent.

**Show:**

The Orchestrate chat window. Type:
"Override ruling, change Sam's prediction to not counted. Reason: the event was processed twice by mistake."
Show the Referee Agent call override_ruling.
Show the result: status changed to not counted, old status right is in the changes log.
Show the leaderboard updated: Sam now has 0 points.

---

## 2:35 to 3:00 — What Is Next and How We Built It

**Say:**

This prototype works with a recorded game.
Our next step is to connect a live game data source.
We also want to add more prediction types when the data supports them.

IBM Bob helped us plan the agent design, write the tool code, and run all 104 tests.
IBM watsonx Orchestrate connected the agents and tools in one place.
IBM Cloudant stored every prediction, event, and ruling.
We built this in a short time because the platform handled the hard parts.
Rivalry Watch Party: fair rulings, clear reasons, and a lot more fun.

**Show:**

Split screen. Left side: a terminal showing "104 tests passed". Right side: the Orchestrate agent builder with both agents visible.
Then show the full architecture diagram one more time: Prediction Agent, Referee Agent, seven tools, one Cloudant database.
End on the project name: Rivalry Watch Party.

---

## Presenter Notes

1. Use made up player names throughout. Do not use real names.
2. Say "recorded game" every time you refer to the game data. Do not say "live" unless a live source is confirmed.
3. The scoring rules live in code. Say this clearly in the demo section. The language model explains the ruling but does not make the decision.
4. No betting language. No prizes. No money. This is a fun tool for friends.
5. The dispute section shows override_ruling. Make clear that only the organizer can do this and that the old ruling is preserved.
6. The 104 tests cover all three prediction types, bad event rejection, dispute logic, leaderboard sorting, and the live source error. You can mention any of these if a question comes up.
