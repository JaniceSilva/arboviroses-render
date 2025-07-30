from flask import Blueprint, jsonify, request
from datetime import datetime
import threading
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.jobs.climate_collector import run_current_collection, run_historical_collection
from src.jobs.infodengue_collector import run_infodengue_collection
from src.jobs.scheduler import JobScheduler

jobs_bp = Blueprint('jobs', __name__)

# Instância global do agendador
scheduler_instance = None
scheduler_thread = None

@jobs_bp.route('/jobs/climate/current', methods=['POST'])
def run_climate_collection():
    """
    Executa coleta de dados de clima atuais
    """
    try:
        result = run_current_collection()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@jobs_bp.route('/jobs/climate/historical', methods=['POST'])
def run_climate_historical():
    """
    Executa coleta de dados históricos de clima
    
    Body parameters:
        days_back: Número de dias para voltar (padrão: 7)
    """
    try:
        data = request.json or {}
        days_back = data.get('days_back', 7)
        
        if not isinstance(days_back, int) or days_back < 1:
            return jsonify({
                'success': False,
                'error': 'days_back deve ser um número inteiro positivo'
            }), 400
        
        result = run_historical_collection(days_back)
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@jobs_bp.route('/jobs/infodengue', methods=['POST'])
def run_infodengue_collection_endpoint():
    """
    Executa coleta de dados do InfoDengue
    """
    try:
        result = run_infodengue_collection()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@jobs_bp.route('/jobs/scheduler/start', methods=['POST'])
def start_scheduler():
    """
    Inicia o agendador de jobs
    
    Body parameters:
        development_mode: Se true, usa intervalos menores para desenvolvimento
    """
    global scheduler_instance, scheduler_thread
    
    try:
        if scheduler_thread and scheduler_thread.is_alive():
            return jsonify({
                'success': False,
                'error': 'Agendador já está em execução'
            }), 400
        
        data = request.json or {}
        development_mode = data.get('development_mode', False)
        
        if development_mode:
            os.environ['DEVELOPMENT_MODE'] = 'true'
        else:
            os.environ.pop('DEVELOPMENT_MODE', None)
        
        scheduler_instance = JobScheduler()
        
        # Executar agendador em thread separada
        def run_scheduler():
            scheduler_instance.run_scheduler()
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Agendador iniciado com sucesso',
            'development_mode': development_mode
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@jobs_bp.route('/jobs/scheduler/stop', methods=['POST'])
def stop_scheduler():
    """
    Para o agendador de jobs
    """
    global scheduler_instance, scheduler_thread
    
    try:
        if not scheduler_thread or not scheduler_thread.is_alive():
            return jsonify({
                'success': False,
                'error': 'Agendador não está em execução'
            }), 400
        
        # Para o agendador (thread daemon será finalizada automaticamente)
        scheduler_instance = None
        scheduler_thread = None
        
        return jsonify({
            'success': True,
            'message': 'Agendador parado com sucesso'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@jobs_bp.route('/jobs/scheduler/status', methods=['GET'])
def get_scheduler_status():
    """
    Obtém status do agendador de jobs
    """
    try:
        global scheduler_instance, scheduler_thread
        
        is_running = scheduler_thread and scheduler_thread.is_alive()
        
        status = {
            'scheduler_running': is_running,
            'development_mode': os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true',
            'thread_alive': scheduler_thread.is_alive() if scheduler_thread else False
        }
        
        if scheduler_instance and is_running:
            try:
                job_status = scheduler_instance.get_job_status()
                status.update(job_status)
            except Exception as e:
                status['scheduler_error'] = str(e)
        
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@jobs_bp.route('/jobs/test-all', methods=['POST'])
def test_all_jobs():
    """
    Executa todos os jobs uma vez para teste
    """
    try:
        test_scheduler = JobScheduler()
        test_scheduler.run_all_jobs_once()
        
        return jsonify({
            'success': True,
            'data': test_scheduler.job_results,
            'message': 'Todos os jobs foram executados para teste'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@jobs_bp.route('/jobs/logs', methods=['GET'])
def get_job_logs():
    """
    Obtém logs dos jobs
    
    Query parameters:
        lines: Número de linhas para retornar (padrão: 100)
    """
    try:
        lines = request.args.get('lines', 100, type=int)
        
        log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'logs',
            'scheduler.log'
        )
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': True,
                'data': {
                    'logs': [],
                    'message': 'Arquivo de log não encontrado'
                }
            })
        
        # Ler últimas linhas do arquivo
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            'success': True,
            'data': {
                'logs': [line.strip() for line in recent_lines],
                'total_lines': len(all_lines),
                'returned_lines': len(recent_lines)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

