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
from info import *
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
        self._start_time = None

    def get_session_name(self):
        """Get or create a session name"""
        base_name = "phoenix-filter-bot"
        session_dir = "sessions"
        
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
            
        # Clean old sessions
        sessions = [f for f in os.listdir(session_dir) if f.startswith(base_name)]
        if len(sessions) > 5:  # Keep only 5 most recent sessions
            sessions.sort(key=lambda x: os.path.getctime(os.path.join(session_dir, x)))
            for old_session in sessions[:-5]:
                try:
                    os.remove(os.path.join(session_dir, old_session))
                except:
                    pass
                    
        # Create new session name with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(session_dir, f"{base_name}_{timestamp}")

    async def connect_with_retries(self, max_retries=3, retry_delay=5):
        """Attempt to connect with retries"""
        for attempt in range(max_retries):
            try:
                await super().start()
                return True
            except FloodWait as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = e.value
                logger.warning(f"FloodWait: Sleeping for {wait_time} seconds (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(retry_delay)
        return False

    async def start(self):
        """Start the bot and initialize required variables"""
        try:
            self._start_time = datetime.now()
            
            # Get banned users and chats
            banned_users, banned_chats = await db.get_banned()
            temp.BANNED_USERS = banned_users
            temp.BANNED_CHATS = banned_chats
            
            # Connect with retries
            connected = await self.connect_with_retries()
            if not connected:
                raise Exception("Failed to connect after maximum retries")
            
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
            time_taken = get_readable_time((datetime.now() - self._start_time).seconds)
            
            start_log = (
                f"<b>Bot Started Successfully ✅\n\n"
                f"Bot: {me.mention}\n"
                f"Session: {self._name}\n"
                f"Date: {today}\n"
                f"Time: {now.strftime('%I:%M:%S %p')}\n"
                f"Timezone: Asia/Kolkata\n"
                f"Took: {time_taken}</b>"
            )
            
            # Send startup notifications
            async def send_notification(chat_id, text):
                try:
                    await self.send_message(chat_id=chat_id, text=text)
                except FloodWait as e:
                    await asyncio.sleep(e.value)
                    await self.send_message(chat_id=chat_id, text=text)
                except Exception as e:
                    logger.error(f"Failed to send notification to {chat_id}: {e}")

            # Send to log channels
            await send_notification(LOG_CHANNEL, start_log)
            await send_notification(LOG_API_CHANNEL, f"#BOT_START\n\nBot started with session: {self._name}")
            
            # Notify admins
            admin_msg = f"<b>Bot Restarted! ✨\nSession: {self._name}\nTook: {time_taken}</b>"
            for admin in str(ADMINS).split():
                await send_notification(int(admin), admin_msg)
                
            logger.info(f"Bot Started as {me.first_name} with session {self._name}")
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            raise

    async def stop(self, *args):
        """Handle bot shutdown"""
        try:
            await super().stop()
            logger.info(f"Bot stopped. Session: {self._name}")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}", exc_info=True)

if __name__ == "__main__":
    retries = 0
    max_retries = 3
    
    while retries < max_retries:
        try:
            app = Bot()
            app.run()
            break
        except FloodWait as e:
            retries += 1
            logger.warning(f"Main FloodWait: Sleeping for {e.value} seconds (attempt {retries}/{max_retries})")
            asyncio.sleep(e.value)
        except Exception as e:
            retries += 1
            logger.error(f"Main loop error: {e}", exc_info=True)
            asyncio.sleep(10)
            
        if retries == max_retries:
            logger.error("Maximum retries reached. Exiting.")
            break
