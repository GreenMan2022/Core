from flask import jsonify, request, session

def register_profile_routes(app, plugin):
    
    @app.route('/api/plugins/beautymaster/profile', methods=['GET', 'PUT'])
    def beautymaster_profile():
        """Профиль мастера"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        if request.method == 'GET':
            profile = db.get_profile()
            return jsonify({'success': True, 'data': profile})
        
        elif request.method == 'PUT':
            data = request.json
            if data:
                # Сохраняем старые значения для сравнения
                old_profile = db.get_profile()
                old_token = old_profile.get('telegram_bot_token') if old_profile else None
                old_enabled = old_profile.get('telegram_notifications') if old_profile else False
                
                # Обновляем профиль
                db.update_profile(data)
                
                # Получаем обновленный профиль
                profile = db.get_profile()
                
                # Перезапускаем бота если изменились настройки
                new_token = profile.get('telegram_bot_token')
                new_enabled = profile.get('telegram_notifications')
                
                if (new_token != old_token or new_enabled != old_enabled):
                    master_id = session['user_id']
                    if new_token and new_enabled:
                        plugin.bot_manager.restart_bot(
                            master_id,
                            new_token,
                            profile.get('telegram_admin_id')
                        )
                        print(f"✅ Бот перезапущен для мастера {master_id}")
                    else:
                        plugin.bot_manager.stop_bot(master_id)
                        print(f"⏹ Бот остановлен для мастера {master_id}")
            
            return jsonify({'success': True, 'data': profile})
    
    @app.route('/api/plugins/beautymaster/test-bot', methods=['POST'])
    def test_bot():
        """Тестирование подключения к Telegram боту"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        data = request.json
        token = data.get('token')
        admin_id = data.get('admin_id')
        
        if not admin_id:
            return jsonify({'error': 'Не указан ID администратора'}), 400
        
        # Если token == 'USE_EXISTING', используем сохраненный токен
        if token == 'USE_EXISTING':
            db = plugin.get_current_master_db()
            profile = db.get_profile()
            token = profile.get('telegram_bot_token')
            if not token:
                return jsonify({'error': 'Токен не сохранен'}), 400
        
        if not token:
            return jsonify({'error': 'Не указан токен'}), 400
        
        try:
            import requests
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {
                'chat_id': admin_id,
                'text': '🔔 **Тестовое сообщение от Beauty Master Pro!**\n\n'
                        'Если вы это видите, значит бот настроен правильно.\n\n'
                        '✅ Подключение работает!'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return jsonify({
                    'success': True, 
                    'message': 'Тестовое сообщение отправлено! Проверьте Telegram.'
                })
            else:
                error_data = response.json()
                return jsonify({
                    'error': f'Ошибка Telegram API: {error_data.get("description", "Неизвестная ошибка")}'
                }), 400
                
        except requests.exceptions.ConnectionError:
            return jsonify({'error': 'Не удалось подключиться к Telegram API'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/plugins/beautymaster/bot-status', methods=['GET'])
    def bot_status():
        """Получение статуса бота"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        profile = db.get_profile()
        master_id = session['user_id']
        
        return jsonify({
            'success': True,
            'data': {
                'configured': bool(profile.get('telegram_bot_token')),
                'enabled': profile.get('telegram_notifications', False),
                'running': master_id in plugin.bot_manager.bots,
                'admin_id': profile.get('telegram_admin_id')
            }
        })
    
    @app.route('/api/plugins/beautymaster/bot-restart', methods=['POST'])
    def bot_restart():
        """Принудительный перезапуск бота"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        profile = db.get_profile()
        master_id = session['user_id']
        
        if not profile.get('telegram_bot_token'):
            return jsonify({'error': 'Бот не настроен'}), 400
        
        if profile.get('telegram_notifications'):
            plugin.bot_manager.restart_bot(
                master_id,
                profile.get('telegram_bot_token'),
                profile.get('telegram_admin_id')
            )
            return jsonify({'success': True, 'message': 'Бот перезапущен'})
        else:
            plugin.bot_manager.stop_bot(master_id)
            return jsonify({'success': True, 'message': 'Бот остановлен'})
    
    @app.route('/api/plugins/beautymaster/bot-stats', methods=['GET'])
    def bot_stats():
        """Статистика работы бота"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        clients = db.get_clients()
        telegram_clients = [c for c in clients if c.get('telegram_id')]
        
        bookings = db.get_bookings()
        telegram_bookings = [b for b in bookings if b.get('client_telegram')]
        
        active_subscribers = [c for c in telegram_clients if c.get('telegram_notifications')]
        
        master_id = session['user_id']
        
        return jsonify({
            'success': True,
            'data': {
                'total_telegram_clients': len(telegram_clients),
                'telegram_bookings': len(telegram_bookings),
                'active_subscribers': len(active_subscribers),
                'bot_running': master_id in plugin.bot_manager.bots
            }
        })