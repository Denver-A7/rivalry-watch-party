"""
convert_raw_game.py

Reads data/raw/pbp_2024_01_BAL_KC.csv (nflverse play-by-play, CC BY 4.0)
and writes data/recorded_game_game_1.json in the game_event format from
AGENTS.md section 4.

Events we keep:
  - Every scoring play (sp == "1") as a "score" event.
  - End of quarter 2 as "half_end".
  - End of quarters 1, 3, 4 (END GAME) as "other" or "game_end".

This gives between 20 and 80 events and covers all three prediction types.

Run:  python scripts/convert_raw_game.py
"""

import csv
import json
import os
import sys

RAW_FILE = "data/raw/pbp_2024_01_BAL_KC.csv"
OUT_FILE = "data/recorded_game_game_1.json"
GAME_ID = "game_1"
SOURCE = "recorded"


def seconds_to_clock(secs_remaining):
    """Convert game_seconds_remaining to a MM:SS clock string."""
    try:
        s = int(float(secs_remaining))
    except (ValueError, TypeError):
        return "00:00"
    # seconds remaining in the current quarter (each quarter = 900 s)
    secs_in_qtr = s % 900
    mins = secs_in_qtr // 60
    secs = secs_in_qtr % 60
    return f"{mins:02d}:{secs:02d}"


def points_scored(row):
    """Return points scored on this play (0 if none)."""
    try:
        before = int(float(row["posteam_score"]))
        after = int(float(row["posteam_score_post"]))
        return max(0, after - before)
    except (ValueError, TypeError):
        return 0


def build_events(rows):
    """
    Walk rows in order and build a list of event dicts.

    One event per:
      - first row of the game (GAME) -> other
      - scoring play (sp == "1")
      - end of quarter 2  -> half_end
      - first kickoff of the second half -> other
      - END QUARTER 1 / END QUARTER 3 -> other
      - END GAME -> game_end
    """
    home_team = rows[0]["home_team"]
    away_team = rows[0]["away_team"]
    events = []
    sequence = 0
    seen_half2 = False  # emit one event for the start of the second half

    for row in rows:
        desc_raw = row.get("desc", "").strip()

        try:
            period = int(float(row["qtr"]))
        except (ValueError, TypeError):
            period = 0

        try:
            hs = int(float(row["total_home_score"]))
            as_ = int(float(row["total_away_score"]))
        except (ValueError, TypeError):
            hs, as_ = 0, 0

        clock = seconds_to_clock(row.get("game_seconds_remaining", "0"))

        # --- game start (first row, desc == "GAME") ---
        if desc_raw == "GAME":
            sequence += 1
            events.append({
                "type": "game_event",
                "game_id": GAME_ID,
                "event_id": f"{GAME_ID}_play_{row['play_id']}",
                "sequence": sequence,
                "event_type": "other",
                "team": None,
                "points": None,
                "home_score": 0,
                "away_score": 0,
                "period": 1,
                "clock": "15:00",
                "description": "Game start.",
                "source": SOURCE,
            })
            continue

        # --- first kickoff of the second half -> other ---
        if (not seen_half2
                and row.get("game_half") == "Half2"
                and row.get("play_type") == "kickoff"):
            seen_half2 = True
            sequence += 1
            events.append({
                "type": "game_event",
                "game_id": GAME_ID,
                "event_id": f"{GAME_ID}_play_{row['play_id']}",
                "sequence": sequence,
                "event_type": "other",
                "team": None,
                "points": None,
                "home_score": hs,
                "away_score": as_,
                "period": period,
                "clock": clock,
                "description": "Start of second half.",
                "source": SOURCE,
            })
            continue

        # --- scoring play ---
        if row.get("sp") == "1":
            pts = points_scored(row)
            if pts <= 0:
                # safety: skip if no actual points (should not happen)
                continue
            sequence += 1
            events.append({
                "type": "game_event",
                "game_id": GAME_ID,
                "event_id": f"{GAME_ID}_play_{row['play_id']}",
                "sequence": sequence,
                "event_type": "score",
                "team": row["posteam"],
                "points": pts,
                "home_score": hs,
                "away_score": as_,
                "period": period,
                "clock": clock,
                "description": desc_raw,
                "source": SOURCE,
            })
            continue

        # --- end of quarter 2 = half_end ---
        if desc_raw == "END QUARTER 2":
            sequence += 1
            events.append({
                "type": "game_event",
                "game_id": GAME_ID,
                "event_id": f"{GAME_ID}_play_{row['play_id']}",
                "sequence": sequence,
                "event_type": "half_end",
                "team": None,
                "points": None,
                "home_score": hs,
                "away_score": as_,
                "period": 2,
                "clock": "00:00",
                "description": "End of first half.",
                "source": SOURCE,
            })
            continue

        # --- end of game ---
        if desc_raw == "END GAME":
            sequence += 1
            events.append({
                "type": "game_event",
                "game_id": GAME_ID,
                "event_id": f"{GAME_ID}_play_{row['play_id']}",
                "sequence": sequence,
                "event_type": "game_end",
                "team": None,
                "points": None,
                "home_score": hs,
                "away_score": as_,
                "period": period,
                "clock": "00:00",
                "description": f"Game over. Final score: {home_team} {hs}, {away_team} {as_}.",
                "source": SOURCE,
            })
            continue

        # --- end of quarter 1 or 3 -> other ---
        if desc_raw in ("END QUARTER 1", "END QUARTER 3"):
            sequence += 1
            events.append({
                "type": "game_event",
                "game_id": GAME_ID,
                "event_id": f"{GAME_ID}_play_{row['play_id']}",
                "sequence": sequence,
                "event_type": "other",
                "team": None,
                "points": None,
                "home_score": hs,
                "away_score": as_,
                "period": period,
                "clock": "00:00",
                "description": desc_raw,
                "source": SOURCE,
            })
            continue

    return home_team, away_team, events


def main():
    if not os.path.exists(RAW_FILE):
        print(f"ERROR: raw file not found: {RAW_FILE}", file=sys.stderr)
        sys.exit(1)

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    home_team, away_team, events = build_events(rows)

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)

    # summary
    score_events = [e for e in events if e["event_type"] == "score"]
    half_ends = [e for e in events if e["event_type"] == "half_end"]
    game_ends = [e for e in events if e["event_type"] == "game_end"]
    others = [e for e in events if e["event_type"] == "other"]
    final = game_ends[0] if game_ends else {}

    print(f"Output: {OUT_FILE}")
    print(f"Total events: {len(events)}")
    print(f"  score: {len(score_events)}  half_end: {len(half_ends)}"
          f"  game_end: {len(game_ends)}  other: {len(others)}")
    print(f"Home team: {home_team}")
    print(f"Away team: {away_team}")
    print(f"Final score: {home_team} {final.get('home_score','?')},"
          f" {away_team} {final.get('away_score','?')}")


if __name__ == "__main__":
    main()
