from flask import jsonify, request, session

def register_services_routes(app, plugin):
    
    @app.route('/api/plugins/beautymaster/services', methods=['GET', 'POST'])
    @app.route('/api/plugins/beautymaster/services/<int:service_id>', methods=['GET', 'PUT', 'DELETE'])
    def beautymaster_services(service_id=None):
        """Услуги мастера"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        if request.method == 'GET' and service_id is None:
            services = db.get_services()
            categories = list(set(s['category'] for s in services if s['category']))
            return jsonify({
                'success': True, 
                'data': services,
                'categories': categories
            })
        
        elif request.method == 'GET' and service_id:
            service = db.get_service(service_id)
            if not service:
                return jsonify({'error': 'Услуга не найдена'}), 404
            return jsonify({'success': True, 'data': service})
        
        elif request.method == 'POST':
            data = request.json
            if not data or 'name' not in data or 'price' not in data:
                return jsonify({'error': 'Не указаны название или цена'}), 400
            
            service_id = db.add_service(data)
            return jsonify({'success': True, 'id': service_id})
        
        elif request.method == 'PUT' and service_id:
            service = db.get_service(service_id)
            if not service:
                return jsonify({'error': 'Услуга не найдена'}), 404
            
            db.update_service(service_id, request.json)
            return jsonify({'success': True})
        
        elif request.method == 'DELETE' and service_id:
            service = db.get_service(service_id)
            if not service:
                return jsonify({'error': 'Услуга не найдена'}), 404
            
            db.delete_service(service_id)
            return jsonify({'success': True})