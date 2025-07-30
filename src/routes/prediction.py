from flask import Blueprint, jsonify, request
from src.models.prediction import Prediction, db
from datetime import datetime, date

prediction_bp = Blueprint('prediction', __name__)

@prediction_bp.route('/predictions', methods=['GET'])
def get_predictions():
    """
    Obtém predições com filtros opcionais
    Query parameters:
    - municipality_code: Código IBGE do município
    - state: UF do estado
    - disease_type: Tipo de doença (dengue, chikungunya, zika)
    - prediction_period: Período da predição
    - start_date: Data inicial da predição (YYYY-MM-DD)
    - end_date: Data final da predição (YYYY-MM-DD)
    - limit: Número máximo de registros (padrão: 100)
    """
    try:
        # Parâmetros de filtro
        municipality_code = request.args.get('municipality_code')
        state = request.args.get('state')
        disease_type = request.args.get('disease_type')
        prediction_period = request.args.get('prediction_period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        # Construir query
        query = Prediction.query
        
        if municipality_code:
            query = query.filter(Prediction.municipality_code == municipality_code)
        
        if state:
            query = query.filter(Prediction.state == state.upper())
        
        if disease_type:
            query = query.filter(Prediction.disease_type == disease_type.lower())
        
        if prediction_period:
            query = query.filter(Prediction.prediction_period == prediction_period)
        
        if start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(Prediction.prediction_date >= start_date_obj)
        
        if end_date:
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(Prediction.prediction_date <= end_date_obj)
        
        # Ordenar por data de predição (mais recente primeiro) e aplicar limite
        predictions = query.order_by(Prediction.prediction_date.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'data': [pred.to_dict() for pred in predictions],
            'count': len(predictions)
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

@prediction_bp.route('/predictions', methods=['POST'])
def create_prediction():
    """
    Cria uma nova predição
    """
    try:
        data = request.json
        
        # Validar dados obrigatórios
        required_fields = ['municipality_code', 'municipality_name', 'state', 
                          'prediction_date', 'prediction_period', 'disease_type', 'predicted_cases']
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
        
        # Converter data
        prediction_date_obj = datetime.strptime(data['prediction_date'], '%Y-%m-%d').date()
        
        # Criar nova predição
        prediction = Prediction(
            municipality_code=data['municipality_code'],
            municipality_name=data['municipality_name'],
            state=data['state'].upper(),
            prediction_date=prediction_date_obj,
            prediction_period=data['prediction_period'],
            disease_type=data['disease_type'].lower(),
            predicted_cases=float(data['predicted_cases']),
            predicted_incidence_rate=data.get('predicted_incidence_rate'),
            predicted_alert_level=data.get('predicted_alert_level'),
            confidence_interval_lower=data.get('confidence_interval_lower'),
            confidence_interval_upper=data.get('confidence_interval_upper'),
            confidence_score=data.get('confidence_score'),
            model_version=data.get('model_version'),
            model_accuracy=data.get('model_accuracy'),
            features_used=data.get('features_used')
        )
        
        db.session.add(prediction)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': prediction.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': 'Formato de data inválido ou parâmetros inválidos'
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@prediction_bp.route('/predictions/<int:prediction_id>', methods=['GET'])
def get_prediction_by_id(prediction_id):
    """
    Obtém predição por ID
    """
    try:
        prediction = Prediction.query.get_or_404(prediction_id)
        return jsonify({
            'success': True,
            'data': prediction.to_dict()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@prediction_bp.route('/predictions/latest', methods=['GET'])
def get_latest_predictions():
    """
    Obtém as predições mais recentes por município e doença
    Query parameters:
    - municipality_code: Código IBGE do município
    - state: UF do estado
    - disease_type: Tipo de doença (dengue, chikungunya, zika)
    """
    try:
        municipality_code = request.args.get('municipality_code')
        state = request.args.get('state')
        disease_type = request.args.get('disease_type')
        
        # Construir query base
        query = Prediction.query
        
        if municipality_code:
            query = query.filter(Prediction.municipality_code == municipality_code)
        
        if state:
            query = query.filter(Prediction.state == state.upper())
        
        if disease_type:
            query = query.filter(Prediction.disease_type == disease_type.lower())
        
        # Obter predições mais recentes por município e doença
        subquery = db.session.query(
            Prediction.municipality_code,
            Prediction.disease_type,
            db.func.max(Prediction.prediction_date).label('max_date')
        ).group_by(
            Prediction.municipality_code,
            Prediction.disease_type
        ).subquery()
        
        predictions = query.join(
            subquery,
            db.and_(
                Prediction.municipality_code == subquery.c.municipality_code,
                Prediction.disease_type == subquery.c.disease_type,
                Prediction.prediction_date == subquery.c.max_date
            )
        ).all()
        
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

@prediction_bp.route('/predictions/summary', methods=['GET'])
def get_predictions_summary():
    """
    Obtém resumo das predições por estado e doença
    Query parameters:
    - state: UF do estado
    - prediction_period: Período da predição
    """
    try:
        state = request.args.get('state')
        prediction_period = request.args.get('prediction_period')
        
        # Construir query
        query = Prediction.query
        
        if state:
            query = query.filter(Prediction.state == state.upper())
        
        if prediction_period:
            query = query.filter(Prediction.prediction_period == prediction_period)
        
        # Obter dados
        predictions = query.all()
        
        # Agrupar por estado e doença
        summary = {}
        for pred in predictions:
            key = f"{pred.state}_{pred.disease_type}"
            if key not in summary:
                summary[key] = {
                    'state': pred.state,
                    'disease_type': pred.disease_type,
                    'total_predicted_cases': 0,
                    'avg_confidence_score': 0,
                    'municipalities_count': 0,
                    'high_risk_municipalities': 0,  # alert_level >= 3
                    'confidence_scores': []
                }
            
            summary[key]['total_predicted_cases'] += pred.predicted_cases or 0
            summary[key]['municipalities_count'] += 1
            
            if pred.confidence_score:
                summary[key]['confidence_scores'].append(pred.confidence_score)
            
            if pred.predicted_alert_level and pred.predicted_alert_level >= 3:
                summary[key]['high_risk_municipalities'] += 1
        
        # Calcular médias
        for key in summary:
            if summary[key]['confidence_scores']:
                summary[key]['avg_confidence_score'] = sum(summary[key]['confidence_scores']) / len(summary[key]['confidence_scores'])
            del summary[key]['confidence_scores']  # Remover lista temporária
        
        return jsonify({
            'success': True,
            'data': list(summary.values()),
            'count': len(summary)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

