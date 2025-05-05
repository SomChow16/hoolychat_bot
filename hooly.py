import logging
import asyncio
import random
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler,
    MessageHandler, filters
)
from translation import translations
import datetime

# Set logging level
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load config
with open('token.json') as config_file:
    config = json.load(config_file)
    TOKEN = config['bot_token']

USER_DATA_FILE = 'user_data.json'
REPORTS_FILE = 'reports.json'
user_in_chat = {}
available_users = set()
user_data = {}

# Load user data from JSON
try:
    with open(USER_DATA_FILE, 'r') as f:
        user_data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    user_data = {}

# Load reports data from JSON
try:
    with open(REPORTS_FILE, 'r') as f:
        reports = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    reports = []

def save_user_data():
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=4)

def save_reports_data():
    with open(REPORTS_FILE, 'w') as f:
        json.dump(reports, f, indent=4)

def get_translation(chat_id, key, **kwargs):
    lang = user_data.get(str(chat_id), {}).get("language", "english").lower()
    return translations.get(lang, translations["english"]).get(key, key).format(**kwargs)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    username = update.effective_user.username or "Unknown"

    if str(chat_id) in user_data:
        await context.bot.send_message(chat_id=chat_id,
            text=get_translation(chat_id, "thanks", username=user_data[str(chat_id)]["username"], language=user_data[str(chat_id)]["language"]))
        user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}
        available_users.add(chat_id)
    else:
        keyboard = [["English"], ["Hindi"], ["Spanish"], ["French"], ["German"],
                    ["Chinese"], ["Japanese"], ["Arabic"], ["Russian"], ["Portuguese"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await context.bot.send_message(chat_id=chat_id,
            text=translations["english"]["welcome"],
            reply_markup=reply_markup)

async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    language = update.message.text.strip().lower()
    username = update.effective_user.username or "Unknown"

    if language in translations:
        user_data[str(chat_id)] = {
            'language': language,
            'username': username,
            'id': chat_id
        }
        save_user_data()

        user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}
        available_users.add(chat_id)

        await context.bot.send_message(chat_id=chat_id,
            text=get_translation(chat_id, "thanks", username=username, language=language))
    else:
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "invalid_language"))

async def queue_check(context: ContextTypes.DEFAULT_TYPE):
    ready_users = list(available_users - set(u for u in user_in_chat if user_in_chat[u].get('chatting')))
    random.shuffle(ready_users)
    while len(ready_users) >= 2:
        user1 = ready_users.pop()
        user2 = ready_users.pop()

        user_in_chat[user1]['chatting'] = True
        user_in_chat[user1]['partner_id'] = user2
        user_in_chat[user2]['chatting'] = True
        user_in_chat[user2]['partner_id'] = user1

        available_users.discard(user1)
        available_users.discard(user2)

        await context.bot.send_message(chat_id=user1, text=get_translation(user1, "found"))
        await context.bot.send_message(chat_id=user2, text=get_translation(user2, "found"))

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if user_in_chat.get(chat_id, {}).get('chatting', False):
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "already_in_chat"))
    else:
        available_users.add(chat_id)
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "looking"))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id in user_in_chat and user_in_chat[chat_id]['chatting']:
        partner_id = user_in_chat[chat_id]['partner_id']
        if partner_id in user_in_chat and user_in_chat[partner_id]['chatting']:
            message_content = update.message.text or update.message.caption
            if message_content:
                await context.bot.send_message(chat_id=partner_id, text=message_content)
            else:
                await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "text_only"))
        else:
            await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "partner_left"))
            user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}
            available_users.add(chat_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "not_in_chat"))

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if user_in_chat.get(chat_id, {}).get('chatting', False):
        partner_id = user_in_chat[chat_id]['partner_id']
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "chat_ended"))
        await context.bot.send_message(chat_id=partner_id, text=get_translation(partner_id, "partner_ended"))

        user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}
        user_in_chat[partner_id] = {'chatting': False, 'partner_id': None}
        available_users.add(chat_id)
        available_users.add(partner_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "not_in_chat"))

async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if user_in_chat.get(chat_id, {}).get('chatting', False):
        partner_id = user_in_chat[chat_id]['partner_id']
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "looking_new"))
        await context.bot.send_message(chat_id=partner_id, text=get_translation(partner_id, "partner_left_new"))

        user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}
        user_in_chat[partner_id] = {'chatting': False, 'partner_id': None}
        available_users.add(chat_id)
        available_users.add(partner_id)
        await start_chat(update, context)
    else:
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "not_in_chat"))

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "media_not_allowed"))

async def handle_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id,
        text=get_translation(update.effective_chat.id, "not_in_chat"))

# Add the report command
async def report_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in user_in_chat or not user_in_chat[chat_id].get("chatting"):
        await context.bot.send_message(chat_id=chat_id, text=get_translation(chat_id, "not_in_chat"))
        return

    partner_id = user_in_chat[chat_id]["partner_id"]

    report_entry = {
        "reporter_id": chat_id,
        "reported_id": partner_id,
        "timestamp": datetime.datetime.now().isoformat()
    }

    try:
        with open(REPORTS_FILE, "r") as f:
            reports = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        reports = []

    reports.append(report_entry)
    save_reports_data()

    await context.bot.send_message(chat_id=chat_id, text="User has been reported. Thank you.")
    await context.bot.send_message(chat_id=partner_id, text="You have been reported. The chat is now ended.")

    # End chat for both users
    user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}
    user_in_chat[partner_id] = {'chatting': False, 'partner_id': None}
    available_users.add(chat_id)
    available_users.add(partner_id)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('start_chat', start_chat))
    app.add_handler(CommandHandler('stop_chat', stop_chat))
    app.add_handler(CommandHandler('next', next_chat))
    app.add_handler(CommandHandler('report', report_user))

    # Media Block
    app.add_handler(MessageHandler(
        filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL,
        handle_media
    ))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language_selection))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(queue_check, interval=10, first=0)
    app.add_error_handler(handle_errors)
    app.run_polling()
