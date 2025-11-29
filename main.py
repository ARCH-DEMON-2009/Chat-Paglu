import os
import logging
import asyncio
import random
import time
import json
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
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
            }, f, indent=2)
        logger.info("Saved admin data")
    except Exception as e:
        logger.error(f"Error saving admin data: {e}")


def is_admin(user) -> bool:
    if user.username == ADMIN_USERNAME:
        return True
    if str(user.id) in admin_ids:
        return True
    return False


def is_super_admin(user) -> bool:
    return user.username == ADMIN_USERNAME


def is_message_after_start(message) -> bool:
    if not message or not message.date:
        return False
    message_time = message.date.timestamp()
    return message_time >= BOT_START_TIME


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_chat_id
    
    if not is_message_after_start(update.message):
        return
    
    user = update.effective_user
    user_name = user.first_name
    
    if is_admin(user):
        admin_chat_id = update.effective_chat.id
        save_admin_data()
        logger.info(f"Admin registered! Chat ID: {admin_chat_id}")
        
        stats = get_stats()
        await update.message.reply_text(
            f"👑 Welcome Admin @{ADMIN_USERNAME}!\n\n"
            "🤖 BOT STATUS:\n"
            f"• Bot Enabled: {'✅ Yes' if bot_enabled else '❌ No'}\n"
            f"• Group Auto-Reply: {'✅ Yes' if group_auto_reply else '❌ No'}\n"
            f"• Private Chats: {stats['total_private_chats']}\n"
            f"• Group Chats: {stats['total_group_chats']}\n"
            f"• Blocked Users: {len(blocked_users)}\n"
            f"• Muted Users: {len(muted_users)}\n"
            f"• Abuse Targets: {len(abuse_targets)}\n"
            f"• Lovers: {len(lover_targets)}\n"
            f"• Other Admins: {len(admin_ids)}\n\n"
            "📋 ADMIN COMMANDS:\n"
            "/admin - Show admin panel\n"
            "/status - Bot status\n"
            "/stop - Disable bot\n"
            "/resume - Enable bot\n"
            "/block @user - Block user\n"
            "/unblock @user - Unblock user\n"
            "/mute @user - Stop talking to user\n"
            "/unmute @user - Resume talking to user\n"
            "/abuse @user - Target user with gaalis\n"
            "/unabuse @user - Stop abusing user\n"
            "/addlover <user_id> - Add lover (auto-flirty mode)\n"
            "/removelover <user_id> - Remove lover\n"
            "/listlovers - Show lovers\n"
            "/reset - Reset all conversation data\n"
            "/restart - Restart bot\n"
            "/groupon - Enable group auto-reply\n"
            "/groupoff - Disable group auto-reply\n"
            "/listblocked - Show blocked users\n"
            "/listmuted - Show muted users\n"
            "/listabuse - Show abuse targets\n"
            "/viewchat <user_id> - See user's chat history\n"
            "/broadcast <message> - Send message to all users\n\n"
            "👤 SUPER ADMIN ONLY:\n"
            "/addadmin <user_id> - Add admin by ID\n"
            "/removeadmin <user_id> - Remove admin\n"
            "/listadmins - List all admins\n\n"
            "💡 I'll send you permission requests for dirty talk!"
        )
        return
    
    await update.message.reply_text(
        f"Hii {user_name}! 💕\n\n"
        "I'm Naina! Nice to meet you~ 😊\n\n"
        "I love making new friends and having fun conversations!\n"
        "Just talk to me like you would with any friend 💬\n\n"
        "Commands:\n"
        "/start - Say hi to me again\n"
        "/clear - Start our chat fresh"
    )
    
    sticker = get_sticker_for_mood("greeting")
    if sticker:
        try:
            await update.message.reply_sticker(sticker)
        except:
            pass


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    
    user = update.effective_user
    if not is_admin(user):
        await update.message.reply_text("Sorry, this command is for admin only! 😊")
        return
    
    stats = get_stats()
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Enable Bot" if not bot_enabled else "❌ Disable Bot", 
                               callback_data="admin_toggle_bot"),
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton("🗣️ Group Reply: " + ("ON" if group_auto_reply else "OFF"), 
                               callback_data="admin_toggle_group"),
            InlineKeyboardButton("🔄 Reset Data", callback_data="admin_reset")
        ],
        [
            InlineKeyboardButton("📋 Blocked List", callback_data="admin_blocked"),
            InlineKeyboardButton("🔇 Muted List", callback_data="admin_muted")
        ],
        [
            InlineKeyboardButton("😈 Abuse List", callback_data="admin_abuse"),
            InlineKeyboardButton("🔃 Restart Bot", callback_data="admin_restart")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👑 ADMIN PANEL\n\n"
        f"🤖 Bot Status: {'✅ Enabled' if bot_enabled else '❌ Disabled'}\n"
        f"💬 Group Auto-Reply: {'✅ ON' if group_auto_reply else '❌ OFF'}\n\n"
        f"📊 STATISTICS:\n"
        f"• Private Chats: {stats['total_private_chats']}\n"
        f"• Group Chats: {stats['total_group_chats']}\n"
        f"• Dirty Chats: {stats['total_dirty_chats']}\n"
        f"• User Preferences: {stats['total_user_preferences']}\n\n"
        f"🚫 Blocked Users: {len(blocked_users)}\n"
        f"🔇 Muted Users: {len(muted_users)}\n"
        f"😈 Abuse Targets: {len(abuse_targets)}\n"
        f"💕 Lovers: {len(lover_targets)}",
        reply_markup=reply_markup
    )


