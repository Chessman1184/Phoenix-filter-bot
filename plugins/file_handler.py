import logging
import asyncio
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.ia_filterdb import Media, get_file_details
from utils import get_size, temp, get_settings, format_file_name
from info import AUTH_CHANNEL, FILE_AUTO_DEL_TIMER

logger = logging.getLogger(__name__)

async def handle_file_request(client: Client, message: Message, file_id: str, grp_id: int):
    """Main function to handle file requests and verify force subscribe"""
    
    try:
        if AUTH_CHANNEL:
            user = message.from_user.id
            try:
                # Check if user has joined the channel
                member = await client.get_chat_member(AUTH_CHANNEL, user)
                if member.status in ["left", "kicked"]:
                    raise UserNotParticipant
                    
            except UserNotParticipant:
                # Generate invite link
                invite_link = await client.create_chat_invite_link(
                    chat_id=AUTH_CHANNEL,
                    creates_join_request=True
                )
                
                btn = [[
                    InlineKeyboardButton("🎗️ Join Channel 🎗️", url=invite_link.invite_link)
                ],[
                    InlineKeyboardButton("♻️ Try Again ♻️", 
                    url=f"https://t.me/{temp.U_NAME}?start=file_{grp_id}_{file_id}")
                ]]
                
                await message.reply_text(
                    text="<b>Please join our channel first to access files!\n\nClick Join Channel button to join, then click Try Again to get your file.</b>",
                    reply_markup=InlineKeyboardMarkup(btn),
                    parse_mode='html'
                )
                return False
                
            except Exception as e:
                logger.error(f"Error checking channel subscription: {e}")
                return False
                
        # Get file details
        files_ = await get_file_details(file_id)
        if not files_:
            await message.reply('<b>⚠️ File not found in database!</b>')
            return False
            
        files = files_[0]
        
        # Get caption settings
        settings = await get_settings(grp_id)
        CAPTION = settings.get('caption', '')
        
        # Format caption
        f_caption = CAPTION.format(
            file_name=format_file_name(files.file_name),
            file_size=get_size(files.file_size),
            file_caption=files.caption if hasattr(files, 'caption') else ''
        )

        # Add stream/download buttons
        btn = [[
            InlineKeyboardButton("⚡️ Stream", callback_data=f'stream#{file_id}'),
            InlineKeyboardButton("📥 Download", callback_data=f'download#{file_id}')
        ]]
        
        # Send file
        file_msg = await client.send_cached_media(
            chat_id=message.from_user.id,
            file_id=files.file_id,
            caption=f_caption,
            reply_markup=InlineKeyboardMarkup(btn)
        )
        
        # Handle auto-delete if enabled
        if settings.get('auto_delete', False):
            delete_msg = await message.reply_text(
                f"<b>⚠️ This file will be deleted in {FILE_AUTO_DEL_TIMER/60:.0f} minutes!</b>"
            )
            await asyncio.sleep(FILE_AUTO_DEL_TIMER)
            await file_msg.delete()
            await delete_msg.edit("<b>File auto-deleted!</b>")
            
        return True
        
    except Exception as e:
        logger.error(f"Error in handle_file_request: {e}")
        await message.reply("<b>Sorry, something went wrong while processing your request!</b>")
        return False
