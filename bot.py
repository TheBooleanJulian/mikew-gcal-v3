"""
bot.py — Telegram bot for MikewNACBot

Copyright © 2026 TheBooleanJulian. All rights reserved.
Disclaimer: Built and maintained by Kew's tech team. Not affiliated with NAC or any government entity.

Commands:
  /thisweek      → this week's schedule (Mon–Sun)
  /nextweek      → next week's schedule
  /today         → today's schedule
  /help          → usage info
  /start         → same as /help

Admin-only commands (ADMIN_IDS env var):
  /addshow       <date> <start> <end> <location...>
  /removeshow    <date> <location...>
  /modifyshow    <date> <newstart> <newend> <location...>
  /overrides     → list all active overrides
  /clearoverride <id>

Auto-posts every Friday at 20:00 SGT (next week's schedule).
Auto-posts every day at 00:00 SGT (today's schedule).
"""

import logging
import os
import threading
from datetime import date, datetime, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from scraper import NAC_PROFILE_URL, build_day_message, build_message, scrape_schedule, _parse_date, _parse_time
from overrides import (
    add_show, remove_show, modify_show, clear_override,
    load_overrides, apply_overrides, format_overrides_list,
)
from health import (
    StatusServer,
    BRAND_NAME, BRAND_GITHUB, BRAND_HANDLE,
    TEAL, BG_DARK, TEXT_WHITE, TEXT_MUTED,
)

load_dotenv()

BOT_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID    = int(os.environ["CHAT_ID"])
ADMIN_IDS  = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()}

SGT = pytz.timezone("Asia/Singapore")

# ─── global bot state for status tracking ───────────────────────────────────
bot_state = {
    "start_time": datetime.now(SGT),
    "last_friday_post": None,
    "last_midnight_post": None,
    "errors": [],
    "command_count": 0,
}

# ─── status server (branded health page) ────────────────────────────────────
status_server = StatusServer(
    bot_name="Mikew NAC Bot",
    bot_username="@MikewNACBot",
    bot_description="Scrapes FattKew's busking schedule from NAC and posts to Telegram",
    bot_version="1.0.0",
    icon_emoji="🎸",
    accent_color=TEAL,
)


def get_bot_metrics():
    """Get current bot metrics for status page."""
    return {
        "Status": "🟢 Running",
        "Last Friday Post": bot_state["last_friday_post"] or "Pending",
        "Last Midnight Post": bot_state["last_midnight_post"] or "Pending",
        "Uptime": str(datetime.now(SGT) - bot_state["start_time"]).split('.')[0],
        "Commands Used": bot_state["command_count"],
        "Recent Errors": len(bot_state["errors"]),
    }


logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ─── week helpers ─────────────────────────────────────────────────────────────

def _this_week() -> tuple[date, date]:
    """Get Monday and Sunday of the current week (SGT timezone)."""
    today = datetime.now(SGT).date()
    start = today - timedelta(days=today.weekday())   # Monday
    return start, start + timedelta(days=6)           # Sunday


def _next_week() -> tuple[date, date]:
    """Get Monday and Sunday of the next week (SGT timezone)."""
    start, _ = _this_week()
    start += timedelta(weeks=1)
    return start, start + timedelta(days=6)


# ─── shared send helper ───────────────────────────────────────────────────────

