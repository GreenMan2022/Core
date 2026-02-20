import asyncio
import threading
import logging
from datetime import datetime, timedelta, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
import sys
import traceback
import re

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class BotInstance:
    """Отдельный экземпляр бота для одного мастера"""

    def __init__(self, master_id: str, token: str, admin_id: str | None, plugin):
        self.master_id = master_id
        self.token = token.strip()
        self.admin_id = admin_id
        self.plugin = plugin
        self.application: Application | None = None
        self.loop = None
        self.running = False
        self.thread: threading.Thread | None = None
        logger.info(f"🤖 Создан экземпляр бота для мастера {master_id}")

    def start(self):
        """Запуск бота в отдельном потоке"""
        if self.running:
            logger.warning(f"Бот {self.master_id} уже запущен")
            return

        self.thread = threading.Thread(target=self._run_bot, daemon=True)
        self.thread.start()
        logger.info(f"✅ Поток бота для мастера {self.master_id} запущен")

    def _run_bot(self):
        """Запуск бота в собственном event loop"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            print(f"\n🚀 [МАСТЕР {self.master_id}] ЗАПУСК БОТА")
            print(f"   Токен: {self.token[:10]}...{self.token[-5:]}")
            print(f"   Admin ID: {self.admin_id}")
            sys.stdout.flush()

            if not self.token:
                print(f"❌ [МАСТЕР {self.master_id}] Токен отсутствует!")
                return

            self.application = Application.builder().token(self.token).build()

            # Регистрация обработчиков
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CallbackQueryHandler(self.button_handler))
            self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
            self.application.add_error_handler(self.error_handler)

            print(f"✅ [МАСТЕР {self.master_id}] Бот инициализирован")
            sys.stdout.flush()

            self.running = True

            # Запуск polling с drop_pending_updates
            self.loop.run_until_complete(self.application.initialize())
            self.loop.run_until_complete(self.application.start())
            self.loop.run_until_complete(
                self.application.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True,
                    poll_interval=0.5,
                    timeout=10,
                )
            )

            self.loop.run_forever()

        except Exception as e:
            logger.exception(f"Критическая ошибка в боте {self.master_id}")
            print(f"❌ [МАСТЕР {self.master_id}] Ошибка: {e}")
            traceback.print_exc()
            sys.stdout.flush()
        finally:
            self.running = False
            if self.application:
                try:
                    self.loop.run_until_complete(self.application.updater.stop())
                    self.loop.run_until_complete(self.application.stop())
                    self.loop.run_until_complete(self.application.shutdown())
                except Exception as e:
                    logger.error(f"Ошибка graceful shutdown: {e}")
            self.loop.close()
            print(f"⏹ [МАСТЕР {self.master_id}] Бот остановлен")
            sys.stdout.flush()

    def stop(self):
        """Остановка бота (вызывается из главного потока)"""
        if not self.running:
            return

        if self.application and self.application.updater and self.loop:
            try:
                future = asyncio.run_coroutine_threadsafe(self._async_stop(), self.loop)
                future.result(timeout=8.0)
            except Exception as e:
                logger.error(f"Ошибка остановки бота {self.master_id}: {e}")

        self.running = False
        logger.info(f"⏹ Бот для мастера {self.master_id} остановлен")

    async def _async_stop(self):
        if self.application:
            await self.application.updater.stop()
            await self.application.stop()
            await self.application.shutdown()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        try:
            user = update.effective_user
            logger.info(f"🤖 [МАСТЕР {self.master_id}] КОМАНДА /start от {user.id} ({user.first_name})")

            from .models import DatabaseManager
            db = DatabaseManager(self.master_id)

            client = db.get_client_by_telegram(str(user.id))

            if client:
                welcome_text = f"👋 С возвращением, {client['name']}!\n\n"
                context.user_data['client_id'] = client['id']
            else:
                welcome_text = "👋 Добро пожаловать! Я помогу вам записаться на услуги.\n\n"

            keyboard = [
                [InlineKeyboardButton("📅 Записаться", callback_data="book")],
                [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")],
                [InlineKeyboardButton("ℹ️ Услуги", callback_data="services")],
                [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
                [InlineKeyboardButton("📨 Связаться с админом", callback_data="contact_admin")],
            ]

            if self.admin_id and str(user.id) == str(self.admin_id):
                keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin")])

            await update.message.reply_text(
                welcome_text + "Выберите действие:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")

    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик кнопок"""
        query = update.callback_query
        await query.answer()

        data = query.data
        user_id = query.from_user.id
        logger.info(f"🤖 [МАСТЕР {self.master_id}] Кнопка {data} от {user_id}")

        try:
            if data == "book":
                await self.show_services(query, context)
            elif data == "my_bookings":
                await self.show_my_bookings(query, context)
            elif data == "services":
                await self.show_services_list(query, context)
            elif data == "contacts":
                await self.show_contacts(query, context)
            elif data == "admin":
                await self.show_admin_panel(query, context)
            elif data == "main_menu":
                await self.show_main_menu(query, context)
            elif data == "contact_admin":
                await self.contact_admin_start(query, context)
            elif data.startswith("service_"):
                service_id = int(data.split("_")[1])
                context.user_data['selected_service'] = service_id
                await self.select_date(query, context)
            elif data.startswith("date_"):
                date_str = data.split("_")[1]
                if self._is_date_in_past(date_str):
                    await query.edit_message_text("❌ Нельзя записаться в прошлое")
                    return
                context.user_data['selected_date'] = date_str
                await self.select_time(query, context)
            elif data.startswith("time_"):
                time_str = data.split("_")[1]
                context.user_data['selected_time'] = time_str
                await self.confirm_booking(query, context)
            elif data == "confirm_booking":
                await self.save_booking(query, context)
            elif data.startswith("cancel_booking_"):
                booking_id = int(data.split("_")[2])
                await self.cancel_booking(query, context, booking_id)
            elif data.startswith("admin_cancel_"):
                booking_id = int(data.split("_")[2])
                await self.admin_cancel_booking(query, context, booking_id)
        except Exception as e:
            logger.error(f"Ошибка в button_handler: {e}")
            await query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")

    def _is_date_in_past(self, date_str: str) -> bool:
        try:
            selected_date = date.fromisoformat(date_str)
            return selected_date < date.today()
        except ValueError:
            return True

    async def show_services(self, query, context):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)
        services = db.get_services(active_only=True)

        if not services:
            await query.edit_message_text(
                "😕 Услуги временно недоступны.",
                reply_markup=self._back_button("main_menu")
            )
            return

        keyboard = []
        for s in services:
            keyboard.append([InlineKeyboardButton(
                f"{s['name']} — {s['price']}₽ ({s['duration']} мин)",
                callback_data=f"service_{s['id']}"
            )])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main_menu")])

        await query.edit_message_text(
            "📋 Выберите услугу:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_services_list(self, query, context):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)
        services = db.get_services(active_only=True)

        if not services:
            await query.edit_message_text("😕 Нет активных услуг.")
            return

        text = "📋 Наши услуги:\n\n"
        for s in services:
            text += f"• {s['name']} — {s['price']}₽ ({s['duration']} мин)\n{s['description']}\n\n"

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_contacts(self, query, context):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)
        profile = db.get_profile()

        text = "📞 Контакты:\n\n"
        text += f"🏢 Салон: {profile.get('salon_name', '—')}\n"
        text += f"📱 Телефон: {profile.get('phone', '—')}\n"
        text += f"📍 Адрес: {profile.get('address', '—')}\n"
        text += f"\nℹ️ {profile.get('description', '')}"

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="main_menu")]]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_admin_panel(self, query, context):
        keyboard = [
            [InlineKeyboardButton("📅 Расписание на сегодня", callback_data="admin_today")],
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("👥 Клиенты", callback_data="admin_clients")],
            [InlineKeyboardButton("⚙️ Настройки", callback_data="admin_settings")],
            [InlineKeyboardButton("◀️ Назад", callback_data="main_menu")],
        ]

        await query.edit_message_text(
            "⚙️ Админ панель:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_main_menu(self, query, context):
        keyboard = [
            [InlineKeyboardButton("📅 Записаться", callback_data="book")],
            [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")],
            [InlineKeyboardButton("ℹ️ Услуги", callback_data="services")],
            [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
            [InlineKeyboardButton("📨 Связаться с админом", callback_data="contact_admin")],
        ]
        
        if self.admin_id and str(query.from_user.id) == str(self.admin_id):
            keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin")])

        await query.edit_message_text(
            "👋 **Главное меню:**\n\nВыберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def contact_admin_start(self, query, context):
        context.user_data['contact_admin'] = True
        await query.edit_message_text(
            "📨 Напишите ваше сообщение для администратора:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Отмена", callback_data="main_menu")]])
        )

    async def select_date(self, query, context):
        today = date.today()
        keyboard = []

        for i in range(14):
            d = today + timedelta(days=i)
            date_str = d.isoformat()
            display = d.strftime("%d.%m.%Y")
            weekday = "Пн Вт Ср Чт Пт Сб Вс".split()[d.weekday()]
            keyboard.append([InlineKeyboardButton(
                f"📅 {display} ({weekday})",
                callback_data=f"date_{date_str}"
            )])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="book")])

        await query.edit_message_text(
            "📅 Выберите дату:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def select_time(self, query, context):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)

        selected_date = context.user_data.get('selected_date')
        if not selected_date:
            await query.edit_message_text("❌ Дата не выбрана")
            return

        # Получаем расписание для дня недели
        day_of_week = datetime.fromisoformat(selected_date).weekday()
        schedule = db.get_schedule()
        day_schedule = next((s for s in schedule if s['day_of_week'] == day_of_week), None)

        if not day_schedule or not day_schedule.get('is_working'):
            await query.edit_message_text("❌ В этот день нет работы")
            return

        start_time = datetime.strptime(day_schedule['start_time'], '%H:%M').time()
        end_time = datetime.strptime(day_schedule['end_time'], '%H:%M').time()

        # Генерируем слоты с шагом 30 минут
        current_time = datetime.combine(date.today(), start_time)
        end_datetime = datetime.combine(date.today(), end_time)

        keyboard = []
        while current_time < end_datetime:
            time_str = current_time.strftime('%H:%M')
            keyboard.append([InlineKeyboardButton(f"🕐 {time_str}", callback_data=f"time_{time_str}")])
            current_time += timedelta(minutes=30)

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"date_{selected_date}")])

        await query.edit_message_text(
            f"📅 Дата: {selected_date}\nВыберите время:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def confirm_booking(self, query, context):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)

        service_id = context.user_data.get('selected_service')
        date_str = context.user_data.get('selected_date')
        time_str = context.user_data.get('selected_time')

        if not all([service_id, date_str, time_str]):
            await query.edit_message_text("❌ Не все данные выбраны")
            return

        service = db.get_service(service_id)
        if not service:
            await query.edit_message_text("❌ Услуга не найдена")
            return

        user = query.from_user
        client = db.get_client_by_telegram(str(user.id))

        if not client:
            context.user_data['temp_booking'] = {
                'service_id': service_id,
                'date': date_str,
                'time': time_str
            }
            context.user_data['reg_step'] = 'name'
            await query.edit_message_text(
                "📝 **Добро пожаловать! Для записи нужно зарегистрироваться**\n\n"
                "✏️ Шаг 1 из 4: Введите ваше **Имя и Фамилию**:",
                parse_mode='Markdown'
            )
            return

        text = (
            f"📋 **Подтверждение записи**\n\n"
            f"💇 Услуга: {service['name']}\n"
            f"💰 Цена: {service['price']}₽\n"
            f"⏱ Длительность: {service['duration']} мин\n"
            f"📅 Дата: {date_str}\n"
            f"🕐 Время: {time_str}\n\n"
            f"Всё верно?"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data="confirm_booking"),
                InlineKeyboardButton("❌ Нет", callback_data="book")
            ]
        ]

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def save_booking(self, query, context):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)

        service_id = context.user_data.get('selected_service')
        date_str = context.user_data.get('selected_date')
        time_str = context.user_data.get('selected_time')

        if not all([service_id, date_str, time_str]):
            await query.edit_message_text("❌ Не все данные выбраны")
            return

        user = query.from_user
        client = db.get_client_by_telegram(str(user.id))

        if not client:
            # Создаём нового клиента
            client_data = {
                'name': user.first_name or f"Гость_{user.id}",
                'phone': '',
                'telegram_id': str(user.id),
                'telegram_notifications': 1
            }
            client_id = db.add_client(client_data)
            client = db.get_client(client_id)
            await self.notify_admin_about_new_client(context, client)

        service = db.get_service(service_id)
        if not service:
            await query.edit_message_text("❌ Услуга не найдена")
            return

        booking_data = {
            'client_id': client['id'],
            'service_id': service_id,
            'date': date_str,
            'time': time_str,
            'duration': service['duration'],
            'status': 'confirmed',
            'notes': 'Запись через Telegram бота'
        }

        booking_id = db.add_booking(booking_data)
        booking = db.get_booking(booking_id)

        # Отправляем уведомление админу
        await self.notify_admin_about_new_booking(context, booking, client, service)

        # Отправляем подтверждение клиенту
        await query.edit_message_text(
            f"✅ **Запись подтверждена!**\n\n"
            f"Спасибо, {client['name']}!\n"
            f"📅 {date_str} в {time_str}\n"
            f"💇 {service['name']}\n\n"
            f"Я напомню вам за день до визита.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")],
                [InlineKeyboardButton("◀️ В меню", callback_data="main_menu")]
            ]),
            parse_mode='Markdown'
        )

        self._clear_user_data(context)

    async def cancel_booking(self, query, context, booking_id):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)

        booking = db.get_booking(booking_id)
        if not booking or booking['status'] != 'confirmed':
            await query.edit_message_text("❌ Запись не найдена или уже отменена")
            return

        db.update_booking(booking_id, {'status': 'cancelled'})

        client = db.get_client(booking['client_id'])
        service = db.get_service(booking['service_id'])

        await self.notify_admin_about_cancellation(context, booking, client, service)

        await query.edit_message_text(
            f"✅ **Запись отменена**\n\n"
            f"📅 {booking['date']} {booking['time']}\n"
            f"💇 {service['name']}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ В меню", callback_data="main_menu")
            ]]),
            parse_mode='Markdown'
        )

    async def admin_cancel_booking(self, query, context, booking_id):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)

        booking = db.get_booking(booking_id)
        if not booking:
            await query.edit_message_text("❌ Запись не найдена")
            return

        if booking['status'] != 'confirmed':
            await query.edit_message_text("❌ Запись уже отменена")
            return

        db.update_booking(booking_id, {'status': 'cancelled_by_admin'})

        client = db.get_client(booking['client_id'])
        service = db.get_service(booking['service_id'])

        # Уведомление клиенту
        if client.get('telegram_id') and client.get('telegram_notifications', 1):
            try:
                message = (
                    f"❌ Ваша запись отменена администратором\n\n"
                    f"💇 Услуга: {service['name']}\n"
                    f"📅 Дата: {booking['date']} {booking['time']}\n\n"
                    f"Свяжитесь с нами для деталей."
                )
                await context.bot.send_message(
                    chat_id=client['telegram_id'],
                    text=message
                )
                logger.info(f"✅ Уведомление клиенту {client['telegram_id']} отправлено")
            except Exception as e:
                logger.error(f"Ошибка уведомления клиента {client['telegram_id']}: {e}")

        await query.edit_message_text(
            "✅ Запись отменена, клиент уведомлён",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ В меню", callback_data="main_menu")
            ]])
        )

    async def show_my_bookings(self, query, context):
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)

        user_id = query.from_user.id
        client = db.get_client_by_telegram(str(user_id))
        if not client:
            await query.edit_message_text(
                "📭 У вас пока нет записей.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📅 Записаться", callback_data="book")
                ]])
            )
            return

        today = date.today().isoformat()
        all_bookings = db.get_bookings(client_id=client['id'])
        upcoming = [b for b in all_bookings if b['date'] >= today and b['status'] == 'confirmed']

        if not upcoming:
            await query.edit_message_text(
                "📭 У вас нет предстоящих записей.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("📅 Записаться", callback_data="book")
                ]])
            )
            return

        text = "📋 **Ваши записи:**\n\n"
        keyboard = []
        for b in upcoming:
            service = db.get_service(b['service_id'])
            text += f"📅 {b['date']} {b['time']}\n💇 {service['name']}\n\n"
            keyboard.append([InlineKeyboardButton(
                f"❌ Отменить {b['date']} {b['time']}",
                callback_data=f"cancel_booking_{b['id']}"
            )])

        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main_menu")])

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text
        user = update.effective_user

        if context.user_data.get('reg_step'):
            await self.handle_registration(update, context, text)
        elif context.user_data.get('contact_admin'):
            await self.send_to_admin(update, context, text)
        else:
            keyboard = [
                [InlineKeyboardButton("📅 Записаться", callback_data="book")],
                [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")],
                [InlineKeyboardButton("ℹ️ Услуги", callback_data="services")],
                [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
                [InlineKeyboardButton("📨 Связаться с админом", callback_data="contact_admin")],
            ]
            await update.message.reply_text(
                "👋 Используйте кнопки меню:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def handle_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Полная регистрация с валидацией"""
        step = context.user_data.get('reg_step')
        temp = context.user_data.get('temp_booking', {})

        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)

        # Шаг 1: Имя
        if step == 'name':
            if len(text.strip()) < 3:
                await update.message.reply_text(
                    "❌ Пожалуйста, введите корректное имя (минимум 3 символа):"
                )
                return

            context.user_data['reg_name'] = text.strip()
            context.user_data['reg_step'] = 'phone'
            await update.message.reply_text(
                "📞 **Шаг 2 из 4:**\n\n"
                "Введите ваш **номер телефона** (например: +7 999 123-45-67):",
                parse_mode='Markdown'
            )

        # Шаг 2: Телефон с форматированием
        elif step == 'phone':
            # Очищаем от лишних символов
            phone = ''.join(filter(str.isdigit, text))

            if len(phone) < 10 or len(phone) > 11:
                await update.message.reply_text(
                    "❌ Неверный формат телефона.\n\n"
                    "Введите номер в формате: +7 999 123-45-67"
                )
                return

            # Приводим к единому формату
            if len(phone) == 10:
                phone = f"7{phone}"
            elif len(phone) == 11 and phone.startswith('8'):
                phone = f"7{phone[1:]}"

            # Форматируем для красоты
            formatted_phone = f"+7 ({phone[1:4]}) {phone[4:7]}-{phone[7:9]}-{phone[9:11]}"

            context.user_data['reg_phone'] = formatted_phone
            context.user_data['reg_step'] = 'birthday'
            await update.message.reply_text(
                "🎂 **Шаг 3 из 4:**\n\n"
                "Введите вашу **дату рождения** (необязательно):\n\n"
                "📅 Формат: ДД.ММ.ГГГГ\n\n"
                "Или отправьте \"пропустить\":",
                parse_mode='Markdown'
            )

        # Шаг 3: Дата рождения с валидацией
        elif step == 'birthday':
            birthday = None

            if text.lower() not in ['пропустить', 'skip', '-', 'нет']:
                try:
                    # Пробуем разные форматы
                    for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d']:
                        try:
                            birthday = datetime.strptime(text, fmt).date()
                            break
                        except:
                            continue

                    if not birthday:
                        raise ValueError("Неверный формат")

                    if birthday > date.today():
                        await update.message.reply_text(
                            "❌ Дата рождения не может быть в будущем. Попробуйте еще раз:"
                        )
                        return

                    age = (date.today() - birthday).days / 365.25
                    if age < 10:
                        await update.message.reply_text(
                            "❌ Вам должно быть не менее 10 лет. Попробуйте еще раз:"
                        )
                        return

                except:
                    await update.message.reply_text(
                        "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ\n"
                        "Или отправьте \"пропустить\":"
                    )
                    return

            context.user_data['reg_birthday'] = birthday.isoformat() if birthday else None
            context.user_data['reg_step'] = 'email'
            await update.message.reply_text(
                "📧 **Шаг 4 из 4:**\n\n"
                "Введите ваш **Email** (необязательно):\n\n"
                "📨 Например: name@example.com\n\n"
                "Или отправьте \"пропустить\":",
                parse_mode='Markdown'
            )

        # Шаг 4: Email с проверкой
        elif step == 'email':
            email = None

            if text.lower() not in ['пропустить', 'skip', '-', 'нет']:
                # Простая проверка email
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if re.match(email_pattern, text):
                    email = text.strip()
                else:
                    await update.message.reply_text(
                        "❌ Неверный формат email. Попробуйте еще раз\n"
                        "Или отправьте \"пропустить\":"
                    )
                    return

            # Сохраняем клиента
            client_data = {
                'name': context.user_data['reg_name'],
                'phone': context.user_data['reg_phone'],
                'email': email or '',
                'birth_date': context.user_data.get('reg_birthday'),
                'telegram_id': str(update.effective_user.id),
                'telegram_notifications': 1,
                'notes': f'Зарегистрирован через бота {datetime.now().strftime("%d.%m.%Y")}'
            }

            client_id = db.add_client(client_data)
            client = db.get_client(client_id)

            # Уведомление админу
            await self.notify_admin_about_new_client(context, client)

            # Приветственное сообщение
            await update.message.reply_text(
                f"✅ **Регистрация завершена!**\n\n"
                f"👤 Имя: {client_data['name']}\n"
                f"📞 Телефон: {client_data['phone']}\n"
                f"🎂 День рождения: {client_data['birth_date'] or 'не указан'}\n"
                f"📧 Email: {client_data['email'] or 'не указан'}\n\n"
                f"Спасибо за регистрацию! 🎉",
                parse_mode='Markdown'
            )

            # Если есть временное бронирование
            if temp:
                context.user_data['selected_service'] = temp.get('service_id')
                context.user_data['selected_date'] = temp.get('date')
                context.user_data['selected_time'] = temp.get('time')
                context.user_data.pop('temp_booking', None)

                service = db.get_service(temp['service_id'])
                text_confirm = (
                    f"📋 **Подтверждение записи**\n\n"
                    f"💇 Услуга: {service['name']}\n"
                    f"💰 Цена: {service['price']}₽\n"
                    f"📅 Дата: {temp['date']}\n"
                    f"🕐 Время: {temp['time']}\n\n"
                    f"Всё верно?"
                )

                keyboard = [
                    [
                        InlineKeyboardButton("✅ Да", callback_data="confirm_booking"),
                        InlineKeyboardButton("❌ Нет", callback_data="book")
                    ]
                ]

                await update.message.reply_text(
                    text_confirm,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                # Показываем меню
                keyboard = [
                    [InlineKeyboardButton("📅 Записаться", callback_data="book")],
                    [InlineKeyboardButton("📋 Мои записи", callback_data="my_bookings")],
                    [InlineKeyboardButton("ℹ️ Услуги", callback_data="services")],
                    [InlineKeyboardButton("📞 Контакты", callback_data="contacts")],
                    [InlineKeyboardButton("📨 Связаться с админом", callback_data="contact_admin")],
                ]
                await update.message.reply_text(
                    "👋 **Главное меню:**\n\nВыберите действие:",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )

            self._clear_user_data(context)

    async def send_to_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        if not self.admin_id:
            await update.message.reply_text("❌ Админ не настроен")
            return

        user = update.effective_user
        from .models import DatabaseManager
        db = DatabaseManager(self.master_id)
        client = db.get_client_by_telegram(str(user.id))
        client_name = client['name'] if client else user.first_name

        try:
            await context.bot.send_message(
                chat_id=self.admin_id,
                text=f"📨 **Сообщение от клиента**\n\n"
                     f"👤 Клиент: {client_name}\n"
                     f"🆔 ID: {user.id}\n"
                     f"📱 Username: @{user.username if user.username else 'нет'}\n\n"
                     f"💬 **Сообщение:**\n{text}",
                parse_mode='Markdown'
            )
            await update.message.reply_text(
                "✅ Сообщение отправлено администратору!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ В меню", callback_data="main_menu")
                ]])
            )
        except Exception as e:
            logger.error(f"Ошибка отправки админу: {e}")
            await update.message.reply_text("❌ Ошибка отправки")

        self._clear_user_data(context)

    def _clear_user_data(self, context):
        keys = ['selected_service', 'selected_date', 'selected_time', 'reg_step', 
                'reg_name', 'reg_phone', 'reg_birthday', 'contact_admin', 'temp_booking']
        for key in keys:
            context.user_data.pop(key, None)

    def _back_button(self, callback_data):
        return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=callback_data)]])

    async def notify_admin_about_new_booking(self, context, booking, client, service):
        """Уведомление администратора о новой записи"""
        try:
            if not self.admin_id or str(self.admin_id).strip() == '':
                logger.warning(f"⚠️ [МАСТЕР {self.master_id}] Admin ID не указан, уведомление не отправлено")
                return

            message = (
                f"🆕 **НОВАЯ ЗАПИСЬ!**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 **Клиент:** {client['name']}\n"
                f"📞 **Телефон:** {client.get('phone', 'не указан')}\n"
                f"📧 **Email:** {client.get('email', 'не указан')}\n\n"
                f"💇 **Услуга:** {service['name']}\n"
                f"💰 **Цена:** {service['price']}₽\n"
                f"📅 **Дата:** {booking['date']}\n"
                f"🕐 **Время:** {booking['time']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **ID записи:** `{booking['id']}`"
            )

            await context.bot.send_message(
                chat_id=self.admin_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Уведомление о новой записи отправлено админу {self.admin_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления админу: {e}")

async def notify_admin_about_cancellation(self, context, booking, client, service):
    """Уведомление администратора об отмене записи"""
    try:
        if not self.admin_id or str(self.admin_id).strip() == '':
            return

        message = (
            f"❌ **ЗАПИСЬ ОТМЕНЕНА!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **Клиент:** {client['name']}\n"
            f"📞 **Телефон:** {client.get('phone', 'не указан')}\n\n"
            f"💇 **Услуга:** {service['name']}\n"
            f"📅 **Дата:** {booking['date']}\n"
            f"🕐 **Время:** {booking['time']}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 **ID записи:** `{booking['id']}`"
        )

        await context.bot.send_message(
            chat_id=self.admin_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Уведомление об отмене отправлено админу {self.admin_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления об отмене: {e}")

async def notify_admin_about_new_client(self, context, client):
    """Уведомление администратора о новом клиенте"""
    try:
        if not self.admin_id or str(self.admin_id).strip() == '':
            return

        message = (
            f"👋 **НОВЫЙ КЛИЕНТ!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 **Имя:** {client['name']}\n"
            f"📞 **Телефон:** {client.get('phone', 'не указан')}\n"
            f"📧 **Email:** {client.get('email', 'не указан')}\n"
            f"🎂 **День рождения:** {client.get('birth_date', 'не указан')}\n"
            f"🆔 **Telegram ID:** `{client.get('telegram_id', 'не указан')}`\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━"
        )

        await context.bot.send_message(
            chat_id=self.admin_id,
            text=message,
            parse_mode='Markdown'
        )
        logger.info(f"✅ Уведомление о новом клиенте отправлено админу {self.admin_id}")

    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления о новом клиенте: {e}")

    async def notify_admin_about_cancellation(self, context, booking, client, service):
        """Уведомление администратора об отмене записи"""
        try:
            if not self.admin_id:
                return

            message = (
                f"❌ **ЗАПИСЬ ОТМЕНЕНА!**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 **Клиент:** {client['name']}\n"
                f"📞 **Телефон:** {client.get('phone', 'не указан')}\n\n"
                f"💇 **Услуга:** {service['name']}\n"
                f"📅 **Дата:** {booking['date']}\n"
                f"🕐 **Время:** {booking['time']}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **ID записи:** `{booking['id']}`"
            )

            await context.bot.send_message(
                chat_id=self.admin_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Уведомление об отмене отправлено админу {self.admin_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления об отмене: {e}")

    async def notify_admin_about_new_client(self, context, client):
        """Уведомление администратора о новом клиенте"""
        try:
            if not self.admin_id:
                return

            message = (
                f"👋 **НОВЫЙ КЛИЕНТ!**\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👤 **Имя:** {client['name']}\n"
                f"📞 **Телефон:** {client.get('phone', 'не указан')}\n"
                f"📧 **Email:** {client.get('email', 'не указан')}\n"
                f"🎂 **День рождения:** {client.get('birth_date', 'не указан')}\n"
                f"🆔 **Telegram ID:** `{client.get('telegram_id', 'не указан')}`\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━"
            )

            await context.bot.send_message(
                chat_id=self.admin_id,
                text=message,
                parse_mode='Markdown'
            )
            logger.info(f"✅ Уведомление о новом клиенте отправлено админу {self.admin_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления о новом клиенте: {e}")

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"❌ Ошибка в боте: {context.error}", exc_info=True)
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте позже."
                )
        except:
            pass


class BotManager:
    """Менеджер нескольких ботов"""

    def __init__(self, plugin):
        self.plugin = plugin
        self.bots: dict[str, BotInstance] = {}
        logger.info("🤖 Менеджер ботов инициализирован")

    def start_bot(self, master_id: str, token: str, admin_id: str | None):
        self.stop_bot(master_id)
        bot = BotInstance(master_id, token, admin_id, self.plugin)
        bot.start()
        self.bots[master_id] = bot
        return True

    def stop_bot(self, master_id: str):
        if master_id in self.bots:
            self.bots[master_id].stop()
            del self.bots[master_id]
            return True
        return False

    def restart_bot(self, master_id: str, token: str, admin_id: str | None):
        self.stop_bot(master_id)
        return self.start_bot(master_id, token, admin_id)

    def stop_all(self):
        for master_id in list(self.bots.keys()):
            self.stop_bot(master_id)
        logger.info("⏹ Все боты остановлены")