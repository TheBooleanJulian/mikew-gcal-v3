"""
bot.py — Telegram bot for MikewNACBot

Copyright © 2026 TheBooleanJulian. All rights reserved.
Disclaimer: Built and maintained by Kew's official tech team. Not affiliated with NAC or any government entity.

Commands:
  /thisweek  → this week's schedule (Mon–Sun)
  /nextweek  → next week's schedule
  /today     → today's schedule
  /help      → usage info
  /start     → same as /help

Auto-posts every Friday at 20:00 SGT (next week's schedule).
Auto-posts every day at 00:00 SGT (today's schedule).
"""

import logging
import os
from datetime import date, datetime, timedelta

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from scraper import NAC_PROFILE_URL, build_day_message, build_message, scrape_schedule

load_dotenv()

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID   = int(os.environ["CHAT_ID"])

SGT = pytz.timezone("Asia/Singapore")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ─── week helpers ─────────────────────────────────────────────────────────────

def _this_week() -> tuple[date, date]:
    today = datetime.now(SGT).date()
    start = today - timedelta(days=today.weekday())   # Monday
    return start, start + timedelta(days=6)           # Sunday


def _next_week() -> tuple[date, date]:
    start, _ = _this_week()
    start += timedelta(weeks=1)
    return start, start + timedelta(days=6)


# ─── shared send helper ───────────────────────────────────────────────────────

async def _send_schedule(week_start: date, week_end: date, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    events  = scrape_schedule(week_start, week_end)
    message = build_message(events, week_start, week_end, NAC_PROFILE_URL)
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")


# ─── command handlers ─────────────────────────────────────────────────────────

async def cmd_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start, end = _this_week()
    await _send_schedule(start, end, context, update.effective_chat.id)


async def cmd_nextweek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start, end = _next_week()
    await _send_schedule(start, end, context, update.effective_chat.id)


async def _send_day_schedule(day: date, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    events  = scrape_schedule(day, day)
    message = build_day_message(events, day, NAC_PROFILE_URL)
    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(SGT).date()
    await _send_day_schedule(today, context, update.effective_chat.id)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hey! I'm the Mikew NAC Bot.\n\n"
        "I track Mikew aka FattKew the OneBoyBand's busking schedule on NAC and post it here "
        "every Friday at 8 PM SGT so you're always ready for the week ahead.\n\n"
        "Automagically pulling Mikew busking gigs from NAC! 🎸 Built by TheBooleanJulian.\n\n"
        "Join the new official Mikew community server for live Mikew updates, exclusive media, and decentralised chatting: https://t.me/mikewmikewbeam\n\n"
        "Commands:\n"
        "/thisweek — this week's schedule\n"
        "/nextweek — next week's schedule\n"
        "/today — today's schedule\n"
        "/help — show this message\n\n"
        "⚠️ Disclaimer: This bot is built and maintained by Kew's official tech team. Not affiliated with or endorsed by NAC or any government entity. "
        "Schedule data is sourced from NAC eServices and may not always be accurate — always verify with Kew or NAC directly.\n"
        "© 2026 TheBooleanJulian"
    )


# ─── scheduled auto-posts ─────────────────────────────────────────────────────

async def _friday_post(app: Application):
    start, end = _next_week()
    await _send_schedule(start, end, app, CHAT_ID)


async def _midnight_post(app: Application):
    today = datetime.now(SGT).date()
    events  = scrape_schedule(today, today)
    message = build_day_message(events, today, NAC_PROFILE_URL)
    await app.bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",    cmd_help))
    app.add_handler(CommandHandler("help",     cmd_help))
    app.add_handler(CommandHandler("thisweek", cmd_schedule))
    app.add_handler(CommandHandler("nextweek", cmd_nextweek))
    app.add_handler(CommandHandler("today",    cmd_today))

    scheduler = AsyncIOScheduler(timezone=SGT)
    scheduler.add_job(
        _friday_post,
        trigger="cron",
        day_of_week="fri",
        hour=20,
        minute=0,
        args=[app],
    )
    scheduler.add_job(
        _midnight_post,
        trigger="cron",
        hour=0,
        minute=0,
        args=[app],
    )
    scheduler.start()
    log.info("Scheduler started — weekly post every Friday 20:00 SGT, daily post every midnight SGT")

    log.info("Bot polling…")
    app.run_polling()


if __name__ == "__main__":
    main()
