from flask import Blueprint, jsonify, request
from src.models.arbovirus_data import ArbovirusData, db

arbovirus_bp = Blueprint('arbovirus', __name__)

@arbovirus_bp.route('/arbovirus', methods=['GET'])
def get_arbovirus_data():
    """
    Obtém dados de arboviroses com filtros opcionais
    Query parameters:
    - municipality_code: Código IBGE do município
    - state: UF do estado
    - disease_type: Tipo de doença (dengue, chikungunya, zika)
    - year: Ano
    - epidemiological_week: Semana epidemiológica
    - limit: Número máximo de registros (padrão: 100)
    """
    try:
        # Parâmetros de filtro
        municipality_code = request.args.get('municipality_code')
        state = request.args.get('state')
        disease_type = request.args.get('disease_type')
        year = request.args.get('year')
        epidemiological_week = request.args.get('epidemiological_week')
        limit = int(request.args.get('limit', 100))
        
        # Construir query
        query = ArbovirusData.query
        
        if municipality_code:
            query = query.filter(ArbovirusData.municipality_code == municipality_code)
        
        if state:
            query = query.filter(ArbovirusData.state == state.upper())
        
        if disease_type:
            query = query.filter(ArbovirusData.disease_type == disease_type.lower())
        
        if year:
            query = query.filter(ArbovirusData.year == int(year))
        
        if epidemiological_week:
            query = query.filter(ArbovirusData.epidemiological_week == int(epidemiological_week))
        
        # Ordenar por ano e semana epidemiológica (mais recente primeiro) e aplicar limite
        arbovirus_data = query.order_by(
            ArbovirusData.year.desc(),
            ArbovirusData.epidemiological_week.desc()
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [data.to_dict() for data in arbovirus_data],
            'count': len(arbovirus_data)
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Parâmetros inválidos. Verifique os tipos de dados'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@arbovirus_bp.route('/arbovirus', methods=['POST'])
def create_arbovirus_data():
    """
    Cria um novo registro de dados de arboviroses
    """
    try:
        data = request.json
        
        # Validar dados obrigatórios
        required_fields = ['municipality_code', 'municipality_name', 'state', 
                          'epidemiological_week', 'year', 'disease_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Campo obrigatório ausente: {field}'
                }), 400
        
        # Validar tipo de doença
        valid_diseases = ['dengue', 'chikungunya', 'zika']
        if data['disease_type'].lower() not in valid_diseases:
            return jsonify({
                'success': False,
                'error': f'Tipo de doença inválido. Use: {", ".join(valid_diseases)}'
            }), 400
        
        # Criar novo registro
        arbovirus_data = ArbovirusData(
            municipality_code=data['municipality_code'],
            municipality_name=data['municipality_name'],
            state=data['state'].upper(),
            epidemiological_week=int(data['epidemiological_week']),
            year=int(data['year']),
            disease_type=data['disease_type'].lower(),
            cases_suspected=data.get('cases_suspected', 0),
            cases_confirmed=data.get('cases_confirmed', 0),
            cases_probable=data.get('cases_probable', 0),
            incidence_rate=data.get('incidence_rate'),
            alert_level=data.get('alert_level'),
            population=data.get('population')
        )
        
        db.session.add(arbovirus_data)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': arbovirus_data.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Parâmetros inválidos. Verifique os tipos de dados'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@arbovirus_bp.route('/arbovirus/<int:arbovirus_id>', methods=['GET'])
def get_arbovirus_data_by_id(arbovirus_id):
    """
    Obtém dados de arboviroses por ID
    """
    try:
        arbovirus_data = ArbovirusData.query.get_or_404(arbovirus_id)
        return jsonify({
            'success': True,
            'data': arbovirus_data.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@arbovirus_bp.route('/arbovirus/summary', methods=['GET'])
def get_arbovirus_summary():
    """
    Obtém resumo dos dados de arboviroses por município e doença
    Query parameters:
    - municipality_code: Código IBGE do município
    - state: UF do estado
    - year: Ano (padrão: ano atual)
    """
    try:
        municipality_code = request.args.get('municipality_code')
        state = request.args.get('state')
        year = request.args.get('year', 2025)
        
        # Construir query
        query = ArbovirusData.query.filter(ArbovirusData.year == int(year))
        
        if municipality_code:
            query = query.filter(ArbovirusData.municipality_code == municipality_code)
        
        if state:
            query = query.filter(ArbovirusData.state == state.upper())
        
        # Obter dados
        data = query.all()
        
        # Agrupar por município e doença
        summary = {}
        for record in data:
            key = f"{record.municipality_code}_{record.disease_type}"
            if key not in summary:
                summary[key] = {
                    'municipality_code': record.municipality_code,
                    'municipality_name': record.municipality_name,
                    'state': record.state,
                    'disease_type': record.disease_type,
                    'total_suspected': 0,
                    'total_confirmed': 0,
                    'total_probable': 0,
                    'max_alert_level': 0,
                    'weeks_count': 0
                }
            
            summary[key]['total_suspected'] += record.cases_suspected or 0
            summary[key]['total_confirmed'] += record.cases_confirmed or 0
            summary[key]['total_probable'] += record.cases_probable or 0
            summary[key]['max_alert_level'] = max(
                summary[key]['max_alert_level'], 
                record.alert_level or 0
            )
            summary[key]['weeks_count'] += 1
        
        return jsonify({
            'success': True,
            'data': list(summary.values()),
            'count': len(summary)
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Parâmetros inválidos. Verifique os tipos de dados'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@arbovirus_bp.route('/arbovirus/municipalities', methods=['GET'])
def get_arbovirus_municipalities():
    """
    Obtém lista de municípios com dados de arboviroses
    """
    try:
        municipalities = db.session.query(
            ArbovirusData.municipality_code,
            ArbovirusData.municipality_name,
            ArbovirusData.state
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

