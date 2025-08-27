import os
import logging
import random
import json
from datetime import datetime, time
from typing import Dict, List, Optional
import sqlite3
from telegram import (
    Update, 
    BotCommand, 
    ChatPermissions, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InputFile,
    ChatMember
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes, 
    filters, 
    CallbackQueryHandler,
    JobQueue
)
from telegram.error import BadRequest

# Bot configuration
BOT_TOKEN = "8443859419:AAGaZ4Nah52TurLvQ2NdINrxhbSiwXQKEi4"
ADMIN_CHAT_ID = 7108127485
ADMIN_USERNAME = "nexanetadmin"
DEFAULT_PASSWORD = "nexanetgenie"
MAIN_CHANNEL = "https://t.me/nexanetofficial"

# MPesa and PayPal donation info
MPESA_NUMBER = "0113004884"
PAYPAL_EMAIL = "joshuasaidi120@gmail.com"

# File extensions for config files
CONFIG_EXTENSIONS = ['.hc', '.ehi', '.dark', '.v2', '.ziv', '.ssc', '.npvt', '.tnl']

# Store admin sessions (in production, use a proper database)
admin_sessions = {}
user_message_map = {}  # Maps user_id to their chat_id for replying

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Jokes and quotes for random sending
JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs!",
    "Why did the developer go broke? Because he used up all his cache!",
    "How many programmers does it take to change a light bulb? None, that's a hardware problem!",
    "Why do Java developers wear glasses? Because they can't C#!",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'"
]

QUOTES = [
    "The best way to predict the future is to implement it. - David Heinemeier Hansson",
    "Software is eating the world. - Marc Andreessen",
    "The most disastrous thing that you can ever learn is your first programming language. - Alan Kay",
    "The computer was born to solve problems that did not exist before. - Bill Gates",
    "Innovation distinguishes between a leader and a follower. - Steve Jobs"
]

GREETINGS = [
    "Good morning valued clients! Remember we're always here to support you.",
    "Rise and shine! Your dedicated support team is here for all your needs.",
    "Good morning! Another day to provide you with excellent service.",
    "Evening greetings! We're available 24/7 for your inquiries.",
    "Good evening! Remember we value your trust in our services."
]

def is_admin(update: Update) -> bool:
    """Check if user is admin based on chat ID or session"""
    user_id = update.effective_user.id
    return user_id == ADMIN_CHAT_ID or admin_sessions.get(user_id, False)