async def handle_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled, group_auto_reply
    
    query = update.callback_query
    await query.answer()
    
    if not is_admin(query.from_user):
        await query.edit_message_text("Only admin can use this! 🙅‍♀️")
        return
    
    data = query.data
    
    if data == "admin_toggle_bot":
        bot_enabled = not bot_enabled
        save_admin_data()
        await query.edit_message_text(f"Bot {'✅ Enabled' if bot_enabled else '❌ Disabled'}!")
        
    elif data == "admin_toggle_group":
        group_auto_reply = not group_auto_reply
        save_admin_data()
        await query.edit_message_text(f"Group Auto-Reply {'✅ ON' if group_auto_reply else '❌ OFF'}!")
        
    elif data == "admin_stats":
        stats = get_stats()
        await query.edit_message_text(
            f"📊 BOT STATISTICS\n\n"
            f"• Total Private Chats: {stats['total_private_chats']}\n"
            f"• Total Group Chats: {stats['total_group_chats']}\n"
            f"• Dirty Talk Chats: {stats['total_dirty_chats']}\n"
            f"• User Preferences Saved: {stats['total_user_preferences']}\n"
            f"• Dirty Permissions: {len(dirty_talk_permissions)}\n"
            f"• Pending Permissions: {len(pending_permissions)}\n\n"
            f"🚫 Blocked: {len(blocked_users)}\n"
            f"🔇 Muted: {len(muted_users)}\n"
            f"😈 Abuse Targets: {len(abuse_targets)}"
        )
        
    elif data == "admin_reset":
        clear_all_data()
        dirty_talk_permissions.clear()
        pending_permissions.clear()
        await query.edit_message_text("✅ All conversation data reset!")
        
    elif data == "admin_blocked":
        if blocked_users:
            blocked_list = "\n".join([f"• {v}" for v in blocked_users.values()])
            await query.edit_message_text(f"🚫 BLOCKED USERS:\n\n{blocked_list}")
        else:
            await query.edit_message_text("No blocked users!")
            
    elif data == "admin_muted":
        if muted_users:
            muted_list = "\n".join([f"• {v}" for v in muted_users.values()])
            await query.edit_message_text(f"🔇 MUTED USERS:\n\n{muted_list}")
        else:
            await query.edit_message_text("No muted users!")
            
    elif data == "admin_abuse":
        if abuse_targets:
            abuse_list = "\n".join([f"• {v}" for v in abuse_targets.values()])
            await query.edit_message_text(f"😈 ABUSE TARGETS:\n\n{abuse_list}")
        else:
            await query.edit_message_text("No abuse targets!")
            
    elif data == "admin_restart":
        await query.edit_message_text("🔄 Restarting bot...")
        os.execv(sys.executable, ['python'] + sys.argv)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    stats = get_stats()
    uptime = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    await update.message.reply_text(
        f"🤖 BOT STATUS\n\n"
        f"• Status: {'✅ Running' if bot_enabled else '❌ Disabled'}\n"
        f"• Uptime: {hours}h {minutes}m {seconds}s\n"
        f"• Group Reply: {'✅ ON' if group_auto_reply else '❌ OFF'}\n\n"
        f"📊 Stats:\n"
        f"• Private Chats: {stats['total_private_chats']}\n"
        f"• Group Chats: {stats['total_group_chats']}\n"
        f"• Blocked: {len(blocked_users)}\n"
        f"• Muted: {len(muted_users)}\n"
        f"• Abuse Targets: {len(abuse_targets)}"
    )


async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    bot_enabled = False
    save_admin_data()
    await update.message.reply_text("❌ Bot disabled! Use /resume to enable.")


async def resume_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global bot_enabled
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    bot_enabled = True
    save_admin_data()
    await update.message.reply_text("✅ Bot enabled!")


async def block_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        blocked_users[str(target.id)] = f"@{target.username}" if target.username else target.first_name
        add_username_mapping(target.id, target.username)
        save_admin_data()
        await update.message.reply_text(f"🚫 Blocked {target.first_name}!")
    elif context.args:
        identifier = context.args[0]
        user_id = resolve_user_id(identifier)
        if not user_id:
            await update.message.reply_text(f"❌ User {identifier} not found! They need to message first.")
            return
        blocked_users[user_id] = identifier
        save_admin_data()
        await update.message.reply_text(f"🚫 Blocked {identifier}!")
    else:
        await update.message.reply_text("Reply to a message or use: /block @username")


async def unblock_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        if str(target.id) in blocked_users:
            del blocked_users[str(target.id)]
            save_admin_data()
            await update.message.reply_text(f"✅ Unblocked {target.first_name}!")
        else:
            await update.message.reply_text("User not blocked!")
    elif context.args:
        username = context.args[0].replace("@", "")
        if username in blocked_users:
            del blocked_users[username]
            save_admin_data()
            await update.message.reply_text(f"✅ Unblocked @{username}!")
        else:
            await update.message.reply_text("User not blocked!")
    else:
        await update.message.reply_text("Reply to a message or use: /unblock @username")


