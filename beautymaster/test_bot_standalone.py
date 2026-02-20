#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Тестовый бот для проверки работы Telegram API
Запустите этот файл отдельно от CRM
"""

import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== Токен бота ==========
# ВСТАВЬТЕ СВОЙ ТОКЕН СЮДА
BOT_TOKEN = "5164549261:AAEouZbi4I6WB-Gf2ggZOW0NEQsa9MwS4bY"  # Замените на ваш реальный токен

# ========== Обработчики команд ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"🤖 Команда /start от пользователя {user.id} ({user.first_name})")
    
    # Создаем клавиатуру
    keyboard = [
        [InlineKeyboardButton("📅 Записаться", callback_data="book")],
        [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")],
        [InlineKeyboardButton("ℹ️ Услуги", callback_data="services")],
        [InlineKeyboardButton("📞 Контакты", callback_data="contacts")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветственное сообщение
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Я тестовый бот для Beauty Master CRM.\n"
        f"Если ты это видишь - бот работает правильно!\n\n"
        f"Твой ID: {user.id}\n\n"
        f"Выбери действие:",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if query.data == "book":
        await query.edit_message_text(
            f"📅 Ты выбрал 'Записаться'\n\n"
            f"Это тестовый режим. В реальном боте здесь был бы выбор услуг и времени."
        )
    elif query.data == "my_bookings":
        await query.edit_message_text(
            f"📋 Твои записи:\n\n"
            f"У тебя пока нет записей. Это тестовый режим."
        )
    elif query.data == "services":
        await query.edit_message_text(
            f"ℹ️ Наши услуги:\n\n"
            f"• Стрижка - 1500₽\n"
            f"• Окрашивание - 3000₽\n"
            f"• Маникюр - 1200₽\n\n"
            f"Это тестовый список."
        )
    elif query.data == "contacts":
        await query.edit_message_text(
            f"📞 Контакты:\n\n"
            f"Телефон: +7 (999) 123-45-67\n"
            f"Адрес: ул. Тестовая, д. 1\n\n"
            f"Это тестовые данные."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "🆘 Помощь:\n\n"
        "/start - начать работу\n"
        "/help - это сообщение\n"
        "/info - информация о боте\n"
        "/stop - остановить бота"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /info"""
    user = update.effective_user
    chat = update.effective_chat
    
    await update.message.reply_text(
        f"ℹ️ Информация:\n\n"
        f"• Твой ID: {user.id}\n"
        f"• Твой username: @{user.username if user.username else 'не указан'}\n"
        f"• Имя: {user.first_name}\n"
        f"• Чат ID: {chat.id}\n"
        f"• Тип чата: {chat.type}\n\n"
        f"Бот работает в тестовом режиме."
    )

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stop"""
    await update.message.reply_text(
        "👋 До свидания! Чтобы снова запустить бота, напиши /start"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ Произошла ошибка. Попробуйте позже."
            )
    except:
        pass

def main():
    """Главная функция запуска бота"""
    print("\n" + "="*60)
    print("🤖 ТЕСТОВЫЙ БОТ ДЛЯ BEAUTY MASTER")
    print("="*60)
    print(f"Токен: {BOT_TOKEN[:10]}...{BOT_TOKEN[-5:] if len(BOT_TOKEN) > 15 else 'не указан'}")
    print("\n⚠️  Убедитесь что токен правильный!")
    print("📱 Откройте Telegram и напишите /start вашему боту")
    print("="*60 + "\n")
    
    if BOT_TOKEN == "ВАШ_ТОКЕН_СЮДА" or len(BOT_TOKEN) < 10:
        print("❌ ОШИБКА: Не указан токен бота!")
        print("📝 Отредактируйте файл и вставьте свой токен в строку BOT_TOKEN")
        return
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("info", info_command))
        application.add_handler(CommandHandler("stop", stop_command))
        
        # Регистрируем обработчик кнопок
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # Регистрируем обработчик ошибок
        application.add_error_handler(error_handler)
        
        print("✅ Бот запущен и готов к работе!")
        print("📋 Нажмите Ctrl+C для остановки\n")
        
        # Запускаем бота
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Бот остановлен")