async def send_admin_notification(context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send notification to admin"""
    await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=message)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when the command /start is issued."""
    user = update.effective_user
    welcome_text = (
        f"👋 Welcome {user.mention_markdown_v2()}\! \n\n"
        "I'm your friendly NexaNet assistant\. Here's what I can do:\n\n"
        "✨ *Features*\n"
        "• Get help with our services\n"
        "• Receive config files\n"
        "• Contact admin for support\n"
        "• Daily jokes and inspiration\n\n"
        "Type /help to see all commands\!"
    )
    
    await update.message.reply_markdown_v2(welcome_text)
    await send_admin_notification(context, f"User {user.name} ({user.id}) started the bot")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message with all available commands."""
    help_text = (
        "🤖 *NexaNet Bot Help*\n\n"
        "📋 *Available Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/info - Get channel info\n"
        "/about - Learn about this bot\n"
        "/rules - Show group rules\n"
        "/donate - Support our work\n"
        "/request - Request a config file\n"
        "/joke - Get a random joke\n"
        "/quote - Get an inspirational quote\n\n"
        "For admin features, please authenticate with /adminlogin"
    )
    
    await update.message.reply_markdown_v2(help_text)

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Information about the bot"""
    about_text = (
        "🌟 *About NexaNet Bot*\n\n"
        "This is an advanced Telegram bot designed to provide:\n\n"
        "• User management for groups/channels\n"
        "• Config file generation and distribution\n"
        "• Secure admin controls\n"
        "• Entertainment with jokes and quotes\n"
        "• 24/7 customer support\n\n"
        "Optimized for performance and reliability with advanced security features\."
    )
    await update.message.reply_markdown_v2(about_text)

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get information about the channel/group"""
    chat = update.effective_chat
    
    info_text = (
        f"📊 *Chat Information*\n\n"
        f"• Title: {chat.title or 'Private Chat'}\n"
        f"• Type: {chat.type}\n"
        f"• ID: {chat.id}\n"
        f"• Members: {await chat.get_member_count() if chat.type != 'private' else '1'}\n\n"
        f"Main Channel: {MAIN_CHANNEL}"
    )
    await update.message.reply_markdown_v2(info_text)

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show group rules"""
    rules_text = (
        "📜 *Group Rules*\n\n"
        "1. Be respectful to all members\n"
        "2. No spam or excessive self-promotion\n"
        "3. Keep discussions relevant to the group topic\n"
        "4. No NSFW content\n"
        "5. Follow Telegram's Terms of Service\n\n"
        "Violations may result in removal or banning\."
    )
    await update.message.reply_markdown_v2(rules_text)

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Donation information"""
    keyboard = [
        [InlineKeyboardButton("📱 MPesa", callback_data="donate_mpesa")],
        [InlineKeyboardButton("💳 PayPal", callback_data="donate_paypal")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    donate_text = (
        "❤️ *Support Our Work*\n\n"
        "Your donations help us maintain and improve our services:\n\n"
        "📱 *MPesa:* {}\n"
        "💳 *PayPal:* {}\n\n"
        "Thank you for your support\!".format(MPESA_NUMBER, PAYPAL_EMAIL)
    )
    await update.message.reply_markdown_v2(donate_text, reply_markup=reply_markup)

async def donate_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle donation button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "donate_mpesa":
        await query.edit_message_text(
            text=f"📱 Please send MPesa to: {MPESA_NUMBER}\nThank you for your support!",
            parse_mode="Markdown"
        )
    elif query.data == "donate_paypal":
        await query.edit_message_text(
            text=f"💳 Please send PayPal to: {PAYPAL_EMAIL}\nThank you for your support!",
            parse_mode="Markdown"
        )

async def joke_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a random joke"""
    joke = random.choice(JOKES)
    await update.message.reply_text(joke)
    await send_admin_notification(context, f"Sent joke to {update.effective_user.name}")

async def quote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send an inspirational quote"""
    quote = random.choice(QUOTES)
    await update.message.reply_text(quote)

async def request_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Request a config file - sends random IP to user and notifies admin"""
    random_ip = f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}"
    
    # Send to user
    await update.message.reply_text(
        f"Your request has been processed. Temporary IP: {random_ip}\n\n"
        "This IP will be valid for 1 hour. Contact admin for permanent config."
    )
    
    # Notify admin
    user = update.effective_user
    request_text = (
        f"🔔 Config Request\n\n"
        f"From: {user.mention_markdown_v2()}\n"
        f"User ID: {user.id}\n"
        f"Temporary IP: {random_ip}\n\n"
        f"Use /sendconfig to provide a permanent config."
    )
    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID, 
        text=request_text,
        parse_mode="Markdown"
    )

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin login command"""
    if context.args and context.args[0] == DEFAULT_PASSWORD:
        user_id = update.effective_user.id
        admin_sessions[user_id] = True
        
        await update.message.reply_text(
            "✅ Admin access granted! Full commands unlocked.\n\n"
            "Use /adminhelp to see admin commands."
        )
        await send_admin_notification(context, f"Admin login by {update.effective_user.name}")
    elif context.args:
        await update.message.reply_text("❌ Invalid password. Access denied.")
    else:
        await update.message.reply_text("Please provide a password: /adminlogin <password>")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin help commands"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    admin_help_text = (
        "🔒 *Admin Commands*\n\n"
        "/adduser <user_id> - Add user to group/channel\n"
        "/removeuser <user_id> - Remove user from group/channel\n"
        "/ban <user_id> [duration] - Ban user temporarily or permanently\n"
        "/reply - Reply to forwarded user messages\n"
        "/send <type> <target> <content> - Send content to channel/user\n"
        "/configs - Generate and send config files\n"
        "/changepassword <new_password> - Change admin password\n"
        "/adminlogout - End admin session\n"
        "/broadcast <message> - Send message to all users\n"
        "/stats - Get bot usage statistics"
    )
    await update.message.reply_markdown_v2(admin_help_text)

async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log out from admin session"""
    user_id = update.effective_user.id
    if user_id in admin_sessions:
        del admin_sessions[user_id]
        await update.message.reply_text("✅ Admin session ended.")
    else:
        await update.message.reply_text("No active admin session.")

