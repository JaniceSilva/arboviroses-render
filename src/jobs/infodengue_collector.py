"""
Job para coleta automática de dados de arboviroses usando InfoDengue API
"""
import os
import sys
import requests
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional

# Adicionar o diretório raiz ao path
# Esta linha pode ser mantida, pois ajuda na organização do projeto na Render
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.user import db
from src.models.arbovirus_data import ArbovirusData
from src.utils.data_validator import DataValidator
from src.utils.database_manager import DatabaseManager
from flask import Flask

class InfoDengueCollector:
    """Coletor de dados de arboviroses usando InfoDengue API"""
    
    def __init__(self):
        self.base_url = "https://info.dengue.mat.br/api/alertcity"
        
        # Principais municípios brasileiros para coleta (código IBGE )
        self.municipalities = [
            {"code": "3550308", "name": "São Paulo", "state": "SP"},
            {"code": "3304557", "name": "Rio de Janeiro", "state": "RJ"},
            {"code": "2927408", "name": "Salvador", "state": "BA"},
            {"code": "2304400", "name": "Fortaleza", "state": "CE"},
            {"code": "1302603", "name": "Manaus", "state": "AM"},
            {"code": "5300108", "name": "Brasília", "state": "DF"}
        ]
        
        # Tipos de doenças disponíveis
        self.diseases = ["dengue", "chikungunya", "zika"]
    
    def create_app(self) -> Flask:
        """
        Criar aplicação Flask para acesso ao banco.
        Esta função agora lê a DATABASE_URL do ambiente, funcionando tanto na Render quanto localmente.
        """
        app = Flask(__name__)
        
        # --- CORREÇÃO 1: Conexão com o Banco de Dados ---
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("❌ ERRO CRÍTICO: DATABASE_URL não configurada. Configure a variável de ambiente no Render.")
        
        # Garante compatibilidade com SQLAlchemy, que prefere 'postgresql://'
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)

        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        return app
    
    def get_epidemiological_week(self, date_obj: date) -> tuple:
        """Calcula a semana epidemiológica para uma data"""
        iso_year, iso_week, _ = date_obj.isocalendar()
        if iso_week >= 52 and date_obj.month == 1:
            return iso_year - 1, iso_week
        return iso_year, iso_week
    
    def get_infodengue_data(self, municipality_code: str, disease: str) -> Optional[List[Dict[str, Any]]]:
        """Obtém dados do InfoDengue para um município e doença específicos"""
        try:
            url = f"{self.base_url}?geocode={municipality_code}&disease={disease}&format=json"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else [data]
        except requests.RequestException as e:
            print(f"❌ Erro na requisição InfoDengue para {municipality_code} ({disease}): {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao decodificar JSON para {municipality_code} ({disease}): {e}")
            return None
    
    def process_infodengue_record(self, record: Dict[str, Any], municipality: Dict[str, str], disease: str) -> Optional[Dict[str, Any]]:
        """Processa um registro do InfoDengue para o formato do banco de dados"""
        try:
            # --- CORREÇÃO 2: Lógica de Processamento de Datas ---
            epi_week = record.get("SE") or record.get("epidemiological_week")
            year = record.get("year") or record.get("ano")

            if not epi_week or not year:
                date_str = record.get("data_iniSE") or record.get("date")
                if date_str and isinstance(date_str, str):
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        year, epi_week = self.get_epidemiological_week(date_obj)
                    except ValueError:
                        print(f"⚠️  Formato de data em texto inválido: {date_str}")
                        return None
                else:
                    print(f"⚠️  Dados de semana/ano ou data não encontrados no registro: {record}")
                    return None
            
            # O resto da função continua, agora com 'year' e 'epi_week' garantidos
            cases_suspected = record.get("casos_est") or record.get("casos") or 0
            cases_confirmed = record.get("casos_confirmados") or 0
            
            arbovirus_data = {
                "municipality_code": municipality["code"],
                "municipality_name": municipality["name"],
                "state": municipality["state"],
                "epidemiological_week": int(epi_week),
                "year": int(year),
                "disease_type": disease.lower(),
                "cases_suspected": int(cases_suspected),
                "cases_confirmed": int(cases_confirmed),
                "cases_probable": int(record.get("casos_prováveis", 0)),
                "incidence_rate": float(record.get("incidência", 0.0)),
                "alert_level": int(record.get("nivel", 0)),
                "population": int(record.get("pop", 0))
            }
            return arbovirus_data
            
        except (ValueError, TypeError) as e:
            print(f"❌ Erro ao processar registro: {e} | Registro problemático: {record}")
            return None
    
    def collect_current_data(self) -> Dict[str, Any]:
        """Coleta dados recentes de arboviroses para todos os municípios"""
        app = self.create_app()
        collected_data = []
        errors = []
        inserted_count = 0
        
        print("🦟 Iniciando coleta de dados de arboviroses...")
        
        with app.app_context():
            for municipality in self.municipalities:
                for disease in self.diseases:
                    print(f"📍 Coletando dados de {disease} para {municipality['name']}, {municipality['state']}...")
                    infodengue_data = self.get_infodengue_data(municipality["code"], disease)
                    
                    if infodengue_data:
                        for record in infodengue_data:
                            processed_data = self.process_infodengue_record(record, municipality, disease)
                            if processed_data:
                                existing = ArbovirusData.query.filter_by(
                                    municipality_code=municipality["code"],
                                    disease_type=disease.lower(),
                                    year=processed_data["year"],
                                    epidemiological_week=processed_data["epidemiological_week"]
                                ).first()
                                
                                if not existing:
                                    is_valid, validation_errors = DataValidator.validate_arbovirus_data(processed_data)
                                    if is_valid:
                                        collected_data.append(processed_data)
                                        print(f"✅ Dados coletados para {municipality['name']} - {disease} - {processed_data['year']}W{processed_data['epidemiological_week']}")
                                    else:
                                        error_msg = f"Dados inválidos para {municipality['name']}: {validation_errors}"
                                        errors.append(error_msg)
                                        print(f"❌ {error_msg}")
                                else:
                                    print(f"⚠️  Dados já existem para {municipality['name']} - {disease} - {processed_data['year']}W{processed_data['epidemiological_week']}")
                    else:
                        errors.append(f"Falha na coleta de dados de {disease} para {municipality['name']}")
            
            if collected_data:
                inserted_count, insert_errors = DatabaseManager.bulk_insert_arbovirus_data(collected_data)
                errors.extend(insert_errors)
                print(f"💾 {inserted_count} novos registros inseridos no banco de dados.")
            else:
                print("⚠️  Nenhum dado novo para inserir.")
        
        return {
            "success": len(errors) == 0,
            "collected_count": len(collected_data),
            "inserted_count": inserted_count,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }

def run_infodengue_collection():
    """Executa a coleta de dados do InfoDengue"""
    collector = InfoDengueCollector()
    result = collector.collect_current_data()
    
    print("\n📊 Resultado da coleta InfoDengue:")
    print(f"   - Sucesso: {'✅' if result['success'] else '❌'}")
    print(f"   - Dados coletados: {result['collected_count']}")
    print(f"   - Registros inseridos: {result['inserted_count']}")
    print(f"   - Erros: {len(result['errors'])}")
    
    if result['errors']:
        print("\n❌ Detalhes dos erros:")
        for error in result['errors']:
            print(f"   - {error}")
    
    return result

if __name__ == "__main__":
    run_infodengue_collection()