async def _send_schedule(week_start: date, week_end: date, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Fetch NAC schedule for given date range, apply overrides, and send formatted message."""
    events  = scrape_schedule(week_start, week_end)
    events  = apply_overrides(events, week_start, week_end)
    message = build_message(events, week_start, week_end, NAC_PROFILE_URL)
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")


# ─── command handlers ─────────────────────────────────────────────────────────

async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /thisweek command."""
    bot_state["command_count"] += 1
    start, end = _this_week()
    await _send_schedule(start, end, context, update.effective_chat.id)


async def cmd_nextweek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /nextweek command."""
    bot_state["command_count"] += 1
    start, end = _next_week()
    await _send_schedule(start, end, context, update.effective_chat.id)


async def _send_day_schedule(day: date, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    """Fetch NAC schedule for a single day, apply overrides, and send formatted message."""
    events  = scrape_schedule(day, day)
    events  = apply_overrides(events, day, day)
    message = build_day_message(events, day, NAC_PROFILE_URL)
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command."""
    bot_state["command_count"] += 1
    today = datetime.now(SGT).date()
    await _send_day_schedule(today, context, update.effective_chat.id)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message with available commands."""
    bot_state["command_count"] += 1
    await update.message.reply_text(
        "👋 Hey! I'm the Mikew NAC Bot.\n\n"
        "I track Mikew aka FattKew the OneBoyBand's busking schedule on NAC and post it here "
        "every Friday at 8 PM SGT so you're always ready for the week ahead.\n\n"
        "Automagically pulling Mikew busking gigs from NAC! 🎸 Built by TheBooleanJulian.\n\n"
        "Join the Mikew community server for live Mikew updates, exclusive media, and decentralised chatting: https://t.me/mikewmikewbeam\n\n"
        "📅 <b>Public Commands:</b>\n"
        "/thisweek — this week's schedule\n"
        "/nextweek — next week's schedule\n"
        "/today — today's schedule\n"
        "/help — show this message\n\n"
        "🔐 <b>Admin-Only Commands:</b> (for authorised users)\n"
        "/addshow <date> <start> <end> <location...> — add custom show\n"
        "/removeshow <date> <location...> — remove show\n"
        "/modifyshow <date> <start> <end> <location...> — modify timing\n"
        "/overrides — list all active overrides\n"
        "/clearoverride <id> — remove specific override\n\n"
        "⚠️ Disclaimer: This bot is built and maintained by Kew's tech team. Not affiliated with or endorsed by NAC or any government entity. "
        "Schedule data is sourced from NAC eServices and may not always be accurate — always verify with Kew or NAC directly.\n"
        "© 2026 TheBooleanJulian",
        parse_mode="HTML"
    )


# ─── admin helpers ────────────────────────────────────────────────────────────

def _is_admin(update: Update) -> bool:
    """Check if the user is in the ADMIN_IDS list."""
    user = update.effective_user
    return user is not None and user.id in ADMIN_IDS


# ─── admin command handlers ───────────────────────────────────────────────────

async def cmd_addshow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /addshow <date> <start> <end> <location...>
    e.g. /addshow 10/4 10:00 14:00 Harbourfront MRT
    """
    msg = update.message
    assert msg

    if not _is_admin(update):
        await msg.reply_text("⛔ This command is admin-only.")
        return

    args = context.args or []
    if len(args) < 4:
        await msg.reply_text(
            "Usage: /addshow <date> <start> <end> <location...>\n"
            "e.g. /addshow 10/4 10:00 14:00 Harbourfront MRT"
        )
        return

    ev_date  = _parse_date(args[0])
    start    = _parse_time(args[1])
    end      = _parse_time(args[2])
    location = " ".join(args[3:])

    if not ev_date:
        await msg.reply_text(
            f"❌ Couldn't read the date — you typed: {args[0]}\n"
            "Try formats like: 10/4  or  10 April  or  10 Apr"
        )
        return
    if not start or not end:
        await msg.reply_text(
            f"❌ Couldn't read the time — you typed: {args[1]} / {args[2]}\n"
            "Try formats like: 10:00  10am  2pm  2:30pm"
        )
        return

    ov_id = add_show(ev_date, location, start, end)
    await msg.reply_text(
        f"✅ Show added! [{ov_id}]\n"
        f"📅 {ev_date.day} {ev_date.strftime('%b')} | {location.upper()} | {start}–{end}\n\n"
        "Use /overrides to see all, /clearoverride to undo."
    )


async def cmd_removeshow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /removeshow <date> <location...>
    e.g. /removeshow 10/4 Harbourfront MRT
    Removes all NAC slots for that location on that day.
    """
    msg = update.message
    assert msg

    if not _is_admin(update):
        await msg.reply_text("⛔ This command is admin-only.")
        return

    args = context.args or []
    if len(args) < 2:
        await msg.reply_text(
            "Usage: /removeshow <date> <location...>\n"
            "e.g. /removeshow 10/4 Harbourfront MRT"
        )
        return

    ev_date  = _parse_date(args[0])
    location = " ".join(args[1:])

    if not ev_date:
        await msg.reply_text(
            f"❌ Couldn't read the date — you typed: {args[0]}\n"
            "Try formats like: 10/4  or  10 April  or  10 Apr"
        )
        return

    ov_id = remove_show(ev_date, location)
    await msg.reply_text(
        f"✅ Show removed! [{ov_id}]\n"
        f"📅 {ev_date.day} {ev_date.strftime('%b')} | {location.upper()} — all slots cancelled\n\n"
        "Use /overrides to see all, /clearoverride to undo."
    )


async def cmd_modifyshow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /modifyshow <date> <newstart> <newend> <location...>
    e.g. /modifyshow 10/4 10:00 14:00 Harbourfront MRT
    Times come before location so multi-word venue names are never ambiguous.
    """
    msg = update.message
    assert msg

    if not _is_admin(update):
        await msg.reply_text("⛔ This command is admin-only.")
        return

    args = context.args or []
    if len(args) < 4:
        await msg.reply_text(
            "Usage: /modifyshow <date> <newstart> <newend> <location...>\n"
            "e.g. /modifyshow 10/4 10:00 14:00 Harbourfront MRT"
        )
        return

    ev_date   = _parse_date(args[0])
    new_start = _parse_time(args[1])
    new_end   = _parse_time(args[2])
    location  = " ".join(args[3:])

    if not ev_date:
        await msg.reply_text(
            f"❌ Couldn't read the date — you typed: {args[0]}\n"
            "Try formats like: 10/4  or  10 April  or  10 Apr"
        )
        return
    if not new_start or not new_end:
        await msg.reply_text(
            f"❌ Couldn't read the new times — you typed: {args[1]} / {args[2]}\n"
            "Try formats like: 10:00  10am  2pm  2:30pm"
        )
        return
    if not location:
        await msg.reply_text("❌ No location specified.")
        return

    ov_id = modify_show(ev_date, location, new_start, new_end)
    await msg.reply_text(
        f"✅ Show timing updated! [{ov_id}]\n"
        f"📅 {ev_date.day} {ev_date.strftime('%b')} | {location.upper()} → {new_start}–{new_end}\n\n"
        "Use /overrides to see all, /clearoverride to undo."
    )


async def cmd_overrides(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active overrides."""
    _ = context
    msg = update.message
    assert msg

    if not _is_admin(update):
        await msg.reply_text("⛔ This command is admin-only.")
        return

    overrides = load_overrides()
    await msg.reply_text(format_overrides_list(overrides), parse_mode="HTML")


async def cmd_clearoverride(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /clearoverride <id>
    Remove a specific override by its ID.
    """
    msg = update.message
    assert msg

    if not _is_admin(update):
        await msg.reply_text("⛔ This command is admin-only.")
        return

    args = context.args or []
    if not args:
        await msg.reply_text("Usage: /clearoverride <id>")
        return

    ov_id = args[0]
    if clear_override(ov_id):
        await msg.reply_text(f"✅ Override [{ov_id}] removed.")
    else:
        await msg.reply_text(f"❌ No override found with ID [{ov_id}].")


# ─── scheduled auto-posts ─────────────────────────────────────────────────────

async def _friday_post(app: Application):
    """Auto-post next week's schedule every Friday at 8 PM SGT."""
    try:
        start, end = _next_week()
        await _send_schedule(start, end, app, CHAT_ID)
        bot_state["last_friday_post"] = datetime.now(SGT).strftime("%a %Y-%m-%d %H:%M:%S")
        log.info("✅ Friday post sent")
    except Exception as e:
        error_msg = f"Friday post failed: {str(e)}"
        log.error(error_msg)
        bot_state["errors"].append({"timestamp": datetime.now(SGT).isoformat(), "message": error_msg})


async def _midnight_post(app: Application):
    """Auto-post today's schedule every day at midnight SGT."""
    try:
        today   = datetime.now(SGT).date()
        events  = scrape_schedule(today, today)
        events  = apply_overrides(events, today, today)
        message = build_day_message(events, today, NAC_PROFILE_URL)
        await app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
        bot_state["last_midnight_post"] = datetime.now(SGT).strftime("%a %Y-%m-%d %H:%M:%S")
        log.info("✅ Midnight post sent")
    except Exception as e:
        error_msg = f"Midnight post failed: {str(e)}"
        log.error(error_msg)
        bot_state["errors"].append({"timestamp": datetime.now(SGT).isoformat(), "message": error_msg})


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    # Initialize bot state
    bot_state["start_time"] = datetime.now(SGT)
    
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",         cmd_help))
    app.add_handler(CommandHandler("help",          cmd_help))
    app.add_handler(CommandHandler("thisweek",      cmd_schedule))
    app.add_handler(CommandHandler("nextweek",      cmd_nextweek))
    app.add_handler(CommandHandler("today",         cmd_today))
    app.add_handler(CommandHandler("addshow",       cmd_addshow))
    app.add_handler(CommandHandler("removeshow",    cmd_removeshow))
    app.add_handler(CommandHandler("modifyshow",    cmd_modifyshow))
    app.add_handler(CommandHandler("overrides",     cmd_overrides))
    app.add_handler(CommandHandler("clearoverride", cmd_clearoverride))

    scheduler = AsyncIOScheduler(timezone=SGT)
    scheduler.add_job(
        _friday_post,
        trigger="cron",
        day_of_week="fri",
        hour=20,
        minute=0,
        args=[app],
        misfire_grace_time=60,
        max_instances=1,
    )
    scheduler.add_job(
        _midnight_post,
        trigger="cron",
        hour=0,
        minute=0,
        args=[app],
        misfire_grace_time=60,
        max_instances=1,
    )
    scheduler.start()
    log.info("Scheduler started — weekly post every Friday 20:00 SGT, daily post every midnight SGT")

    # Start branded status server in background thread
    status_thread = threading.Thread(
        target=lambda: status_server.start(
            port=8080,
            metrics_callback=get_bot_metrics,
        ),
        daemon=True,
    )
    status_thread.start()
    log.info("🎵 Status page available at http://0.0.0.0:8080/ · Built by TheBooleanJulian")
    
    log.info("Bot polling…")
    app.run_polling()


if __name__ == "__main__":
    main()
