import logging
import aiohttp
import asyncio
import pytz
from datetime import datetime
from typing import Union, List, Optional
from imdb import Cinemagoer
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant, FloodWait
from pyrogram import enums
from info import (
    SETTINGS, AUTH_CHANNEL, LONG_IMDB_DESCRIPTION, 
    IS_VERIFY, START_IMG
)
from database.users_chats_db import db

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BANNED = {}
imdb = Cinemagoer()

class temp(object):
    ME = None
    CURRENT = 2
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None
    B_LINK = None
    SETTINGS = {}
    FILES_ID = {} 
    USERS_CANCEL = False
    GROUPS_CANCEL = False
    CHAT = {}

def get_size(size_in_bytes: int) -> str:
    """Convert size in bytes to human readable format"""
    for unit in ['', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} PB"

async def get_shortlink(link: str, group_id: int = None, second: bool = False, third: bool = False, pm_mode: bool = False) -> str:
    """Generate short link using configured URL shortener"""
    if not group_id or pm_mode:
        settings = SETTINGS
    else:
        settings = await db.get_settings(group_id)
    
    try:
        baseurl = settings.get("shortener_api_url", "")
        api_key = settings.get("shortener_api", "")
        
        if second:
            baseurl = settings.get("shortener_api_url2", "")
            api_key = settings.get("shortener_api2", "")
        elif third:
            baseurl = settings.get("shortener_api_url3", "")
            api_key = settings.get("shortener_api3", "")
            
        if not baseurl or not api_key:
            return link
            
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{baseurl}/api?api={api_key}&url={link}") as resp:
                data = await resp.json()
                if data.get("status") == "success":
                    return data.get("shortenedUrl", link)
                else:
                    logger.error(f"Error shortening URL: {data.get('message')}")
                    return link
                    
    except Exception as e:
        logger.error(f"Error in shortlink generation: {e}")
        return link

async def get_settings(group_id: int, pm_mode: bool = False) -> dict:
    """Get settings for group or default settings for PM"""
    if pm_mode:
        return SETTINGS.copy()
    settings = await db.get_settings(group_id) 
    return settings

async def is_subscribed(bot, update) -> bool:
    """Check if user is subscribed to required chat"""
    if not AUTH_CHANNEL:
        return True
    try:
        user = await bot.get_chat_member(AUTH_CHANNEL, update.from_user.id)
        if user.status == enums.ChatMemberStatus.BANNED:
            return False
    except UserNotParticipant:
        return False
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        return False
    else:
        return True

def get_readable_time(seconds: int) -> str:
    """Convert seconds to readable time format"""
    periods = [('d', 86400), ('h', 3600), ('m', 60), ('s', 1)]
    result = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result.append(f"{period_value}{period_name}")
    return ' '.join(result)

def list_to_str(lst: List[str]) -> str:
    """Convert list to comma-separated string"""
    return " ".join([str(i) for i in lst]) if lst else ""

async def get_poster(query: str, bulk: bool = False, id: bool = False, file: str = None) -> Optional[dict]:
    """Get movie/TV show poster and details from IMDb"""
    if not id:
        # Clean and prepare the search query
        query = query.strip().lower()
        title = query
        year = ""
        
        # Extract year if present
        year_match = re.findall(r'[1-2]\d{3}$', query, re.IGNORECASE)
        if year_match:
            year = year_match[0]
            title = query.replace(year, "").strip()
        elif file:
            year_match = re.findall(r'[1-2]\d{3}', file, re.IGNORECASE)
            if year_match:
                year = year_match[0]

        try:
            movies = imdb.search_movie(title)
            if not movies:
                return None

            # Filter results
            if year:
                movies = [movie for movie in movies if str(movie.get('year')) == str(year)]
            movies = [movie for movie in movies if movie.get('kind') in ['movie', 'tv series']]
            
            if not movies:
                return None
                
            if bulk:
                return movies

            movie = movies[0]
            movie_id = movie.movieID
            
        except Exception as e:
            logger.error(f"Error searching IMDb: {e}")
            return None
    else:
        movie_id = query

    try:
        movie = imdb.get_movie(movie_id)
        plot = movie.get('plot outline') if LONG_IMDB_DESCRIPTION else (movie.get('plot', [''])[0] if movie.get('plot') else '')
        
        return {
            'title': movie.get('title'),
            'votes': movie.get('votes'),
            'aka': list_to_str(movie.get("akas", [])),
            'seasons': movie.get("number of seasons"),
            'box_office': movie.get('box office'),
            'localized_title': movie.get('localized title'),
            'kind': movie.get("kind"),
            'imdb_id': f"tt{movie.get('imdbID')}",
            'cast': list_to_str(movie.get("cast", [])),
            'runtime': list_to_str(movie.get("runtimes", [])),
            'countries': list_to_str(movie.get("countries", [])),
            'certificates': list_to_str(movie.get("certificates", [])),
            'languages': list_to_str(movie.get("languages", [])),
            'director': list_to_str(movie.get("director", [])),
            'writer': list_to_str(movie.get("writer", [])),
            'producer': list_to_str(movie.get("producer", [])),
            'composer': list_to_str(movie.get("composer", [])),
            'cinematographer': list_to_str(movie.get("cinematographer", [])),
            'music_team': list_to_str(movie.get("music department", [])),
            'distributors': list_to_str(movie.get("distributors", [])),
            'release_date': movie.get('original air date') or movie.get('year'),
            'year': movie.get('year'),
            'genres': list_to_str(movie.get("genres", [])),
            'poster': movie.get('full-size cover url', START_IMG),
            'plot': plot,
            'rating': str(movie.get("rating")),
            'url': f'https://www.imdb.com/title/tt{movie_id}'
        }
    except Exception as e:
        logger.error(f"Error getting movie details: {e}")
        return None

async def broadcast_messages(user_id: int, message: Message, pin: bool = False) -> tuple:
    """Broadcast message to users"""
    try:
        await message.copy(chat_id=user_id)
        return True, "Success"
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await broadcast_messages(user_id, message, pin)
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        return False, "Error"
