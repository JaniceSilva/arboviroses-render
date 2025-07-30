from flask import Blueprint, jsonify, request
from datetime import datetime, date
import os
import sys
import threading
import glob

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ml.prediction_model import ArbovirusPredictionModel
from src.models.user import db
from src.models.prediction import Prediction

ml_bp = Blueprint('ml', __name__)

# Cache global para modelos treinados
trained_models = {}
training_status = {}

@ml_bp.route('/ml/models', methods=['GET'])
def list_models():
    """
    Lista modelos salvos
    """
    try:
        model_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'models'
        )
        
        if not os.path.exists(model_dir):
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Nenhum modelo encontrado'
            })
        
        # Buscar arquivos de modelo
        model_files = glob.glob(os.path.join(model_dir, "*.keras"))
        models = []
        
        for model_file in model_files:
            base_name = os.path.basename(model_file).replace('.keras', '')
            metrics_file = os.path.join(model_dir, f"{base_name}_metrics.json")
            
            model_info = {
                'name': base_name,
                'path': model_file,
                'created_at': datetime.fromtimestamp(os.path.getctime(model_file)).isoformat(),
                'size_mb': round(os.path.getsize(model_file) / (1024 * 1024), 2),
                'has_metrics': os.path.exists(metrics_file)
            }
            
            # Carregar métricas se disponível
            if model_info['has_metrics']:
                try:
                    import json
                    with open(metrics_file, 'r') as f:
                        metrics = json.load(f)
                    model_info['metrics'] = metrics
                except Exception:
                    model_info['metrics'] = None
            
            models.append(model_info)
        
        # Ordenar por data de criação (mais recente primeiro)
        models.sort(key=lambda x: x['created_at'], reverse=True)
        
        return jsonify({
            'success': True,
            'data': models,
            'count': len(models)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ml_bp.route('/ml/train', methods=['POST'])
def train_model():
    """
    Treina um novo modelo
    
    Body parameters:
        municipality_code: Código IBGE do município
        disease_type: Tipo de doença
        use_synthetic_data: Se deve usar dados sintéticos (padrão: true)
        epochs: Número de épocas (padrão: 50)
    """
    try:
        data = request.json or {}
        
        municipality_code = data.get('municipality_code')
        disease_type = data.get('disease_type')
        use_synthetic_data = data.get('use_synthetic_data', True)
        epochs = data.get('epochs', 50)
        
        if not municipality_code or not disease_type:
            return jsonify({
                'success': False,
                'error': 'municipality_code e disease_type são obrigatórios'
            }), 400
        
        # Verificar se já está treinando
        training_key = f"{municipality_code}_{disease_type}"
        if training_key in training_status and training_status[training_key]['status'] == 'training':
            return jsonify({
                'success': False,
                'error': 'Modelo já está sendo treinado para este município e doença'
            }), 400
        
        # Inicializar status de treinamento
        training_status[training_key] = {
            'status': 'training',
            'started_at': datetime.now().isoformat(),
            'progress': 0,
            'message': 'Iniciando treinamento...'
        }
        
        def train_async():
            try:
                model = ArbovirusPredictionModel()
                
                # Atualizar status
                training_status[training_key]['message'] = 'Preparando dados...'
                training_status[training_key]['progress'] = 10
                
                # Treinar modelo
                metrics = model.train_model(
                    municipality_code, 
                    disease_type, 
                    use_synthetic_data=use_synthetic_data,
                    epochs=epochs
                )
                
                # Atualizar status
                training_status[training_key]['message'] = 'Salvando modelo...'
                training_status[training_key]['progress'] = 90
                
                # Salvar modelo
                model_path = model.save_model()
                
                # Armazenar modelo treinado no cache
                trained_models[training_key] = model
                
                # Finalizar status
                training_status[training_key] = {
                    'status': 'completed',
                    'completed_at': datetime.now().isoformat(),
                    'progress': 100,
                    'message': 'Treinamento concluído com sucesso',
                    'model_path': model_path,
                    'metrics': metrics
                }
                
            except Exception as e:
                training_status[training_key] = {
                    'status': 'failed',
                    'failed_at': datetime.now().isoformat(),
                    'progress': 0,
                    'message': f'Erro no treinamento: {str(e)}',
                    'error': str(e)
                }
        
        # Iniciar treinamento em thread separada
        thread = threading.Thread(target=train_async)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Treinamento iniciado',
            'training_key': training_key,
            'status': training_status[training_key]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ml_bp.route('/ml/training-status/<training_key>', methods=['GET'])
def get_training_status(training_key):
    """
    Obtém status do treinamento
    
    Args:
        training_key: Chave do treinamento (municipality_code_disease_type)
    """
    try:
        if training_key not in training_status:
            return jsonify({
                'success': False,
                'error': 'Treinamento não encontrado'
            }), 404
        
        return jsonify({
            'success': True,
            'data': training_status[training_key]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ml_bp.route('/ml/predict', methods=['POST'])
def make_prediction():
    """
    Faz predições usando modelo treinado
    
    Body parameters:
        municipality_code: Código IBGE do município
        disease_type: Tipo de doença
        weeks_ahead: Número de semanas para predizer (padrão: 4)
        model_path: Caminho do modelo (opcional, usa o mais recente se não especificado)
    """
    try:
        data = request.json or {}
        
        municipality_code = data.get('municipality_code')
        disease_type = data.get('disease_type')
        weeks_ahead = data.get('weeks_ahead', 4)
        model_path = data.get('model_path')
        
        if not municipality_code or not disease_type:
            return jsonify({
                'success': False,
                'error': 'municipality_code e disease_type são obrigatórios'
            }), 400
        
        training_key = f"{municipality_code}_{disease_type}"
        
        # Verificar se há modelo no cache
        if training_key in trained_models:
            model = trained_models[training_key]
        else:
            # Carregar modelo do disco
            if not model_path:
                # Buscar modelo mais recente
                model_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    'models'
                )
                
                model_files = glob.glob(os.path.join(model_dir, "arbovirus_predictor_*.keras"))
                if not model_files:
                    return jsonify({
                        'success': False,
                        'error': 'Nenhum modelo treinado encontrado'
                    }), 404
                
                # Pegar o mais recente
                model_files.sort(key=os.path.getctime, reverse=True)
                model_path = model_files[0].replace('.keras', '')
            
            # Carregar modelo
            model = ArbovirusPredictionModel()
            model.load_model(model_path)
            
            # Armazenar no cache
            trained_models[training_key] = model
        
        # Gerar predições
        predictions = model.generate_predictions_for_municipality(
            municipality_code, disease_type, weeks_ahead
        )
        
        return jsonify({
            'success': True,
            'data': predictions,
            'count': len(predictions),
            'model_info': {
                'municipality_code': municipality_code,
                'disease_type': disease_type,
                'weeks_ahead': weeks_ahead,
                'model_metrics': model.model_metrics if hasattr(model, 'model_metrics') else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ml_bp.route('/ml/save-predictions', methods=['POST'])
def save_predictions_to_db():
    """
    Salva predições no banco de dados
    
    Body parameters:
        municipality_code: Código IBGE do município
        disease_type: Tipo de doença
        weeks_ahead: Número de semanas para predizer (padrão: 4)
        municipality_name: Nome do município
        state: Estado
    """
    try:
        data = request.json or {}
        
        municipality_code = data.get('municipality_code')
        disease_type = data.get('disease_type')
        weeks_ahead = data.get('weeks_ahead', 4)
        municipality_name = data.get('municipality_name', 'Desconhecido')
        state = data.get('state', 'XX')
        
        if not municipality_code or not disease_type:
            return jsonify({
                'success': False,
                'error': 'municipality_code e disease_type são obrigatórios'
            }), 400
        
        training_key = f"{municipality_code}_{disease_type}"
        
        # Verificar se há modelo disponível
        if training_key not in trained_models:
            return jsonify({
                'success': False,
                'error': 'Modelo não encontrado. Treine um modelo primeiro.'
            }), 404
        
        model = trained_models[training_key]
        
        # Gerar predições
        predictions = model.generate_predictions_for_municipality(
            municipality_code, disease_type, weeks_ahead
        )
        
        # Salvar no banco de dados
        saved_predictions = []
        
        for pred_data in predictions:
            # Verificar se já existe predição para esta data
            existing = Prediction.query.filter(
                Prediction.municipality_code == municipality_code,
                Prediction.disease_type == disease_type,
                Prediction.prediction_date == pred_data['prediction_date']
            ).first()
            
            if existing:
                # Atualizar predição existente
                existing.predicted_cases = pred_data['predicted_cases_suspected']
                existing.predicted_incidence_rate = pred_data['predicted_incidence_rate']
                existing.predicted_alert_level = pred_data['alert_level']
                existing.confidence_interval_lower = pred_data['confidence_interval_lower']
                existing.confidence_interval_upper = pred_data['confidence_interval_upper']
                existing.model_version = pred_data['model_version']
                existing.updated_at = datetime.now()
                
                saved_predictions.append(existing.to_dict())
            else:
                # Criar nova predição
                prediction = Prediction(
                    municipality_code=municipality_code,
                    municipality_name=municipality_name,
                    state=state.upper(),
                    disease_type=disease_type.lower(),
                    prediction_date=pred_data['prediction_date'],
                    prediction_period=f"{pred_data['year']}-W{pred_data['epidemiological_week']:02d}",
                    predicted_cases=pred_data['predicted_cases_suspected'],
                    predicted_incidence_rate=pred_data['predicted_incidence_rate'],
                    predicted_alert_level=pred_data['alert_level'],
                    confidence_interval_lower=pred_data['confidence_interval_lower'],
                    confidence_interval_upper=pred_data['confidence_interval_upper'],
                    confidence_score=0.8,  # Score fixo para demonstração
                    model_version=pred_data['model_version']
                )
                
                db.session.add(prediction)
                saved_predictions.append(prediction.to_dict())
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': saved_predictions,
            'count': len(saved_predictions),
            'message': f'{len(saved_predictions)} predições salvas no banco de dados'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ml_bp.route('/ml/run-monthly-predictions', methods=['POST'])
def run_monthly_predictions():
    """
    Executa predições mensais para todos os municípios com modelos treinados
    """
    try:
        # Lista de municípios principais
        municipalities = [
            {"code": "3550308", "name": "São Paulo", "state": "SP"},
            {"code": "3304557", "name": "Rio de Janeiro", "state": "RJ"},
            {"code": "2927408", "name": "Salvador", "state": "BA"},
            {"code": "2304400", "name": "Fortaleza", "state": "CE"},
            {"code": "1302603", "name": "Manaus", "state": "AM"},
            {"code": "5300108", "name": "Brasília", "state": "DF"}
        ]
        
        diseases = ["dengue", "chikungunya", "zika"]
        
        results = []
        errors = []
        
        for municipality in municipalities:
            for disease in diseases:
                try:
                    training_key = f"{municipality['code']}_{disease}"
                    
                    # Verificar se há modelo treinado
                    if training_key not in trained_models:
                        # Tentar treinar modelo rapidamente
                        model = ArbovirusPredictionModel()
                        model.train_model(
                            municipality['code'], 
                            disease, 
                            use_synthetic_data=True,
                            epochs=20  # Treinamento rápido
                        )
                        trained_models[training_key] = model
                    
                    model = trained_models[training_key]
                    
                    # Gerar e salvar predições
                    predictions = model.generate_predictions_for_municipality(
                        municipality['code'], disease, weeks_ahead=4
                    )
                    
                    # Salvar no banco
                    for pred_data in predictions:
                        existing = Prediction.query.filter(
                            Prediction.municipality_code == municipality['code'],
                            Prediction.disease_type == disease,
                            Prediction.prediction_date == pred_data['prediction_date']
                        ).first()
                        
                        if existing:
                            existing.predicted_cases_suspected = pred_data['predicted_cases_suspected']
                            existing.predicted_cases_confirmed = pred_data['predicted_cases_confirmed']
                            existing.predicted_incidence_rate = pred_data['predicted_incidence_rate']
                            existing.updated_at = datetime.now()
                        else:
                            prediction = Prediction(
                                municipality_code=municipality['code'],
                                municipality_name=municipality['name'],
                                state=municipality['state'],
                                disease_type=disease,
                                prediction_date=pred_data['prediction_date'],
                                epidemiological_week=pred_data['epidemiological_week'],
                                year=pred_data['year'],
                                predicted_cases_suspected=pred_data['predicted_cases_suspected'],
                                predicted_cases_confirmed=pred_data['predicted_cases_confirmed'],
                                predicted_incidence_rate=pred_data['predicted_incidence_rate'],
                                confidence_interval_lower=pred_data['confidence_interval_lower'],
                                confidence_interval_upper=pred_data['confidence_interval_upper'],
                                alert_level=pred_data['alert_level'],
                                model_version=pred_data['model_version']
                            )
                            db.session.add(prediction)
                    
                    results.append({
                        'municipality': municipality['name'],
                        'disease': disease,
                        'predictions_count': len(predictions),
                        'status': 'success'
                    })
                    
                except Exception as e:
                    errors.append({
                        'municipality': municipality['name'],
                        'disease': disease,
                        'error': str(e)
                    })
        
        db.session.commit()
        
        return jsonify({
            'success': len(errors) == 0,
            'data': {
                'results': results,
                'errors': errors,
                'total_processed': len(results),
                'total_errors': len(errors)
            },
            'message': f'Processadas {len(results)} predições com {len(errors)} erros'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

