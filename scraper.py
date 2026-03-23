"""
scraper.py — NAC busking schedule scraper for FattKew / OneBoyBand

HTML structure (confirmed from real page source):

  <div class="col-md-6 col-lg-3 col-cuttor" id="div-booking-{uuid}">
    <div class="dash-bx borderTopRed">
      <div class="dash-bx-title" ...> ... </div>
      <ul class="dash-bx-menus owner"> ... </ul>
      <ul class="dash-bx-times">
        <li> Mon, 23 March </li>
        <li><span> 10:00:AM - 11:00:AM </span></li>
        <li class="address">
          <a href="..."> MRT STATION - CCL HARBOURFRONT </a>
        </li>
      </ul>
    </div>
  </div>

Key quirk: time format uses a COLON before AM/PM → "10:00:AM" not "10:00 AM"

No JavaScript rendering required — the full card grid is in the static HTML.
Uses requests + BeautifulSoup only (no Playwright, no headless browser).
"""

import re
import json
import logging
import requests
from datetime import date, timedelta
from typing import Optional
from collections import defaultdict
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

_BUSKER_ID = "dbc5b6bc-e22a-4e60-9fe4-f4d6a1aa17a4"
NAC_PROFILE_URL = (
    "https://eservices.nac.gov.sg/Busking/busker/profile/" + _BUSKER_ID
)
_NAC_EVENTS_URL      = "https://eservices.nac.gov.sg/Busking/events/buskers/" + _BUSKER_ID + "/public"
_NAC_EVENTS_MORE_URL = _NAC_EVENTS_URL + "/more"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-SG,en;q=0.9",
}

# ─── data model ───────────────────────────────────────────────────────────────

class BuskEvent:
    def __init__(self, event_date: date, location: str, start_time: str, end_time: str):
        self.date       = event_date
        self.location   = location.strip().upper()
        self.start_time = start_time   # "HH:MM" 24h
        self.end_time   = end_time     # "HH:MM" 24h

    def __repr__(self):
        return f"BuskEvent({self.date} | {self.location} | {self.start_time}–{self.end_time})"


# ─── date / time helpers ──────────────────────────────────────────────────────

MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "january": 1, "february": 2, "march": 3, "april": 4,
    "june": 6, "july": 7, "august": 8, "september": 9,
    "october": 10, "november": 11, "december": 12,
}
DAY_NAMES = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def _guess_year(month: int, day: int) -> int:
    """Return the nearest upcoming year for the given month/day."""
    today = date.today()
    for yr in [today.year, today.year + 1]:
        try:
            candidate = date(yr, month, day)
            if candidate >= today - timedelta(days=7):
                return yr
        except ValueError:
            pass
    return today.year


def _parse_date(s: str) -> Optional[date]:
    """
    Parse date strings as they appear on the NAC cards:
      "Mon, 23 March"   "Tue, 24 March"   "Wed, 25 March"
    Also handles:  "23 March 2026"  "23/3/2026"
    """
    s = s.strip()
    # Strip leading weekday e.g. "Mon, " / "Monday, "
    s = re.sub(r"^[A-Za-z]+,?\s+", "", s).strip()

    # "23 March" or "23 March 2026"
    m = re.match(r"(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?$", s)
    if m:
        day    = int(m.group(1))
        mo_key = m.group(2).lower()[:3]
        mo     = MONTH_MAP.get(mo_key)
        year   = int(m.group(3)) if m.group(3) else _guess_year(mo or 1, day)
        if mo:
            try:
                return date(year, mo, day)
            except ValueError:
                pass

    # "23/3" or "23/3/2026"
    m = re.match(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{4}))?$", s)
    if m:
        day  = int(m.group(1))
        mo   = int(m.group(2))
        year = int(m.group(3)) if m.group(3) else _guess_year(mo, day)
        try:
            return date(year, mo, day)
        except ValueError:
            pass

    return None


