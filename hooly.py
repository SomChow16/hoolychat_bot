import logging
import asyncio
import random
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters , JobQueue

# Set logging level
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
 
import json

with open('token.json') as config_file:
    config = json.load(config_file)
    TOKEN = config['bot_token']

# User state variable
user_in_chat = {}  # Dictionary to track user chat status (True/False) and partner ID
available_users = set()  # Set to store chat-ready users


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id,
                                   text="Welcome to HoolyBot! Let's explore the world together and discover Diversity. Type /start_chat to find a chat partner.")
    user_in_chat[chat_id] = {'chatting': False, 'partner_id': None}  # Set user's chat status and partner ID
    available_users.add(chat_id)  # Add user to available list

async def queue_check(context: ContextTypes.DEFAULT_TYPE):
    while True:
        if len(available_users) > 1:
            # Randomly select two users from the available list
            user_ids = random.sample(available_users, 2)
            user1_id, user2_id = user_ids

            # Inform both users that they are now connected
            await context.bot.send_message(chat_id=user1_id,
                                           text=f"Found a chat partner! Say hi to your new friend. Press /stop_chat to terminate the session.")
            await context.bot.send_message(chat_id=user2_id,
                                           text=f"Found a chat partner! Say hi to your new friend. Press /stop_chat to terminate the session.")

            # Update user statuses and partner IDs
            user_in_chat[user1_id]['chatting'] = True
            user_in_chat[user1_id]['partner_id'] = user2_id
            user_in_chat[user2_id]['chatting'] = True
            user_in_chat[user2_id]['partner_id'] = user1_id

            available_users.remove(user1_id)
            available_users.remove(user2_id)
        else:
            # Send messages to users in the queue who haven't been paired yet
            for  user_id in available_users:
                if not user_in_chat[user_id]['chatting']:
                    await context.bot.send_message(chat_id=user_id,
                                                   text="Finding an interesting person for you. It may take a while, please wait patiently...")
                    await asyncio.sleep(5)
                    await context.bot.send_message(chat_id=user_id,
                                                    text="Till then, please kindly share this bot with your friends. You know our bot depends entirely on people like you.")
                    await asyncio.sleep(5)
                    await context.bot.send_message(chat_id=user_id,
                                                   text="Do you want some best conversational tips? Stay tuned with us until you get connected to someone...")
                    await asyncio.sleep(5)
                    await context.bot.send_message(chat_id=user_id,
                                                   text="Never ask 'How are you', instead ask 'How's your day?'. Want more conversational facts? Stay tuned...")
                    await asyncio.sleep(8)
                    await context.bot.send_message(chat_id=user_id, text="STILL SEARCHING...")


        await asyncio.sleep(60)  # Check the queue every 60 seconds


async def handle_errors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="You first need to type /start to begin. ")

