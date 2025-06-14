import logging
from struct import pack
import re
import asyncio
from typing import Dict, List, Union
from datetime import datetime
from pymongo.errors import DuplicateKeyError
from umongo import MotorAsyncIOInstance, Document, fields
from motor.motor_asyncio import AsyncIOMotorClient
from marshmallow.exceptions import ValidationError
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

client = AsyncIOMotorClient(DATABASE_URI)
database = client[DATABASE_NAME]
instance = MotorAsyncIOInstance(database)  # Changed from Instance to MotorAsyncIOInstance

@instance.register
class Media(Document):
    file_id = fields.StrField(attribute='_id')
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    
    class Meta:
        collection_name = COLLECTION_NAME
        indexes = [
            {'key': ['file_id'], 'unique': True},
            {'key': ['file_name'], 'unique': False}
        ]

    @classmethod
    async def ensure_indexes(cls):
        """Create required indexes"""
        try:
            await cls.ensure_all_indexes()
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating database indexes: {e}")

async def save_file(media: Media) -> bool:
    """Save file in database"""
    try:
        await media.commit()
        return True
    except DuplicateKeyError:
        logger.warning(
            f"{media.file_name} is already saved in database"
        )
        return False
    except ValidationError as e:
        logger.error(f"Error occurred while saving file in database: {e}")
        return False
    except Exception as e:
        logger.error(f"Error occurred while saving file: {e}")
        return False

async def get_search_results(query: str, file_type: str = None, max_results: int = 10, offset: int = 0) -> List[Media]:
    """For given query return list of results"""
    try:
        query = query.strip()
        if not query:
            raw_pattern = "."
        elif ' ' not in query:
            raw_pattern = r"(\b|[\.\+\-_])"+query+"(\b|[\.\+\-_])"
        else:
            raw_pattern = query.replace(' ', r".*[\s\.\+\-_]")
            
        try:
            reg_pattern = re.compile(raw_pattern, re.IGNORECASE)
        except:
            reg_pattern = re.compile(r".")
            
        filter_dict = {'file_name': reg_pattern}
        if file_type:
            filter_dict['file_type'] = file_type
            
        total_results = await Media.count_documents(filter_dict)
        next_offset = offset + max_results

        if next_offset > total_results:
            next_offset = ''
            
        cursor = Media.find(filter_dict)
        cursor.skip(offset).limit(max_results)
        files = await cursor.to_list(length=max_results)
        
        return files, next_offset, total_results
    except Exception as e:
        logger.error(f"Error occurred while getting search results: {e}")
        return [], '', 0

async def get_file_details(query: str) -> List[Media]:
    """For given query return list of files"""
    try:
        cursor = Media.find({'file_id': query})
        filedetails = await cursor.to_list(length=1)
        return filedetails
    except Exception as e:
        logger.error(f"Error occurred while getting file details: {e}")
        return []
