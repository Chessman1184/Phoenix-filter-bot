import logging
import asyncio
from datetime import datetime, date
import pytz
from aiohttp import web
from typing import Union, Optional, AsyncGenerator
from pyrogram import Client, __version__, types
from pyrogram.enums import ChatMemberStatus
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import (
    API_ID, API_HASH, BOT_TOKEN, PORT, ADMINS,
    LOG_CHANNEL, SUPPORT_GROUP
)
from utils import temp, get_readable_time
from plugins import web_server, check_expired_premium
from Script import script

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="phoenix-filter-bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=10,
        )
        self.username = None
        
    async def start(self):
        """Start the bot and initialize required variables"""
        try:
            start_time = datetime.now()
            
            # Get banned users and chats
            banned_users, banned_chats = await db.get_banned()
            temp.BANNED_USERS = banned_users
            temp.BANNED_CHATS = banned_chats
            
            # Start the client
            await super().start()
            
            # Initialize database indexes
            await Media.ensure_indexes()
            
            # Get bot info
            me = await self.get_me()
            self.username = '@' + me.username
            temp.ME = me.id
            temp.U_NAME = me.username
            temp.B_NAME = me.first_name
            temp.B_LINK = me.mention
            
            # Start premium checker task
            self.loop.create_task(check_expired_premium(self))
            
            # Start web server
            app = web.AppRunner(await web_server())
            await app.setup()
            await web.TCPSite(app, "0.0.0.0", PORT).start()
            
            # Log bot start
            tz = pytz.timezone('Asia/Kolkata')
            today = date.today()
            now = datetime.now(tz)
            time_taken = get_readable_time((datetime.now() - start_time).seconds)
            
            start_log = (
                f"<b>Bot Started Successfully ✅\n\n"
                f"Bot: {me.mention}\n"
                f"Date: {today}\n"
                f"Time: {now.strftime('%I:%M:%S %p')}\n"
                f"Timezone: Asia/Kolkata\n"
                f"Took: {time_taken}</b>"
            )
            
            # Send startup notifications
            await self.send_message(LOG_CHANNEL, start_log)
            for admin in ADMINS:
                try:
                    await self.send_message(
                        chat_id=admin,
                        text=f"<b>Bot Restarted! ✨\nTook: {time_taken}</b>"
                    )
                except Exception as e:
                    logger.error(f"Failed to send startup message to admin {admin}: {e}")
                    
            logger.info(f"Bot Started as {me.first_name}")
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            exit(1)
            
    async def stop(self, *args):
        """Handle bot shutdown"""
        try:
            await super().stop()
            logger.info("Bot stopped. Bye!")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)
            
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """
        Iterate through messages in a chat
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            
            messages = await self.get_messages(
                chat_id, 
                list(range(current, current + new_diff + 1))
            )
            
            for message in messages:
                yield message
                current += 1

if __name__ == "__main__":
    app = Bot()
    app.run()
