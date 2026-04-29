# ─────────────────────────────────────────────
# CONFIGURATION — fill these in before running
# ─────────────────────────────────────────────

# Your bot token from @BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# The chat_id of your Telegram group (negative number, e.g. -1001234567890)
GROUP_ID = -1001234567890

# Map each floor name → its topic's message_thread_id
# To find a thread ID: send a message in the topic, right-click → Copy Link
# The number after the last `/` is the thread ID
FLOOR_TOPICS = {
    "Level 1": 123,
    "Level 2": 456,
    "Level 3": 789,
    "Level 4": 101,
}

# Your local timezone offset from UTC, in hours
# Malaysia (MYT) = UTC+8, so set this to 8
LOCAL_UTC_OFFSET = 8