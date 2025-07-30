"""
Job para coleta automática de dados de clima usando Open-Meteo API
"""
import os
import sys
import requests
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.user import db
from src.models.climate_data import ClimateData
from src.utils.data_validator import DataValidator
from src.utils.database_manager import DatabaseManager
from flask import Flask

class ClimateCollector:
    """Coletor de dados de clima usando Open-Meteo API"""
    
    def __init__(self):
        self.base_url = "https://api.open-meteo.com/v1/forecast"
        self.historical_url = "https://archive-api.open-meteo.com/v1/archive"
        
        # Principais municípios brasileiros para coleta (código IBGE e coordenadas)
        self.municipalities = [
            {
                "code": "3550308",  # São Paulo
                "name": "São Paulo",
                "state": "SP",
                "lat": -23.5505,
                "lon": -46.6333
            },
            {
                "code": "3304557",  # Rio de Janeiro
                "name": "Rio de Janeiro", 
                "state": "RJ",
                "lat": -22.9068,
                "lon": -43.1729
            },
            {
                "code": "2927408",  # Salvador
                "name": "Salvador",
                "state": "BA", 
                "lat": -12.9714,
                "lon": -38.5014
            },
            {
                "code": "2304400",  # Fortaleza
                "name": "Fortaleza",
                "state": "CE",
                "lat": -3.7319,
                "lon": -38.5267
            },
            {
                "code": "1302603",  # Manaus
                "name": "Manaus",
                "state": "AM",
                "lat": -3.1190,
                "lon": -60.0217
            },
            {
                "code": "5300108",  # Brasília
                "name": "Brasília",
                "state": "DF",
                "lat": -15.8267,
                "lon": -47.9218
            }
        ]
    
    def create_app(self) -> Flask:
        """Criar aplicação Flask para acesso ao banco"""
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')}"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        return app
    
    def get_current_weather_data(self, municipality: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Obtém dados meteorológicos atuais para um município
        
        Args:
            municipality: Dicionário com dados do município
            
        Returns:
            Dicionário com dados meteorológicos ou None se houver erro
        """
        try:
            params = {
                "latitude": municipality["lat"],
                "longitude": municipality["lon"],
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m", 
                    "precipitation",
                    "wind_speed_10m",
                    "surface_pressure"
                ],
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum"
                ],
                "timezone": "America/Sao_Paulo",
                "forecast_days": 1
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Extrair dados atuais e diários
            current = data.get("current", {})
            daily = data.get("daily", {})
            
            # Preparar dados para inserção
            climate_data = {
                "municipality_code": municipality["code"],
                "municipality_name": municipality["name"],
                "state": municipality["state"],
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
        """
        Obtém dados meteorológicos históricos para um município
        
        Args:
            municipality: Dicionário com dados do município
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de dicionários com dados meteorológicos históricos
        """
        try:
            params = {
                "latitude": municipality["lat"],
                "longitude": municipality["lon"],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "temperature_2m_mean",
                    "relative_humidity_2m_mean",
                    "precipitation_sum",
                    "wind_speed_10m_mean",
                    "surface_pressure_mean"
                ],
                "timezone": "America/Sao_Paulo"
            }
            
            response = requests.get(self.historical_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            daily = data.get("daily", {})
            
            # Processar dados diários
            historical_data = []
            dates = daily.get("time", [])
            
            for i, date_str in enumerate(dates):
                climate_data = {
                    "municipality_code": municipality["code"],
                    "municipality_name": municipality["name"],
                    "state": municipality["state"],
                    "date": date_str,
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
        """
        Coleta dados meteorológicos atuais para todos os municípios
        
        Returns:
            Dicionário com resultado da coleta
        """
        app = self.create_app()
        collected_data = []
        errors = []
        
        print(f"🌤️  Iniciando coleta de dados meteorológicos atuais...")
        
        with app.app_context():
            for municipality in self.municipalities:
                print(f"📍 Coletando dados de {municipality['name']}, {municipality['state']}...")
                
                # Verificar se já existem dados para hoje
                today = date.today()
                existing = ClimateData.query.filter(
                    ClimateData.municipality_code == municipality["code"],
                    ClimateData.date == today
                ).first()
                
                if existing:
                    print(f"⚠️  Dados já existem para {municipality['name']} em {today}")
                    continue
                
                # Coletar dados
                climate_data = self.get_current_weather_data(municipality)
                if climate_data:
                    # Validar dados
                    is_valid, validation_errors = DataValidator.validate_climate_data(climate_data)
                    if is_valid:
                        collected_data.append(climate_data)
                        print(f"✅ Dados coletados para {municipality['name']}")
                    else:
                        errors.append(f"Dados inválidos para {municipality['name']}: {validation_errors}")
                        print(f"❌ Dados inválidos para {municipality['name']}: {validation_errors}")
                else:
                    errors.append(f"Falha na coleta de dados para {municipality['name']}")
            
            # Inserir dados no banco
            if collected_data:
                inserted_count, insert_errors = DatabaseManager.bulk_insert_climate_data(collected_data)
                errors.extend(insert_errors)
                print(f"💾 {inserted_count} registros inseridos no banco de dados")
            else:
                print("⚠️  Nenhum dado novo para inserir")
        
        return {
            "success": len(errors) == 0,
            "collected_count": len(collected_data),
            "inserted_count": inserted_count if collected_data else 0,
            "errors": errors,
            "timestamp": datetime.now().isoformat()
        }
    
    def collect_historical_data(self, days_back: int = 7) -> Dict[str, Any]:
        """
        Coleta dados meteorológicos históricos
        
        Args:
            days_back: Número de dias para voltar na coleta
            
        Returns:
            Dicionário com resultado da coleta
        """
        app = self.create_app()
        collected_data = []
        errors = []
        
        end_date = date.today() - timedelta(days=1)  # Ontem
        start_date = end_date - timedelta(days=days_back)
        
        print(f"📅 Coletando dados históricos de {start_date} a {end_date}...")
        
        with app.app_context():
            for municipality in self.municipalities:
                print(f"📍 Coletando dados históricos de {municipality['name']}, {municipality['state']}...")
                
                # Coletar dados históricos
                historical_data = self.get_historical_weather_data(municipality, start_date, end_date)
                
                for climate_data in historical_data:
                    # Verificar se já existem dados para esta data
                    data_date = datetime.strptime(climate_data["date"], '%Y-%m-%d').date()
                    existing = ClimateData.query.filter(
                        ClimateData.municipality_code == municipality["code"],
                        ClimateData.date == data_date
                    ).first()
                    
                    if not existing:
                        # Validar dados
                        is_valid, validation_errors = DataValidator.validate_climate_data(climate_data)
                        if is_valid:
                            collected_data.append(climate_data)
                        else:
                            errors.append(f"Dados inválidos para {municipality['name']} em {climate_data['date']}: {validation_errors}")
            
            # Inserir dados no banco
            if collected_data:
                inserted_count, insert_errors = DatabaseManager.bulk_insert_climate_data(collected_data)
                errors.extend(insert_errors)
                print(f"💾 {inserted_count} registros históricos inseridos no banco de dados")
            else:
                print("⚠️  Nenhum dado histórico novo para inserir")
        
        return {
            "success": len(errors) == 0,
            "collected_count": len(collected_data),
            "inserted_count": inserted_count if collected_data else 0,
            "errors": errors,
            "period": f"{start_date} a {end_date}",
            "timestamp": datetime.now().isoformat()
        }

def run_current_collection():
    """Executa coleta de dados atuais"""
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
    """Executa coleta de dados históricos"""
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

