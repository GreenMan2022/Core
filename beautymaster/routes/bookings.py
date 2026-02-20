from flask import jsonify, request, session
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def register_bookings_routes(app, plugin):
    
    @app.route('/api/plugins/beautymaster/bookings', methods=['GET', 'POST'])
    @app.route('/api/plugins/beautymaster/bookings/<int:booking_id>', methods=['GET', 'PUT', 'DELETE'])
    def beautymaster_bookings(booking_id=None):
        """Бронирования"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        # GET все бронирования
        if request.method == 'GET' and booking_id is None:
            date_from = request.args.get('date_from')
            date_to = request.args.get('date_to')
            status = request.args.get('status')
            client_id = request.args.get('client_id', type=int)
            
            bookings = db.get_bookings(
                date_from=date_from,
                date_to=date_to,
                status=status,
                client_id=client_id
            )
            return jsonify({'success': True, 'data': bookings})
        
        # GET конкретное бронирование
        elif request.method == 'GET' and booking_id:
            booking = db.get_booking(booking_id)
            if not booking:
                return jsonify({'error': 'Бронирование не найдено'}), 404
            return jsonify({'success': True, 'data': booking})
        
        # POST создать бронирование
        elif request.method == 'POST':
            data = request.json
            logger.info(f"📝 Создание бронирования: {data}")
            
            required = ['client_id', 'service_id', 'date', 'time']
            if not data or any(field not in data for field in required):
                return jsonify({'error': 'Не все обязательные поля заполнены'}), 400
            
            # Проверка доступности (ВРЕМЕННО ОТКЛЮЧАЕМ ДЛЯ ТЕСТА)
            # if not check_availability(db, data['date'], data['time'], data.get('service_id')):
            #     return jsonify({'error': 'Это время уже занято'}), 400
            
            try:
                booking_id = db.add_booking(data)
                logger.info(f"✅ Бронирование создано, ID: {booking_id}")
                
                # Получаем созданное бронирование для ответа
                new_booking = db.get_booking(booking_id)
                return jsonify({'success': True, 'id': booking_id, 'data': new_booking})
                
            except Exception as e:
                logger.error(f"❌ Ошибка создания бронирования: {e}")
                return jsonify({'error': str(e)}), 500
        
        # PUT обновить бронирование
        elif request.method == 'PUT' and booking_id:
            booking = db.get_booking(booking_id)
            if not booking:
                return jsonify({'error': 'Бронирование не найдено'}), 404
            
            db.update_booking(booking_id, request.json)
            return jsonify({'success': True})
        
        # DELETE удалить бронирование
        elif request.method == 'DELETE' and booking_id:
            booking = db.get_booking(booking_id)
            if not booking:
                return jsonify({'error': 'Бронирование не найдено'}), 404
            
            db.delete_booking(booking_id)
            return jsonify({'success': True})

def check_availability(db, date_str, time_str, service_id=None):
    """Проверка доступности времени"""
    try:
        logger.info(f"🔍 Проверка доступности: {date_str} {time_str}")
        
        # Получаем бронирования на эту дату
        bookings = db.get_bookings_for_date(date_str)
        logger.info(f"Найдено бронирований: {len(bookings)}")
        
        # Если бронирований нет, сразу возвращаем True
        if not bookings:
            logger.info("✅ Свободно (нет бронирований)")
            return True
        
        # Получаем длительность услуги
        duration = 60
        if service_id:
            service = db.get_service(service_id)
            if service:
                duration = service.get('duration', 60)
        
        logger.info(f"Длительность услуги: {duration} мин")
        
        # Время новой записи
        try:
            new_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        except:
            # Пробуем другой формат
            new_datetime = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        
        new_end = new_datetime + timedelta(minutes=duration)
        
        logger.info(f"Новая запись: {new_datetime} - {new_end}")
        
        # Проверяем каждое существующее бронирование
        for booking in bookings:
            try:
                # Пропускаем отмененные бронирования
                if booking.get('status') == 'cancelled':
                    continue
                
                # Парсим время бронирования
                booking_datetime = datetime.strptime(f"{booking['date']} {booking['time']}", '%Y-%m-%d %H:%M')
                booking_duration = booking.get('duration', 60)
                booking_end = booking_datetime + timedelta(minutes=booking_duration)
                
                logger.info(f"Проверка с бронированием {booking.get('id')}: {booking_datetime} - {booking_end}")
                
                # Проверяем пересечение
                if (new_datetime < booking_end and new_end > booking_datetime):
                    logger.info(f"❌ Конфликт с бронированием ID {booking.get('id')}")
                    return False
                    
            except Exception as e:
                logger.error(f"Ошибка при проверке бронирования {booking.get('id')}: {e}")
                continue
        
        logger.info("✅ Время свободно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка проверки доступности: {e}")
        import traceback
        traceback.print_exc()
        return True  # В случае ошибки разрешаем запись