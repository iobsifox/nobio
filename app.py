import os
import asyncio
import logging
from datetime import datetime
import pytz
from auth_manager import AuthManager

# تنظیمات لاگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NOBioUserBot:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            logger.error("❌ DATABASE_URL تنظیم نشده است!")
            raise ValueError("DATABASE_URL required")
        self.auth_manager = AuthManager(self.db_url)
        
    def get_tehran_time(self):
        """دریافت زمان تهران"""
        try:
            tehran_tz = pytz.timezone('Asia/Tehran')
            return datetime.now(tehran_tz).strftime('%H:%M')
        except:
            return datetime.now().strftime('%H:%M')
    
    async def update_all_profiles(self):
        """آپدیت پروفایل تمام کاربران فعال"""
        logger.info("🔄 شروع آپدیت پروفایل‌ها...")
        
        users = await self.auth_manager.get_active_users()
        if not users:
            logger.info("📭 کاربر فعالی یافت نشد")
            return 0
        
        logger.info(f"📊 تعداد کاربران فعال: {len(users)}")
        
        success_count = 0
        for user in users:
            try:
                logger.info(f"🔧 پردازش کاربر: {user['phone']}")
                
                # آپدیت پروفایل
                result = await self.auth_manager.update_user_profile(user)
                if result:
                    success_count += 1
                    logger.info(f"✅ پروفایل کاربر {user['phone']} آپدیت شد")
                else:
                    logger.warning(f"⚠️ آپدیت پروفایل کاربر {user['phone']} ناموفق بود")
                
                # تأخیر بین آپدیت‌ها
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"❌ خطا در پردازش کاربر {user.get('phone', 'Unknown')}: {str(e)}")
                continue
        
        logger.info(f"🎯 آپدیت کامل شد: {success_count}/{len(users)} موفق")
        return success_count

async def main():
    """تابع اصلی - اجرای دوره‌ای"""
    logger.info("🚀 NOBio User Bot Worker Started!")
    
    while True:
        try:
            bot = NOBioUserBot()
            success_count = await bot.update_all_profiles()
            logger.info(f"🏁 کار به پایان رسید. {success_count} پروفایل آپدیت شد")
            
            # خواب ۱ دقیقه‌ای
            logger.info("💤 خواب به مدت 60 ثانیه...")
            await asyncio.sleep(60)
            
        except Exception as e:
            logger.error(f"💥 خطای کلی: {str(e)}")
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main())
