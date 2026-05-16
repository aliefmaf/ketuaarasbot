# 🏢 Ketua Aras Telegram Bot

A Telegram bot for block heads to manage floor inspection reports from floor representatives. Reps submit twice-daily reports (morning & night) via a guided conversation, which are automatically forwarded to the correct floor topic in a Telegram group.

---

## Features

- Guided conversation flow: name → floor → photo → cleanliness rating → notes
- Two daily shifts: morning (6am–6pm) and night (6pm–1am)
- Remembers each rep's name and floor after first submission
- Automatically routes reports to the correct Telegram group topic
- Hourly reminders starting at 12pm (morning) and 10pm (night) for pending submissions
- Prevents duplicate submissions per shift

---

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- A Telegram group with **Topics enabled** and the bot added as **admin**

---

## Setup

### 1. Clone the repo
```bash
git clone https://github.com/yourusername/ketuaarasbot.git
cd ketuaarasbot
```

### 2. Rename `.env.example` to `.env` file
Then fill in the values:
```
BOT_TOKEN=your_token_here
GROUP_ID=-1001234567890
LOCAL_UTC_OFFSET=8
```

### 3. Configure your floors
In `config.py`, map each floor name to its Telegram topic thread ID:
```python
FLOOR_TOPICS = {
    "A100": 3,
    "A200": 4,
}
```
To find a thread ID: open the topic in Telegram Web, the number after the last `/` in the URL is the thread ID.

### 4. Create the data file
Run this in the terminal in the current directory
```bash
mkdir -p data           # create the folder first
echo '{"users": {}}' > data/data.json   # then create the file
```

### 5a. Run with Docker
```bash
docker-compose up -d --build
```

### 5b. Running Locally (without Docker)

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
python bot.py
```

---

## Project Structure

```
ketuaarasbot/
├── bot.py              # Main bot logic and conversation handler
├── config.py           # Configuration (token, group ID, floor topics)
├── storage.py          # JSON-based persistence layer
├── data/
│   └── data.json       # User profiles and submission records (not committed)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## How It Works

**Submission flow:**
1. Rep sends `/start` to the bot privately
2. Bot detects the current shift (morning/night) based on local time
3. If the rep has already submitted for that shift, they are blocked
4. If the rep is returning, name and floor are pre-filled — they go straight to the photo step
5. After all steps, the bot sends a formatted report with photo to the correct group topic

**Reminder system:**
- Morning reminders fire every hour from 12pm until 6pm for reps who haven't submitted
- Night reminders fire every hour from 10pm until 1am
- Reminders are sent as private DMs — reps must have started the bot at least once

**Data storage:**
- User profiles and submission records are stored in `data/data.json`
- Submissions are tracked per shift per day, keyed by local date
- The `data/` folder is mounted as a Docker volume so data persists across container restarts

---

## Updating

After making changes on your machine:

```bash
docker build -t yourusername/ketuaarasbot .
docker push yourusername/ketuaarasbot
```

On your server:
```bash
docker-compose pull
docker-compose up -d
```

---

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `BOT_TOKEN` | Telegram bot token from @BotFather | `123456:ABC-DEF...` |
| `GROUP_ID` | Telegram group chat ID (negative number) | `-1001234567890` |
| `LOCAL_UTC_OFFSET` | Your timezone offset from UTC | `8` (Malaysia) |