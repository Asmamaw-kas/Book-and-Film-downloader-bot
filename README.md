# 🎬 YoungMovies Premium Bot

A Telegram bot for managing premium access to YoungMovies content channels.

---

## Features

| Step | Description |
|------|-------------|
| 1 | User starts bot → sees welcome video preview |
| 2 | Taps **Continue** → sees Basic & VIP plan options |
| 3 | Selects a plan → sees Telebirr & CBE payment details (copyable) |
| 4 | Pays & taps **I Paid** → receives private channel join link |
| 5 | Admin gets notified (name, username, Telegram ID, plan) |
| 6 | Admin verifies payment → taps **Approved** → user gets confirmation |

### Plans
| Plan | Price | Access |
|------|-------|--------|
| 🔵 Basic | 499 Birr/month | Basic Young Movies private channel |
| 👑 VIP | 999 Birr/month | VIP videos + Dating Mini App inside the channel |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure `.env`

Edit `.env` and fill in:

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | From [@BotFather](https://t.me/BotFather) |
| `ADMIN_ID` | Your numeric Telegram ID (get it from [@userinfobot](https://t.me/userinfobot)) |
| `TELEBIRR_NAME` | TeleBirr account holder name |
| `TELEBIRR_ACCOUNT` | TeleBirr phone number |
| `CBE_NAME` | CBE account holder name |
| `CBE_ACCOUNT` | CBE account number |
| `BASIC_CHANNEL_LINK` | Invite link for Basic private channel |
| `VIP_CHANNEL_LINK` | Invite link for VIP private channel |
| `WELCOME_VIDEO_FILE_ID` | See step 3 below |
| `DB_PATH` | SQLite database file path (default: `bot.sqlite3`) |

### 3. Upload your welcome video

1. Start your bot and send it the welcome video in a private chat.
2. Reply to that video message with `/upload_video`.
3. The bot will respond with the `file_id` — copy it into `WELCOME_VIDEO_FILE_ID` in `.env`.
4. Restart the bot.

### 4. Create private channels & invite links

1. Create two **private** Telegram channels (Basic & VIP).
2. Add your bot as an **admin** with *Invite Users* permission.
3. Go to **Manage Channel → Invite Links** and create a permanent invite link for each.
4. Paste the links into `.env` as `BASIC_CHANNEL_LINK` and `VIP_CHANNEL_LINK`.

### 5. Run the bot

```bash
python bot.py
```

---

## Admin Commands

| Command | Description |
|---------|-------------|
| `/stats` | View total pending / approved / plan breakdown |
| `/pending` | List the latest 20 pending payment requests |
| `/upload_video` | Reply to a video to get its `file_id` for the welcome screen |

---

## How Approval Works

1. User taps **I Paid** → bot saves the request to SQLite and sends a notification to the admin.
2. Admin sees the message with the user's name, Telegram ID, username, and plan.
3. Admin verifies the payment in their banking app.
4. Admin taps **✅ Approved — Notify User** inside Telegram.
5. Bot sends the user a confirmation message with the channel join link.
6. User clicks the link → requests to join → admin approves them inside the channel.

> The bot sends the join link immediately after "I Paid" so users can request to join right away. The admin approval step inside the channel is the final gate.

---

## Project Structure

```
telegram-bot/
├── bot.py            # Main bot code
├── .env              # Configuration (never commit this)
├── requirements.txt  # Python dependencies
├── bot.sqlite3       # Auto-created SQLite database
└── README.md         # This file
```

---

## Tech Stack

- **python-telegram-bot** v21 — async bot framework
- **python-dotenv** — environment config
- **SQLite** — lightweight payment tracking (no external DB needed)
