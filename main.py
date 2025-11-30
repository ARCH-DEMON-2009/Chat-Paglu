import os
import logging
import asyncio
import random
import time
import json
import sys
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, JobQueue

# Load environment variables from .env file if it exists
load_dotenv()
from ai_chat import (
    get_ai_response, get_group_response, add_to_group_history,
    clear_conversation, clear_group_conversation, clear_all_data,
    is_dirty_message, get_dirty_response, get_sticker_for_mood,
    is_abuse_message, get_abuse_response, is_advice_message,
    save_user_preference, get_custom_abuse_response, get_stats, get_lover_response,
    conversation_history, get_random_joke, get_random_quote, get_daily_tip,
    get_random_compliment, get_random_fortune, get_random_dare, get_random_truth
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask app for Render Web Service
app = Flask(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ADMIN_USERNAME = "CoffinWifi"
ADMIN_DATA_FILE = "admin_data.json"
BOT_DATA_FILE = "bot_data.json"

BOT_START_TIME = time.time()

dirty_talk_permissions = {}
pending_permissions = {}
admin_chat_id = None
admin_ids = set()
blocked_users = {}
muted_users = {}
abuse_targets = {}
lover_targets = {}
user_chat_history = {}
username_to_id = {}
blocked_naughty_users = {}
bot_enabled = True
group_auto_reply = True
tracked_groups = set()  # Track group/channel IDs for broadcasting

GENTLE_REJECTION_MESSAGES = [
    "Hey! Aise baatein nahi karte na. 🥺",
    "Nahi, please. Mujhe yeh bilkul pasand nahi hai. 🥺",
    "Bas ab, yeh sab nahi okay? 😔",
    "Pleaseee, let's talk about something nice? 🥺💕",
    "Arre nahi! Meri dignity ka khayal rakh~ 🙈",
]

RUDE_REJECTION_MESSAGES = [
    "Tum kaun ho? Main sirf apne admin ke orders follow karti hoon! 🙅‍♀️",
    "Arre! Tum mera admin nahi ho. Main aapke orders nahi manunga! 😏",
    "LOL, no. You're not my admin. Shoo! 🚫",
    "Nice try! But you're not the boss of me, sorry! 😤",
    "Admin? Nahi nahi! Only @CoffinWifi is my admin! 💪",
]


def resolve_user_id(identifier: str) -> str:
    identifier = identifier.replace("@", "").strip().lower()
    if identifier.isdigit():
        return identifier
    if identifier in username_to_id:
        return str(username_to_id[identifier])
    return None


async def keep_alive_job(context: ContextTypes.DEFAULT_TYPE):
    """Send keep-alive message to admin chat every 10 mins to keep Render (15min timeout) & PythonAnywhere awake"""
    global admin_chat_id
    if admin_chat_id:
        try:
            current_time = time.strftime("%H:%M:%S", time.localtime())
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=f"💫 Auto keep-alive check [{current_time}] - Naina is alive! 💕"
            )
            logger.info(f"✅ Keep-alive message sent to admin at {current_time}")
        except Exception as e:
            logger.error(f"Failed to send keep-alive: {e}")


def add_username_mapping(user_id: int, username: str):
    if username:
        username_to_id[username.lower()] = str(user_id)


def load_admin_data():
    global admin_chat_id, admin_ids, blocked_users, muted_users, abuse_targets, lover_targets, blocked_naughty_users, bot_enabled, group_auto_reply, tracked_groups
    try:
        if os.path.exists(ADMIN_DATA_FILE):
            with open(ADMIN_DATA_FILE, 'r') as f:
                data = json.load(f)
                admin_chat_id = data.get('admin_chat_id')
                tracked_groups = set(data.get('tracked_groups', []))
                admin_ids = set(data.get('admin_ids', []))
                blocked_users = data.get('blocked_users', {})
                muted_users = data.get('muted_users', {})
                abuse_targets = data.get('abuse_targets', {})
                lover_targets = data.get('lover_targets', {})
                blocked_naughty_users = data.get('blocked_naughty_users', {})
                bot_enabled = data.get('bot_enabled', True)
                group_auto_reply = data.get('group_auto_reply', True)
                logger.info(f"Loaded admin data. Admin chat ID: {admin_chat_id}, Admin IDs: {admin_ids}")
    except Exception as e:
        logger.error(f"Error loading admin data: {e}")


def save_admin_data():
    try:
        with open(ADMIN_DATA_FILE, 'w') as f:
            json.dump({
                'admin_chat_id': admin_chat_id,
                'admin_ids': list(admin_ids),
                'blocked_users': blocked_users,
                'muted_users': muted_users,
                'abuse_targets': abuse_targets,
                'lover_targets': lover_targets,
                'blocked_naughty_users': blocked_naughty_users,
                'bot_enabled': bot_enabled,
                'group_auto_reply': group_auto_reply,
                'tracked_groups': list(tracked_groups)
            }, f)
    except Exception as e:
        logger.error(f"Error saving admin data: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_chat_id, admin_ids
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    add_username_mapping(user_id, update.effective_user.username)
    
    if update.effective_chat.type == "private":
        if not admin_chat_id:
            admin_chat_id = user_id
            admin_ids.add(str(user_id))
            save_admin_data()
            await update.message.reply_text("💕 Heyy! I'm Naina, your personal AI girlfriend! 🌹\n\n"
                                          "I'm here to chat, joke around, give advice, and keep you company! 😊\n\n"
                                          "📝 Use /help to see all my commands!\n"
                                          "You're my admin now! 👑")
        else:
            user_id_str = str(user_id)
            if user_id_str not in conversation_history:
                conversation_history[user_id_str] = []
            
            await update.message.reply_text("Hi babe! 💕 Welcome back!\n\nUse /help to see what I can do for you!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_enabled:
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username
    chat_id = update.effective_chat.id
    message_text = update.message.text
    
    add_username_mapping(user_id, username)
    
    user_id_str = str(user_id)
    chat_id_str = str(chat_id)
    
    # Track group/channel
    if update.effective_chat.type in ["group", "supergroup", "channel"]:
        tracked_groups.add(chat_id_str)
        save_admin_data()
        
        if not group_auto_reply or user_id_str in muted_users or user_id in blocked_users:
            return
        
        if is_abuse_message(message_text):
            response = get_custom_abuse_response(user_id_str, message_text, "hindi")
            await context.bot.send_message(chat_id=chat_id, text=response)
            return
        
        response = get_group_response(user_id_str, message_text)
        add_to_group_history(user_id_str, message_text, response)
        await context.bot.send_message(chat_id=chat_id, text=response)
    else:
        # Private chat
        if user_id_str in blocked_users or user_id_str in muted_users:
            return
        
        if user_id_str not in conversation_history:
            conversation_history[user_id_str] = []
        
        if is_abuse_message(message_text):
            response = get_custom_abuse_response(user_id_str, message_text, "hindi")
            await context.bot.send_message(chat_id=chat_id, text=response)
            return
        
        if is_advice_message(message_text):
            save_user_preference(user_id_str, message_text)
        
        if user_id_str in lover_targets:
            response = get_lover_response(user_id_str, message_text)
        elif user_id_str in dirty_talk_permissions:
            response = get_dirty_response(user_id_str, message_text)
        else:
            response = get_ai_response(user_id_str, message_text)
        
        conversation_history[user_id_str].append({"role": "user", "content": message_text})
        conversation_history[user_id_str].append({"role": "assistant", "content": response})
        
        await context.bot.send_message(chat_id=chat_id, text=response)


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if update.effective_chat.type == "private":
        if user_id not in conversation_history:
            conversation_history[user_id] = []
        
        mood = get_sticker_for_mood("happy")
        await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=mood)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    keyboard = [
        [InlineKeyboardButton("🚫 Block User", callback_data="admin_block")],
        [InlineKeyboardButton("🔇 Mute User", callback_data="admin_mute")],
        [InlineKeyboardButton("😈 Abuse Target", callback_data="admin_abuse")],
        [InlineKeyboardButton("❤️ Add Lover", callback_data="admin_lover")],
        [InlineKeyboardButton("👗 Dirty Talk", callback_data="admin_dirty")],
        [InlineKeyboardButton("📊 Status", callback_data="admin_status")],
        [InlineKeyboardButton("🔄 Reset", callback_data="admin_reset")],
        [InlineKeyboardButton("🔌 Stop/Resume", callback_data="admin_stop")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👑 **ADMIN CONTROL PANEL** 👑\n\nChoose an option:", reply_markup=reply_markup)


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    uptime = time.time() - BOT_START_TIME
    uptime_hours = int(uptime // 3600)
    uptime_mins = int((uptime % 3600) // 60)
    
    stats = get_stats()
    
    status_msg = f"""
🤖 **BOT STATUS**
✅ Status: {'Active' if bot_enabled else 'Inactive'}
⏰ Uptime: {uptime_hours}h {uptime_mins}m
👥 Total Users: {len(conversation_history)}
📊 Stats: {stats}
"""
    await update.message.reply_text(status_msg)


async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    bot_enabled = False
    save_admin_data()
    await update.message.reply_text("🔌 Bot disabled! Use /resume to turn it back on.")


async def resume_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    bot_enabled = True
    save_admin_data()
    await update.message.reply_text("✅ Bot is back online! 💕")


async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /block @username or /block user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    blocked_users[target] = True
    save_admin_data()
    await update.message.reply_text(f"✅ User {target} blocked!")


async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unblock @username or /unblock user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    blocked_users.pop(target, None)
    save_admin_data()
    await update.message.reply_text(f"✅ User {target} unblocked!")


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /mute @username or /mute user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    muted_users[target] = True
    save_admin_data()
    await update.message.reply_text(f"🔇 User {target} muted!")


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unmute @username or /unmute user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    muted_users.pop(target, None)
    save_admin_data()
    await update.message.reply_text(f"✅ User {target} unmuted!")


async def abuse_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /abuse @username or /abuse user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    abuse_targets[target] = True
    save_admin_data()
    await update.message.reply_text(f"😈 User {target} is now a gaali target!")


async def unabuse_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unabuse @username or /unabuse user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    abuse_targets.pop(target, None)
    save_admin_data()
    await update.message.reply_text(f"✅ User {target} removed from abuse list!")


async def reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global conversation_history, dirty_talk_permissions, pending_permissions, blocked_users, muted_users, abuse_targets, lover_targets, blocked_naughty_users
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    conversation_history.clear()
    dirty_talk_permissions.clear()
    pending_permissions.clear()
    blocked_users.clear()
    muted_users.clear()
    abuse_targets.clear()
    lover_targets.clear()
    blocked_naughty_users.clear()
    save_admin_data()
    await update.message.reply_text("🔄 All data reset!")


async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    await update.message.reply_text("🔄 Restarting... bye! 👋")
    os.system("pkill -f 'python main.py'")


async def group_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global group_auto_reply
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    group_auto_reply = True
    save_admin_data()
    await update.message.reply_text("✅ Group auto-reply ENABLED!")


async def group_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global group_auto_reply
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    group_auto_reply = False
    save_admin_data()
    await update.message.reply_text("🔇 Group auto-reply DISABLED!")


async def list_blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not blocked_users:
        await update.message.reply_text("No blocked users!")
        return
    
    blocked_list = "\n".join(blocked_users.keys())
    await update.message.reply_text(f"🚫 **BLOCKED USERS:**\n{blocked_list}")


async def list_muted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not muted_users:
        await update.message.reply_text("No muted users!")
        return
    
    muted_list = "\n".join(muted_users.keys())
    await update.message.reply_text(f"🔇 **MUTED USERS:**\n{muted_list}")


async def list_abuse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not abuse_targets:
        await update.message.reply_text("No abuse targets!")
        return
    
    abuse_list = "\n".join(abuse_targets.keys())
    await update.message.reply_text(f"😈 **ABUSE TARGETS:**\n{abuse_list}")


async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id != str(update.effective_user.id) or user_id not in admin_ids:
        if user_id != "@CoffinWifi":
            await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
            return
    
    if not context.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    
    try:
        new_admin = str(int(context.args[0]))
        admin_ids.add(new_admin)
        save_admin_data()
        await update.message.reply_text(f"✅ Admin {new_admin} added!")
    except:
        await update.message.reply_text("Invalid user ID!")


async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id != "@CoffinWifi":
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    
    try:
        admin_to_remove = str(int(context.args[0]))
        admin_ids.discard(admin_to_remove)
        save_admin_data()
        await update.message.reply_text(f"✅ Admin {admin_to_remove} removed!")
    except:
        await update.message.reply_text("Invalid user ID!")


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not admin_ids:
        await update.message.reply_text("No admins!")
        return
    
    admins_list = "\n".join(admin_ids)
    await update.message.reply_text(f"👑 **ADMINS:**\n{admins_list}")


async def add_lover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /addlover @username or /addlover user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    lover_targets[target] = True
    save_admin_data()
    await update.message.reply_text(f"❤️ User {target} is now a lover! 💕")


async def remove_lover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /removelover @username or /removelover user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    lover_targets.pop(target, None)
    save_admin_data()
    await update.message.reply_text(f"💔 User {target} is no longer a lover.")


async def list_lovers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not lover_targets:
        await update.message.reply_text("No lovers! 💔")
        return
    
    lovers_list = "\n".join(lover_targets.keys())
    await update.message.reply_text(f"❤️ **MY LOVERS:**\n{lovers_list}")


async def block_naughty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /blocknaughty @username or /blocknaughty user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    blocked_naughty_users[target] = True
    save_admin_data()
    await update.message.reply_text(f"🔒 User {target} blocked from naughty talk!")


async def unblock_naughty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unblocknaughty @username or /unblocknaughty user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target:
        await update.message.reply_text("User not found!")
        return
    
    blocked_naughty_users.pop(target, None)
    save_admin_data()
    await update.message.reply_text(f"✅ User {target} can now receive naughty talk!")


async def list_blocked_naughty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not blocked_naughty_users:
        await update.message.reply_text("No users blocked from naughty talk!")
        return
    
    blocked_list = "\n".join(blocked_naughty_users.keys())
    await update.message.reply_text(f"🔒 **NAUGHTY-BLOCKED USERS:**\n{blocked_list}")


async def handle_permission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    if str(user_id) != admin_chat_id:
        await query.answer("You're not the admin!", show_alert=True)
        return
    
    if query.data.startswith("approve_"):
        requester_id = query.data.split("_")[1]
        dirty_talk_permissions[requester_id] = True
        await query.edit_message_text(f"✅ Dirty talk approved for {requester_id}! 🔥")
    
    elif query.data.startswith("deny_"):
        requester_id = query.data.split("_")[1]
        pending_permissions.pop(requester_id, None)
        await query.edit_message_text(f"❌ Dirty talk denied for {requester_id}.")


async def tell_joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    joke = get_random_joke()
    await update.message.reply_text(f"😂 {joke}")


async def send_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quote = get_random_quote()
    await update.message.reply_text(f"✨ {quote}")


async def daily_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tip = get_daily_tip()
    await update.message.reply_text(f"💡 {tip}")


async def compliment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    compliment = get_random_compliment()
    await update.message.reply_text(f"💕 {compliment}")


async def fortune_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fortune = get_random_fortune()
    await update.message.reply_text(f"🔮 {fortune}")


async def dare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dare = get_random_dare()
    await update.message.reply_text(f"😈 {dare}")


async def truth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    truth = get_random_truth()
    await update.message.reply_text(f"🤔 {truth}")


async def flip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = random.choice(["Heads 🪙", "Tails 🪙"])
    await update.message.reply_text(f"Flip result: {result}")


async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = random.randint(1, 6)
    await update.message.reply_text(f"🎲 You rolled: {result}")


async def love_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    compatibility = random.randint(1, 100)
    await update.message.reply_text(f"💕 Love Meter: {compatibility}%")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
💕 **NAINA COMMAND GUIDE** 💕

**🎮 FUN & GAMES:**
/joke - Random funny joke
/quote - Motivational quote
/tip - Daily life tips
/compliment - Sweet compliment
/fortune - Your fortune! 🔮
/dare - Get a dare challenge
/truth - Truth or dare question
/flip - Coin flip 🪙
/dice - Dice roll 🎲
/lovetest - Check love meter

**📋 USER COMMANDS:**
/clear - Clear chat history
/help - Show this help
/myinfo - Your personal status

**👑 ADMIN ONLY:**
/admin - Admin control panel
/status - Bot status
/block @user - Block user
/mute @user - Mute user
/abuse @user - Target for gaalis
/lover @user - Mark as lover
"""
    await update.message.reply_text(help_text)


async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    is_admin = "✅ Yes" if user_id in admin_ids else "❌ No"
    is_blocked = "✅ Yes" if user_id in blocked_users else "❌ No"
    is_muted = "✅ Yes" if user_id in muted_users else "❌ No"
    is_lover = "❤️ Yes" if user_id in lover_targets else "❌ No"
    
    info = f"""
📱 **YOUR INFO WITH NAINA**
👤 User ID: {user_id}
👑 Admin: {is_admin}
🚫 Blocked: {is_blocked}
🔇 Muted: {is_muted}
❤️ Lover: {is_lover}
"""
    await update.message.reply_text(info)


async def view_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /viewchat @username or /viewchat user_id")
        return
    
    target = resolve_user_id(context.args[0])
    if not target or target not in conversation_history:
        await update.message.reply_text("User not found or has no history!")
        return
    
    history = conversation_history[target][-20:]
    chat_display = ""
    for msg in history:
        chat_display += f"**{msg['role']}:** {msg['content']}\n\n"
    
    await update.message.reply_text(f"📜 Last 20 messages with {target}:\n\n{chat_display}")


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not conversation_history:
        await update.message.reply_text("No users yet!")
        return
    
    users_list = "\n".join(conversation_history.keys())
    await update.message.reply_text(f"👥 **TOTAL USERS ({len(conversation_history)}):**\n{users_list}")


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in admin_ids:
        await update.message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    count = 0
    
    for user in conversation_history.keys():
        try:
            await context.bot.send_message(chat_id=user, text=f"📢 **BROADCAST FROM ADMIN:**\n\n{message}")
            count += 1
        except:
            pass
    
    for group in tracked_groups:
        try:
            await context.bot.send_message(chat_id=group, text=f"📢 **BROADCAST FROM ADMIN:**\n\n{message}")
            count += 1
        except:
            pass
    
    await update.message.reply_text(f"✅ Message sent to {count} users/groups!")


async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in conversation_history:
        await update.message.reply_text("No chat history to clear!")
        return
    
    clear_conversation(user_id)
    await update.message.reply_text("🧹 Your chat history cleared!")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


# ========== FLASK ROUTES FOR RENDER WEB SERVICE ==========

@app.route('/', methods=['GET'])
def health():
    """Health check endpoint for Render"""
    return {'status': 'Bot is running!'}, 200


@app.route('/webhook', methods=['POST'])
async def webhook():
    """Telegram webhook endpoint"""
    data = request.get_json()
    try:
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return 'ok', 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'error', 400


def setup_bot():
    global application
    
    load_admin_data()
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stop", stop_bot))
    application.add_handler(CommandHandler("resume", resume_bot))
    application.add_handler(CommandHandler("block", block_user))
    application.add_handler(CommandHandler("unblock", unblock_user))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("abuse", abuse_user))
    application.add_handler(CommandHandler("unabuse", unabuse_user))
    application.add_handler(CommandHandler("reset", reset_data))
    application.add_handler(CommandHandler("restart", restart_bot))
    application.add_handler(CommandHandler("groupon", group_on))
    application.add_handler(CommandHandler("groupoff", group_off))
    application.add_handler(CommandHandler("listblocked", list_blocked))
    application.add_handler(CommandHandler("listmuted", list_muted))
    application.add_handler(CommandHandler("listabuse", list_abuse))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("removeadmin", remove_admin))
    application.add_handler(CommandHandler("listadmins", list_admins))
    application.add_handler(CommandHandler("addlover", add_lover))
    application.add_handler(CommandHandler("removelover", remove_lover))
    application.add_handler(CommandHandler("listlovers", list_lovers))
    application.add_handler(CommandHandler("blocknaughty", block_naughty))
    application.add_handler(CommandHandler("unblocknaughty", unblock_naughty))
    application.add_handler(CommandHandler("listblocknaughty", list_blocked_naughty))
    application.add_handler(CommandHandler("joke", tell_joke))
    application.add_handler(CommandHandler("quote", send_quote))
    application.add_handler(CommandHandler("tip", daily_tip))
    application.add_handler(CommandHandler("compliment", compliment_command))
    application.add_handler(CommandHandler("fortune", fortune_command))
    application.add_handler(CommandHandler("dare", dare_command))
    application.add_handler(CommandHandler("truth", truth_command))
    application.add_handler(CommandHandler("flip", flip_command))
    application.add_handler(CommandHandler("dice", dice_command))
    application.add_handler(CommandHandler("lovetest", love_test))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("myinfo", my_info))
    application.add_handler(CommandHandler("viewchat", view_chat))
    application.add_handler(CommandHandler("listusers", list_users))
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("clear", clear_chat))
    
    application.add_handler(CallbackQueryHandler(handle_permission_callback))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error_handler)
    
    # Setup keep-alive job to send message every 10 minutes
    job_queue = application.job_queue
    job_queue.run_repeating(keep_alive_job, interval=600, first=60)
    
    logger.info("✅ Naina Bot setup complete!")


# ========== START BOT ==========

if __name__ == '__main__':
    setup_bot()
    
    # Run Flask for Render Web Service
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
