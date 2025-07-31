# climate_collector.py (versão final e rápida)
"""
Job para coleta automática de dados de clima usando Open-Meteo API.
Versão OTIMIZADA: lê a lista de municípios de um arquivo JSON local para máxima performance.
"""
import os
import sys
import requests
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from dotenv import load_dotenv
from flask import Flask
from src.models.user import db
from src.models.climate_data import ClimateData
from src.utils.data_validator import DataValidator
from src.utils.database_manager import DatabaseManager

load_dotenv()

class ClimateCollector:
    """Coletor de dados de clima usando Open-Meteo API"""
    
    def __init__(self):
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.archive_url = "https://archive-api.open-meteo.com/v1/archive"
        
        # Carrega a lista de municípios a partir do arquivo JSON local
        self.municipalities = self.load_municipalities_from_file( )

    def load_municipalities_from_file(self) -> List[Dict[str, Any]]:
        """Carrega a lista de municípios do arquivo JSON e adiciona as capitais."""
        # Caminho para o arquivo JSON
        # __file__ se refere a este script, então construímos o caminho a partir dele
        json_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'municipalities_with_coords.json')
        
        print(f"📄 Carregando lista de municípios de '{json_path}'...")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                mg_municipalities = json.load(f)
            print(f"✅ Carregados {len(mg_municipalities)} municípios de MG.")
        except FileNotFoundError:
            print(f"❌ ERRO CRÍTICO: Arquivo '{json_path}' não encontrado. Execute o script 'generate_coords.py' primeiro.")
            return []
        
        # Lista de capitais base
        base_capitals = [
            {"code": "3550308", "name": "São Paulo", "state": "SP", "lat": -23.55, "lon": -46.63},
            {"code": "3304557", "name": "Rio de Janeiro", "state": "RJ", "lat": -22.91, "lon": -43.17},
            {"code": "2927408", "name": "Salvador", "state": "BA", "lat": -12.97, "lon": -38.50},
            {"code": "2304400", "name": "Fortaleza", "state": "CE", "lat": -3.73, "lon": -38.52},
            {"code": "1302603", "name": "Manaus", "state": "AM", "lat": -3.12, "lon": -60.02},
            {"code": "5300108", "name": "Brasília", "state": "DF", "lat": -15.82, "lon": -47.92}
        ]
        
        # Combina as listas, garantindo que não haja duplicatas
        final_map = {muni['code']: muni for muni in mg_municipalities}
        for capital in base_capitals:
            final_map[capital['code']] = capital
            
        final_list = list(final_map.values())
        print(f"✅ Lista final de coleta preparada com {len(final_list)} municípios.")
        return final_list

    # O resto do código (create_app, get_weather_data, etc.) permanece o mesmo.
    # Cole o restante do seu código aqui, pois ele já está correto e robusto.
    def create_app(self) -> Flask:
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

    def get_current_weather_data(self, municipality: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            params = {
                "latitude": municipality["lat"], "longitude": municipality["lon"],
                "current": ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "surface_pressure"],
                "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
                "timezone": "America/Sao_Paulo", "forecast_days": 1
            }
            response = requests.get(self.forecast_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            current, daily = data.get("current", {}), data.get("daily", {})
            climate_data = {
                "municipality_code": municipality["code"], "municipality_name": municipality["name"], "state": municipality["state"],
                "date": date.today().isoformat(),
                "temperature_max": daily.get("temperature_2m_max", [None])[0],
                "temperature_min": daily.get("temperature_2m_min", [None])[0],
                "temperature_avg": current.get("temperature_2m"),
                "humidity": current.get("relative_humidity_2m"),
                "precipitation": daily.get("precipitation_sum", [None])[0] or current.get("precipitation", 0),
                "wind_speed": current.get("wind_speed_10m"),
                "pressure": current.get("surface_pressure")
            }
            return climate_data
        except requests.RequestException as e:
            print(f"❌ Erro na requisição para {municipality['name']}: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro ao processar dados de {municipality['name']}: {e}")
            return None

    def get_historical_weather_data(self, municipality: Dict[str, Any], start_date: date, end_date: date) -> List[Dict[str, Any]]:
        try:
            params = {
                "latitude": municipality["lat"], "longitude": municipality["lon"],
                "start_date": start_date.isoformat(), "end_date": end_date.isoformat(),
                "daily": ["temperature_2m_max", "temperature_2m_min", "temperature_2m_mean", "relative_humidity_2m_mean", "precipitation_sum", "wind_speed_10m_mean", "surface_pressure_mean"],
                "timezone": "America/Sao_Paulo"
            }
            response = requests.get(self.archive_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})
            historical_data = []
            dates = daily.get("time", [])
            for i, date_str in enumerate(dates):
                climate_data = {
                    "municipality_code": municipality["code"], "municipality_name": municipality["name"], "state": municipality["state"], "date": date_str,
                    "temperature_max": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                    "temperature_min": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                    "temperature_avg": daily.get("temperature_2m_mean", [])[i] if i < len(daily.get("temperature_2m_mean", [])) else None,
                    "humidity": daily.get("relative_humidity_2m_mean", [])[i] if i < len(daily.get("relative_humidity_2m_mean", [])) else None,
                    "precipitation": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                    "wind_speed": daily.get("wind_speed_10m_mean", [])[i] if i < len(daily.get("wind_speed_10m_mean", [])) else None,
                    "pressure": daily.get("surface_pressure_mean", [])[i] if i < len(daily.get("surface_pressure_mean", [])) else None
                }
                historical_data.append(climate_data)
            return historical_data
        except requests.RequestException as e:
            print(f"❌ Erro na requisição histórica para {municipality['name']}: {e}")
            return []
        except Exception as e:
            print(f"❌ Erro ao processar dados históricos de {municipality['name']}: {e}")
            return []

    def collect_current_data(self) -> Dict[str, Any]:
        if not self.municipalities:
            print("❌ Coleta abortada: não foi possível obter a lista de municípios.")
            return {}
        app = self.create_app()
        collected_data, errors, inserted_count = [], [], 0
        print(f"🌤️  Iniciando coleta de dados meteorológicos atuais para {len(self.municipalities)} municípios...")
        with app.app_context():
            for municipality in self.municipalities:
                print(f"📍 Coletando dados de {municipality['name']}, {municipality['state']}...")
                today = date.today()
                existing = ClimateData.query.filter_by(municipality_code=municipality["code"], date=today).first()
                if existing:
                    print(f"⚠️  Dados já existem para {municipality['name']} em {today}")
                    continue
                climate_data = self.get_current_weather_data(municipality)
                if climate_data:
                    is_valid, validation_errors = DataValidator.validate_climate_data(climate_data)
                    if is_valid:
                        collected_data.append(climate_data)
                        print(f"✅ Dados coletados para {municipality['name']}")
                    else:
                        errors.append(f"Dados inválidos para {municipality['name']}: {validation_errors}")
                else:
                    errors.append(f"Falha na coleta para {municipality['name']}")
            if collected_data:
                inserted_count, insert_errors = DatabaseManager.bulk_insert_climate_data(collected_data)
                errors.extend(insert_errors)
                print(f"💾 {inserted_count} registros inseridos no banco de dados")
            else:
                print("⚠️  Nenhum dado novo para inserir")
        return {"success": len(errors) == 0, "collected_count": len(collected_data), "inserted_count": inserted_count, "errors": errors, "timestamp": datetime.now().isoformat()}

    def collect_historical_data(self, days_back: int = 7) -> Dict[str, Any]:
        if not self.municipalities:
            print("❌ Coleta abortada: não foi possível obter a lista de municípios.")
            return {}
        app = self.create_app()
        collected_data, errors, inserted_count = [], [], 0
        end_date, start_date = date.today() - timedelta(days=1), date.today() - timedelta(days=days_back + 1)
        print(f"📅 Coletando dados históricos de {start_date} a {end_date} para {len(self.municipalities)} municípios...")
        with app.app_context():
            for municipality in self.municipalities:
                print(f"📍 Coletando dados históricos de {municipality['name']}, {municipality['state']}...")
                historical_data = self.get_historical_weather_data(municipality, start_date, end_date)
                for climate_data in historical_data:
                    data_date = datetime.strptime(climate_data["date"], '%Y-%m-%d').date()
                    existing = ClimateData.query.filter_by(municipality_code=municipality["code"], date=data_date).first()
                    if not existing:
                        is_valid, validation_errors = DataValidator.validate_climate_data(climate_data)
                        if is_valid:
                            collected_data.append(climate_data)
                        else:
                            errors.append(f"Dados inválidos para {municipality['name']} em {climate_data['date']}: {validation_errors}")
            if collected_data:
                inserted_count, insert_errors = DatabaseManager.bulk_insert_climate_data(collected_data)
                errors.extend(insert_errors)
                print(f"💾 {inserted_count} registros históricos inseridos no banco de dados")
            else:
                print("⚠️  Nenhum dado histórico novo para inserir")
        return {"success": len(errors) == 0, "collected_count": len(collected_data), "inserted_count": inserted_count, "errors": errors, "period": f"{start_date} a {end_date}", "timestamp": datetime.now().isoformat()}

