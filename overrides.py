"""
overrides.py — Manual schedule overrides for MikewNACBot

Copyright © 2026 TheBooleanJulian. All rights reserved.
Disclaimer: Built and maintained by Kew's tech team. Not affiliated with NAC or any government entity.

Stores a JSON file of admin-defined additions, removals, and modifications
that are applied on top of the NAC-scraped events before display.

Override types:
  add    — add a show not on NAC (e.g. private gig, non-busking venue)
  remove — cancel/remove all NAC slots for a given location on a given day
  modify — replace all NAC slots for a given location on a given day with new timing
"""

import json
import uuid
import logging
from datetime import date
from pathlib import Path

from scraper import BuskEvent

log = logging.getLogger(__name__)

OVERRIDES_FILE = Path("overrides.json")


# ─── persistence ──────────────────────────────────────────────────────────────

def load_overrides() -> list[dict]:
    if not OVERRIDES_FILE.exists():
        return []
    with OVERRIDES_FILE.open() as f:
        return json.load(f).get("overrides", [])


def _save_overrides(overrides: list[dict]):
    OVERRIDES_FILE.write_text(json.dumps({"overrides": overrides}, indent=2, default=str))


# ─── write operations ─────────────────────────────────────────────────────────

def add_show(ev_date: date, location: str, start_time: str, end_time: str) -> str:
    """Add a show not in NAC. Returns the new override ID."""
    overrides = load_overrides()
    ov_id = str(uuid.uuid4())[:8]
    overrides.append({
        "id": ov_id,
        "type": "add",
        "date": ev_date.isoformat(),
        "location": location.strip().upper(),
        "start_time": start_time,
        "end_time": end_time,
    })
    _save_overrides(overrides)
    log.info(f"Override added [{ov_id}]: ADD {ev_date} {location} {start_time}–{end_time}")
    return ov_id


def remove_show(ev_date: date, location: str) -> str:
    """Mark all NAC slots for a location on a day as removed. Returns the new override ID."""
    overrides = load_overrides()
    ov_id = str(uuid.uuid4())[:8]
    overrides.append({
        "id": ov_id,
        "type": "remove",
        "date": ev_date.isoformat(),
        "location": location.strip().upper(),
    })
    _save_overrides(overrides)
    log.info(f"Override added [{ov_id}]: REMOVE {ev_date} {location}")
    return ov_id


def modify_show(ev_date: date, location: str, new_start: str, new_end: str) -> str:
    """Replace all NAC slots for a location on a day with new timing. Returns the new override ID."""
    overrides = load_overrides()
    ov_id = str(uuid.uuid4())[:8]
    overrides.append({
        "id": ov_id,
        "type": "modify",
        "date": ev_date.isoformat(),
        "location": location.strip().upper(),
        "new_start_time": new_start,
        "new_end_time": new_end,
    })
    _save_overrides(overrides)
    log.info(f"Override added [{ov_id}]: MODIFY {ev_date} {location} → {new_start}–{new_end}")
    return ov_id


def clear_override(ov_id: str) -> bool:
    """Remove a specific override by ID. Returns True if found and deleted."""
    overrides = load_overrides()
    new_overrides = [o for o in overrides if o["id"] != ov_id]
    if len(new_overrides) == len(overrides):
        return False
    _save_overrides(new_overrides)
    log.info(f"Override cleared: {ov_id}")
    return True


# ─── apply ────────────────────────────────────────────────────────────────────

def apply_overrides(events: list[BuskEvent], range_start: date, range_end: date) -> list[BuskEvent]:
    """
    Apply stored overrides to a list of scraped events for the given date range.

    Processing order (each override applied in insertion order):
      remove  — strips all scraped slots for a location on a day
      modify  — strips all scraped slots for a location on a day, adds one consolidated slot
      add     — appends a new slot unconditionally

    Overrides outside the requested date range are silently ignored.
    """
    overrides = load_overrides()
    result = list(events)

    for ov in overrides:
        ov_date = date.fromisoformat(ov["date"])
        if not (range_start <= ov_date <= range_end):
            continue

        ov_loc = ov["location"].upper()

        if ov["type"] == "remove":
            before = len(result)
            result = [e for e in result if not (e.date == ov_date and e.location.upper() == ov_loc)]
            log.info(f"Override REMOVE [{ov['id']}]: removed {before - len(result)} slot(s) for {ov_loc} on {ov_date}")

        elif ov["type"] == "modify":
            before = len(result)
            result = [e for e in result if not (e.date == ov_date and e.location.upper() == ov_loc)]
            result.append(BuskEvent(ov_date, ov_loc, ov["new_start_time"], ov["new_end_time"]))
            log.info(f"Override MODIFY [{ov['id']}]: replaced {before - len(result) + 1} slot(s) for {ov_loc} on {ov_date} → {ov['new_start_time']}–{ov['new_end_time']}")

        elif ov["type"] == "add":
            result.append(BuskEvent(ov_date, ov_loc, ov["start_time"], ov["end_time"]))
            log.info(f"Override ADD [{ov['id']}]: added {ov_loc} on {ov_date} {ov['start_time']}–{ov['end_time']}")

    return result


# ─── formatting ───────────────────────────────────────────────────────────────

def format_overrides_list(overrides: list[dict]) -> str:
    if not overrides:
        return "No active overrides."

    lines = ["<b>Active Overrides</b>\n"]
    for ov in overrides:
        ov_id   = ov["id"]
        ov_type = ov["type"].upper()
        ov_date = ov["date"]
        ov_loc  = ov["location"]

        if ov_type == "ADD":
            lines.append(f"[{ov_id}] {ov_type} {ov_date} | {ov_loc} | {ov['start_time']}–{ov['end_time']}")
        elif ov_type == "REMOVE":
            lines.append(f"[{ov_id}] {ov_type} {ov_date} | {ov_loc}")
        elif ov_type == "MODIFY":
            lines.append(f"[{ov_id}] {ov_type} {ov_date} | {ov_loc} → {ov['new_start_time']}–{ov['new_end_time']}")

    lines.append("\nUse /clearoverride &lt;id&gt; to remove one.")
    return "\n".join(lines)