def _parse_time(s: str) -> Optional[str]:
    """
    Parse NAC's quirky time format: "10:00:AM" / "06:00:PM"
    Also handles standard:          "10:00 AM" / "10:00"
    Returns 24h string "HH:MM".
    """
    s = s.strip()
    # "HH:MM:AM" or "HH:MM:PM"  ← NAC's actual format
    m = re.match(r"(\d{1,2}):(\d{2}):?(AM|PM)", s, re.IGNORECASE)
    if m:
        h, mn, period = int(m.group(1)), int(m.group(2)), m.group(3).upper()
        if period == "PM" and h != 12:
            h += 12
        elif period == "AM" and h == 12:
            h = 0
        return f"{h:02d}:{mn:02d}"
    # Bare "HH:MM"
    m = re.match(r"(\d{1,2}):(\d{2})$", s)
    if m:
        return f"{int(m.group(1)):02d}:{int(m.group(2)):02d}"
    return None


def _parse_time_range(s: str):
    """
    "10:00:AM - 11:00:AM"  →  ("10:00", "11:00")
    "12:00:PM - 02:00:PM"  →  ("12:00", "14:00")
    """
    # Split on " - " or "–"
    parts = re.split(r"\s*[-–]\s*", s.strip(), maxsplit=1)
    if len(parts) == 2:
        return _parse_time(parts[0]), _parse_time(parts[1])
    return None, None


def _fmt_time(t: str) -> str:
    """'10:00'→'10am'  '14:00'→'2pm'  '13:30'→'1:30pm'"""
    try:
        h, m = map(int, t.split(":"))
        period = "am" if h < 12 else "pm"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d}{period}" if m else f"{h12}{period}"
    except Exception:
        return t


def _fmt_time_range(start: str, end: str) -> str:
    return f"{_fmt_time(start)}-{_fmt_time(end)}"


# ─── main scraper ─────────────────────────────────────────────────────────────

