import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler  # This was missing in your imports
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration (replace with your actual values)
BOT_TOKEN = ""
PRIVATE_CHANNEL_ID =   # Your private channel ID
PUBLIC_CHANNEL = "https://t.me/fana_film_store"
MOVIES_PER_PAGE = 8  # Number of movies to show per request

class MovieBot:
    def __init__(self):
        self.user_sessions = {}  # Stores user pagination data

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message"""
        keyboard = [
            [InlineKeyboardButton("🎬 Get Movies", callback_data="get_movies")],
            [InlineKeyboardButton("📢 Join Channel", url=PUBLIC_CHANNEL)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎥 Welcome to Movie Bot!\n\n"
            f"Join our channel: {PUBLIC_CHANNEL}\n\n"
            "Send a movie ID to get that movie plus the next 9 movies\n"
            "Example: 123",
            reply_markup=reply_markup
        )

    async def handle_movie_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle when user sends a movie ID"""
        try:
            movie_id = int(update.message.text.strip())
            user_id = update.effective_user.id
            
            # Store the starting ID for pagination
            self.user_sessions[user_id] = {
                'current_id': movie_id,
                'remaining': MOVIES_PER_PAGE,
                'last_message': None  # To track the last sent message
            }
            
            await self._send_movie_batch(update, context, user_id)
            
        except ValueError:
            await update.message.reply_text(
                "Please send a valid movie ID number\nExample: 123"
            )

    async def _send_movie_batch(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Send a batch of movies"""
        if user_id not in self.user_sessions:
            return
            
        session = self.user_sessions[user_id]
        current_id = session['current_id']
        remaining = session['remaining']
        successful_sends = 0
        
        for i in range(remaining):
            try:
                # Forward the movie
                await context.bot.forward_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=PRIVATE_CHANNEL_ID,
                    message_id=current_id + i
                )
                successful_sends += 1
            except Exception as e:
                logger.error(f"Error forwarding movie {current_id + i}: {e}")
                # If we hit an error, stop trying to send more
                break
        
        # Update session
        if successful_sends > 0:
            session['current_id'] += successful_sends
            session['remaining'] -= successful_sends
            
            if session['remaining'] > 0:
                keyboard = [
                    [InlineKeyboardButton("📜 Load More", callback_data=f"more_{user_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Edit the last message if it exists, otherwise send new
                if session.get('last_message'):
                    try:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=session['last_message'],
                            text=f"✅ Sent {successful_sends} movies. Load more?",
                            reply_markup=reply_markup
                        )
                    except Exception:
                        # If editing fails, send new message
                        msg = await update.message.reply_text(
                            f"✅ Sent {successful_sends} movies. Load more?",
                            reply_markup=reply_markup
                        )
                        session['last_message'] = msg.message_id
                else:
                    msg = await update.message.reply_text(
                        f"✅ Sent {successful_sends} movies. Load more?",
                        reply_markup=reply_markup
                    )
                    session['last_message'] = msg.message_id
            else:
                if session.get('last_message'):
                    try:
                        await context.bot.edit_message_text(
                            chat_id=update.effective_chat.id,
                            message_id=session['last_message'],
                            text="🎉 All movies sent!"
                        )
                    except Exception:
                        await update.message.reply_text("🎉 All movies sent!")
                else:
                    await update.message.reply_text("🎉 All movies sent!")
                del self.user_sessions[user_id]
        else:
            await update.message.reply_text(
                "❌ No movies found starting from that ID. Please check the ID and try again."
            )
            del self.user_sessions[user_id]

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("more_"):
            user_id = int(query.data.split("_")[1])
            await query.edit_message_reply_markup(reply_markup=None)
            await self._send_movie_batch(update, context, user_id)
        elif query.data == "get_movies":
            await query.edit_message_text(
                "Send a movie ID to get that movie plus the next 9 movies\n"
                "Example: 123"
            )

def main():
    """Start the bot."""
    movie_bot = MovieBot()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", movie_bot.start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, movie_bot.handle_movie_request))
    application.add_handler(CallbackQueryHandler(movie_bot.handle_callback))  # Fixed the handler name
    
    application.run_polling()

if __name__ == "__main__":

    main()
