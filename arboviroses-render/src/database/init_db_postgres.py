"""
Script para inicialização do banco de dados PostgreSQL
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def create_database_if_not_exists():
    """
    Cria o banco de dados se ele não existir
    """
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        print("❌ DATABASE_URL não configurada")
        return False
    
    try:
        # Tentar conectar ao banco
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Conexão com banco de dados estabelecida")
            return True
            
    except OperationalError as e:
        print(f"❌ Erro ao conectar com banco: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def initialize_tables():
    """
    Inicializa as tabelas do banco de dados
    """
    try:
        from flask import Flask
        from src.models.user import db
        from src.models.climate_data import ClimateData
        from src.models.arbovirus_data import ArbovirusData
        from src.models.prediction import Prediction
        
        # Criar app Flask temporário
        app = Flask(__name__)
        
        # Configurar banco
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        else:
            print("❌ DATABASE_URL não configurada")
            return False
            
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Inicializar banco
        db.init_app(app)
        
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            print("✅ Tabelas criadas com sucesso")
            
            # Verificar se as tabelas foram criadas
            tables = db.engine.table_names()
            print(f"📊 Tabelas disponíveis: {tables}")
            
        return True
        
    except Exception as e:
        print(f"❌ Erro ao inicializar tabelas: {e}")
        return False

def main():
    """
    Função principal
    """
    print("🚀 Inicializando banco de dados PostgreSQL...")
    
    # Verificar conexão
    if not create_database_if_not_exists():
        print("❌ Falha na conexão com banco de dados")
        sys.exit(1)
    
    # Inicializar tabelas
    if not initialize_tables():
        print("❌ Falha na inicialização das tabelas")
        sys.exit(1)
    
    print("✅ Banco de dados inicializado com sucesso!")

if __name__ == "__main__":
    main()