def scrape_schedule(week_start: date, week_end: date) -> list[BuskEvent]:
    """
    Fetch the NAC profile page and parse all booking cards.
    Returns events within [week_start, week_end], sorted by date+time.
    """
    # First page
    log.info(f"Fetching {_NAC_EVENTS_URL}")
    resp = requests.get(_NAC_EVENTS_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    try:
        html = json.loads(resp.text)
    except json.JSONDecodeError:
        html = resp.text

    all_events = _parse_html(html)

    # Paginate via /more until empty
    PAGE_SIZE = 8
    skip = PAGE_SIZE
    while True:
        url = f"{_NAC_EVENTS_MORE_URL}?skip={skip}&take={PAGE_SIZE}"
        log.info(f"Fetching {url}")
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        try:
            page_html = json.loads(r.text)
        except json.JSONDecodeError:
            page_html = r.text
        page_events = _parse_html(page_html)
        if not page_events:
            break
        all_events.extend(page_events)
        skip += PAGE_SIZE
    log.info(f"Parsed {len(all_events)} total events from page")

    week_events = [e for e in all_events if week_start <= e.date <= week_end]
    week_events.sort(key=lambda e: (e.date, e.start_time))

    log.info(f"Events in week {week_start}–{week_end}: {len(week_events)}")
    return week_events


def _parse_html(html: str) -> list[BuskEvent]:
    """
    Parse all col-cuttor booking cards from raw HTML.
    Selector chain:
      div.col-cuttor
        └── ul.dash-bx-times
              ├── li[0]          → date  "Mon, 23 March"
              ├── li[1] > span   → time  "10:00:AM - 11:00:AM"
              └── li.address > a → loc   "MRT STATION - CCL HARBOURFRONT"
    """
    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.find_all("div", class_="col-cuttor")
    log.info(f"Found {len(cards)} booking cards")

    events = []
    for card in cards:
        times_ul = card.find("ul", class_="dash-bx-times")
        if not times_ul:
            continue

        lis = times_ul.find_all("li", recursive=False)
        if len(lis) < 2:
            continue

        # ── Date ──────────────────────────────────────────────────────────
        date_raw = lis[0].get_text(strip=True)
        ev_date  = _parse_date(date_raw)
        if not ev_date:
            log.debug(f"Skipping card — unparseable date: {date_raw!r}")
            continue

        # ── Time range ────────────────────────────────────────────────────
        time_raw = lis[1].get_text(strip=True)
        start_t, end_t = _parse_time_range(time_raw)
        if not start_t:
            log.debug(f"Skipping card — unparseable time: {time_raw!r}")
            continue

        # ── Location ──────────────────────────────────────────────────────
        loc_li  = card.find("li", class_="address")
        loc_raw = loc_li.get_text(strip=True) if loc_li else "See NAC website"

        events.append(BuskEvent(ev_date, loc_raw, start_t, end_t or start_t))

    return events


# ─── slot consolidation ───────────────────────────────────────────────────────

def consolidate_events(events: list[BuskEvent]) -> list[BuskEvent]:
    """
    Merge consecutive 1-hour slots at the same location on the same day.

    NAC books in hourly slots, but we display them as a single block:
      Harbourfront 10:00–11:00 + 11:00–12:00  →  Harbourfront 10:00–12:00
      AMK HUB      18:00–19:00 + 19:00–20:00  →  AMK HUB      18:00–20:00
    """
    if not events:
        return events

    # Sort: date → location → start_time so consecutive slots are adjacent
    sorted_evts = sorted(events, key=lambda e: (e.date, e.location, e.start_time))

    merged: list[BuskEvent] = []
    cur = sorted_evts[0]

    for nxt in sorted_evts[1:]:
        same_day = nxt.date == cur.date
        same_loc = nxt.location == cur.location
        adjacent = nxt.start_time == cur.end_time

        if same_day and same_loc and adjacent:
            # Extend current block's end time
            cur = BuskEvent(cur.date, cur.location, cur.start_time, nxt.end_time)
        else:
            merged.append(cur)
            cur = nxt

    merged.append(cur)

    # Re-sort by date then start_time for natural chronological display
    merged.sort(key=lambda e: (e.date, e.start_time))

    log.info(f"Consolidation: {len(events)} slots → {len(merged)} blocks")
    return merged


# ─── message builder ──────────────────────────────────────────────────────────

def build_message(events: list[BuskEvent], week_start: date, week_end: date, nac_url: str) -> str:
    """
    Format events into a Telegram HTML message.

    Example output:
      📅 Upcoming Busking Schedule
      23 Mar – 29 Mar 2026

      MON 23/3
      MRT STATION - CCL HARBOURFRONT
      10am-12pm
      AMK HUB
      6pm-9pm

      TUE 24/3
      ...

      Please ask Kew here in chat or check the NAC website, in case of
      cancellations/timing/location changes 🙏
    """
    week_label = f"{week_start.day} {week_start.strftime('%b')} – {week_end.day} {week_end.strftime('%b %Y')}"

    if not events:
        return (
            f"📅 <b>Busking Schedule</b> | {week_label}\n\n"
            "No upcoming bookings found for this week.\n\n"
            f"Please check the <a href=\"{nac_url}\">NAC website</a> directly, "
            "or ask Kew in chat for updates! 🙏"
        )

    consolidated = consolidate_events(events)

    by_date: dict[date, list[BuskEvent]] = defaultdict(list)
    for e in consolidated:
        by_date[e.date].append(e)

    lines = [f"📅 <b>Upcoming Busking Schedule</b>\n{week_label}\n"]

    for d in sorted(by_date.keys()):
        lines.append(f"<b>{DAY_NAMES[d.weekday()]} {d.day}/{d.month}</b>")
        for ev in sorted(by_date[d], key=lambda e: e.start_time):
            lines.append(ev.location)
            lines.append(_fmt_time_range(ev.start_time, ev.end_time))
        lines.append("")  # blank line between days

    lines.append(
        "Please ask Kew here in chat or check the "
        f"<a href=\"{nac_url}\">NAC website</a>, "
        "in case of cancellations/timing/location changes 🙏"
    )

    return "\n".join(lines)
