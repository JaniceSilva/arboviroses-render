"""
Script para inicialização e configuração do banco de dados
"""
import os
import sys
import sqlite3
from datetime import datetime, date

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.user import db
from src.models.climate_data import ClimateData
from src.models.arbovirus_data import ArbovirusData
from src.models.prediction import Prediction
from flask import Flask

def create_app():
    """Criar aplicação Flask para inicialização do banco"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), 'app.db')}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    return app

def init_database():
    """Inicializar banco de dados e criar tabelas"""
    app = create_app()
    
    with app.app_context():
        # Criar todas as tabelas
        db.create_all()
        print("✅ Tabelas criadas com sucesso!")
        
        # Verificar se as tabelas foram criadas
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"📋 Tabelas criadas: {', '.join(tables)}")
        
        return True

def add_sample_data():
    """Adicionar dados de exemplo para teste"""
    app = create_app()
    
    with app.app_context():
        # Verificar se já existem dados
        if ClimateData.query.first() is not None:
            print("⚠️  Dados de exemplo já existem no banco")
            return
        
        # Dados de exemplo para clima
        sample_climate = ClimateData(
            municipality_code="3550308",  # São Paulo
            municipality_name="São Paulo",
            state="SP",
            date=date.today(),
            temperature_max=28.5,
            temperature_min=18.2,
            temperature_avg=23.4,
            humidity=65.0,
            precipitation=0.0,
            wind_speed=12.5,
            pressure=1013.2
        )
        
        # Dados de exemplo para arboviroses
        sample_arbovirus = ArbovirusData(
            municipality_code="3550308",  # São Paulo
            municipality_name="São Paulo",
            state="SP",
            epidemiological_week=29,
            year=2025,
            disease_type="dengue",
            cases_suspected=150,
            cases_confirmed=45,
            cases_probable=120,
            incidence_rate=1.2,
            alert_level=2,
            population=12396372
        )
        
        # Dados de exemplo para predição
        sample_prediction = Prediction(
            municipality_code="3550308",  # São Paulo
            municipality_name="São Paulo",
            state="SP",
            prediction_date=date.today(),
            prediction_period="2025-08",
            disease_type="dengue",
            predicted_cases=180.5,
            predicted_incidence_rate=1.45,
            predicted_alert_level=2,
            confidence_interval_lower=150.0,
            confidence_interval_upper=220.0,
            confidence_score=0.78,
            model_version="v1.0",
            model_accuracy=0.85,
            features_used='{"temperature": true, "humidity": true, "precipitation": true}'
        )
        
        # Adicionar ao banco
        db.session.add(sample_climate)
        db.session.add(sample_arbovirus)
        db.session.add(sample_prediction)
        
        try:
            db.session.commit()
            print("✅ Dados de exemplo adicionados com sucesso!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro ao adicionar dados de exemplo: {e}")

def check_database_status():
    """Verificar status do banco de dados"""
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar conexão usando SQLAlchemy 2.x syntax
            with db.engine.connect() as connection:
                connection.execute(db.text("SELECT 1"))
            print("✅ Conexão com banco de dados OK")
            
            # Contar registros em cada tabela
            climate_count = ClimateData.query.count()
            arbovirus_count = ArbovirusData.query.count()
            prediction_count = Prediction.query.count()
            
            print(f"📊 Estatísticas do banco:")
            print(f"   - Dados de clima: {climate_count} registros")
            print(f"   - Dados de arboviroses: {arbovirus_count} registros")
            print(f"   - Predições: {prediction_count} registros")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro na conexão com banco: {e}")
            return False

if __name__ == "__main__":
    print("🚀 Inicializando banco de dados...")
    
    # Inicializar banco
    if init_database():
        print("✅ Banco de dados inicializado!")
        
        # Adicionar dados de exemplo
        add_sample_data()
        
        # Verificar status
        check_database_status()
        
        print("🎉 Configuração do banco concluída!")
    else:
        print("❌ Falha na inicialização do banco de dados")