async def change_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change admin password"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /changepassword <new_password>")
        return
        
    new_password = context.args[0]
    global DEFAULT_PASSWORD
    DEFAULT_PASSWORD = new_password
    
    await update.message.reply_text("✅ Password updated successfully.")
    await send_admin_notification(context, f"Password changed by {update.effective_user.name}")

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add user to group/channel"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /adduser <user_id>")
        return
        
    user_id = context.args[0]
    try:
        # This would need the appropriate method based on your group/channel setup
        # For illustration purposes only
        await update.message.reply_text(f"✅ User {user_id} added successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error adding user: {str(e)}")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove user from group/channel"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /removeuser <user_id>")
        return
        
    user_id = context.args[0]
    try:
        # This would need the appropriate method based on your group/channel setup
        # For illustration purposes only
        await update.message.reply_text(f"✅ User {user_id} removed successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error removing user: {str(e)}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban user from group/channel"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /ban <user_id> [duration]")
        return
        
    user_id = context.args[0]
    duration = context.args[1] if len(context.args) > 1 else "permanent"
    
    try:
        # This would need the appropriate method based on your group/channel setup
        # For illustration purposes only
        await update.message.reply_text(f"✅ User {user_id} banned ({duration}).")
    except Exception as e:
        await update.message.reply_text(f"❌ Error banning user: {str(e)}")

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward user messages to admin and store mapping"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    user_message_map[user_id] = chat_id
    
    # Forward the message to admin
    try:
        if update.message.text:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"📩 Message from {update.effective_user.mention_markdown_v2()}\n"
                     f"User ID: {user_id}\n\n"
                     f"Message: {update.message.text}",
                parse_mode="Markdown"
            )
        elif update.message.photo:
            # Forward photo
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=update.message.photo[-1].file_id,
                caption=f"📷 Photo from {update.effective_user.name}\nUser ID: {user_id}"
            )
        elif update.message.document:
            # Forward document
            await context.bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=update.message.document.file_id,
                caption=f"📄 Document from {update.effective_user.name}\nUser ID: {user_id}"
            )
    except Exception as e:
        logger.error(f"Error forwarding message to admin: {e}")

async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin replies to user by replying to forwarded message"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Please reply to a user's message to respond.")
        return
        
    # Extract user ID from the forwarded message caption
    replied_message = update.message.reply_to_message
    if replied_message.caption:
        # Try to find user ID in the caption
        import re
        match = re.search(r"User ID: (\d+)", replied_message.caption)
        if match:
            user_chat_id = int(match.group(1))
            
            # Send the admin's reply to the user
            try:
                if update.message.text:
                    await context.bot.send_message(
                        chat_id=user_chat_id,
                        text=f"📨 Reply from admin:\n\n{update.message.text}"
                    )
                elif update.message.photo:
                    await context.bot.send_photo(
                        chat_id=user_chat_id,
                        photo=update.message.photo[-1].file_id,
                        caption=update.message.caption or "📨 Reply from admin"
                    )
                elif update.message.document:
                    await context.bot.send_document(
                        chat_id=user_chat_id,
                        document=update.message.document.file_id,
                        caption=update.message.caption or "📨 Reply from admin"
                    )
                    
                await update.message.reply_text("✅ Reply sent to user.")
            except Exception as e:
                await update.message.reply_text(f"❌ Error sending reply: {str(e)}")
            return
    
    await update.message.reply_text("❌ Could not identify user to reply to.")

async def send_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send content to channels or users"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /send <type> <target> <content>\n\n"
            "Types: text, photo, video, document\n"
            "Target: channel username (@channel) or user ID\n"
            "Content: text or file caption"
        )
        return
        
    content_type = context.args[0].lower()
    target = context.args[1]
    content = ' '.join(context.args[2:])
    
    try:
        if content_type == "text":
            await context.bot.send_message(chat_id=target, text=content)
        elif content_type == "photo":
            # This would need a photo file_id or URL
            await context.bot.send_photo(chat_id=target, caption=content)
        elif content_type == "video":
            # This would need a video file_id or URL
            await context.bot.send_video(chat_id=target, caption=content)
        elif content_type == "document":
            # This would need a document file_id or URL
            await context.bot.send_document(chat_id=target, caption=content)
        else:
            await update.message.reply_text("❌ Invalid content type. Use: text, photo, video, document")
            return
            
        await update.message.reply_text("✅ Content sent successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending content: {str(e)}")

async def generate_configs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate and send config files directly from server"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    # This would connect to your server and generate config files
    # For demonstration, we'll create a sample config
    
    config_content = "# Sample config file\nserver=nexanet.com\nport=443\nprotocol=tls"
    config_file = InputFile(
        bytes(config_content, 'utf-8'),
        filename=f"nexanet_config_{datetime.now().strftime('%Y%m%d_%H%M%S')}.hc"
    )
    
    try:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=config_file,
            caption="📁 Your generated config file"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error generating config: {str(e)}")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users (admin only)"""
    if not is_admin(update):
        await update.message.reply_text("❌ Admin access required.")
        return
        
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
        
    # In a real implementation, you would iterate through all known users
    # For demonstration, we'll just
