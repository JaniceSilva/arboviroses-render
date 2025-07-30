from flask import Blueprint, jsonify, request
from src.models.climate_data import ClimateData, db
from src.utils.data_validator import DataValidator
from datetime import datetime, date

climate_bp = Blueprint('climate', __name__)

@climate_bp.route('/climate', methods=['GET'])
def get_climate_data():
    """
    Obtém dados de clima com filtros opcionais
    Query parameters:
    - municipality_code: Código IBGE do município
    - state: UF do estado
    - start_date: Data inicial (YYYY-MM-DD)
    - end_date: Data final (YYYY-MM-DD)
    - limit: Número máximo de registros (padrão: 100)
    """
    try:
        # Parâmetros de filtro
        municipality_code = request.args.get('municipality_code')
        state = request.args.get('state')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        # Construir query
        query = ClimateData.query
        
        if municipality_code:
            query = query.filter(ClimateData.municipality_code == municipality_code)
        
        if state:
            query = query.filter(ClimateData.state == state.upper())
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(ClimateData.date >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(ClimateData.date <= end_date_obj)
        
        # Ordenar por data (mais recente primeiro) e aplicar limite
        climate_data = query.order_by(ClimateData.date.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [data.to_dict() for data in climate_data],
            'count': len(climate_data)
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Formato de data inválido. Use YYYY-MM-DD'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@climate_bp.route('/climate', methods=['POST'])
def create_climate_data():
    """
    Cria um novo registro de dados de clima
    """
    try:
        data = request.json
        
        # Validar dados usando DataValidator
        is_valid, errors = DataValidator.validate_climate_data(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'errors': errors
            }), 400
        
        # Converter data
        date_obj = datetime.strptime(data['date'], '%Y-%m-%d').date()
        
        # Criar novo registro
        climate_data = ClimateData(
            municipality_code=data['municipality_code'],
            municipality_name=data['municipality_name'],
            state=data['state'].upper(),
            date=date_obj,
            temperature_max=data.get('temperature_max'),
            temperature_min=data.get('temperature_min'),
            temperature_avg=data.get('temperature_avg'),
            humidity=data.get('humidity'),
            precipitation=data.get('precipitation'),
            wind_speed=data.get('wind_speed'),
            pressure=data.get('pressure')
        )
        
        db.session.add(climate_data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': climate_data.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Formato de data inválido. Use YYYY-MM-DD'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@climate_bp.route('/climate/<int:climate_id>', methods=['GET'])
def get_climate_data_by_id(climate_id):
    """
    Obtém dados de clima por ID
    """
    try:
        climate_data = ClimateData.query.get_or_404(climate_id)
        return jsonify({
            'success': True,
            'data': climate_data.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@climate_bp.route('/climate/municipalities', methods=['GET'])
def get_municipalities():
    """
    Obtém lista de municípios com dados de clima
    """
    try:
        municipalities = db.session.query(
            ClimateData.municipality_code,
            ClimateData.municipality_name,
            ClimateData.state
        ).distinct().all()
        
        result = [
            {
                'municipality_code': mun[0],
                'municipality_name': mun[1],
                'state': mun[2]
            }
            for mun in municipalities
        ]
        
        return jsonify({
            'success': True,
            'data': result,
            'count': len(result)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

