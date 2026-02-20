import sys
import os
import logging
import threading
import time
from datetime import datetime

# Настройка подробного логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    from telegram.error import TelegramError
    logger.info("✅ Библиотека telegram импортирована")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта telegram: {e}")
    sys.exit(1)

def check_bot_directly():
    """Прямая проверка бота через Telegram API"""
    
    # ВАШ ТОКЕН - вставьте сюда
    TOKEN = "5164549261:AAEouZbi4I6WB-Gf2ggZOW0NEQsa9MwS4bY"
    ADMIN_ID = "1411829425"
    
    logger.info("="*60)
    logger.info("🔍 ПРЯМАЯ ПРОВЕРКА БОТА")
    logger.info("="*60)
    logger.info(f"Токен: {TOKEN[:10]}...{TOKEN[-5:]}")
    logger.info(f"Admin ID: {ADMIN_ID}")
    
    # Проверка через requests
    try:
        import requests
        logger.info("\n📡 Проверка через Telegram API (requests)...")
        
        # Проверяем токен
        url = f"https://api.telegram.org/bot{TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                bot_info = data['result']
                logger.info(f"✅ Токен работает!")
                logger.info(f"   Имя бота: {bot_info['first_name']}")
                logger.info(f"   Username: @{bot_info['username']}")
                logger.info(f"   ID: {bot_info['id']}")
            else:
                logger.error(f"❌ Ошибка API: {data}")
        else:
            logger.error(f"❌ HTTP ошибка: {response.status_code}")
            logger.error(f"   {response.text}")
            
        # Проверяем отправку сообщения админу
        if ADMIN_ID:
            logger.info(f"\n📤 Отправка тестового сообщения админу {ADMIN_ID}...")
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            data = {
                'chat_id': ADMIN_ID,
                'text': '🔔 Тестовое сообщение от отладчика бота!\n\nЕсли вы это видите - API работает.',
                'parse_mode': 'HTML'
            }
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Сообщение отправлено! Проверьте Telegram.")
            else:
                logger.error(f"❌ Ошибка отправки: {response.status_code}")
                logger.error(f"   {response.text}")
                
    except Exception as e:
        logger.error(f"❌ Ошибка при проверке через requests: {e}")
    
    logger.info("\n" + "="*60)
    logger.info("🤖 ЗАПУСК БОТА ДЛЯ ТЕСТА")
    logger.info("="*60)
    
    # Создаем простого бота для теста
    class TestBot:
        def __init__(self, token):
            self.token = token
            self.application = None
            
        async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            logger.info(f"✅ ПОЛУЧЕНА КОМАНДА /start от {user.id} ({user.first_name})")
            
            await update.message.reply_text(
                f"✅ Бот работает!\n\n"
                f"Ваш ID: {user.id}\n"
                f"Имя: {user.first_name}\n"
                f"Username: @{user.username if user.username else 'нет'}"
            )
            
        async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(
                "Доступные команды:\n"
                "/start - начать\n"
                "/help - помощь\n"
                "/info - информация"
            )
            
        async def info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            chat = update.effective_chat
            
            await update.message.reply_text(
                f"📊 Информация:\n"
                f"User ID: {user.id}\n"
                f"Chat ID: {chat.id}\n"
                f"Chat type: {chat.type}"
            )
            
        async def error(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"❌ Ошибка в боте: {context.error}")
            
        def run(self):
            try:
                logger.info("🔄 Создание приложения...")
                self.application = Application.builder().token(self.token).build()
                
                logger.info("🔄 Регистрация обработчиков...")
                self.application.add_handler(CommandHandler("start", self.start))
                self.application.add_handler(CommandHandler("help", self.help))
                self.application.add_handler(CommandHandler("info", self.info))
                self.application.add_error_handler(self.error)
                
                logger.info("✅ Бот запущен и готов к работе!")
                logger.info("📱 Отправьте команду /start боту в Telegram")
                logger.info("⏳ Ожидание сообщений... (нажмите Ctrl+C для остановки)")
                
                # Запускаем бота
                self.application.run_polling(allowed_updates=Update.ALL_TYPES)
                
            except Exception as e:
                logger.error(f"❌ Ошибка запуска: {e}")
                import traceback
                traceback.print_exc()
    
    # Запускаем тестового бота
    test_bot = TestBot(TOKEN)
    
    try:
        test_bot.run()
    except KeyboardInterrupt:
        logger.info("\n👋 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")

if __name__ == "__main__":
    check_bot_directly()