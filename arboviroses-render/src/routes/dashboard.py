from flask import Blueprint, jsonify, request
from datetime import datetime
from src.utils.database_manager import DatabaseManager
from src.models.user import db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard/statistics', methods=['GET'])
def get_database_statistics():
    """
    Obtém estatísticas gerais do banco de dados
    """
    try:
        stats = DatabaseManager.get_database_statistics()
        return jsonify({
            'success': True,
            'data': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/dashboard/municipalities', methods=['GET'])
def get_municipalities_with_data():
    """
    Obtém lista de municípios que possuem dados
    """
    try:
        municipalities = DatabaseManager.get_municipalities_with_data()
        return jsonify({
            'success': True,
            'data': municipalities,
            'count': len(municipalities)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/dashboard/state/<state>', methods=['GET'])
def get_state_summary(state):
    """
    Obtém resumo dos dados por estado
    
    Args:
        state: UF do estado
    """
    try:
        summary = DatabaseManager.get_data_summary_by_state(state)
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/dashboard/municipality/<municipality_code>/latest-predictions', methods=['GET'])
def get_municipality_latest_predictions(municipality_code):
    """
    Obtém as predições mais recentes de um município
    
    Args:
        municipality_code: Código IBGE do município
    
    Query parameters:
        disease_type: Tipo de doença (opcional)
    """
    try:
        disease_type = request.args.get('disease_type')
        predictions = DatabaseManager.get_latest_predictions_by_municipality(
            municipality_code, disease_type
        )
        
        return jsonify({
            'success': True,
            'data': [pred.to_dict() for pred in predictions],
            'count': len(predictions)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@dashboard_bp.route('/dashboard/health', methods=['GET'])
def health_check():
    """
    Verifica a saúde da aplicação e do banco de dados
    """
    try:
        # Testar conexão com banco
        with db.engine.connect() as connection:
            connection.execute(db.text("SELECT 1"))
        
        # Obter estatísticas básicas
        stats = DatabaseManager.get_database_statistics()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database': 'connected',
            'total_records': sum(stats['total_records'].values()),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 500

@dashboard_bp.route('/dashboard/cleanup', methods=['POST'])
def cleanup_old_data():
    """
    Remove dados antigos do banco de dados
    
    Body parameters:
        days_to_keep: Número de dias de dados para manter (padrão: 365)
    """
    try:
        data = request.json or {}
        days_to_keep = data.get('days_to_keep', 365)
        
        if not isinstance(days_to_keep, int) or days_to_keep < 1:
            return jsonify({
                'success': False,
                'error': 'days_to_keep deve ser um número inteiro positivo'
            }), 400
        
        result = DatabaseManager.cleanup_old_data(days_to_keep)
        
        return jsonify({
            'success': True,
            'data': result,
            'message': f'Dados anteriores a {days_to_keep} dias foram removidos'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

