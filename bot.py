import logging
from datetime import date, datetime, time, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from config import BOT_TOKEN, GROUP_ID, FLOOR_TOPICS, LOCAL_UTC_OFFSET
from storage import load_data, save_submission


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# Conversation states
NAME, FLOOR, PHOTO, RATING, NOTES = range(5)

# Shift windows (local time, 24h)
MORNING_START = 12   # Reminders start at 12pm
MORNING_END   = 18   # 6pm — end of morning shift
NIGHT_START   = 22   # Reminders start at 10pm
NIGHT_END_H   = 1    # 1am

LOCAL_TZ = timezone(timedelta(hours=LOCAL_UTC_OFFSET))


def local_now() -> datetime:
    return datetime.now(tz=LOCAL_TZ)


def current_shift() -> str | None:
    """Return 'morning' or 'night' based on local time, or None if between shifts."""
    hour = local_now().hour
    if 6 <= hour < 18:
        return "morning"
    if hour >= 18:
        return "night"


def has_submitted_shift(user_info: dict, shift: str) -> bool:
    today = date.today().isoformat()
    return user_info.get("submissions", {}).get(today, {}).get(shift, False)


# ── Conversation Handlers ──────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()

    if user_id not in data["users"]:
        data["users"][user_id] = {"name": None, "submissions": {}}
        save_submission(data)

    shift = current_shift()

    if shift and has_submitted_shift(data["users"][user_id], shift):
        await update.message.reply_text(
            f"✅ You've already submitted your *{shift}* report today!\n\n"
            "Come back for the next shift.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    shift_label = (
        "🌤 Morning shift" if shift == "morning"
        else "🌙 Night shift" if shift == "night"
        else "📋 Report"
    )
    context.user_data["shift"] = shift or "manual"

    await update.message.reply_text(
        f"👋 Welcome! Filing: *{shift_label}*\n\nWhat is your *name*?",
        parse_mode="Markdown"
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    keyboard = [
        [InlineKeyboardButton(floor, callback_data=floor)]
        for floor in FLOOR_TOPICS.keys()
    ]
    await update.message.reply_text(
        "Which *floor* are you representing?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return FLOOR


async def get_floor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["floor"] = query.data
    await query.edit_message_text(f"Floor *{query.data}* selected ✅", parse_mode="Markdown")
    await query.message.reply_text("📸 Please send a *photo* of the corridor.", parse_mode="Markdown")
    return PHOTO


async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["photo_file_id"] = update.message.photo[-1].file_id
    keyboard = [[
        InlineKeyboardButton("1 ⭐", callback_data="1"),
        InlineKeyboardButton("2 ⭐", callback_data="2"),
        InlineKeyboardButton("3 ⭐", callback_data="3"),
        InlineKeyboardButton("4 ⭐", callback_data="4"),
        InlineKeyboardButton("5 ⭐", callback_data="5"),
    ]]
    await update.message.reply_text(
        "How would you rate the *corridor cleanliness*? (1–5)",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return RATING


async def get_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["rating"] = int(query.data)
    stars = "⭐" * int(query.data)
    await query.edit_message_text(f"Rating: {stars} ({query.data}/5)")
    await query.message.reply_text(
        "Any additional notes? (smell, issues, anything else)\n\nType your notes or send /skip to skip."
    )
    return NOTES


async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["notes"] = update.message.text
    await finalize_report(update, context)
    return ConversationHandler.END


async def skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["notes"] = "_No additional notes._"
    await finalize_report(update, context)
    return ConversationHandler.END


async def finalize_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    floor = ud["floor"]
    shift = ud["shift"]
    thread_id = FLOOR_TOPICS[floor]
    stars = "⭐" * ud["rating"]
    shift_emoji = "🌤" if shift == "morning" else "🌙"

    caption = (
        f"📋 *Floor Report — {floor}*\n\n"
        f"{shift_emoji} Shift: {shift.capitalize()}\n"
        f"👤 Rep: {ud['name']}\n"
        f"📅 Date: {date.today().strftime('%d %B %Y')}\n"
        f"🏆 Corridor Rating: {stars} ({ud['rating']}/5)\n"
        f"📝 Notes: {ud['notes']}"
    )

    await context.bot.send_photo(
        chat_id=GROUP_ID,
        message_thread_id=thread_id,
        photo=ud["photo_file_id"],
        caption=caption,
        parse_mode="Markdown"
    )

    data = load_data()
    user_id = str(update.effective_user.id)
    today = date.today().isoformat()
    data["users"][user_id]["name"] = ud["name"]
    data["users"][user_id].setdefault("submissions", {}).setdefault(today, {})[shift] = True
    save_submission(data)

    await update.message.reply_text("✅ Report submitted successfully! Thank you.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Report cancelled. Send /start to begin again.")
    return ConversationHandler.END


# ── Reminder Jobs ──────────────────────────────────────────────────────────────

async def remind_morning(context: ContextTypes.DEFAULT_TYPE):
    hour = local_now().hour
    # Bail if outside morning window
    if not (MORNING_START <= hour < MORNING_END):
        return

    today = date.today().isoformat()
    data = load_data()

    for user_id, info in data["users"].items():
        if not has_submitted_shift(info, "morning"):
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        "⏰ *🌤 Morning Shift Reminder*\n\n"
                        "You haven't submitted your *morning* floor report yet.\n"
                        "Please send /start to fill it in now."
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Could not remind user {user_id}: {e}")


async def remind_night(context: ContextTypes.DEFAULT_TYPE):
    hour = local_now().hour
    # Bail if outside night window (10pm–1am)
    if not (hour >= NIGHT_START or hour < NIGHT_END_H):
        return

    today = date.today().isoformat()
    data = load_data()

    for user_id, info in data["users"].items():
        if not has_submitted_shift(info, "night"):
            try:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=(
                        "⏰ *🌙 Night Shift Reminder*\n\n"
                        "You haven't submitted your *night* floor report yet.\n"
                        "Please send /start to fill it in now."
                    ),
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.warning(f"Could not remind user {user_id}: {e}")


# ── Helpers ────────────────────────────────────────────────────────────────────

def local_to_utc_time(local_hour: int, local_minute: int = 0) -> time:
    """Convert local wall-clock hour to a UTC time object for job scheduling."""
    utc_hour = (local_hour - LOCAL_UTC_OFFSET) % 24
    return time(hour=utc_hour, minute=local_minute, tzinfo=timezone.utc)


# ── App Entry ──────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            FLOOR:  [CallbackQueryHandler(get_floor)],
            PHOTO:  [MessageHandler(filters.PHOTO, get_photo)],
            RATING: [CallbackQueryHandler(get_rating)],
            NOTES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_notes),
                CommandHandler("skip", skip_notes),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_handler)

    jq = app.job_queue

    # Morning reminders: first fires at 12:00pm local, then every 1 hour
    # The window guard inside remind_morning stops it after 6pm
    jq.run_repeating(
        remind_morning,
        interval=3600,  # 1 hour
        first=local_to_utc_time(MORNING_START, 0),
    )

    # Night reminders: first fires at 10:00pm local, then every 30 min
    # The window guard inside remind_night stops it after 1am
    jq.run_repeating(
        remind_night,
        interval=1800,
        first=local_to_utc_time(NIGHT_START, 0),
    )

    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()