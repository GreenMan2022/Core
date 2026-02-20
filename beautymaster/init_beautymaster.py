import sys
import os
from datetime import datetime, timedelta

# Добавляем путь к корневой папке проекта
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Импортируем DatabaseManager
from plugins.beautymaster.models import DatabaseManager

def init_master_db(master_id=1):
    """Инициализация базы данных мастера тестовыми данными"""
    
    print(f"🔄 Инициализация базы данных мастера {master_id}...")
    
    # Создаем менеджер базы данных (он сам создаст таблицы)
    db = DatabaseManager(master_id)
    
    # Получаем соединение
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже данные
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='services'")
    if cursor.fetchone()[0] == 0:
        print("❌ Таблицы не создались автоматически, создаем вручную...")
        # Создаем таблицы вручную, если DatabaseManager не сработал
        db.init_database()
    
    # Очищаем существующие данные
    cursor.execute('DELETE FROM bookings')
    cursor.execute('DELETE FROM clients')
    cursor.execute('DELETE FROM services')
    cursor.execute('DELETE FROM schedule')
    
    # Создаем расписание (пн-пт 9:00-18:00)
    print("📅 Создание расписания...")
    schedule_data = [
        (0, '09:00', '18:00', 1),  # Пн
        (1, '09:00', '18:00', 1),  # Вт
        (2, '09:00', '18:00', 1),  # Ср
        (3, '09:00', '18:00', 1),  # Чт
        (4, '09:00', '18:00', 1),  # Пт
        (5, None, None, 0),         # Сб
        (6, None, None, 0)          # Вс
    ]
    
    for day in schedule_data:
        cursor.execute('''
            INSERT INTO schedule (day_of_week, start_time, end_time, is_working)
            VALUES (?, ?, ?, ?)
        ''', day)
    
    # Создаем услуги
    print("💇 Создание услуг...")
    services = [
        ('Стрижка женская', 'Классическая стрижка', 1500, 60, 'hair'),
        ('Стрижка мужская', 'Мужская стрижка', 1000, 45, 'hair'),
        ('Окрашивание', 'Полное окрашивание', 3000, 120, 'color'),
        ('Маникюр', 'Классический маникюр', 1200, 60, 'nails'),
        ('Педикюр', 'Классический педикюр', 2000, 90, 'nails'),
        ('Макияж', 'Вечерний макияж', 2500, 60, 'makeup'),
    ]
    
    for s in services:
        cursor.execute('''
            INSERT INTO services (name, description, price, duration, category, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', s)
    
    # Создаем клиентов
    print("👥 Создание клиентов...")
    clients = [
        ('Иван Петров', '+7 (999) 123-45-67', 'ivan@mail.com', None, 'Постоянный клиент'),
        ('Елена Смирнова', '+7 (999) 765-43-21', 'elena@mail.com', None, ''),
        ('Анна Иванова', '+7 (999) 555-55-55', 'anna@mail.com', None, ''),
        ('Тестовый клиент', '+7 (999) 111-22-33', 'test@mail.com', None, 'Для тестов'),
    ]
    
    client_ids = []
    for c in clients:
        cursor.execute('''
            INSERT INTO clients (name, phone, email, birth_date, notes)
            VALUES (?, ?, ?, ?, ?)
        ''', c)
        client_ids.append(cursor.lastrowid)
    
    # Создаем несколько тестовых бронирований на завтра и послезавтра
    print("📅 Создание тестовых бронирований...")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    
    bookings = [
        (client_ids[0], 1, tomorrow, '10:00', 60, 'confirmed', 'Первая запись'),
        (client_ids[1], 3, tomorrow, '12:00', 120, 'confirmed', ''),
        (client_ids[2], 4, tomorrow, '15:00', 60, 'confirmed', ''),
        (client_ids[3], 2, day_after, '11:00', 45, 'confirmed', 'Тест'),
        (client_ids[0], 5, day_after, '14:00', 90, 'confirmed', ''),
    ]
    
    for b in bookings:
        cursor.execute('''
            INSERT INTO bookings (client_id, service_id, date, time, duration, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', b)
    
    # Обновляем профиль мастера
    cursor.execute('''
        UPDATE master_profile 
        SET salon_name = ?, phone = ?, address = ?, description = ?
        WHERE id = 1
    ''', ('Мой салон красоты', '+7 (495) 123-45-67', 'ул. Пушкина, д. 10', 'Лучший салон в городе'))
    
    conn.commit()
    conn.close()
    
    print("✅ База данных успешно инициализирована!")
    print(f"   - Услуг: {len(services)}")
    print(f"   - Клиентов: {len(clients)}")
    print(f"   - Бронирований: {len(bookings)}")
    print(f"   - Расписание: пн-пт 9:00-18:00")
    
    # Показываем созданные данные
    print("\n📊 Созданные данные:")
    print("   Услуги:")
    for i, s in enumerate(services, 1):
        print(f"     {i}. {s[0]} - {s[2]}₽ ({s[3]} мин)")
    
    print("\n   Клиенты:")
    for i, c in enumerate(clients, 1):
        print(f"     {i}. {c[0]} - {c[1]}")

if __name__ == '__main__':
    # Инициализируем для админа (user_id=1)
    init_master_db(1)
    
    print("\n" + "="*50)
    print("✅ Готово! Теперь перезапустите сервер:")
    print("   python crm.py")
    print("="*50)