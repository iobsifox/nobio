import os
import asyncio
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    ApiIdInvalidError,
    FloodWaitError
)
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.sessions import StringSession

logger = logging.getLogger(__name__)

class AuthManager:
    def __init__(self, db_url):
        self.db_url = db_url
    
    def get_db_connection(self):
        """اتصال به دیتابیس"""
        return psycopg2.connect(self.db_url, cursor_factory=RealDictCursor)
    
    async def get_active_users(self):
        """دریافت کاربران فعال"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, uuid, telegram_id, api_id, api_hash, phone, 
                           first_name, last_name, bio, clock_enabled, session_string
                    FROM users 
                    WHERE status = 'active' 
                    AND api_id IS NOT NULL 
                    AND api_hash IS NOT NULL 
                    AND phone IS NOT NULL
                    AND session_string IS NOT NULL
                """)
                return cur.fetchall()
        except Exception as e:
            logger.error(f"خطا در دریافت کاربران: {e}")
            return []
        finally:
            conn.close()
    
    async def connect_with_session(self, user):
        """اتصال با استفاده از session string"""
        try:
            session = StringSession(user['session_string'])
            client = TelegramClient(
                session=session,
                api_id=int(user['api_id']),
                api_hash=user['api_hash']
            )
            
            await client.connect()
            
            if await client.is_user_authorized():
                logger.info(f"✅ اتصال با session موفق برای {user['phone']}")
                return client
            else:
                logger.warning(f"❌ Session منقضی شده برای {user['phone']}")
                await client.disconnect()
                return None
                
        except Exception as e:
            logger.error(f"❌ خطا در اتصال با session برای {user['phone']}: {e}")
            return None
    
    async def update_user_profile(self, user):
        """آپدیت پروفایل کاربر"""
        try:
            client = await self.connect_with_session(user)
            
            if not client:
                logger.warning(f"⚠️ امکان اتصال برای {user['phone']} وجود ندارد")
                await self.log_update(user['id'], 'profile_update', False, 'No valid session')
                return False
            
            # آماده‌سازی اطلاعات
            first_name = user['first_name'] or ""
            last_name = user['last_name'] or ""
            bio = user['bio'] or ""
            
            # اضافه کردن زمان به بیو
            if user['clock_enabled']:
                from app import NOBioUserBot
                temp_bot = NOBioUserBot()
                tehran_time = temp_bot.get_tehran_time()
                
                if '{time}' in bio:
                    bio = bio.replace('{time}', tehran_time)
                elif bio:
                    bio = f"{bio} 🕐 {tehran_time}"
                else:
                    bio = f"🕐 {tehran_time}"
            
            # آپدیت پروفایل
            await client(UpdateProfileRequest(
                first_name=first_name,
                last_name=last_name,
                about=bio
            ))
            
            await client.disconnect()
            await self.log_update(user['id'], 'profile_update', True, '')
            logger.info(f"✅ پروفایل {user['phone']} آپدیت شد")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطا در آپدیت پروفایل {user['phone']}: {e}")
            await self.log_update(user['id'], 'profile_update', False, str(e))
            return False
    
    async def log_update(self, user_id, update_type, success, error_message=''):
        """لاگ کردن آپدیت‌ها"""
        conn = self.get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO update_logs 
                    (user_id, update_type, success, error_message, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (user_id, update_type, success, error_message))
                conn.commit()
        except Exception as e:
            logger.error(f"خطا در لاگ کردن: {e}")
        finally:
            conn.close()
