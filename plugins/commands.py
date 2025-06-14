import os
import logging
import random
import asyncio
import string
from datetime import datetime
import pytz
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.errors import ChatAdminRequired, FloodWait, UserNotParticipant
from database.ia_filterdb import Media, get_file_details
from database.users_chats_db import db
from utils import (
    temp, get_size, is_subscribed, get_readable_time,
    get_shortlink
)
from plugins.file_handler import handle_file_request
from info import (
    ADMINS, AUTH_CHANNEL, SUPPORT_GROUP, FILE_AUTO_DEL_TIMER,
    START_IMG, CUSTOM_FILE_CAPTION, VERIFY_EXPIRE_TIME, IS_VERIFY
)
from Script import script

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client: Client, message: Message):
    """Handle /start command"""
    try:
        # Log start command
        logger.info(f"Start command from {message.from_user.id}")
        
        if len(message.command) > 1:
            query = message.command[1]
            logger.info(f"Start parameter: {query}")
            
            # Handle file requests
            if query.startswith(('file_', 'pm_mode_')):
                if query.startswith('pm_mode_'):
                    query = query.replace('pm_mode_', '')
                
                try:
                    pre, grp_id, file_id = query.split('_', 2)
                    grp_id = int(grp_id)
                    
                    # Handle file request
                    success = await handle_file_request(client, message, file_id, grp_id)
                    if success:
                        return
                        
                except Exception as e:
                    logger.error(f"Error handling file request: {e}")
                    await message.reply("Sorry, couldn't process file request!")
                    return
                    
            # Handle verification
            elif query.startswith('verify_'):
                _, user_id, verify_id = query.split('_')
                user_id = int(user_id)
                
                # Check verification
                verify_info = await db.get_verify_id_info(user_id, verify_id)
                if not verify_info or verify_info.get("verified"):
                    await message.reply("<b>Invalid or expired verification link!</b>")
                    return
                    
                # Mark as verified
                ist_timezone = pytz.timezone('Asia/Kolkata')
                await db.update_verify_id_info(
                    user_id, 
                    verify_id,
                    {"verified": True, "verified_time": datetime.now(ist_timezone)}
                )
                
                # Send success message
                await message.reply(
                    "<b>✅ Verification successful!\nNow you can access files.</b>",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("Try accessing file again", url=f"t.me/{temp.U_NAME}")]
                    ])
                )
                return
                
        # Check user in database
        if not await db.is_user_exist(message.from_user.id):
            await db.add_user(message.from_user.id, message.from_user.first_name)
            await client.send_message(
                LOG_CHANNEL,
                f"#NewUser\nName: {message.from_user.mention}\nID: {message.from_user.id}"
            )
            
        # Check force subscribe
        if AUTH_CHANNEL and not await is_subscribed(client, message):
            try:
                invite_link = await client.create_chat_invite_link(AUTH_CHANNEL)
                btn = [[
                    InlineKeyboardButton("🔥 Join Channel 🔥", url=invite_link.invite_link)
                ]]
                await message.reply(
                    text="<b>Please join our channel to use this bot!</b>",
                    reply_markup=InlineKeyboardMarkup(btn)
                )
                return
            except Exception as e:
                logger.error(f"Force sub error: {e}")
                return
                
        # Send start message
        buttons = [[
            InlineKeyboardButton('➕ Add me to your group ➕', 
                url=f'http://t.me/{temp.U_NAME}?startgroup=true')
        ],[
            InlineKeyboardButton('ℹ️ Help', callback_data='help'),
            InlineKeyboardButton('👤 About', callback_data='about')
        ]]
        
        await message.reply_photo(
            photo=START_IMG,
            caption=script.START_TXT.format(
                message.from_user.mention,
                temp.B_NAME
            ),
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        await message.reply("Sorry, something went wrong!")

# Add other command handlers here...