async def start_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in user_in_chat and user_in_chat[chat_id]['chatting']:  # Check if user is already in a chat
        await context.bot.send_message(chat_id=chat_id, text="You are already in a chat session. Use /stop_chat or /next to end the current session.")
    else:
        # Remove the user from available_users if they were previously added
        available_users.discard(chat_id)
        
        # Check if there are other available users
        potential_partners = list(available_users - {chat_id})
        
        if potential_partners:
            # Randomly select another available user
            partner_id = random.choice(potential_partners)

            # Send messages to both users to initiate chat
            await context.bot.send_message(chat_id=chat_id,
                                           text=f"Found a chat partner! Say hi to your new friend. Press /stop_chat to terminate the session.")
            await context.bot.send_message(chat_id=partner_id,
                                           text=f"Found a chat partner! Say hi to your new friend. Press /stop_chat to terminate the session.")

            # Update user statuses and partner IDs
            user_in_chat[chat_id] = {'chatting': True, 'partner_id': partner_id}
            user_in_chat[partner_id] = {'chatting': True, 'partner_id': chat_id}
            available_users.remove(chat_id)
            available_users.remove(partner_id)
        else:
            # Add user back to the available users list if no partners were found
            available_users.add(chat_id)
            await context.bot.send_message(chat_id=chat_id, text="No available users at the moment. Please wait...")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if chat_id in user_in_chat and user_in_chat[chat_id]['chatting']:
        partner_id = user_in_chat[chat_id]['partner_id']

        # Ensure the partner is also still in the chat session
        if partner_id in user_in_chat and user_in_chat[partner_id]['chatting']:
            message = update.message

            message_content = message.text if message.text else message.caption  # Check for text or caption
            if message_content:
                await context.bot.send_message(chat_id=partner_id, text=message_content)
            else:
                # Inform user about unsupported content (GIFs, stickers, etc.)
                unsupported_message_reply = (
                    "Hi there! \n"
                    "For a safe and positive environment, we currently only allow forwarding text messages within the chat. \n"
                    "This helps prevent the spread of potential misinformation or inappropriate content like offensive images or videos. \n"
                    "If you'd like to share a picture, video, or GIF, send it directly to your chat partner in their private messages (DMs). \n"
                    "Thanks for your understanding!"
                )
                await context.bot.send_message(chat_id=chat_id, text=unsupported_message_reply)
        else:
            await context.bot.send_message(chat_id=chat_id,
                                           text="Your chat partner has ended the session. Use /start_chat to find a new partner.")
            user_in_chat[chat_id]['chatting'] = False
            user_in_chat[chat_id]['partner_id'] = None
            available_users.add(chat_id)
    else:
        await context.bot.send_message(chat_id=chat_id,
                                       text="You are not currently in a chat session. Use /start_chat to find a partner.")

async def stop_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if user_in_chat[chat_id]['chatting']:
        partner_id = user_in_chat[chat_id]['partner_id']

        # Send messages to both users informing about ending chat
        await context.bot.send_message(chat_id=chat_id, text="Chat session ended.")
        await context.bot.send_message(chat_id=partner_id, text="Your chat partner has ended the session.")

        # Reset chat status and partner ID for both users
        user_in_chat[chat_id]['chatting'] = False
        user_in_chat[chat_id]['partner_id'] = None
        user_in_chat[partner_id]['chatting'] = False
        user_in_chat[partner_id]['partner_id'] = None

        # Remove users from the user_in_chat dictionary
        del user_in_chat[chat_id]
        del user_in_chat[partner_id]

        # Add users back to available list
        available_users.add(chat_id)
        available_users.add(partner_id)
    else:
        await context.bot.send_message(chat_id=chat_id, text="You are not currently in a chat session.")


async def next_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if user_in_chat[chat_id]['chatting']:
        partner_id = user_in_chat[chat_id]['partner_id']

        # Inform both users that the chat session has ended
        await context.bot.send_message(chat_id=chat_id, text="You have ended the chat session. Finding you a new partner...")
        await context.bot.send_message(chat_id=partner_id, text="Your chat partner has ended the session. Finding you a new partner...")

        # Reset chat status and partner ID for both users
        user_in_chat[chat_id]['chatting'] = False
        user_in_chat[chat_id]['partner_id'] = None
        user_in_chat[partner_id]['chatting'] = False
        user_in_chat[partner_id]['partner_id'] = None

        # Add users back to available list
        available_users.add(chat_id)
        available_users.add(partner_id)
        
        # Automatically start a new chat for the user who initiated /next
        await start_chat(update, context)
    else:
        await context.bot.send_message(chat_id=chat_id, text="You are not currently in a chat session. Use /start_chat to find a partner.")

# Main function and application setup
if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()

    start_handler = CommandHandler('start', start)
    start_chat_handler = CommandHandler('start_chat', start_chat)
    stop_chat_handler = CommandHandler('stop_chat', stop_chat)
    next_chat_handler = CommandHandler('next', next_chat)

    #message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message 
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)

    application.add_handler(message_handler)
     

     # Start queue check task in the background
    job_queue = application.job_queue
    application.job_queue.run_repeating(queue_check, interval=60, first=0)

    #application.add_handler(message_handler)
    
    application.add_handler(start_handler)
    application.add_handler(start_chat_handler)
    application.add_handler(stop_chat_handler)
    application.add_handler(next_chat_handler)   
    application.add_error_handler(handle_errors)

    application.run_polling()
