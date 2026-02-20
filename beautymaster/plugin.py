import sys
import os
from datetime import datetime, date, time, timedelta

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from plugin_base import Plugin
from flask import jsonify, request, session, g
from extensions import db
from .models import DatabaseManager
from .bot_manager import BotManager

# Импортируем маршруты
from .routes.profile import register_profile_routes
from .routes.services import register_services_routes
from .routes.clients import register_clients_routes
from .routes.bookings import register_bookings_routes
from .routes.schedule import register_schedule_routes

class BeautyMasterPlugin(Plugin):
    name = "Beauty Master Pro"
    description = "Полноценная CRM для салона красоты: услуги, клиенты, бронирования"
    icon = "💅"
    version = "3.0"
    is_plugin = True
    
    def __init__(self, app, db):
        super().__init__(app, db)
        self.bot_manager = BotManager(self)
        self.setup_routes()
        print("✅ Beauty Master Pro инициализирован")
    
    def get_db_for_master(self, master_id):
        """Получить менеджер базы данных для мастера"""
        return DatabaseManager(master_id)
    
    def get_current_master_db(self):
        """Получить базу данных для текущего пользователя"""
        if 'user_id' not in session:
            return None
        
        # Используем user_id как master_id
        master_id = session['user_id']
        return self.get_db_for_master(master_id)
    
    def setup_routes(self):
        """Регистрация всех маршрутов"""
        register_profile_routes(self.app, self)
        register_services_routes(self.app, self)
        register_clients_routes(self.app, self)
        register_bookings_routes(self.app, self)
        register_schedule_routes(self.app, self)
    
    def get_widget(self):
        """Виджет для отображения"""
        try:
            template_path = os.path.join(os.path.dirname(__file__), 'templates', 'widget.html')
            
            if not os.path.exists(template_path):
                print(f"❌ Файл шаблона не найден: {template_path}")
                return "<h3 style='color: red; text-align: center; padding: 20px;'>❌ Ошибка: файл widget.html не найден</h3>"
            
            with open(template_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            print(f"✅ Шаблон загружен: {template_path}")
            print(f"✅ Размер HTML: {len(html_content)} символов")
            return html_content
            
        except Exception as e:
            print(f"❌ Ошибка загрузки шаблона: {e}")
            return f"<h3 style='color: red; text-align: center; padding: 20px;'>❌ Ошибка загрузки шаблона: {str(e)}</h3>"