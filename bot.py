# bot.py
import logging
import os
import re
import sys
import time
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

import config
from utils.youtube import get_video_info, extract_video_id
from utils.helpers import is_youtube_url, extract_youtube_id_from_text, format_duration, format_filesize

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL)
)
logger = logging.getLogger(__name__)

# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    user_first_name = update.effective_user.first_name
    await update.message.reply_text(
        f"👋 Hello, {user_first_name}!\n\n"
        f"I'm a YouTube Downloader Bot. Send me any YouTube link, and I'll provide download options.\n\n"
        f"Just paste a YouTube URL and I'll do the rest!"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help information when the /help command is issued."""
    await update.message.reply_text(
        "📚 *YouTube Downloader Bot Help*\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/about - Information about this bot\n\n"
        "*How to use:*\n"
        "1. Simply send me a YouTube video URL\n"
        "2. I'll analyze the video and provide download options\n"
        "3. Select your preferred format\n\n"
        "*Supported links:*\n"
        "• Regular YouTube URLs\n"
        "• YouTube Shorts\n"
        "• Mobile YouTube URLs\n"
        "• URLs within text\n\n"
        "If you have any issues, feel free to contact my developer.",
        parse_mode="Markdown"
    )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send information about the bot when the /about command is issued."""
    await update.message.reply_text(
        "ℹ️ *About YouTube Downloader Bot*\n\n"
        "This bot helps you download videos from YouTube in various formats and qualities.\n\n"
        "*Features:*\n"
        "• Download videos in multiple resolutions\n"
        "• Extract audio from videos\n"
        "• Support for YouTube Shorts\n"
        "• Fast and reliable downloads\n\n"
        "*Technical Info:*\n"
        "• Built with Python and python-telegram-bot\n"
        "• Uses yt-dlp for video extraction\n"
        "• Open-source project\n\n"
        "*Version:* 1.0.0",
        parse_mode="Markdown"
    )

# Message handler for YouTube links
async def handle_youtube_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process YouTube URLs sent by users."""
    message_text = update.message.text
    
    # Check if message contains a YouTube URL
    if not is_youtube_url(message_text):
        await update.message.reply_text(
            "This doesn't look like a YouTube URL. Please send a valid YouTube video link."
        )
        return
    
    # Extract video ID
    video_id = extract_youtube_id_from_text(message_text)
    if not video_id:
        await update.message.reply_text(
            "I couldn't extract a valid YouTube video ID from your message."
        )
        return
    
    # Send "processing" message
    processing_message = await update.message.reply_text(
        "🔄 Processing your YouTube video... Please wait."
    )
    
    try:
        # Get video URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Get video information
        video_info = get_video_info(video_url)
        
        if not video_info:
            await processing_message.edit_text(
                "❌ Sorry, I couldn't retrieve information for this video. "
                "It might be age-restricted, private, or unavailable."
            )
            return
        
        # Create response with video details
        title = video_info['title']
        thumbnail = video_info['thumbnail']
        channel = video_info.get('channel', 'Unknown channel')
        duration = format_duration(video_info.get('duration', 0))
        
        # Create keyboard with download options
        keyboard = []
        
        for format_info in video_info['formats']:
            size_text = format_filesize(format_info['filesize'])
            btn_text = f"{format_info['format_name']} - {size_text}"
            callback_data = f"dl_{video_id}_{format_info['format_id']}"
            
            # Ensure callback data isn't too long (Telegram limit is 64 bytes)
            if len(callback_data) > 64:
                callback_data = f"dl_{video_id}_i{format_info['format_id'][-10:]}"
                
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_data)])
        
        # Add a button to get direct links (for cases when download fails)
        keyboard.append([InlineKeyboardButton("🔗 Get Direct Links", callback_data=f"links_{video_id}")])
        
        # Add a button for more info
        keyboard.append([InlineKeyboardButton("ℹ️ Video Info", callback_data=f"info_{video_id}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Caption for the response
        caption = (
            f"*{title}*\n\n"
            f"👤 *Channel:* {channel}\n"
            f"⏱️ *Duration:* {duration}\n\n"
            f"Choose your preferred format to download:"
        )
        
        # Send response with thumbnail and options
        await update.message.reply_photo(
            photo=thumbnail,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        # Delete the processing message
        await processing_message.delete()
        
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        await processing_message.edit_text(
            f"❌ An error occurred while processing your request: {str(e)}\n\n"
            f"Please try again later or try a different video."
        )

# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button presses from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    # Extract info from callback data
    callback_data = query.data
    
    # Handle download format selection
    if callback_data.startswith("dl_"):
        _, video_id, format_id = callback_data.split("_", 2)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            # Get video info to get the direct URL
            video_info = get_video_info(video_url)
            
            # Find the selected format
            selected_format = None
            for format_info in video_info['formats']:
                if format_id == format_info['format_id'] or f"i{format_info['format_id'][-10:]}" == format_id:
                    selected_format = format_info
                    break
            
            if not selected_format or not selected_format.get('url'):
                await query.edit_message_caption(
                    caption="❌ Sorry, I couldn't generate a download link for this format."
                )
                return
            
            # Create a message with the download link
            download_url = selected_format['url']
            format_name = selected_format['format_name']
            
            caption = (
                f"*{video_info['title']}*\n\n"
                f"✅ Your download is ready!\n"
                f"📌 Format: {format_name}\n\n"
                f"⚠️ *Important:*\n"
                f"1. The download link will expire in 6 hours\n"
                f"2. If the link doesn't work, try requesting the video again\n\n"
                f"[🔽 Click here to download]({download_url})"
            )
            
            await query.edit_message_caption(
                caption=caption,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error generating download link: {str(e)}")
            await query.edit_message_caption(
                caption=f"❌ Error generating download link: {str(e)}"
            )
    
    # Handle "Get Direct Links" button
    elif callback_data.startswith("links_"):
        _, video_id = callback_data.split("_", 1)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            # Get alternative download services
            caption = (
                f"📋 *Alternative Download Options*\n\n"
                f"Use these services to download the video:\n\n"
                f"• [Y2mate](https://www.y2mate.com/youtube/{video_id})\n"
                f"• [SaveFrom.net](https://en.savefrom.net/#{video_url})\n"
                f"• [9xbuddy](https://9xbuddy.com/youtube/{video_id})\n\n"
                f"💡 These external services might have ads but are reliable alternatives."
            )
            
            await query.edit_message_caption(
                caption=caption,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error generating alternative links: {str(e)}")
            await query.edit_message_caption(
                caption=f"❌ Error generating alternative links: {str(e)}"
            )
    
    # Handle "Video Info" button
    elif callback_data.startswith("info_"):
        _, video_id = callback_data.split("_", 1)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        try:
            # Get detailed video info
            video_info = get_video_info(video_url)
            
            # Format the information
            title = video_info['title']
            channel = video_info.get('channel', 'Unknown')
            duration = format_duration(video_info.get('duration', 0))
            
            caption = (
                f"📊 *Video Information*\n\n"
                f"*Title:* {title}\n"
                f"*Channel:* {channel}\n"
                f"*Duration:* {duration}\n"
                f"*Video ID:* `{video_id}`\n\n"
                f"🔗 *Links:*\n"
                f"• [Watch on YouTube](https://www.youtube.com/watch?v={video_id})\n"
                f"• [Share link](https://youtu.be/{video_id})"
            )
            
            # Add back button
            keyboard = [[InlineKeyboardButton("🔙 Back to Download Options", callback_data=f"back_{video_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_caption(
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error fetching video info: {str(e)}")
            await query.edit_message_caption(
                caption=f"❌ Error fetching video information: {str(e)}"
            )
    
    # Handle "Back" button
    elif callback_data.startswith("back_"):
        _, video_id = callback_data.split("_", 1)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Re-fetch video info and show download options
        try:
            await handle_youtube_url(update, context)
        except Exception as e:
            logger.error(f"Error returning to download options: {str(e)}")
            await query.edit_message_caption(
                caption=f"❌ Error: {str(e)}\n\nPlease send the YouTube link again."
            )

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))

    
    # Add message handler for YouTube links
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_youtube_url))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Set up webhook or polling based on configuration
    if config.WEBHOOK_MODE and config.WEBHOOK_URL:
        application.run_webhook(
            listen="0.0.0.0",
            port=config.PORT,
            webhook_url=config.WEBHOOK_URL
        )
        logger.info(f"Bot started in webhook mode on port {config.PORT}")
    else:
        application.run_polling()
        logger.info("Bot started in polling mode")

    

if __name__ == "__main__":
    logger.info("Starting YouTube Downloader Bot")
    main()




