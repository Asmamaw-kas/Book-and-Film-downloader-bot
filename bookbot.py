import logging
import os
import threading
import time
import requests
import uvicorn
from fastapi import FastAPI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ─────────────────────────────
#  LOGGING
# ─────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────
#  FASTAPI APP
# ─────────────────────────────
app = FastAPI()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Bot is running!", "timestamp": time.time()}

@app.get("/ping")
def ping():
    return {"status": "pong", "timestamp": time.time()}

# ─────────────────────────────
#  ENVIRONMENT VARIABLES
# ─────────────────────────────
TOKEN = os.getenv("BOT_TOKEN")
PRIVATE_CHANNEL_ID = os.getenv("PRIVATE_CHANNEL_ID")
PUBLIC_CHANNEL = os.getenv("PUBLIC_CHANNEL")
RENDER_URL = os.getenv("RENDER_URL", "https://mybot-uwgk.onrender.com")  # 🔁 Replace with your actual Render URL

# ─────────────────────────────
#  TELEGRAM COMMAND HANDLERS
# ─────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📚 Get Started", callback_data="get_started")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")],
        [InlineKeyboardButton("Join Channel", url=PUBLIC_CHANNEL)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📚 Welcome to Book Bot!\n\n"
        f"Join our channel:\n{PUBLIC_CHANNEL}\n\n"
        "Send a book ID to download.\nExample: 123",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "get_started":
        await query.edit_message_text(
            text=f"📖 How to download:\n\n1. Find book IDs in:\n{PUBLIC_CHANNEL}\n\n2. Send the ID like: <code>123</code>",
            parse_mode="HTML"
        )
    elif query.data == "help":
        await query.edit_message_text(
            text=f"ℹ️ Help:\n• Send book ID to download\n• Find IDs in: {PUBLIC_CHANNEL}",
            parse_mode="HTML"
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.isdigit():
        try:
            await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id=int(PRIVATE_CHANNEL_ID),
                message_id=int(text)
            )
            await update.message.reply_text("✅ Book sent!")
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            await update.message.reply_text(f"❌ Error. Check ID at {PUBLIC_CHANNEL}")
    else:
        await update.message.reply_text(
            f"📚 Send a valid book ID\nFind IDs at: {PUBLIC_CHANNEL}\nExample: <code>123</code>",
            parse_mode="HTML"
        )

# ─────────────────────────────
#  IMPROVED KEEP ALIVE SYSTEM
# ─────────────────────────────
def keep_alive():
    """Enhanced ping system to keep Render awake"""
    urls_to_ping = [
        RENDER_URL,
        f"{RENDER_URL}/",
        f"{RENDER_URL}/ping"
    ]
    
    while True:
        for url in urls_to_ping:
            try:
                response = requests.get(url, timeout=10)
                logger.info(f"✅ Pinged {url} - Status: {response.status_code}")
            except requests.exceptions.RequestException as e:
                logger.warning(f"❌ Ping failed for {url}: {e}")
            time.sleep(10)  # Small delay between pings
        
        # Wait 4 minutes before next round of pings
        # This keeps the service active without hitting rate limits
        time.sleep(240)

# ─────────────────────────────
#  BOT HEALTH MONITOR
# ─────────────────────────────
def bot_health_monitor(application):
    """Monitor bot health and restart if needed"""
    while True:
        try:
            # Check if bot is running by attempting a simple API call
            bot_info = application.bot.get_me()
            logger.info(f"🤖 Bot is healthy: {bot_info.username}")
        except Exception as e:
            logger.error(f"❌ Bot health check failed: {e}")
            # In a real scenario, you might want to restart the bot
            # For now, we'll just log the error
        time.sleep(300)  # Check every 5 minutes

# ─────────────────────────────
#  RUN FASTAPI
# ─────────────────────────────
def run_fastapi():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

# ─────────────────────────────
#  MAIN ENTRY POINT
# ─────────────────────────────
def main():
    if not all([TOKEN, PRIVATE_CHANNEL_ID, PUBLIC_CHANNEL]):
        missing = []
        if not TOKEN: missing.append("BOT_TOKEN")
        if not PRIVATE_CHANNEL_ID: missing.append("PRIVATE_CHANNEL_ID")
        if not PUBLIC_CHANNEL: missing.append("PUBLIC_CHANNEL")
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        raise ValueError(f"Missing: {', '.join(missing)}")

    # Validate RENDER_URL is set
    if RENDER_URL == "https://your-app-name.onrender.com":
        logger.warning("⚠️  Please set RENDER_URL environment variable to your actual Render URL")

    # Start FastAPI in background
    fastapi_thread = threading.Thread(target=run_fastapi, daemon=True)
    fastapi_thread.start()
    logger.info("🚀 FastAPI server started")

    # Start keep-alive ping thread
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("🔔 Keep-alive system started")

    # Start Telegram bot
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start bot health monitor
    health_thread = threading.Thread(target=bot_health_monitor, args=(application,), daemon=True)
    health_thread.start()
    logger.info("❤️  Health monitor started")

    logger.info("🤖 Bot started successfully!")
    
    try:
        application.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        # Attempt to restart after a delay
        time.sleep(60)
        logger.info("🔄 Attempting to restart bot...")
        main()

if __name__ == "__main__":
    main()
