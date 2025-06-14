import logging
import asyncio
from datetime import datetime, date
import pytz
import os
from aiohttp import web
from typing import Union, Optional, AsyncGenerator
from pyrogram import Client, __version__, types
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import FloodWait
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import (
    API_ID, API_HASH, BOT_TOKEN, PORT, ADMINS,
    LOG_CHANNEL, SUPPORT_GROUP, AUTH_CHANNEL,
    CHANNELS, DELETE_CHANNELS, LOG_API_CHANNEL,
    MOVIE_UPDATE_CHANNEL, REQUEST_CHANNEL
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
        name = self.get_session_name()
        super().__init__(
            name=name,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=10,
        )
        self.username = None

    def get_session_name(self):
        """Get or create a session name"""
        base_name = "phoenix-filter-bot"
        session_dir = "sessions"
        
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
            
        sessions = [f for f in os.listdir(session_dir) if f.startswith(base_name)]
        if not sessions:
            return os.path.join(session_dir, base_name)
            
        # Use existing session or create new one
        latest_session = max(sessions)
        if os.path.getsize(os.path.join(session_dir, latest_session)) > 0:
            num = int(latest_session.split('.')[-1]) if '.' in latest_session else 0
            return os.path.join(session_dir, f"{base_name}.{num + 1}")
        return os.path.join(session_dir, latest_session)
        
    async def start(self):
        """Start the bot and initialize required variables"""
        try:
            start_time = datetime.now()
            
            # Get banned users and chats
            banned_users, banned_chats = await db.get_banned()
            temp.BANNED_USERS = banned_users
            temp.BANNED_CHATS = banned_chats
            
            # Start the client with flood wait handling
            try:
                await super().start()
            except FloodWait as e:
                logger.warning(f"FloodWait: Sleeping for {e.value} seconds")
                # Create a marker file for the flood wait
                with open(os.path.join("sessions", "flood_wait.txt"), "w") as f:
                    f.write(f"{e.value}")
                await asyncio.sleep(e.value)
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
            
            # Remove flood wait marker if exists
            flood_wait_file = os.path.join("sessions", "flood_wait.txt")
            if os.path.exists(flood_wait_file):
                os.remove(flood_wait_file)
            
            start_log = (
                f"<b>Bot Started Successfully ✅\n\n"
                f"Bot: {me.mention}\n"
                f"Date: {today}\n"
                f"Time: {now.strftime('%I:%M:%S %p')}\n"
                f"Timezone: Asia/Kolkata\n"
                f"Session: {self._name}\n"
                f"Took: {time_taken}</b>"
            )
            
            # Send startup notifications with flood wait handling
            try:
                await self.send_message(LOG_CHANNEL, start_log)
                await self.send_message(LOG_API_CHANNEL, 
                    f"#BOT_START\n\nBot started with session: {self._name}")
                
                for admin in str(ADMINS).split():
                    try:
                        await self.send_message(
                            chat_id=int(admin),
                            text=f"<b>Bot Restarted! ✨\nSession: {self._name}\nTook: {time_taken}</b>"
                        )
                    except Exception as e:
                        logger.error(f"Failed to send startup message to admin {admin}: {e}")
            except FloodWait as e:
                logger.warning(f"FloodWait in startup notification: Sleeping for {e.value} seconds")
                await asyncio.sleep(e.value)
                
            logger.info(f"Bot Started as {me.first_name} with session {self._name}")
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            await asyncio.sleep(10)
            exit(1)
            
    async def stop(self, *args):
        """Handle bot shutdown"""
        try:
            await super().stop()
            logger.info("Bot stopped. Bye!")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)

if __name__ == "__main__":
    while True:
        try:
            app = Bot()
            app.run()
        except FloodWait as e:
            logger.warning(f"Main FloodWait: Sleeping for {e.value} seconds")
            # Create a marker file for the flood wait
            with open(os.path.join("sessions", "flood_wait.txt"), "w") as f:
                f.write(f"{e.value}")
            asyncio.sleep(e.value)
        except Exception as e:
            logger.error(f"Main loop error: {e}", exc_info=True)
            asyncio.sleep(10)
