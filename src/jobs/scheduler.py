"""
Agendador de jobs para coleta automática de dados
"""
import os
import sys
import schedule
import time
import logging
from datetime import datetime
from typing import Dict, Any

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.jobs.climate_collector import run_current_collection, run_historical_collection
from src.jobs.infodengue_collector import run_infodengue_collection

# Configurar logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, 'scheduler.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class JobScheduler:
    """Agendador de jobs para coleta automática de dados"""
    
    def __init__(self):
        self.job_results = {}
        
        # Diretório de logs já criado na configuração global
        self.log_dir = log_dir
    
    def log_job_result(self, job_name: str, result: Dict[str, Any]):
        """
        Registra o resultado de um job
        
        Args:
            job_name: Nome do job
            result: Resultado da execução
        """
        self.job_results[job_name] = {
            'last_run': datetime.now().isoformat(),
            'result': result
        }
        
        # Log do resultado
        if result.get('success', False):
            logger.info(f"✅ {job_name} executado com sucesso - {result.get('collected_count', 0)} dados coletados")
        else:
            logger.error(f"❌ {job_name} falhou - {len(result.get('errors', []))} erros")
            for error in result.get('errors', []):
                logger.error(f"   - {error}")
    
    def collect_climate_data_job(self):
        """Job para coleta de dados de clima"""
        logger.info("🌤️  Iniciando job de coleta de dados de clima...")
        
        try:
            result = run_current_collection()
            self.log_job_result("Coleta de Dados de Clima", result)
        except Exception as e:
            logger.error(f"❌ Erro no job de coleta de clima: {e}")
            self.log_job_result("Coleta de Dados de Clima", {
                'success': False,
                'errors': [str(e)],
                'collected_count': 0
            })
    
    def collect_infodengue_data_job(self):
        """Job para coleta de dados do InfoDengue"""
        logger.info("🦟 Iniciando job de coleta de dados do InfoDengue...")
        
        try:
            result = run_infodengue_collection()
            self.log_job_result("Coleta de Dados InfoDengue", result)
        except Exception as e:
            logger.error(f"❌ Erro no job de coleta InfoDengue: {e}")
            self.log_job_result("Coleta de Dados InfoDengue", {
                'success': False,
                'errors': [str(e)],
                'collected_count': 0
            })
    
    def collect_historical_climate_job(self):
        """Job para coleta de dados históricos de clima (semanal)"""
        logger.info("📅 Iniciando job de coleta de dados históricos de clima...")
        
        try:
            result = run_historical_collection(days_back=7)
            self.log_job_result("Coleta Histórica de Clima", result)
        except Exception as e:
            logger.error(f"❌ Erro no job de coleta histórica: {e}")
            self.log_job_result("Coleta Histórica de Clima", {
                'success': False,
                'errors': [str(e)],
                'collected_count': 0
            })
    
    def monthly_prediction_job(self):
        """Job para execução mensal de predições (placeholder)"""
        logger.info("🔮 Iniciando job de predição mensal...")
        
        # TODO: Implementar quando o modelo de ML estiver pronto
        logger.info("⚠️  Job de predição ainda não implementado")
        
        self.log_job_result("Predição Mensal", {
            'success': True,
            'message': 'Job de predição ainda não implementado',
            'collected_count': 0
        })
    
    def setup_schedules(self):
        """Configura os agendamentos dos jobs"""
        logger.info("⏰ Configurando agendamentos...")
        
        # Coleta de dados de clima - diariamente às 06:00
        schedule.every().day.at("06:00").do(self.collect_climate_data_job)
        logger.info("   - Coleta de clima: diariamente às 06:00")
        
        # Coleta de dados InfoDengue - diariamente às 07:00
        schedule.every().day.at("07:00").do(self.collect_infodengue_data_job)
        logger.info("   - Coleta InfoDengue: diariamente às 07:00")
        
        # Coleta histórica de clima - semanalmente às segundas às 05:00
        schedule.every().monday.at("05:00").do(self.collect_historical_climate_job)
        logger.info("   - Coleta histórica: segundas às 05:00")
        
        # Predição mensal - primeiro dia do mês às 08:00
        schedule.every().month.do(self.monthly_prediction_job)
        logger.info("   - Predição mensal: primeiro dia do mês às 08:00")
        
        # Para desenvolvimento/teste - executar a cada 30 minutos
        if os.getenv('DEVELOPMENT_MODE', 'false').lower() == 'true':
            schedule.every(30).minutes.do(self.collect_climate_data_job)
            schedule.every(35).minutes.do(self.collect_infodengue_data_job)
            logger.info("   - Modo desenvolvimento: jobs a cada 30-35 minutos")
    
    def run_scheduler(self):
        """Executa o agendador"""
        logger.info("🚀 Iniciando agendador de jobs...")
        
        self.setup_schedules()
        
        logger.info("⏰ Agendador ativo. Aguardando execução dos jobs...")
        logger.info("   Pressione Ctrl+C para parar")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Verificar a cada minuto
        except KeyboardInterrupt:
            logger.info("⏹️  Agendador interrompido pelo usuário")
        except Exception as e:
            logger.error(f"❌ Erro no agendador: {e}")
    
    def run_all_jobs_once(self):
        """Executa todos os jobs uma vez (para teste)"""
        logger.info("🧪 Executando todos os jobs uma vez para teste...")
        
        self.collect_climate_data_job()
        time.sleep(5)
        
        self.collect_infodengue_data_job()
        time.sleep(5)
        
        self.collect_historical_climate_job()
        time.sleep(5)
        
        self.monthly_prediction_job()
        
        logger.info("✅ Execução de teste concluída")
        
        # Mostrar resultados
        logger.info("📊 Resultados dos jobs:")
        for job_name, job_data in self.job_results.items():
            result = job_data['result']
            status = "✅" if result.get('success', False) else "❌"
            logger.info(f"   {status} {job_name}: {result.get('collected_count', 0)} dados coletados")
    
    def get_job_status(self) -> Dict[str, Any]:
        """
        Obtém status dos jobs
        
        Returns:
            Dicionário com status dos jobs
        """
        return {
            'scheduler_status': 'running',
            'next_runs': {
                'climate_collection': str(schedule.next_run()),
                'infodengue_collection': str(schedule.next_run()),
            },
            'job_results': self.job_results,
            'scheduled_jobs': len(schedule.jobs)
        }

def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agendador de jobs para coleta de dados")
    parser.add_argument("--test", action="store_true", help="Executar todos os jobs uma vez para teste")
    parser.add_argument("--dev", action="store_true", help="Modo desenvolvimento (jobs mais frequentes)")
    
    args = parser.parse_args()
    
    # Configurar modo desenvolvimento
    if args.dev:
        os.environ['DEVELOPMENT_MODE'] = 'true'
    
    scheduler = JobScheduler()
    
    if args.test:
        scheduler.run_all_jobs_once()
    else:
        scheduler.run_scheduler()

if __name__ == "__main__":
    main()

