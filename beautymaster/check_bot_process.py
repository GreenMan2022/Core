import psutil
import os
import sys
import time
import requests

def check_bot_status():
    """Проверка статуса бота"""
    
    print("="*60)
    print("🔍 ПРОВЕРКА БОТА")
    print("="*60)
    
    # Проверяем запущенные процессы Python
    print("\n📊 ЗАПУЩЕННЫЕ ПРОЦЕССЫ PYTHON:")
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if proc.info['name'] and 'python' in proc.info['name'].lower():
            cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
            if 'crm.py' in cmdline or 'bot' in cmdline.lower():
                python_processes.append({
                    'pid': proc.info['pid'],
                    'cmdline': cmdline[:100]
                })
                print(f"  PID: {proc.info['pid']} - {cmdline[:100]}")
    
    # Проверяем открытые порты
    print("\n🔌 ОТКРЫТЫЕ ПОРТЫ:")
    try:
        import socket
        common_ports = [5000, 8080, 8000, 8888, 8443, 80, 443]
        for port in common_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            if result == 0:
                print(f"  ✅ Порт {port} открыт")
            else:
                print(f"  ❌ Порт {port} закрыт")
            sock.close()
    except Exception as e:
        print(f"  Ошибка проверки портов: {e}")
    
    # Проверяем бота через Telegram API
    print("\n🤖 ПРОВЕРКА БОТА ЧЕРЕЗ API:")
    
    # Токен бота
    token = "5164549261:AAEouZbi4I6WB-Gf2ggZOW0NEQsa9MwS4bY"
    
    try:
        # Проверяем getMe
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                bot = data['result']
                print(f"  ✅ Бот доступен:")
                print(f"     Имя: {bot['first_name']}")
                print(f"     Username: @{bot['username']}")
                print(f"     ID: {bot['id']}")
            else:
                print(f"  ❌ Ошибка API: {data}")
        else:
            print(f"  ❌ HTTP ошибка: {response.status_code}")
            
        # Проверяем информацию о вебхуке
        url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data['ok']:
                webhook = data['result']
                print(f"\n  📡 Webhook info:")
                print(f"     URL: {webhook.get('url', 'не установлен')}")
                print(f"     pending updates: {webhook.get('pending_update_count', 0)}")
                if webhook.get('last_error_date'):
                    print(f"     last error: {webhook.get('last_error_message', '')}")
                    
    except Exception as e:
        print(f"  ❌ Ошибка при проверке: {e}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    check_bot_status()
    
    print("\n📋 ИНСТРУКЦИЯ:")
    print("1. Убедитесь что crm.py запущен")
    print("2. В плагине нажмите 'Перезапустить' в разделе бота")
    print("3. Проверьте логи сервера")
    print("4. Отправьте /start боту")