async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        muted_users[str(target.id)] = f"@{target.username}" if target.username else target.first_name
        add_username_mapping(target.id, target.username)
        save_admin_data()
        await update.message.reply_text(f"🔇 Won't talk to {target.first_name} anymore!")
    elif context.args:
        identifier = context.args[0]
        user_id = resolve_user_id(identifier)
        if not user_id:
            await update.message.reply_text(f"❌ User {identifier} not found! They need to message first.")
            return
        muted_users[user_id] = identifier
        save_admin_data()
        await update.message.reply_text(f"🔇 Won't talk to {identifier} anymore!")
    else:
        await update.message.reply_text("Reply to a message or use: /mute @username")


async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        if str(target.id) in muted_users:
            del muted_users[str(target.id)]
            save_admin_data()
            await update.message.reply_text(f"✅ Will talk to {target.first_name} again!")
        else:
            await update.message.reply_text("User not muted!")
    elif context.args:
        username = context.args[0].replace("@", "")
        if username in muted_users:
            del muted_users[username]
            save_admin_data()
            await update.message.reply_text(f"✅ Will talk to @{username} again!")
        else:
            await update.message.reply_text("User not muted!")
    else:
        await update.message.reply_text("Reply to a message or use: /unmute @username")


async def abuse_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        abuse_targets[str(target.id)] = f"@{target.username}" if target.username else target.first_name
        add_username_mapping(target.id, target.username)
        save_admin_data()
        await update.message.reply_text(f"😈 Will abuse {target.first_name} now!")
    elif context.args:
        identifier = context.args[0]
        user_id = resolve_user_id(identifier)
        if not user_id:
            await update.message.reply_text(f"❌ User {identifier} not found! They need to message first.")
            return
        abuse_targets[user_id] = identifier
        save_admin_data()
        await update.message.reply_text(f"😈 Will abuse {identifier} now!")
    else:
        await update.message.reply_text("Reply to a message or use: /abuse @username")


async def unabuse_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user
        if str(target.id) in abuse_targets:
            del abuse_targets[str(target.id)]
            save_admin_data()
            await update.message.reply_text(f"✅ Won't abuse {target.first_name} anymore!")
        else:
            await update.message.reply_text("User not in abuse list!")
    elif context.args:
        identifier = context.args[0]
        user_id = resolve_user_id(identifier)
        if not user_id or user_id not in abuse_targets:
            await update.message.reply_text(f"❌ {identifier} is not in abuse list!")
            return
        del abuse_targets[user_id]
        save_admin_data()
        await update.message.reply_text(f"✅ Won't abuse {identifier} anymore!")
    else:
        await update.message.reply_text("Reply to a message or use: /unabuse @username")


async def reset_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    clear_all_data()
    dirty_talk_permissions.clear()
    pending_permissions.clear()
    await update.message.reply_text("✅ All conversation data reset!")


async def restart_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    await update.message.reply_text("🔄 Restarting bot...")
    os.execv(sys.executable, ['python'] + sys.argv)


async def group_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global group_auto_reply
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    group_auto_reply = True
    save_admin_data()
    await update.message.reply_text("✅ Group auto-reply enabled!")


async def group_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global group_auto_reply
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    group_auto_reply = False
    save_admin_data()
    await update.message.reply_text("❌ Group auto-reply disabled!")


async def list_blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if blocked_users:
        blocked_list = "\n".join([f"• {v}" for v in blocked_users.values()])
        await update.message.reply_text(f"🚫 BLOCKED USERS:\n\n{blocked_list}")
    else:
        await update.message.reply_text("No blocked users!")


async def list_muted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if muted_users:
        muted_list = "\n".join([f"• {v}" for v in muted_users.values()])
        await update.message.reply_text(f"🔇 MUTED USERS:\n\n{muted_list}")
    else:
        await update.message.reply_text("No muted users!")


async def list_abuse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if abuse_targets:
        abuse_list = "\n".join([f"• {v}" for v in abuse_targets.values()])
        await update.message.reply_text(f"😈 ABUSE TARGETS:\n\n{abuse_list}")
    else:
        await update.message.reply_text("No abuse targets!")


async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_super_admin(update.effective_user):
        await update.message.reply_text("Only super admin (@CoffinWifi) can add admins!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /addadmin <user_id>\nExample: /addadmin 123456789")
        return
    
    user_id = context.args[0].strip()
    if not user_id.isdigit():
        await update.message.reply_text("Please provide a valid numeric user ID!")
        return
    
    admin_ids.add(user_id)
    save_admin_data()
    await update.message.reply_text(f"✅ Added admin: {user_id}")


async def remove_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_super_admin(update.effective_user):
        await update.message.reply_text("Only super admin (@CoffinWifi) can remove admins!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>\nExample: /removeadmin 123456789")
        return
    
    user_id = context.args[0].strip()
    if user_id in admin_ids:
        admin_ids.remove(user_id)
        save_admin_data()
        await update.message.reply_text(f"✅ Removed admin: {user_id}")
    else:
        await update.message.reply_text(f"User {user_id} is not an admin!")


async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    admin_list = f"👑 Super Admin: @{ADMIN_USERNAME}\n\n"
    if admin_ids:
        admin_list += "👤 Other Admins:\n"
        admin_list += "\n".join([f"• {aid}" for aid in admin_ids])
    else:
        admin_list += "No other admins added."
    
    await update.message.reply_text(admin_list)


