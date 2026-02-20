from flask import jsonify, request, session
from datetime import datetime, timedelta, date

def register_schedule_routes(app, plugin):
    
    @app.route('/api/plugins/beautymaster/schedule', methods=['GET', 'POST'])
    def beautymaster_schedule():
        """Расписание работы"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        if request.method == 'GET':
            schedule = db.get_schedule()
            return jsonify({'success': True, 'data': schedule})
        
        elif request.method == 'POST':
            data = request.json
            if not isinstance(data, list):
                return jsonify({'error': 'Ожидается массив'}), 400
            
            db.update_schedule(data)
            return jsonify({'success': True})
    
    @app.route('/api/plugins/beautymaster/availability', methods=['GET'])
    def beautymaster_availability():
        """Проверка доступности времени"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        date_str = request.args.get('date')
        if not date_str:
            return jsonify({'error': 'Не указана дата'}), 400
        
        try:
            check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            return jsonify({'error': 'Неверный формат даты'}), 400
        
        # Получаем расписание на этот день
        schedule = db.get_schedule()
        day_schedule = next((s for s in schedule if s['day_of_week'] == check_date.weekday()), None)
        
        if not day_schedule or not day_schedule.get('is_working'):
            return jsonify({
                'success': True,
                'is_working': False,
                'available_slots': []
            })
        
        # Получаем бронирования на эту дату
        bookings = db.get_bookings_for_date(date_str)
        
        # Генерируем доступные слоты
        available_slots = []
        current = datetime.combine(check_date, datetime.strptime(day_schedule['start_time'], '%H:%M').time())
        end = datetime.combine(check_date, datetime.strptime(day_schedule['end_time'], '%H:%M').time())
        
        while current < end:
            time_str = current.strftime('%H:%M')
            is_available = True
            
            for b in bookings:
                b_dt = datetime.combine(
                    datetime.strptime(b['date'], '%Y-%m-%d').date(),
                    datetime.strptime(b['time'], '%H:%M').time()
                )
                b_end = b_dt + timedelta(minutes=b['duration'])
                
                if b_dt <= current < b_end:
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(time_str)
            
            current += timedelta(minutes=30)
        
        return jsonify({
            'success': True,
            'is_working': True,
            'schedule': day_schedule,
            'available_slots': available_slots,
            'bookings': bookings
        })
    
    @app.route('/api/plugins/beautymaster/stats', methods=['GET'])
    def beautymaster_stats():
        """Статистика"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        stats = db.get_stats()
        return jsonify({'success': True, 'data': stats})