import logging
import asyncio
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
import json

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
with open('token.json') as config_file:
    config = json.load(config_file)
    TOKEN = config['bot_token']

user_in_chat = {}
available_users = set()
send_semaphore = asyncio.Semaphore(10)

async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="Welcome to HoolyBot! Type /start_chat to find a chat partner.")
    user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}
    available_users.add(chat_id)

async def queue_check(context: CallbackContext):
    while True:
        await asyncio.sleep(10)
        if len(available_users) > 1:
            await pair_users(context)

async def pair_users(context):
    user_ids = random.sample(available_users, 2)
    user1_id, user2_id = user_ids
    async with send_semaphore:
        await context.bot.send_message(user1_id, "Found a chat partner! Press /stop_chat to terminate.")
        await context.bot.send_message(user2_id, "Found a chat partner! Press /stop_chat to terminate.")
    user_in_chat[user1_id] = {'chatting': True, 'partner_id': user2_id}
    user_in_chat[user2_id] = {'chatting': True, 'partner_id': user1_id}
    available_users.discard(user1_id)
    available_users.discard(user2_id)

async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if chat_id in user_in_chat and user_in_chat[chat_id]['chatting']:
        partner_id = user_in_chat[chat_id]['partner_id']
        if partner_id in user_in_chat and user_in_chat[partner_id]['chatting']:
            message_text = update.message.text
            if message_text:
                await context.bot.send_message(chat_id=partner_id, text=message_text)
        else:
            await context.bot.send_message(chat_id=chat_id, text="Your chat partner has ended the session. Use /start_chat to find a new partner.")
            user_in_chat[chat_id]['chatting'] = False
            user_in_chat[chat_id]['partner_id'] = None
            available_users.add(chat_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text="You are not currently in a chat session. Use /start_chat to find a partner.")

async def handle_errors(update: Update, context: CallbackContext):
    """Log the error and send a message to the user."""
    logging.error(f"An error occurred: {context.error}")
    try:
        # Attempt to send an error message to the user
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Sorry, an unexpected error occurred. Please try again later.")
    except Exception as e:
        # This is to handle cases where the error might prevent a message from being sent
        logging.error(f"An error occurred while handling another error: {e}")

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(handle_errors)
    job_queue = application.job_queue
    job_queue.run_repeating(queue_check, interval=10, first=0)
    application.run_polling()