async def add_lover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /addlover @username or <user_id>\nExample: /addlover @TanduriShadow")
        return
    
    identifier = context.args[0]
    user_id = resolve_user_id(identifier)
    
    if not user_id:
        await update.message.reply_text(f"❌ User {identifier} not found! They need to message the bot first, or use their numeric ID.")
        return
    
    lover_targets[user_id] = identifier
    save_admin_data()
    await update.message.reply_text(f"💕 Will talk lovingly with {identifier}!")


async def remove_lover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /removelover @username or <user_id>")
        return
    
    identifier = context.args[0]
    user_id = resolve_user_id(identifier)
    
    if not user_id or user_id not in lover_targets:
        await update.message.reply_text(f"❌ {identifier} is not a lover!")
        return
    
    del lover_targets[user_id]
    save_admin_data()
    await update.message.reply_text(f"✅ Removed lover: {identifier}")


async def list_lovers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if lover_targets:
        lover_list = "\n".join([f"• {v}" for v in lover_targets.values()])
        await update.message.reply_text(f"💕 LOVERS:\n\n{lover_list}")
    else:
        await update.message.reply_text("No lovers added!")


async def block_naughty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /blocknaughty @username or <user_id>")
        return
    
    identifier = context.args[0]
    user_id = resolve_user_id(identifier)
    
    if not user_id:
        await update.message.reply_text(f"❌ User {identifier} not found! They need to message first.")
        return
    
    blocked_naughty_users[user_id] = identifier
    save_admin_data()
    await update.message.reply_text(f"🚫 Blocked naughty talk from {identifier}!")


async def unblock_naughty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /unblocknaughty @username or <user_id>")
        return
    
    identifier = context.args[0]
    user_id = resolve_user_id(identifier)
    
    if not user_id or user_id not in blocked_naughty_users:
        await update.message.reply_text(f"❌ {identifier} is not blocked from naughty talk!")
        return
    
    del blocked_naughty_users[user_id]
    save_admin_data()
    await update.message.reply_text(f"✅ Allowed naughty talk for {identifier}!")


async def list_blocked_naughty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if blocked_naughty_users:
        naughty_list = "\n".join([f"• {v}" for v in blocked_naughty_users.values()])
        await update.message.reply_text(f"🚫 NAUGHTY BLOCKED:\n\n{naughty_list}")
    else:
        await update.message.reply_text("No users blocked from naughty talk!")


async def tell_joke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    await simulate_typing(context, update.effective_chat.id)
    joke = get_random_joke()
    await update.message.reply_text(joke)


async def send_quote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    await simulate_typing(context, update.effective_chat.id)
    quote = get_random_quote()
    await update.message.reply_text(quote)


async def daily_tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    await simulate_typing(context, update.effective_chat.id)
    tip = get_daily_tip()
    await update.message.reply_text(tip)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    
    help_text = """📚 HINATA KE FEATURES:

💬 **Chat Commands:**
/start - Naina se miliye
/clear - Chat history clear karo
/joke - Ek funny joke sunao
/quote - Motivational quote
/tip - Daily helpful tip
/compliment - Random compliment! 💕
/fortune - Aapka fortune jaano! 🔮
/dare - Dare le lo! 😈
/truth - Truth ka jawab do! 🤔
/flip - Coin flip karo! 🪙
/dice - Dice roll karo! 🎲
/lovetest - Love meter check karo! 💕

👑 **Admin Commands:**
/admin - Admin panel
/block @user - Block karo
/mute @user - Mute karo
/addlover @user - Lover mode
/viewchat <id> - Chat history dekho
/broadcast <msg> - Sab ko message bhejo

📋 **Also Try:**
Group messages with "Admin order [command]"

Bilkul, main aapke liye hamesha ready hoon! 😊"""
    
    await update.message.reply_text(help_text)


async def my_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    
    user = update.effective_user
    user_id = str(user.id)
    user_name = user.first_name or "Friend"
    
    is_lover = user_id in lover_targets
    is_blocked_naughty = user_id in blocked_naughty_users
    has_permission = dirty_talk_permissions.get(user_id, False)
    
    info_text = f"""👤 **Aapka Info:**
Name: {user_name}
User ID: {user_id}
💕 Lover Mode: {'✅ Yes' if is_lover else '❌ No'}
🔞 Naughty Allowed: {'✅ Yes' if has_permission else '❌ No'}
🚫 Naughty Blocked: {'✅ Yes' if is_blocked_naughty else '❌ No'}

Aap Naina ke liye bahut special ho! 😊"""
    
    await update.message.reply_text(info_text)


async def compliment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    await simulate_typing(context, update.effective_chat.id)
    compliment = get_random_compliment()
    await update.message.reply_text(compliment)


async def fortune_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    await simulate_typing(context, update.effective_chat.id)
    fortune = get_random_fortune()
    await update.message.reply_text(fortune)


async def dare_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    await simulate_typing(context, update.effective_chat.id)
    dare = get_random_dare()
    await update.message.reply_text(dare)


async def truth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    await simulate_typing(context, update.effective_chat.id)
    truth = get_random_truth()
    await update.message.reply_text(truth)


async def flip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    result = random.choice(["🪙 Heads! 😊", "🪙 Tails! 😄"])
    await update.message.reply_text(result)


