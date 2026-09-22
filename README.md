<div align="center">

# MikewNACBot (mikew-gcal-v3)

**Telegram bot that scrapes FattKew / OneBoyBand's NAC busking schedule and posts it to a group chat — automatically or on demand.**

![Python](https://img.shields.io/badge/-Python-3776AB?logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/-Telegram-26A5E4?logo=telegram&logoColor=white)
![Zeabur](https://img.shields.io/badge/-Zeabur-6C5CE7)
![License](https://img.shields.io/badge/license-AGPLv3%20%2B%20Commercial-00D4C8.svg)

![Hero](assets/hero.png)

</div>

---

> **Disclaimer:** This bot is built and maintained by TheBooleanJulian. It is not affiliated with, endorsed by, or associated with the National Arts Council (NAC) or any related government entities. Schedule data is sourced publicly from the NAC eServices website and may not always be accurate or up to date. Always verify directly with Kew or the [NAC website](https://eservices.nac.gov.sg/Busking/busker/profile/dbc5b6bc-e22a-4e60-9fe4-f4d6a1aa17a4).

---

## What it does

MikewNACBot scrapes FattKew / OneBoyBand's upcoming busking schedule from the NAC eServices website and formats it into clean Telegram messages. It auto-posts next week's full schedule every Friday at 8 PM SGT, and today's schedule every day at midnight SGT — so the group chat stays up to date without anyone having to lift a finger. Manual commands let anyone pull the current or next week's schedule on demand, and admins can add, remove, or modify show entries that aren't listed on NAC. This is the third iteration of the Mikew schedule tooling — it drops Google Calendar sync entirely in favor of posting straight to Telegram; see [mikew-gcal-v1](../mikew-gcal-v1) and [mikew-gcal-v2](../mikew-gcal-v2) for the earlier calendar-syncing versions.

## Features

- Auto-posts next week's Mon–Sun schedule every **Friday at 8 PM SGT**
- Auto-posts today's schedule every day at **midnight SGT**
- Manual commands: `/today`, `/thisweek`, `/nextweek`
- Admin-only schedule overrides — add, remove, or modify shows not on NAC
- Overrides are applied automatically to all queries and auto-posts
- Flask health check endpoint (`/healthz`) and branded status page on port 8080
- Containerised via Docker, deployed on Zeabur

## Tech Stack

| Layer | Choice |
|---|---|
| Bot | python-telegram-bot 21.6 (polling) + APScheduler |
| Scraper | requests + BeautifulSoup4 |
| Scheduler | APScheduler 3.10.4 |
| Health check | Flask 3.1 |
| Hosting | Zeabur (Docker, GitHub CI/CD) |

## Commands

| Command | What it does |
|---|---|
| `/thisweek` | Post this week's schedule (Mon–Sun) |
| `/nextweek` | Post next week's schedule |
| `/today` | Post today's schedule |
| `/help` | Show help message |
| `/start` | Same as `/help` |

**Admin-only** (requires `ADMIN_IDS`):

| Command | What it does |
|---|---|
| `/addshow <date> <start> <end> <location...>` | Add a custom show override |
| `/removeshow <date> <location...>` | Remove a show override |
| `/modifyshow <date> <newstart> <newend> <location...>` | Modify an existing show override |
| `/overrides` | List all active overrides |
| `/clearoverride <id>` | Clear a specific override by ID |

## Screenshots

![Branded status page hero art](assets/hero.png)

_The image above is the branded status-page hero art; a full screenshot of the running `/healthz` status page is coming soon._

## Quick Start

```bash
git clone https://github.com/TheBooleanJulian/mikew-gcal-v3
cd mikew-gcal-v3
pip install -r requirements.txt
cp .env.example .env
# Fill in BOT_TOKEN, CHAT_ID, and optionally ADMIN_IDS in .env
python bot.py
```

## Configuration

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `CHAT_ID` | Yes | Telegram chat/group ID to post schedules to |
| `ADMIN_IDS` | No | Comma-separated Telegram user IDs with access to admin commands |

## Project Structure

```
mikew-gcal-v3/
├── bot.py            Telegram bot + APScheduler (Friday 8 PM + daily midnight cron)
├── scraper.py        HTTP scraper (requests + BeautifulSoup)
├── overrides.py      Schedule override management (add/remove/modify shows)
├── health.py         Flask health check and status page (port 8080)
├── requirements.txt  Python dependencies
├── Dockerfile        Container definition
├── zeabur.json       Zeabur deployment config
└── .env.example      Environment variable template
```

## Deployment

Deployed on Zeabur via Docker. Push to `main` triggers a redeploy. The container exposes port 8080 for the health check endpoint (`/healthz`) and a branded status page (`/`).

## Status / Roadmap

- [x] NAC scraper with pagination
- [x] Friday auto-post (next week's schedule)
- [x] Daily midnight auto-post (today's schedule)
- [x] Admin override commands
- [x] Health check + status page
- [x] Deployed on Zeabur
- [ ] Cancellation detection / change alerts

## Changelog

- **2026-07-18** — Rebranded README with hero image and updated maintainer attribution; switched project to dual AGPLv3 + commercial licensing
- **2026-04-08** — Fixed HTML parse mode escaping for angle brackets in admin command examples; fixed missing module import in Docker build; added Flask health check server (`/healthz` + `/`) with branded status page; added admin commands (`/addshow`, `/removeshow`, `/modifyshow`, `/overrides`, `/clearoverride`) and schedule overrides system
- **2026-03-30** — Fixed duplicate auto-posts on redeploy using `misfire_grace_time` and `max_instances`; added copyright and disclaimer notices to all files and bot messages
- **2026-03-27/28** — Added `/today` command and daily midnight auto-post; renamed `/schedule` to `/thisweek`; fixed today's date resolving in SGT instead of server local timezone; added signature line to schedule outputs
- **2026-03-24** — Initial working bot: `bot.py`, NAC scraper with pagination fix, NAC events endpoint

## License

This project is dual licensed.

- Community Edition — [GNU Affero General Public License v3 (AGPLv3)](LICENSE). Free to use, modify, and self-host. If you distribute a modified version or run it as a network service, you must make the corresponding source available.
- Commercial License — for organisations that want to embed, modify, or distribute this software without AGPLv3's obligations. See [COMMERCIAL-LICENSE.md](COMMERCIAL-LICENSE.md).

---

<div align="center">
<sub>Built by <a href="https://github.com/TheBooleanJulian">@TheBooleanJulian</a></sub>
</div>
