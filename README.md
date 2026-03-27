# 🎵 MikewNACBot

A Telegram bot that scrapes **FattKew / OneBoyBand**'s upcoming busking schedule from the NAC eServices website and posts it neatly to a Telegram chat.

**Auto-posts every Friday at 8 PM SGT** with next week's schedule, and **every day at midnight SGT** with that day's schedule. Trigger manually anytime.

---

## Example Output

**Weekly (`/thisweek`, `/nextweek`, Friday auto-post):**
```
📅 Upcoming Busking Schedule
23 Mar – 29 Mar 2026

MON 23/3
MRT STATION - CCL HARBOURFRONT
10am-12pm
AMK HUB
6pm-9pm

TUE 24/3
MRT STATION - CCL HARBOURFRONT
10am-2pm
KAMPUNG ADMIRALTY
5pm-7pm

Please ask Kew here in chat or check the NAC website,
in case of cancellations/timing/location changes 🙏
```

**Daily (`/today`, midnight auto-post):**
```
📅 Today's Busking Schedule
MON 23/3/2026

MRT STATION - CCL HARBOURFRONT
10am-12pm
AMK HUB
6pm-9pm

Please ask Kew here in chat or check the NAC website,
in case of cancellations/timing/location changes 🙏
```

---

## Commands

| Command | What it does |
|---|---|
| `/thisweek` | Post **this week's** schedule (Mon–Sun) |
| `/nextweek` | Post **next week's** schedule |
| `/today` | Post **today's** schedule |
| `/help` | Show help message |
| `/start` | Same as `/help` |

The bot also:
- **Auto-posts every Friday at 8 PM SGT** with next week's Mon–Sun schedule
- **Auto-posts every day at midnight SGT** with that day's schedule

---

## Files

```
mikewinacbot/
├── bot.py            Telegram bot + APScheduler (Friday + daily midnight cron)
├── scraper.py        HTTP scraper (requests + BeautifulSoup)
├── requirements.txt  Python dependencies
├── Dockerfile        Container definition
├── zeabur.json       Zeabur deployment config
├── .env.example      Environment variable template
└── README.md         This file
```

---

## Setup

### Step 1 — Create the Telegram bot

