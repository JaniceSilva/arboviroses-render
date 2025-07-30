#!/usr/bin/env python3
"""
Script de inicialização do banco de dados para o Render
Execute este script após o primeiro deploy para configurar o banco
"""
import os
import sys
import logging

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(__file__))

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
    """Função principal de inicialização"""
    logger.info("🚀 Inicializando banco de dados no Render...")
    
    try:
        # Verificar se DATABASE_URL está configurada
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.error("❌ DATABASE_URL não configurada")
            logger.info("Configure a variável de ambiente DATABASE_URL no Render")
            sys.exit(1)
        
        # Configurar Flask app
        from flask import Flask
        from src.models.user import db
        
        # Importar todos os modelos
        from src.models.climate_data import ClimateData
        from src.models.arbovirus_data import ArbovirusData
        from src.models.prediction import Prediction
        from src.models.user import User
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-key')
        
        # Inicializar banco
        db.init_app(app)
        
        with app.app_context():
            logger.info("📊 Criando tabelas...")
            db.create_all()
            logger.info("✅ Tabelas criadas com sucesso")
            
            # Verificar tabelas criadas
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            logger.info(f"📋 Tabelas disponíveis: {tables}")
            
            # Criar índices otimizados
            logger.info("🔍 Criando índices...")
            try:
                from src.utils.postgres_optimizer import postgres_optimizer
                created_indexes = postgres_optimizer.create_indexes()
                logger.info(f"✅ {created_indexes} índices criados")
            except Exception as e:
                logger.warning(f"⚠️  Erro ao criar índices: {e}")
            
            # Executar otimizações
            logger.info("⚡ Executando otimizações...")
            try:
                from src.utils.postgres_optimizer import postgres_optimizer
                postgres_optimizer.optimize_queries()
                logger.info("✅ Otimizações executadas")
            except Exception as e:
                logger.warning(f"⚠️  Erro nas otimizações: {e}")
        
        logger.info("🎉 Inicialização concluída com sucesso!")
        logger.info("💡 Próximos passos:")
        logger.info("   1. Verificar se os cron jobs estão ativos no Render")
        logger.info("   2. Monitorar logs dos jobs de coleta")
        logger.info("   3. Verificar se os dados estão sendo coletados")
        
    except Exception as e:
        logger.error(f"❌ Erro na inicialização: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

