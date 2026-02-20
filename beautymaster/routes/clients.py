from flask import jsonify, request, session

def register_clients_routes(app, plugin):
    
    @app.route('/api/plugins/beautymaster/clients', methods=['GET', 'POST'])
    @app.route('/api/plugins/beautymaster/clients/<int:client_id>', methods=['GET', 'PUT', 'DELETE'])
    def beautymaster_clients(client_id=None):
        """Клиенты"""
        if 'user_id' not in session:
            return jsonify({'error': 'Не авторизован'}), 401
        
        db = plugin.get_current_master_db()
        if not db:
            return jsonify({'error': 'База данных не найдена'}), 400
        
        if request.method == 'GET' and client_id is None:
            clients = db.get_clients()
            return jsonify({'success': True, 'data': clients})
        
        elif request.method == 'GET' and client_id:
            client = db.get_client(client_id)
            if not client:
                return jsonify({'error': 'Клиент не найдена'}), 404
            return jsonify({'success': True, 'data': client})
        
        elif request.method == 'POST':
            data = request.json
            if not data or 'name' not in data or 'phone' not in data:
                return jsonify({'error': 'Не указаны имя или телефон'}), 400
            
            client_id = db.add_client(data)
            return jsonify({'success': True, 'id': client_id})
        
        elif request.method == 'PUT' and client_id:
            client = db.get_client(client_id)
            if not client:
                return jsonify({'error': 'Клиент не найден'}), 404
            
            db.update_client(client_id, request.json)
            return jsonify({'success': True})
        
        elif request.method == 'DELETE' and client_id:
            client = db.get_client(client_id)
            if not client:
                return jsonify({'error': 'Клиент не найден'}), 404
            
            db.delete_client(client_id)
            return jsonify({'success': True})