import sqlite3
import os

def fix_master_db(master_id=1):
    """Добавление полей для бота в существующую базу данных"""
    
    db_path = os.path.join('databases', f'master_{master_id}.db')
    
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return
    
    print(f"🔄 Обновление базы данных мастера {master_id}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Проверяем существующие колонки в master_profile
    cursor.execute("PRAGMA table_info(master_profile)")
    columns = [col[1] for col in cursor.fetchall()]
    
    print(f"Существующие колонки: {columns}")
    
    # Добавляем недостающие колонки
    if 'telegram_bot_token' not in columns:
        print("➕ Добавление колонки telegram_bot_token...")
        cursor.execute("ALTER TABLE master_profile ADD COLUMN telegram_bot_token TEXT")
    
    if 'telegram_admin_id' not in columns:
        print("➕ Добавление колонки telegram_admin_id...")
        cursor.execute("ALTER TABLE master_profile ADD COLUMN telegram_admin_id TEXT")
    
    if 'telegram_notifications' not in columns:
        print("➕ Добавление колонки telegram_notifications...")
        cursor.execute("ALTER TABLE master_profile ADD COLUMN telegram_notifications INTEGER DEFAULT 0")
    
    # Проверяем, есть ли запись в master_profile
    cursor.execute("SELECT COUNT(*) FROM master_profile")
    if cursor.fetchone()[0] == 0:
        print("➕ Создание записи профиля...")
        cursor.execute('''
            INSERT INTO master_profile (salon_name, phone, address, description)
            VALUES ('Мой салон', '', '', '')
        ''')
    
    conn.commit()
    conn.close()
    
    print("✅ База данных обновлена!")

def fix_all_masters():
    """Обновление всех баз данных мастеров"""
    databases_dir = 'databases'
    
    if not os.path.exists(databases_dir):
        print(f"❌ Папка не найдена: {databases_dir}")
        return
    
    for file in os.listdir(databases_dir):
        if file.startswith('master_') and file.endswith('.db'):
            master_id = file.replace('master_', '').replace('.db', '')
            try:
                fix_master_db(int(master_id))
            except:
                print(f"❌ Ошибка при обработке {file}")

if __name__ == '__main__':
    print("="*60)
    print("🔧 ИСПРАВЛЕНИЕ СХЕМЫ БАЗЫ ДАННЫХ")
    print("="*60)
    
    fix_all_masters()
    
    print("\n" + "="*60)
    print("✅ Готово! Теперь:")
    print("1. Перезапустите сервер: python crm.py")
    print("2. В плагине настройте бота заново")
    print("3. Нажмите 'Сохранить' и 'Перезапустить'")
    print("="*60)