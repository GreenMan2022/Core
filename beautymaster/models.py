import sqlite3
import os
from datetime import datetime
import json

class DatabaseManager:
    """Менеджер базы данных для конкретного мастера"""
    
    def __init__(self, master_id):
        self.master_id = master_id
        self.db_path = os.path.join(os.path.dirname(__file__), 'databases', f'master_{master_id}.db')
        
        # Создаем папку databases если её нет
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Инициализируем базу данных
        self.init_database()
    
    def get_connection(self):
        """Получить соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Создание всех таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица профиля мастера
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS master_profile (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                salon_name TEXT,
                phone TEXT,
                address TEXT,
                description TEXT,
                telegram_bot_token TEXT,
                telegram_admin_id TEXT,
                telegram_notifications INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица услуг
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                duration INTEGER DEFAULT 60,
                category TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                birth_date TEXT,
                notes TEXT,
                telegram_id TEXT UNIQUE,
                telegram_notifications INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица расписания
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_of_week INTEGER NOT NULL,
                start_time TEXT,
                end_time TEXT,
                is_working INTEGER DEFAULT 1
            )
        ''')
        
        # Таблица бронирований
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                duration INTEGER,
                status TEXT DEFAULT 'confirmed',
                notes TEXT,
                reminder_sent INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id),
                FOREIGN KEY (service_id) REFERENCES services (id)
            )
        ''')
        
        # Таблица отзывов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL,
                booking_id INTEGER NOT NULL,
                rating INTEGER,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id),
                FOREIGN KEY (booking_id) REFERENCES bookings (id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Создаем начальные данные если их нет
        self.create_initial_data()
    
    def create_initial_data(self):
        """Создание начальных данных (профиль)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Проверяем есть ли профиль
        cursor.execute('SELECT COUNT(*) FROM master_profile')
        if cursor.fetchone()[0] == 0:
            cursor.execute('''
                INSERT INTO master_profile (salon_name, phone, address, description)
                VALUES (?, ?, ?, ?)
            ''', ('Мой салон', '', '', ''))
        
        conn.commit()
        conn.close()
    
    # ========== ПРОФИЛЬ ==========
    
    def get_profile(self):
        """Получить профиль мастера"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM master_profile LIMIT 1')
        profile = cursor.fetchone()
        conn.close()
        
        if profile:
            return dict(profile)
        return None
    
    def update_profile(self, data):
        """Обновить профиль мастера"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = []
        values = []
        for key in ['salon_name', 'phone', 'address', 'description', 
                   'telegram_bot_token', 'telegram_admin_id', 'telegram_notifications']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        
        if fields:
            cursor.execute(f'''
                UPDATE master_profile SET {', '.join(fields)}
            ''', values)
            conn.commit()
        
        conn.close()
        return self.get_profile()
    
    # ========== УСЛУГИ ==========
    
    def get_services(self, active_only=True):
        """Получить все услуги"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('SELECT * FROM services WHERE is_active = 1 ORDER BY name')
        else:
            cursor.execute('SELECT * FROM services ORDER BY name')
        
        services = cursor.fetchall()
        conn.close()
        return [dict(s) for s in services]
    
    def get_service(self, service_id):
        """Получить услугу по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM services WHERE id = ?', (service_id,))
        service = cursor.fetchone()
        conn.close()
        return dict(service) if service else None
    
    def add_service(self, data):
        """Добавить услугу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO services (name, description, price, duration, category, is_active)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data.get('description', ''),
            data['price'],
            data.get('duration', 60),
            data.get('category', ''),
            data.get('is_active', 1)
        ))
        conn.commit()
        service_id = cursor.lastrowid
        conn.close()
        return service_id
    
    def update_service(self, service_id, data):
        """Обновить услугу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = []
        values = []
        for key in ['name', 'description', 'price', 'duration', 'category', 'is_active']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        
        values.append(service_id)
        cursor.execute(f'''
            UPDATE services SET {', '.join(fields)} WHERE id = ?
        ''', values)
        conn.commit()
        conn.close()
    
    def delete_service(self, service_id):
        """Удалить услугу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))
        conn.commit()
        conn.close()
    
    # ========== КЛИЕНТЫ ==========
    
    def get_clients(self):
        """Получить всех клиентов"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients ORDER BY name')
        clients = cursor.fetchall()
        conn.close()
        
        result = []
        for c in clients:
            client = dict(c)
            # Получаем количество визитов
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM bookings WHERE client_id = ?', (client['id'],))
            client['total_visits'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT MAX(date) FROM bookings WHERE client_id = ?', (client['id'],))
            last_date = cursor.fetchone()[0]
            client['last_visit'] = last_date
            conn.close()
            
            result.append(client)
        
        return result
    
    def get_client(self, client_id):
        """Получить клиента по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE id = ?', (client_id,))
        client = cursor.fetchone()
        conn.close()
        return dict(client) if client else None
    
    def get_client_by_telegram(self, telegram_id):
        """Получить клиента по Telegram ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM clients WHERE telegram_id = ?', (telegram_id,))
        client = cursor.fetchone()
        conn.close()
        return dict(client) if client else None
    
    def add_client(self, data):
        """Добавить клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO clients (name, phone, email, birth_date, notes, telegram_id, telegram_notifications)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['phone'],
            data.get('email', ''),
            data.get('birth_date'),
            data.get('notes', ''),
            data.get('telegram_id'),
            data.get('telegram_notifications', 1)
        ))
        conn.commit()
        client_id = cursor.lastrowid
        conn.close()
        return client_id
    
    def update_client(self, client_id, data):
        """Обновить клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = []
        values = []
        for key in ['name', 'phone', 'email', 'birth_date', 'notes', 'telegram_id', 'telegram_notifications']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        
        values.append(client_id)
        cursor.execute(f'''
            UPDATE clients SET {', '.join(fields)} WHERE id = ?
        ''', values)
        conn.commit()
        conn.close()
    
    def delete_client(self, client_id):
        """Удалить клиента"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM clients WHERE id = ?', (client_id,))
        conn.commit()
        conn.close()
    
    # ========== РАСПИСАНИЕ ==========
    
    def get_schedule(self):
        """Получить расписание"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM schedule ORDER BY day_of_week')
        schedule = cursor.fetchall()
        conn.close()
        return [dict(s) for s in schedule]
    
    def update_schedule(self, schedule_data):
        """Обновить расписание"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Очищаем старое расписание
        cursor.execute('DELETE FROM schedule')
        
        # Добавляем новое
        for item in schedule_data:
            cursor.execute('''
                INSERT INTO schedule (day_of_week, start_time, end_time, is_working)
                VALUES (?, ?, ?, ?)
            ''', (
                item['day_of_week'],
                item.get('start_time'),
                item.get('end_time'),
                item.get('is_working', 1)
            ))
        
        conn.commit()
        conn.close()
    
    # ========== БРОНИРОВАНИЯ ==========
    
    def get_bookings(self, date_from=None, date_to=None, status=None, client_id=None):
        """Получить бронирования с фильтрами"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = '''
            SELECT b.*, c.name as client_name, s.name as service_name, s.price
            FROM bookings b
            JOIN clients c ON b.client_id = c.id
            JOIN services s ON b.service_id = s.id
            WHERE 1=1
        '''
        params = []
        
        if date_from:
            query += ' AND b.date >= ?'
            params.append(date_from)
        if date_to:
            query += ' AND b.date <= ?'
            params.append(date_to)
        if status:
            query += ' AND b.status = ?'
            params.append(status)
        if client_id:
            query += ' AND b.client_id = ?'
            params.append(client_id)
        
        query += ' ORDER BY b.date, b.time'
        
        cursor.execute(query, params)
        bookings = cursor.fetchall()
        conn.close()
        return [dict(b) for b in bookings]
    
    def get_booking(self, booking_id):
        """Получить бронирование по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as client_name, s.name as service_name, s.price
            FROM bookings b
            JOIN clients c ON b.client_id = c.id
            JOIN services s ON b.service_id = s.id
            WHERE b.id = ?
        ''', (booking_id,))
        booking = cursor.fetchone()
        conn.close()
        return dict(booking) if booking else None
    
    def add_booking(self, data):
        """Добавить бронирование"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO bookings (client_id, service_id, date, time, duration, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['client_id'],
            data['service_id'],
            data['date'],
            data['time'],
            data.get('duration'),
            data.get('status', 'confirmed'),
            data.get('notes', '')
        ))
        conn.commit()
        booking_id = cursor.lastrowid
        conn.close()
        return booking_id
    
    def update_booking(self, booking_id, data):
        """Обновить бронирование"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        fields = []
        values = []
        for key in ['client_id', 'service_id', 'date', 'time', 'duration', 'status', 'notes', 'reminder_sent']:
            if key in data:
                fields.append(f"{key} = ?")
                values.append(data[key])
        
        values.append(booking_id)
        cursor.execute(f'''
            UPDATE bookings SET {', '.join(fields)} WHERE id = ?
        ''', values)
        conn.commit()
        conn.close()
    
    def delete_booking(self, booking_id):
        """Удалить бронирование"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM bookings WHERE id = ?', (booking_id,))
        conn.commit()
        conn.close()
    
    def get_bookings_for_date(self, date):
        """Получить бронирования на конкретную дату"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as client_name, s.name as service_name, s.duration
            FROM bookings b
            JOIN clients c ON b.client_id = c.id
            JOIN services s ON b.service_id = s.id
            WHERE b.date = ? AND b.status != 'cancelled'
            ORDER BY b.time
        ''', (date,))
        bookings = cursor.fetchall()
        conn.close()
    
        result = []
        for b in bookings:
            booking_dict = dict(b)
            # Преобразуем время в строку, если нужно
            if booking_dict.get('time'):
                booking_dict['time'] = str(booking_dict['time'])
            result.append(booking_dict)
        
        return result
    
    def get_upcoming_bookings(self, days=7):
        """Получить предстоящие бронирования"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT b.*, c.name as client_name, c.telegram_id, s.name as service_name
            FROM bookings b
            JOIN clients c ON b.client_id = c.id
            JOIN services s ON b.service_id = s.id
            WHERE b.date >= date('now') 
              AND b.date <= date('now', ?)
              AND b.status = 'confirmed'
              AND b.reminder_sent = 0
            ORDER BY b.date, b.time
        ''', (f'+{days} days',))
        bookings = cursor.fetchall()
        conn.close()
        return [dict(b) for b in bookings]
    
    # ========== СТАТИСТИКА ==========
    
    def get_stats(self):
        """Получить статистику"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM clients')
        total_clients = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM services WHERE is_active = 1')
        total_services = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bookings')
        total_bookings = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bookings WHERE status = "completed"')
        completed_bookings = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM bookings WHERE status = "cancelled"')
        cancelled_bookings = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM bookings 
            WHERE date >= date('now', 'start of month')
        ''')
        month_bookings = cursor.fetchone()[0]
        
        # Популярные услуги
        cursor.execute('''
            SELECT s.name, COUNT(b.id) as count
            FROM bookings b
            JOIN services s ON b.service_id = s.id
            GROUP BY s.id
            ORDER BY count DESC
            LIMIT 5
        ''')
        popular = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_clients': total_clients,
            'total_services': total_services,
            'total_bookings': total_bookings,
            'completed_bookings': completed_bookings,
            'cancelled_bookings': cancelled_bookings,
            'month_bookings': month_bookings,
            'popular_services': [{'name': p[0], 'count': p[1]} for p in popular]
        }
    
    # ========== ДЛЯ БОТА ==========
    
    def get_clients_for_notifications(self):
        """Получить клиентов для уведомлений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM clients 
            WHERE telegram_id IS NOT NULL 
              AND telegram_notifications = 1
        ''')
        clients = cursor.fetchall()
        conn.close()
        return [dict(c) for c in clients]