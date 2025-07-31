"""
Job para coleta automática de dados de arboviroses usando InfoDengue API.
Agora inclui a coleta de todos os municípios de Minas Gerais.
"""
import os
import sys
import requests
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from flask import Flask
from dotenv import load_dotenv  

load_dotenv()  # <--  CARREGAR O ARQUIVO .env

# Adicionar o diretório raiz ao path
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
        self.ibge_api_url = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/{UF}/municipios"
        
        # Lista base de principais capitais (ainda será coletada )
        self.base_municipalities = [
            {"code": "3550308", "name": "São Paulo", "state": "SP"},
            {"code": "3304557", "name": "Rio de Janeiro", "state": "RJ"},
            {"code": "2927408", "name": "Salvador", "state": "BA"},
            {"code": "2304400", "name": "Fortaleza", "state": "CE"},
            {"code": "1302603", "name": "Manaus", "state": "AM"},
            {"code": "5300108", "name": "Brasília", "state": "DF"}
        ]
        
        # Tipos de doenças disponíveis
        self.diseases = ["dengue", "chikungunya", "zika"]
        
        # A lista final de municípios será preenchida dinamicamente
        self.municipalities = []

    # --- NOVO MÉTODO PARA BUSCAR MUNICÍPIOS ---
    def get_municipalities_from_ibge(self, state_uf: str = "MG") -> List[Dict[str, str]]:
        """Busca a lista de municípios de um estado na API do IBGE."""
        print(f"🏛️  Buscando lista de municípios para o estado {state_uf} na API do IBGE...")
        try:
            url = self.ibge_api_url.format(UF=state_uf)
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            municipalities_data = response.json()
            
            # Formata a lista para o padrão que usamos no script
            formatted_list = [
                {"code": str(muni["id"]), "name": muni["nome"], "state": state_uf}
                for muni in municipalities_data
            ]
            print(f"✅ Encontrados {len(formatted_list)} municípios em {state_uf}.")
            return formatted_list
        except requests.RequestException as e:
            print(f"❌ Erro ao buscar municípios do IBGE para {state_uf}: {e}")
            return []

    # O resto do código permanece o mesmo, mas a função `collect_current_data` será ajustada
    # para chamar o novo método.

    def create_app(self) -> Flask:
        # ... (esta função não muda, continua igual à versão anterior)
        app = Flask(__name__)
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            raise ValueError("❌ ERRO CRÍTICO: DATABASE_URL não configurada.")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)
        return app

    def get_infodengue_data(self, municipality_code: str, disease: str) -> Optional[List[Dict[str, Any]]]:
        # ... (esta função não muda)
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
        # ... (esta função não muda, continua igual à versão final anterior)
        try:
            year, epi_week = None, None
            se_value = record.get("SE")
            if se_value and isinstance(se_value, int) and se_value > 100000:
                se_str = str(se_value)
                year, epi_week = int(se_str[:4]), int(se_str[4:])
            if not year or not epi_week:
                year, epi_week = record.get("year"), record.get("epidemiological_week")
            if not year or not epi_week:
                print(f"⚠️  Não foi possível extrair ano/semana do registro: {record}")
                return None
            arbovirus_data = {
                "municipality_code": municipality["code"], "municipality_name": municipality["name"],
                "state": municipality["state"], "epidemiological_week": int(epi_week), "year": int(year),
                "disease_type": disease.lower(), "cases_suspected": int(record.get("casos_est", 0) or 0),
                "cases_confirmed": int(record.get("casos_confirmados", 0) or 0),
                "cases_probable": int(record.get("casos_prováveis", 0) or 0),
                "incidence_rate": float(record.get("incidência", 0.0) or 0.0),
                "alert_level": int(record.get("nivel", 0) or 0), "population": int(record.get("pop", 0) or 0)
            }
            return arbovirus_data
        except (ValueError, TypeError) as e:
            print(f"❌ Erro ao processar registro: {e} | Registro: {record}")
            return None
    
    def collect_current_data(self) -> Dict[str, Any]:
        """Coleta dados recentes de arboviroses para todos os municípios configurados."""
        app = self.create_app()
        collected_data = []
        errors = []
        inserted_count = 0
        
        # --- AJUSTE NA LÓGICA DE COLETA ---
        # 1. Pega a lista de municípios de Minas Gerais
        mg_municipalities = self.get_municipalities_from_ibge("MG")
        
        # 2. Junta a lista base de capitais com a lista de MG
        # Usamos um dicionário para remover duplicatas, caso alguma capital já esteja na lista de MG
        final_municipalities_map = {muni['code']: muni for muni in self.base_municipalities}
        for muni in mg_municipalities:
            final_municipalities_map[muni['code']] = muni
        
        self.municipalities = list(final_municipalities_map.values())
        
        print(f"\n🦟 Iniciando coleta de dados para um total de {len(self.municipalities)} municípios...")
        
        with app.app_context():
            # O resto do loop continua como antes, mas agora com a lista completa
            for municipality in self.municipalities:
                for disease in self.diseases:
                    # ... (o resto do loop é idêntico ao código anterior)
                    print(f"📍 Coletando dados de {disease} para {municipality['name']}, {municipality['state']}...")
                    infodengue_data = self.get_infodengue_data(municipality["code"], disease)
                    if infodengue_data:
                        for record in infodengue_data:
                            processed_data = self.process_infodengue_record(record, municipality, disease)
                            if processed_data:
                                existing = ArbovirusData.query.filter_by(
                                    municipality_code=processed_data["municipality_code"],
                                    disease_type=processed_data["disease_type"],
                                    year=processed_data["year"],
                                    epidemiological_week=processed_data["epidemiological_week"]
                                ).first()
                                if not existing:
                                    is_valid, validation_errors = DataValidator.validate_arbovirus_data(processed_data)
                                    if is_valid:
                                        collected_data.append(processed_data)
                                        print(f"✅ Dados coletados para {municipality['name']} - {disease} - {processed_data['year']}W{processed_data['epidemiological_week']}")
                                    else:
                                        errors.append(f"Dados inválidos: {validation_errors}")
                                else:
                                    print(f"⚠️  Dados já existem para {municipality['name']} - {disease}")
                    else:
                        errors.append(f"Falha na coleta de {disease} para {municipality['name']}")
            
            if collected_data:
                inserted_count, insert_errors = DatabaseManager.bulk_insert_arbovirus_data(collected_data)
                errors.extend(insert_errors)
                print(f"💾 {inserted_count} novos registros inseridos no banco de dados.")
            else:
                print("⚠️  Nenhum dado novo para inserir.")
        
        return {
            "success": len(errors) == 0, "collected_count": len(collected_data),
            "inserted_count": inserted_count, "errors": errors,
            "timestamp": datetime.now().isoformat()
        }

# O resto do arquivo (run_infodengue_collection e if __name__ == "__main__") não precisa de alterações.
def run_infodengue_collection():
    # ... (sem alterações)
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
