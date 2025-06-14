import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from utils import users_broadcast, groups_broadcast, temp, get_readable_time
from database.users_chats_db import db
from info import ADMINS, LOG_CHANNEL

logger = logging.getLogger(__name__)

@Client.on_message(filters.command("broadcast") & filters.user(ADMINS) & filters.reply)
async def broadcast_handler(bot: Client, message: Message):
    """
    Broadcast messages to all users or groups
    """
    try:
        # Get all users
        all_users = await db.get_all_users()
        broadcast_msg = message.reply_to_message
        
        if len(message.command) > 1:
            if message.command[1] == 'pin':
                pin = True
            else:
                pin = False
        else:
            pin = False
            
        # Start broadcast
        broadcast_start_time = datetime.now()
        await message.reply_text("<b>Broadcasting messages... This may take a while.</b>")
        
        success_msg = await users_broadcast(bot, broadcast_msg, all_users, pin)
        
        time_taken = get_readable_time(
            (datetime.now() - broadcast_start_time).seconds
        )
        
        await message.reply_text(
            f"<b>{success_msg}\nTime taken: {time_taken}</b>"
        )
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}", exc_info=True)
        await message.reply_text(f"<b>Error in broadcast:</b>\n<code>{str(e)}</code>")

@Client.on_message(filters.command("group_broadcast") & filters.user(ADMINS) & filters.reply)
async def group_broadcast_handler(bot: Client, message: Message):
    """
    Broadcast messages to all groups
    """
    try:
        # Get all groups
        all_groups = await db.get_all_chats()
        broadcast_msg = message.reply_to_message
        
        if len(message.command) > 1:
            if message.command[1] == 'pin':
                pin = True
            else:
                pin = False
        else:
            pin = False
            
        # Start broadcast
        broadcast_start_time = datetime.now()
        await message.reply_text("<b>Broadcasting to groups... This may take a while.</b>")
        
        success_msg = await groups_broadcast(bot, broadcast_msg, all_groups, pin)
        
        time_taken = get_readable_time(
            (datetime.now() - broadcast_start_time).seconds
        )
        
        await message.reply_text(
            f"<b>{success_msg}\nTime taken: {time_taken}</b>"
        )
        
    except Exception as e:
        logger.error(f"Group broadcast error: {e}", exc_info=True)
        await message.reply_text(f"<b>Error in group broadcast:</b>\n<code>{str(e)}</code>")