async def dice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    roll = random.randint(1, 6)
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    await update.message.reply_text(f"🎲 {emojis[roll-1]} You got a {roll}!")


async def love_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    percentage = random.randint(1, 100)
    hearts = "❤️" * (percentage // 20)
    empty = "🤍" * (5 - len(hearts))
    await update.message.reply_text(f"💕 Love meter: {hearts}{empty}\n{percentage}% love for you! 😊")


async def view_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /viewchat @username or <user_id>\nExample: /viewchat @TanduriShadow")
        return
    
    identifier = context.args[0]
    resolved_id = resolve_user_id(identifier)
    
    if not resolved_id:
        await update.message.reply_text(f"❌ User {identifier} not found! They need to message the bot first, or use numeric ID.")
        return
    
    if resolved_id not in conversation_history or not conversation_history[resolved_id]:
        await update.message.reply_text(f"No chat history with {identifier}")
        return
    
    chat_text = f"💬 CHAT WITH {identifier}:\n\n"
    for msg in conversation_history[resolved_id][-20:]:
        text = msg["parts"][0]["text"] if msg["parts"] else ""
        chat_text += f"{msg['role'].upper()}: {text}\n\n"
    
    if len(chat_text) > 4000:
        await update.message.reply_text(chat_text[:4000] + "\n\n... (truncated)")
    else:
        await update.message.reply_text(chat_text)


async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    if not is_admin(update.effective_user):
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>\nExample: /broadcast Hello everyone!\n\nReply to a photo/video to broadcast it too!")
        return
    
    message = " ".join(context.args)
    photo = None
    video = None
    
    # Check if replying to a photo or video
    if update.message.reply_to_message:
        if update.message.reply_to_message.photo:
            photo = update.message.reply_to_message.photo[-1].file_id
        elif update.message.reply_to_message.video:
            video = update.message.reply_to_message.video.file_id
    
    await update.message.reply_text(f"📢 Broadcasting to {len(conversation_history)} users and {len(tracked_groups)} groups/channels...")
    
    sent_count = 0
    failed_count = 0
    
    # Broadcast to all users
    for user_id in conversation_history.keys():
        try:
            if photo:
                await context.bot.send_photo(chat_id=int(user_id), photo=photo, caption=message)
            elif video:
                await context.bot.send_video(chat_id=int(user_id), video=video, caption=message)
            else:
                await context.bot.send_message(chat_id=int(user_id), text=message)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to user {user_id}: {e}")
            failed_count += 1
    
    # Broadcast to all groups/channels
    for group_id in tracked_groups:
        try:
            if photo:
                await context.bot.send_photo(chat_id=int(group_id), photo=photo, caption=message)
            elif video:
                await context.bot.send_video(chat_id=int(group_id), video=video, caption=message)
            else:
                await context.bot.send_message(chat_id=int(group_id), text=message)
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to broadcast to group {group_id}: {e}")
            failed_count += 1
    
    await update.message.reply_text(f"✅ Broadcast complete!\n📨 Sent to: {sent_count}\n❌ Failed: {failed_count}")


async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_message_after_start(update.message):
        return
    
    chat_type = update.effective_chat.type
    chat_id = str(update.effective_chat.id)
    user_id = str(update.effective_user.id)
    
    if chat_type == "private":
        if clear_conversation(user_id):
            await update.message.reply_text("Okay! Let's start fresh~ 🌸 What do you wanna talk about?")
        else:
            await update.message.reply_text("We haven't talked much yet! Let's change that 😊")
    else:
        if clear_group_conversation(chat_id):
            await update.message.reply_text("Group chat cleared! Fresh start for everyone~ 🌸")
        else:
            await update.message.reply_text("Nothing to clear here! Let's chat 😊")


async def handle_permission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        logger.error(f"Query answer failed (likely expired): {e}")
    
    if query.data.startswith("admin_"):
        await handle_admin_callback(update, context)
        return
    
    admin_username = query.from_user.username
    if admin_username != ADMIN_USERNAME:
        try:
            await query.edit_message_text("Only the admin can respond to this request! 🙅‍♀️")
        except:
            pass
        return
    
    data = query.data
    parts = data.split("_")
    action = parts[0]
    user_id = parts[1]
    
    if user_id in pending_permissions:
        original_chat_id = pending_permissions[user_id]["chat_id"]
        original_message = pending_permissions[user_id]["message"]
        user_name = pending_permissions[user_id]["user_name"]
        original_message_id = pending_permissions[user_id].get("message_id")
        
        try:
            if action == "allow":
                dirty_talk_permissions[user_id] = True
                save_admin_data()
                try:
                    await query.edit_message_text(f"✅ Permission granted for {user_name}!")
                except:
                    pass
                
                response = get_dirty_response(user_id, original_message, user_name)
                
                await simulate_typing(context, original_chat_id)
                await context.bot.send_message(
                    chat_id=original_chat_id, 
                    text=response,
                    reply_to_message_id=original_message_id
                )
                
                mood_sticker = get_sticker_for_mood("flirty")
                if mood_sticker and random.random() > 0.5:
                    try:
                        await context.bot.send_sticker(chat_id=original_chat_id, sticker=mood_sticker)
                    except:
                        pass
                
            elif action == "deny":
                dirty_talk_permissions[user_id] = False
                save_admin_data()
                try:
                    await query.edit_message_text(f"❌ Permission denied for {user_name}.")
                except:
                    pass
                
                await context.bot.send_message(
                    chat_id=original_chat_id,
                    text="Hey! Let's keep our chat fun and friendly~ 😊 What else do you wanna talk about?",
                    reply_to_message_id=original_message_id
                )
        except Exception as e:
            logger.error(f"Error processing permission callback: {e}")
        
        if user_id in pending_permissions:
            del pending_permissions[user_id]


async def simulate_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")
        delay = random.uniform(0.8, 2.5)
        await asyncio.sleep(delay)
    except:
        pass


async def ask_admin_permission(context: ContextTypes.DEFAULT_TYPE, user_id: str, user_name: str, message: str, chat_id: int, message_id: int = None) -> bool:
    """Send permission request to admin and return success status"""
    global admin_chat_id
    
    if not admin_chat_id:
        logger.error("Admin chat ID not set! Admin needs to /start the bot first.")
        return False
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes, Allow", callback_data=f"allow_{user_id}"),
            InlineKeyboardButton("❌ No, Deny", callback_data=f"deny_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    pending_permissions[user_id] = {
        "chat_id": chat_id,
        "message": message,
        "user_name": user_name,
        "message_id": message_id
    }
    
    try:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"🔔 Permission Request\n\n"
                 f"User: {user_name}\n"
                 f"User ID: {user_id}\n\n"
                 f"Message: \"{message}\"\n\n"
                 f"Allow dirty talk with this user?",
            reply_markup=reply_markup
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send permission request: {e}")
        return False


def is_user_blocked(user) -> bool:
    user_id = str(user.id)
    username = user.username or ""
    return user_id in blocked_users or username in blocked_users


def is_user_muted(user) -> bool:
    user_id = str(user.id)
    username = user.username or ""
    return user_id in muted_users or username in muted_users


def is_abuse_target(user) -> bool:
    user_id = str(user.id)
    username = user.username or ""
    return user_id in abuse_targets or username in abuse_targets


def is_lover(user) -> bool:
    user_id = str(user.id)
    username = user.username or ""
    return user_id in lover_targets or username in lover_targets


async def handle_admin_order(update: Update, context: ContextTypes.DEFAULT_TYPE, order_text: str) -> bool:
    """Handle admin orders like 'change name', 'stop talking to', etc. Returns True if order was processed"""
    user = update.effective_user
    message = update.message
    
    order_lower = order_text.lower().strip()
    
    # Change name order
    if order_lower.startswith("change name to ") or order_lower.startswith("change your name to "):
        new_name = order_text.split("to ", 1)[1].strip() if "to " in order_text else ""
        if new_name:
            context.bot.username = new_name
            await message.reply_text(f"✅ Okay boss! Mujhe ab {new_name} bulao~ 😊")
            return True
    
    # Stop talking to user
    elif order_lower.startswith("stop talking to "):
        target = order_text.split("to ", 1)[1].strip() if "to " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id:
                muted_users[resolved_id] = target
                save_admin_data()
                await message.reply_text(f"✅ Muted {target}! Won't talk to them anymore~ 🤐")
                return True
    
    # Resume talking to user
    elif order_lower.startswith("talk to ") or order_lower.startswith("unmute "):
        target = order_text.split(" ", 2)[2].strip() if " " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id and resolved_id in muted_users:
                del muted_users[resolved_id]
                save_admin_data()
                await message.reply_text(f"✅ Unmuted {target}! Ready to chat~ 😊")
                return True
    
    # Block user
    elif order_lower.startswith("block "):
        target = order_text.split("block ", 1)[1].strip() if "block " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id:
                blocked_users[resolved_id] = target
                save_admin_data()
                await message.reply_text(f"✅ Blocked {target}! 🚫")
                return True
    
    # Unblock user
    elif order_lower.startswith("unblock "):
        target = order_text.split("unblock ", 1)[1].strip() if "unblock " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id and resolved_id in blocked_users:
                del blocked_users[resolved_id]
                save_admin_data()
                await message.reply_text(f"✅ Unblocked {target}! 😊")
                return True
    
    # Mark as lover
    elif order_lower.startswith("lover ") or order_lower.startswith("add lover "):
        target = order_text.split()[-1].strip() if " " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id:
                lover_targets[resolved_id] = target
                save_admin_data()
                await message.reply_text(f"💕 {target} is now my lover~ So sweet! 😍")
                return True
    
    # Remove lover
    elif order_lower.startswith("unlover ") or order_lower.startswith("remove lover "):
        target = order_text.split()[-1].strip() if " " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id and resolved_id in lover_targets:
                del lover_targets[resolved_id]
                save_admin_data()
                await message.reply_text(f"💔 {target} is no longer my lover~ 😔")
                return True
    
    # Abuse target
    elif order_lower.startswith("abuse "):
        target = order_text.split("abuse ", 1)[1].strip() if "abuse " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id:
                abuse_targets[resolved_id] = target
                save_admin_data()
                await message.reply_text(f"✅ {target} is now an abuse target! 😈")
                return True
    
    # Unabuse target
    elif order_lower.startswith("unabuse "):
        target = order_text.split("unabuse ", 1)[1].strip() if "unabuse " in order_text else ""
        if target:
            resolved_id = resolve_user_id(target)
            if resolved_id and resolved_id in abuse_targets:
                del abuse_targets[resolved_id]
                save_admin_data()
                await message.reply_text(f"✅ {target} is no longer an abuse target~ 😊")
                return True
    
    # Reset all data
    elif order_lower == "reset" or order_lower == "reset all" or order_lower.startswith("reset"):
        clear_all_data()
        dirty_talk_permissions.clear()
        blocked_naughty_users.clear()
        await message.reply_text("✅ All data cleared! Fresh start~ 🌸")
        return True
    
    # Restart bot
    elif order_lower == "restart" or order_lower == "restart bot":
        await message.reply_text("🔄 Restarting now, boss! See you in a second~ ⚡")
        logger.info("Admin restart command received")
        os.execv(sys.executable, ['python'] + sys.argv)
        return True
    
    # Personality changes - make slut/dirty/naughty
    elif order_lower.startswith("make "):
        personality = order_text.split("make ", 1)[1].strip().lower()
        if personality in ["slut", "dirty", "naughty", "flirty"]:
            await message.reply_text(f"✅ Okay boss! Mujhe ab {personality} mode mein set kar diya~ 😈💋")
            return True
        elif personality in ["normal", "good", "nice", "respectful"]:
            await message.reply_text(f"✅ Okay boss! Normal mode mein aa gayi~ 😊")
            return True
        elif personality in ["angry", "mean", "rude"]:
            await message.reply_text(f"✅ Okay boss! Angry mode activated! Don't mess with me now~ 😤")
            return True
        elif personality in ["cute", "shy", "innocent"]:
            await message.reply_text(f"✅ Okay boss! Cute shy mode~ 🙈")
            return True
    
    # Generic custom order handler - acknowledge any order
    else:
        if order_lower and len(order_lower) > 3:
            await message.reply_text(f"✅ Samjha boss! '{order_text}' - Order noted! 💪 Karunga ab from now on~")
            return True
    
    return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global admin_chat_id
    
    if not bot_enabled and not is_admin(update.effective_user):
        return
    
    message = update.message
    if not message or not message.text:
        return
    
    if not is_message_after_start(message):
        return
    
    user = update.effective_user
    if not user:
        return
    
    add_username_mapping(user.id, user.username)
    
    if is_user_blocked(user):
        return
    
    user_id = str(user.id)
    user_name = user.first_name or "Cutie"
    user_message = message.text
    chat_type = update.effective_chat.type
    chat_id = str(update.effective_chat.id)
    
    if is_admin(user) and not admin_chat_id:
        admin_chat_id = user.id
        save_admin_data()
        logger.info(f"Admin registered from message! Chat ID: {admin_chat_id}")
    
    bot_username = context.bot.username
    is_mentioned = f"@{bot_username}" in user_message if bot_username else False
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id
    is_private = chat_type == "private"
    is_group = chat_type in ["group", "supergroup"]
    
    if is_group:
        tracked_groups.add(chat_id)  # Track this group/channel for broadcasting
        clean_message = user_message.replace(f"@{bot_username}", "").strip() if bot_username and is_mentioned else user_message
        add_to_group_history(chat_id, user_name, clean_message)
        logger.info(f"[GROUP {chat_id}] {user_name}: {clean_message}")
    
    if is_user_muted(user):
        return
    
    should_respond_group = group_auto_reply and is_group and not message.reply_to_message
    should_respond = is_private or is_mentioned or is_reply_to_bot or should_respond_group
    
    if not should_respond:
        return
    
    if is_mentioned and bot_username:
        user_message = user_message.replace(f"@{bot_username}", "").strip()
    
    # Check for admin orders (works in groups/channels)
    if "admin order" in user_message.lower():
        order_part = user_message.lower().split("admin order", 1)[1].strip()
        
        if not is_admin(user):
            # Non-admin trying to give orders - respond rudely
            await message.reply_text(random.choice(RUDE_REJECTION_MESSAGES))
            return
        else:
            # Admin giving order - process it
            full_order = user_message.split("admin order", 1)[1].strip()
            if await handle_admin_order(update, context, full_order):
                return
    
    logger.info(f"Responding to {user_name} ({user_id}) in {chat_type}: {user_message}")
    
    if is_lover(user):
        await simulate_typing(context, update.effective_chat.id)
        response = get_lover_response(user_id, user_message, user_name)
        await message.reply_text(response)
        
        mood_sticker = get_sticker_for_mood("flirty")
        if mood_sticker and random.random() > 0.6:
            try:
                await message.reply_sticker(mood_sticker)
            except:
                pass
        return
    
    if is_abuse_target(user):
        await simulate_typing(context, update.effective_chat.id)
        response = get_custom_abuse_response(user_name)
        await message.reply_text(response)
        return
    
    if is_abuse_message(user_message):
        await simulate_typing(context, update.effective_chat.id)
        response = get_abuse_response(user_id, user_message, user_name)
        await message.reply_text(response)
        return
    
    if is_advice_message(user_message):
        save_user_preference(user_id, user_message)
    
    if is_dirty_message(user_message):
        if user_id in blocked_naughty_users:
            await simulate_typing(context, update.effective_chat.id)
            rejection = random.choice(GENTLE_REJECTION_MESSAGES)
            await message.reply_text(rejection)
            return
        
        if user_id not in dirty_talk_permissions:
            await simulate_typing(context, update.effective_chat.id)
            await message.reply_text("Hold on a sec~ Let me check something 🤔")
            
            success = await ask_admin_permission(
                context, user_id, user_name, user_message, 
                update.effective_chat.id, message.message_id
            )
            
            if not success:
                if not admin_chat_id:
                    await message.reply_text("My admin hasn't set me up yet~ 😅 Let's chat about something else!")
                else:
                    await message.reply_text("Hmm, I'm having trouble right now. Let's talk about something else? 😊")
            return
        
        elif not dirty_talk_permissions.get(user_id, False):
            await simulate_typing(context, update.effective_chat.id)
            rejection = random.choice(GENTLE_REJECTION_MESSAGES)
            await message.reply_text(rejection)
            return
        
        else:
            await simulate_typing(context, update.effective_chat.id)
            response = get_dirty_response(user_id, user_message, user_name)
            await message.reply_text(response)
            
            mood_sticker = get_sticker_for_mood("flirty")
            if mood_sticker and random.random() > 0.6:
                try:
                    await message.reply_sticker(mood_sticker)
                except:
                    pass
            return
    
    await simulate_typing(context, update.effective_chat.id)
    
    if is_group:
        ai_response = get_group_response(chat_id, user_name, user_message)
    else:
        ai_response = get_ai_response(user_id, user_message, user_name)
    
    logger.info(f"Naina to {user_name}: {ai_response}")
    
    await message.reply_text(ai_response)
    
    mood = detect_mood(user_message, ai_response)
    if random.random() > 0.7:
        mood_sticker = get_sticker_for_mood(mood)
        if mood_sticker:
            try:
                await asyncio.sleep(0.5)
                await message.reply_sticker(mood_sticker)
            except:
                pass


def detect_mood(user_message: str, response: str):
    lower_msg = user_message.lower()
    lower_resp = response.lower()
    
    if any(word in lower_msg for word in ["sad", "upset", "crying", "depressed", "hurt", "pain"]):
        return "caring"
    elif any(word in lower_msg for word in ["haha", "lol", "funny", "joke", "😂", "🤣"]):
        return "happy"
    elif any(word in lower_msg for word in ["love", "beautiful", "cute", "pretty", "gorgeous", "❤", "💕"]):
        return "flirty"
    elif any(word in lower_msg for word in ["hi", "hello", "hey", "morning", "evening"]):
        return "greeting"
    elif any(word in lower_resp for word in ["😊", "💕", "🥰", "😘"]):
        return "happy"
    return "neutral"


async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_enabled:
        return
    
    if not update.message or not update.message.sticker:
        return
    
    if not is_message_after_start(update.message):
        return
    
    chat_type = update.effective_chat.type
    if chat_type != "private":
        return
    
    user = update.effective_user
    if is_user_blocked(user) or is_user_muted(user):
        return
    
    user_id = str(user.id)
    user_name = user.first_name or "Cutie"
    
    await simulate_typing(context, update.effective_chat.id)
    
    responses = [
        "Aww cute sticker! 😊",
        "Hehe I love stickers too! 💕",
        "Nice one! 😄",
        "Sticker war? You're on! 😜",
        "That's adorable~ 🥰"
    ]
    
    await update.message.reply_text(random.choice(responses))
    
    if random.random() > 0.5:
        mood_sticker = get_sticker_for_mood("happy")
        if mood_sticker:
            try:
                await update.message.reply_sticker(mood_sticker)
            except:
                pass


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


def main():
    global BOT_START_TIME
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found! Please set it in Secrets.")
        print("❌ ERROR: TELEGRAM_BOT_TOKEN is missing!")
        print("Please add your Telegram Bot Token to the Secrets tab.")
        return
    
    if not os.environ.get("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY not found! Please set it in Secrets.")
        print("❌ ERROR: GEMINI_API_KEY is missing!")
        print("Please add your Gemini API Key to the Secrets tab.")
        return
    
    load_admin_data()
    
    BOT_START_TIME = time.time()
    
    logger.info("Starting Naina Bot...")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("status", status_command))
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
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("clear", clear_chat))
    application.add_handler(CallbackQueryHandler(handle_permission_callback))
    application.add_handler(MessageHandler(filters.Sticker.ALL, handle_sticker))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    application.add_error_handler(error_handler)
    
    logger.info("Naina Bot is running! Press Ctrl+C to stop.")
    print("✅ Naina Bot is running successfully!")
    print("📱 Works in private chats, groups, and channels!")
    print("💬 Responds to ALL messages in groups (auto-reply enabled)")
    print("😈 Replies with abuse when someone abuses")
    print("📝 Follows user advice and suggestions")
    print(f"👑 Admin: @{ADMIN_USERNAME}")
    print("\n📋 ADMIN FEATURES:")
    print("• /admin - Admin panel with all controls")
    print("• /stop, /resume - Enable/disable bot")
    print("• /block, /unblock - Block/unblock users")
    print("• /mute, /unmute - Stop/resume talking to users")
    print("• /abuse, /unabuse - Target users with gaalis")
    print("• /reset - Reset all data")
    print("• /restart - Restart bot")
    print("• /groupon, /groupoff - Toggle group auto-reply")
    
    if admin_chat_id:
        print(f"\n✅ Admin chat ID loaded: {admin_chat_id}")
    else:
        print("\n⚠️ Admin needs to /start the bot to receive permission requests")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
