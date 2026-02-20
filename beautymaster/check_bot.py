import sqlite3
import os
import sys
import threading
import time

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    print("✅ Библиотека telegram импортирована")
except ImportError as e:
    print(f"❌ Ошибка импорта telegram: {e}")
    print("Установите: pip install python-telegram-bot==20.7")
    sys.exit(1)

def check_bot_for_master(master_id=1):
    """Проверка бота для конкретного мастера"""
    
    # Путь к базе данных мастера
    db_path = os.path.join('plugins', 'beautymaster', 'databases', f'master_{master_id}.db')
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"\n📁 База данных: {db_path}")
    
    # Подключаемся к базе
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Получаем настройки бота
    cursor.execute('SELECT telegram_bot_token, telegram_admin_id, telegram_notifications FROM master_profile LIMIT 1')
    profile = cursor.fetchone()
    
    if not profile:
        print("❌ Профиль мастера не найден")
        conn.close()
        return
    
    token, admin_id, notifications = profile
    
    print(f"\n🤖 Настройки бота:")
    print(f"   Токен: {'✅ Установлен' if token else '❌ Не установлен'}")
    print(f"   Admin ID: {admin_id or '❌ Не указан'}")
    print(f"   Включен: {'✅ Да' if notifications else '❌ Нет'}")
    
    if not token or not notifications:
        print("\n❌ Бот не настроен или отключен")
        conn.close()
        return
    
    # Проверяем, запущен ли бот
    print(f"\n🔍 Проверка бота с токеном: {token[:10]}...{token[-5:] if token else ''}")
    
    try:
        # Создаем простое приложение для проверки
        application = Application.builder().token(token).build()
        
        # Проверяем, можем ли получить информацию о боте
        import asyncio
        
        async def get_bot_info():
            bot = application.bot
            me = await bot.get_me()
            return me
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        bot_info = loop.run_until_complete(get_bot_info())
        loop.close()
        
        print(f"✅ Бот подключен!")
        print(f"   Имя: {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   ID: {bot_info.id}")
        
        # Проверяем, может ли бот отправить сообщение админу
        if admin_id:
            print(f"\n📤 Отправка тестового сообщения админу {admin_id}...")
            
            async def send_test():
                await bot.send_message(
                    chat_id=admin_id,
                    text="🔔 **Проверка бота!**\n\nЕсли вы это видите, бот работает правильно."
                )
                return True
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(send_test())
                loop.close()
                print("✅ Тестовое сообщение отправлено!")
            except Exception as e:
                print(f"❌ Не удалось отправить сообщение: {e}")
                print("   Возможно, админ не начал диалог с ботом")
        
    except Exception as e:
        print(f"❌ Ошибка подключения к Telegram: {e}")
    
    conn.close()

def check_all_masters():
    """Проверка всех мастеров"""
    databases_dir = os.path.join('plugins', 'beautymaster', 'databases')
    
    if not os.path.exists(databases_dir):
        print(f"❌ Папка с базами данных не найдена: {databases_dir}")
        return
    
    print("="*60)
    print("🔍 ПРОВЕРКА TELEGRAM БОТОВ")
    print("="*60)
    
    for file in os.listdir(databases_dir):
        if file.startswith('master_') and file.endswith('.db'):
            master_id = file.replace('master_', '').replace('.db', '')
            try:
                master_id = int(master_id)
                check_bot_for_master(master_id)
                print("-"*60)
            except:
                pass

if __name__ == '__main__':
    check_all_masters()
    
    print("\n" + "="*60)
    print("📋 ИНСТРУКЦИЯ:")
    print("="*60)
    print("1. Убедитесь, что бот включен в настройках")
    print("2. Напишите боту команду /start в Telegram")
    print("3. Проверьте логи сервера (должны появиться сообщения)")
    print("4. Если бот не отвечает, перезапустите его в интерфейсе")