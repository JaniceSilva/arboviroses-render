#!/usr/bin/env python3
"""
Script de teste para validar configurações do projeto
"""
import os
import sys
import logging
from datetime import datetime

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

def test_imports():
    """Testa se todos os imports estão funcionando"""
    logger.info("🔍 Testando imports...")
    
    try:
        # Testar imports principais
        from flask import Flask
        from src.models.user import db, User
        from src.models.climate_data import ClimateData
        from src.models.arbovirus_data import ArbovirusData
        from src.models.prediction import Prediction
        
        # Testar imports dos jobs
        from src.jobs.climate_collector import ClimateCollector
        from src.jobs.infodengue_collector import InfoDengueCollector
        from src.jobs.scheduler import JobScheduler
        
        # Testar imports das rotas
        from src.routes.user import user_bp
        from src.routes.climate import climate_bp
        from src.routes.arbovirus import arbovirus_bp
        from src.routes.prediction import prediction_bp
        from src.routes.dashboard import dashboard_bp
        from src.routes.jobs import jobs_bp
        from src.routes.ml import ml_bp
        
        logger.info("✅ Todos os imports funcionando")
        return True
        
    except ImportError as e:
        logger.error(f"❌ Erro no import: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Erro inesperado: {e}")
        return False

def test_flask_app():
    """Testa se a aplicação Flask pode ser criada"""
    logger.info("🌐 Testando aplicação Flask...")
    
    try:
        from flask import Flask
        from src.models.user import db
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SECRET_KEY'] = 'test-key'
        
        # Registrar blueprints
        from src.routes.user import user_bp
        from src.routes.climate import climate_bp
        from src.routes.arbovirus import arbovirus_bp
        from src.routes.prediction import prediction_bp
        from src.routes.dashboard import dashboard_bp
        from src.routes.jobs import jobs_bp
        from src.routes.ml import ml_bp
        
        app.register_blueprint(user_bp, url_prefix='/api')
        app.register_blueprint(climate_bp, url_prefix='/api')
        app.register_blueprint(arbovirus_bp, url_prefix='/api')
        app.register_blueprint(prediction_bp, url_prefix='/api')
        app.register_blueprint(dashboard_bp, url_prefix='/api')
        app.register_blueprint(jobs_bp, url_prefix='/api')
        app.register_blueprint(ml_bp, url_prefix='/api')
        
        # Inicializar banco
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
        
        logger.info("✅ Aplicação Flask criada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na aplicação Flask: {e}")
        return False

def test_database_models():
    """Testa se os modelos de banco funcionam"""
    logger.info("🗄️  Testando modelos de banco...")
    
    try:
        from flask import Flask
        from src.models.user import db, User
        from src.models.climate_data import ClimateData
        from src.models.arbovirus_data import ArbovirusData
        from src.models.prediction import Prediction
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        
        with app.app_context():
            db.create_all()
            
            # Testar criação de registros
            user = User(username='test', email='test@test.com')
            db.session.add(user)
            
            climate = ClimateData(
                municipality_code='3550308',
                municipality_name='São Paulo',
                state='SP',
                date=datetime.now().date(),
                temperature_avg=25.0
            )
            db.session.add(climate)
            
            arbovirus = ArbovirusData(
                municipality_code='3550308',
                municipality_name='São Paulo',
                state='SP',
                epidemiological_week=30,
                year=2025,
                disease_type='dengue',
                cases_suspected=100
            )
            db.session.add(arbovirus)
            
            prediction = Prediction(
                municipality_code='3550308',
                municipality_name='São Paulo',
                state='SP',
                prediction_date=datetime.now().date(),
                prediction_period='2025-08',
                disease_type='dengue',
                predicted_cases=150.0
            )
            db.session.add(prediction)
            
            db.session.commit()
            
            # Verificar se foram criados
            assert User.query.count() == 1
            assert ClimateData.query.count() == 1
            assert ArbovirusData.query.count() == 1
            assert Prediction.query.count() == 1
        
        logger.info("✅ Modelos de banco funcionando")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro nos modelos: {e}")
        return False

def test_job_scripts():
    """Testa se os scripts de job podem ser executados"""
    logger.info("⚙️  Testando scripts de job...")
    
    try:
        # Testar se os scripts existem e são executáveis
        scripts = [
            'src/jobs/run_climate_job.py',
            'src/jobs/run_infodengue_job.py',
            'src/jobs/run_historical_job.py'
        ]
        
        for script in scripts:
            if not os.path.exists(script):
                logger.error(f"❌ Script não encontrado: {script}")
                return False
            
            # Verificar se o arquivo é legível
            with open(script, 'r') as f:
                content = f.read()
                if 'def main():' not in content:
                    logger.error(f"❌ Script inválido: {script}")
                    return False
        
        logger.info("✅ Scripts de job válidos")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro nos scripts: {e}")
        return False

def test_requirements():
    """Testa se todas as dependências estão listadas"""
    logger.info("📦 Testando requirements...")
    
    try:
        with open('requirements.txt', 'r') as f:
            requirements = f.read()
        
        # Verificar dependências essenciais
        essential_deps = [
            'Flask',
            'flask-cors',
            'Flask-SQLAlchemy',
            'psycopg2-binary',
            'gunicorn',
            'requests',
            'pandas',
            'numpy',
            'scikit-learn'
        ]
        
        missing_deps = []
        for dep in essential_deps:
            if dep.lower() not in requirements.lower():
                missing_deps.append(dep)
        
        if missing_deps:
            logger.error(f"❌ Dependências faltando: {missing_deps}")
            return False
        
        logger.info("✅ Requirements válidos")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro no requirements: {e}")
        return False

def test_render_config():
    """Testa se a configuração do Render está válida"""
    logger.info("🚀 Testando configuração do Render...")
    
    try:
        import yaml
        
        with open('render.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Verificar estrutura básica
        if 'services' not in config:
            logger.error("❌ Seção 'services' não encontrada")
            return False
        
        if 'databases' not in config:
            logger.error("❌ Seção 'databases' não encontrada")
            return False
        
        # Verificar serviços
        services = config['services']
        service_types = [s.get('type') for s in services]
        
        if 'web' not in service_types:
            logger.error("❌ Serviço web não encontrado")
            return False
        
        cron_count = service_types.count('cron')
        if cron_count < 3:
            logger.warning(f"⚠️  Apenas {cron_count} cron jobs configurados")
        
        logger.info(f"✅ Configuração do Render válida ({len(services)} serviços)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro na configuração do Render: {e}")
        return False

def main():
    """Função principal de teste"""
    logger.info("🧪 Iniciando testes de configuração...")
    logger.info("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Flask App", test_flask_app),
        ("Database Models", test_database_models),
        ("Job Scripts", test_job_scripts),
        ("Requirements", test_requirements),
        ("Render Config", test_render_config),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n🔍 Executando: {test_name}")
        if test_func():
            passed += 1
        else:
            logger.error(f"❌ Falhou: {test_name}")
    
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 Resultado: {passed}/{total} testes passaram")
    
    if passed == total:
        logger.info("🎉 Todos os testes passaram! Projeto pronto para deploy.")
        return True
    else:
        logger.error(f"❌ {total - passed} testes falharam. Corrija os problemas antes do deploy.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