1. Open Telegram and message **[@BotFather](https://t.me/BotFather)**
2. Send `/newbot`
3. When prompted for a name, enter: `MikewNAC Bot`
4. When prompted for a username, enter: `MikewNACBot`
5. BotFather will reply with a **token** that looks like:
   ```
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
   Copy this — it's your `BOT_TOKEN`.

### Step 2 — Add the bot to your group

1. Open the Telegram group you want the bot to post in
2. Tap the group name → **Add Members** → search `@MikewNACBot` → Add
3. Make the bot an **admin** so it can send messages freely:
   - Tap the group name → **Edit** → **Administrators** → Add Administrator → select `@MikewNACBot`
   - Permissions needed: **Post Messages** only

### Step 3 — Get the Chat ID

The bot needs to know **which chat to auto-post to** on Friday nights.

**Option A — Using @userinfobot (easiest)**
1. Add **[@userinfobot](https://t.me/userinfobot)** to the group temporarily
2. It will print the group's numeric ID, e.g. `-1001234567890`
3. Remove @userinfobot from the group

**Option B — Using the Telegram API**
1. Send any message to the group
2. Visit in your browser (replace with your token):
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
3. Look for `"chat":{"id":` in the JSON — the number is your `CHAT_ID`

> Group IDs are **negative numbers** starting with `-100`, e.g. `-1001234567890`.
> Personal chat IDs are positive numbers.

### Step 4 — Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
BOT_TOKEN=7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
CHAT_ID=-1001234567890
```

---

## Running the Bot

### Option A — Run locally with Python

**Requirements:** Python 3.11+

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export BOT_TOKEN=your_token_here
export CHAT_ID=your_chat_id_here
# Or on Windows:
# set BOT_TOKEN=your_token_here
# set CHAT_ID=your_chat_id_here

# 4. Run the bot
python bot.py
```

You should see:
```
2026-03-23 20:00:00 | INFO | __main__ | Scheduler started — weekly post every Friday 20:00 SGT, daily post every midnight SGT
2026-03-23 20:00:00 | INFO | __main__ | Bot polling…
```

Test it by sending `/thisweek` or `/today` in the Telegram group.

**To stop:** Press `Ctrl+C`

---

### Option B — Run locally with Docker

**Requirements:** [Docker](https://docs.docker.com/get-docker/) installed

```bash
# 1. Build the image
docker build -t mikewinacbot .

# 2. Run with environment variables
docker run -d \
  --name mikewinacbot \
  --restart unless-stopped \
  -e BOT_TOKEN=your_token_here \
  -e CHAT_ID=your_chat_id_here \
  mikewinacbot
```

**Useful Docker commands:**
```bash
# Check it's running
docker ps

# View live logs
docker logs -f mikewinacbot

# Stop the bot
docker stop mikewinacbot

# Restart after code changes
docker stop mikewinacbot && docker rm mikewinacbot
docker build -t mikewinacbot . && docker run -d --name mikewinacbot --restart unless-stopped -e BOT_TOKEN=... -e CHAT_ID=... mikewinacbot
```

---

### Option C — Deploy to Zeabur (recommended for 24/7)

Zeabur is the simplest way to keep the bot running permanently in the cloud. It's the same platform used for the NASA APOD bot.

**Prerequisites:**
- GitHub account
- Zeabur account ([zeabur.com](https://zeabur.com)) — free tier works

**Steps:**

1. **Push code to GitHub**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   # Create a new repo on github.com, then:
   git remote add origin https://github.com/YOUR_USERNAME/mikewinacbot.git
   git push -u origin main
   ```

2. **Create a new Zeabur project**
   - Go to [dash.zeabur.com](https://dash.zeabur.com)
   - Click **New Project**
   - Click **Deploy New Service** → **GitHub**
   - Select your `mikewinacbot` repository
   - Zeabur auto-detects the `Dockerfile` and starts building

3. **Set environment variables**
   - In your Zeabur service, go to the **Variables** tab
   - Add:
     | Key | Value |
     |-----|-------|
     | `BOT_TOKEN` | Your BotFather token |
     | `CHAT_ID` | Your group chat ID |
   - Click **Redeploy** to apply

4. **Confirm it's running**
   - Check the **Logs** tab — you should see `Bot polling…`
   - Send `/thisweek` or `/today` in your Telegram group

**Updating the bot after code changes:**
```bash
git add .
git commit -m "Update scraper"
git push
```
Zeabur auto-redeploys on every push.

---

## How the Scraper Works

The NAC profile page loads all booking cards as **static HTML** — no JavaScript rendering needed. Each card has this structure:

```html
<div class="col-cuttor">
  <div class="dash-bx">
    <ul class="dash-bx-times">
      <li>Mon, 23 March</li>
      <li><span>10:00:AM - 11:00:AM</span></li>
      <li class="address">
        <a href="...">MRT STATION - CCL HARBOURFRONT</a>
      </li>
    </ul>
  </div>
</div>
```

The scraper:
1. **Fetches** the page with `requests`
2. **Parses** every `div.col-cuttor` card with `BeautifulSoup`
3. **Extracts** date, time range, and location from each card
4. **Consolidates** consecutive 1-hour slots at the same venue into a single block (e.g. two `10:00–11:00` + `11:00–12:00` slots become `10am–12pm`)
5. **Filters** to the requested Mon–Sun window
6. **Formats** into the Telegram message

> **Note on time format:** NAC uses `10:00:AM` (colon before AM/PM) rather than the standard `10:00 AM`. The scraper handles this correctly.

---

## Troubleshooting

**Bot doesn't respond to commands**
- Make sure the bot is an admin in the group
- Check that `BOT_TOKEN` is correct — no extra spaces
- View logs: `docker logs mikewinacbot`

**Auto-post not firing**
- The Friday post runs at 20:00 **SGT (UTC+8)** and the daily post runs at 00:00 **SGT**. Timezone is handled automatically by pytz.
- Verify the bot is still running: `docker ps` or check Zeabur logs

**"No upcoming bookings found"**
- The NAC page only shows bookings that have been confirmed. If Kew hasn't booked slots yet, the page will be empty for that period.
- You can verify by visiting the [NAC profile page](https://eservices.nac.gov.sg/Busking/busker/profile/dbc5b6bc-e22a-4e60-9fe4-f4d6a1aa17a4) directly.

**Scraper returns wrong week/day**
- `/thisweek` → current Mon–Sun
- `/nextweek` → following Mon–Sun
- `/today` → today only
- The Friday auto-post always sends **next week**; the midnight auto-post sends **today**

**NAC page structure changes**
- If NAC updates their website, the `col-cuttor` / `dash-bx-times` selectors in `scraper.py` may need updating
- Check the `_parse_html()` function in `scraper.py` and update the CSS selectors to match the new structure

---

## Dependencies

| Package | Version | Purpose |
|---|---|---|
| `python-telegram-bot` | 21.6 | Telegram Bot API wrapper |
| `apscheduler` | 3.10.4 | Friday + daily midnight cron scheduler |
| `requests` | 2.31.0 | HTTP fetch of NAC page |
| `beautifulsoup4` | 4.12.3 | HTML parsing |
| `pytz` | 2024.2 | SGT timezone handling |
