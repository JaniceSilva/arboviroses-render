"""
Job para coleta automática de dados de arboviroses usando InfoDengue API
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
from src.models.arbovirus_data import ArbovirusData
from src.utils.data_validator import DataValidator
from src.utils.database_manager import DatabaseManager
from flask import Flask

class InfoDengueCollector:
    """Coletor de dados de arboviroses usando InfoDengue API"""
    
    def __init__(self):
        self.base_url = "https://info.dengue.mat.br/api/alertcity"
        
        # Principais municípios brasileiros para coleta (código IBGE)
        self.municipalities = [
            {
                "code": "3550308",  # São Paulo
                "name": "São Paulo",
                "state": "SP"
            },
            {
                "code": "3304557",  # Rio de Janeiro
                "name": "Rio de Janeiro", 
                "state": "RJ"
            },
            {
                "code": "2927408",  # Salvador
                "name": "Salvador",
                "state": "BA"
            },
            {
                "code": "2304400",  # Fortaleza
                "name": "Fortaleza",
                "state": "CE"
            },
            {
                "code": "1302603",  # Manaus
                "name": "Manaus",
                "state": "AM"
            },
            {
                "code": "5300108",  # Brasília
                "name": "Brasília",
                "state": "DF"
            }
        ]
        
        # Tipos de doenças disponíveis
        self.diseases = ["dengue", "chikungunya", "zika"]
    
    def create_app(self) -> Flask:
        """Criar aplicação Flask para acesso ao banco"""
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')}"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        return app
    
    def get_epidemiological_week(self, date_obj: date) -> tuple:
        """
        Calcula a semana epidemiológica para uma data
        
        Args:
            date_obj: Data para calcular a semana epidemiológica
            
        Returns:
            Tuple com (ano, semana_epidemiológica)
        """
        # Semana epidemiológica começa no domingo
        # Para simplificar, usaremos a semana ISO com ajuste
        iso_year, iso_week, iso_weekday = date_obj.isocalendar()
        
        # Ajustar para começar no domingo (ISO começa na segunda)
        epi_week = iso_week
        epi_year = iso_year
        
        # Se estivermos no início do ano e a semana ISO for alta (52/53),
        # significa que ainda estamos na semana epidemiológica do ano anterior
        if iso_week >= 52 and date_obj.month == 1:
            epi_year = iso_year - 1
        
        return epi_year, epi_week
    
    def get_infodengue_data(self, municipality_code: str, disease: str, format_type: str = "json") -> Optional[List[Dict[str, Any]]]:
        """
        Obtém dados do InfoDengue para um município e doença específicos
        
        Args:
            municipality_code: Código IBGE do município
            disease: Tipo de doença (dengue, chikungunya, zika)
            format_type: Formato da resposta (json ou csv)
            
        Returns:
            Lista de dicionários com dados ou None se houver erro
        """
        try:
            # Construir URL da API
            url = f"{self.base_url}?geocode={municipality_code}&disease={disease}&format={format_type}"
            
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            if format_type == "json":
                data = response.json()
                return data if isinstance(data, list) else [data]
            else:
                # Para CSV, seria necessário processar o texto
                return None
                
        except requests.RequestException as e:
            print(f"❌ Erro na requisição InfoDengue para {municipality_code} ({disease}): {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao decodificar JSON para {municipality_code} ({disease}): {e}")
            return None
        except Exception as e:
            print(f"❌ Erro inesperado para {municipality_code} ({disease}): {e}")
            return None
    
    def process_infodengue_record(self, record: Dict[str, Any], municipality: Dict[str, str], disease: str) -> Optional[Dict[str, Any]]:
        """
        Processa um registro do InfoDengue para o formato do banco de dados
        
        Args:
            record: Registro bruto do InfoDengue
            municipality: Dados do município
            disease: Tipo de doença
            
        Returns:
            Dicionário formatado para inserção no banco ou None se inválido
        """
        try:
            # Extrair dados do registro InfoDengue
            # A estrutura pode variar, então tentamos diferentes campos
            
            # Data/Semana epidemiológica
            epi_week = record.get("SE") or record.get("epidemiological_week")
            year = record.get("year") or record.get("ano")
            
            if not epi_week or not year:
                # Tentar extrair da data se disponível
                date_str = record.get("data_iniSE") or record.get("date")
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                        year, epi_week = self.get_epidemiological_week(date_obj)
                    except ValueError:
                        print(f"⚠️  Formato de data inválido: {date_str}")
                        return None
                else:
                    print(f"⚠️  Dados de semana/ano não encontrados no registro")
                    return None
            
            # Casos
            cases_suspected = record.get("casos_est") or record.get("casos") or record.get("suspected_cases") or 0
            cases_confirmed = record.get("casos_confirmados") or record.get("confirmed_cases") or 0
            cases_probable = record.get("casos_prováveis") or record.get("probable_cases") or 0
            
            # Taxa de incidência
            incidence_rate = record.get("incidência") or record.get("incidence_rate") or record.get("taxa_incidencia")
            
            # Nível de alerta
            alert_level = record.get("nivel") or record.get("alert_level") or record.get("nivel_alerta")
            if alert_level and isinstance(alert_level, str):
                # Converter nível textual para numérico
                level_map = {"verde": 1, "amarelo": 2, "laranja": 3, "vermelho": 4}
                alert_level = level_map.get(alert_level.lower(), 0)
            
            # População
            population = record.get("pop") or record.get("population") or record.get("populacao")
            
            # Preparar dados para inserção
            arbovirus_data = {
                "municipality_code": municipality["code"],
                "municipality_name": municipality["name"],
                "state": municipality["state"],
                "epidemiological_week": int(epi_week),
                "year": int(year),
                "disease_type": disease.lower(),
                "cases_suspected": int(cases_suspected) if cases_suspected else 0,
                "cases_confirmed": int(cases_confirmed) if cases_confirmed else 0,
                "cases_probable": int(cases_probable) if cases_probable else 0,
                "incidence_rate": float(incidence_rate) if incidence_rate else None,
                "alert_level": int(alert_level) if alert_level else None,
                "population": int(population) if population else None
            }
            
            return arbovirus_data
            
        except (ValueError, TypeError) as e:
            print(f"❌ Erro ao processar registro: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro inesperado ao processar registro: {e}")
            return None
    
    def collect_current_data(self, weeks_back: int = 4) -> Dict[str, Any]:
        """
        Coleta dados recentes de arboviroses para todos os municípios
        
        Args:
            weeks_back: Número de semanas para voltar na coleta
            
        Returns:
            Dicionário com resultado da coleta
        """
        app = self.create_app()
        collected_data = []
        errors = []
        
        print(f"🦟 Iniciando coleta de dados de arboviroses...")
        
        with app.app_context():
            for municipality in self.municipalities:
                for disease in self.diseases:
                    print(f"📍 Coletando dados de {disease} para {municipality['name']}, {municipality['state']}...")
                    
                    # Obter dados do InfoDengue
                    infodengue_data = self.get_infodengue_data(municipality["code"], disease)
                    
                    if infodengue_data:
                        for record in infodengue_data:
                            # Processar registro
                            processed_data = self.process_infodengue_record(record, municipality, disease)
                            
                            if processed_data:
                                # Verificar se já existem dados para esta semana/ano/doença
                                existing = ArbovirusData.query.filter(
                                    ArbovirusData.municipality_code == municipality["code"],
                                    ArbovirusData.disease_type == disease.lower(),
                                    ArbovirusData.year == processed_data["year"],
                                    ArbovirusData.epidemiological_week == processed_data["epidemiological_week"]
                                ).first()
                                
                                if not existing:
                                    # Validar dados
                                    is_valid, validation_errors = DataValidator.validate_arbovirus_data(processed_data)
                                    if is_valid:
                                        collected_data.append(processed_data)
                                        print(f"✅ Dados coletados para {municipality['name']} - {disease} - {processed_data['year']}W{processed_data['epidemiological_week']}")
                                    else:
                                        errors.append(f"Dados inválidos para {municipality['name']} - {disease}: {validation_errors}")
                                        print(f"❌ Dados inválidos para {municipality['name']} - {disease}: {validation_errors}")
                                else:
                                    print(f"⚠️  Dados já existem para {municipality['name']} - {disease} - {processed_data['year']}W{processed_data['epidemiological_week']}")
                    else:
                        errors.append(f"Falha na coleta de dados de {disease} para {municipality['name']}")
            
            # Inserir dados no banco
            if collected_data:
                inserted_count, insert_errors = DatabaseManager.bulk_insert_arbovirus_data(collected_data)
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

def run_infodengue_collection():
    """Executa coleta de dados do InfoDengue"""
    collector = InfoDengueCollector()
    result = collector.collect_current_data()
    
    print(f"\n📊 Resultado da coleta InfoDengue:")
    print(f"   - Sucesso: {'✅' if result['success'] else '❌'}")
    print(f"   - Dados coletados: {result['collected_count']}")
    print(f"   - Registros inseridos: {result['inserted_count']}")
    print(f"   - Erros: {len(result['errors'])}")
    
    if result['errors']:
        print(f"\n❌ Erros encontrados:")
        for error in result['errors']:
            print(f"   - {error}")
    
    return result

if __name__ == "__main__":
    run_infodengue_collection()