# O código para executar o script pela linha de comando permanece o mesmo
def run_current_collection():
    collector = ClimateCollector()
    result = collector.collect_current_data()
    print(f"\n📊 Resultado da coleta:")
    print(f"   - Sucesso: {'✅' if result['success'] else '❌'}")
    print(f"   - Dados coletados: {result['collected_count']}")
    print(f"   - Registros inseridos: {result['inserted_count']}")
    print(f"   - Erros: {len(result['errors'])}")
    if result['errors']:
        print(f"\n❌ Erros encontrados:")
        for error in result['errors']:
            print(f"   - {error}")
    return result

def run_historical_collection(days_back: int = 7):
    collector = ClimateCollector()
    result = collector.collect_historical_data(days_back)
    print(f"\n📊 Resultado da coleta histórica:")
    print(f"   - Sucesso: {'✅' if result['success'] else '❌'}")
    print(f"   - Período: {result['period']}")
    print(f"   - Dados coletados: {result['collected_count']}")
    print(f"   - Registros inseridos: {result['inserted_count']}")
    print(f"   - Erros: {len(result['errors'])}")
    if result['errors']:
        print(f"\n❌ Erros encontrados:")
        for error in result['errors']:
            print(f"   - {error}")
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Coletor de dados meteorológicos")
    parser.add_argument("--historical", action="store_true", help="Coletar dados históricos")
    parser.add_argument("--days", type=int, default=7, help="Número de dias para coleta histórica")
    args = parser.parse_args()
    if args.historical:
        run_historical_collection(args.days)
    else:
        run_current_collection()
