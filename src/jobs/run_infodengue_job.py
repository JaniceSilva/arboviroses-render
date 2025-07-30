#!/usr/bin/env python3
"""
Script executável para job de coleta de dados do InfoDengue
"""
import os
import sys
import logging
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Função principal do job"""
    logger.info("🦟 Iniciando job de coleta de dados do InfoDengue...")
    
    try:
        # Configurar Flask app context
        from flask import Flask
        from src.models.user import db
        from src.jobs.infodengue_collector import run_infodengue_collection
        
        app = Flask(__name__)
        
        # Configurar banco
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL não configurada")
            sys.exit(1)
        
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-key')
        
        # Inicializar banco
        db.init_app(app)
        
        with app.app_context():
            # Executar coleta
            result = run_infodengue_collection()
            
            if result.get('success', False):
                logger.info(f"✅ Job concluído com sucesso - {result.get('collected_count', 0)} dados coletados")
            else:
                logger.error(f"❌ Job falhou - {len(result.get('errors', []))} erros")
                for error in result.get('errors', []):
                    logger.error(f"   - {error}")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Erro no job: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

