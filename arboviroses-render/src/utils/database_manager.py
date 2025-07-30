"""
Gerenciador de operações de banco de dados
"""
import os
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy import and_, or_, func
from sqlalchemy.exc import IntegrityError

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.user import db
from src.models.climate_data import ClimateData
from src.models.arbovirus_data import ArbovirusData
from src.models.prediction import Prediction

class DatabaseManager:
    """Classe para gerenciar operações complexas no banco de dados"""
    
    @staticmethod
    def get_climate_data_by_municipality_and_period(
        municipality_code: str,
        start_date: date,
        end_date: date
    ) -> List[ClimateData]:
        """
        Obtém dados de clima por município e período
        
        Args:
            municipality_code: Código IBGE do município
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            Lista de dados de clima
        """
        return ClimateData.query.filter(
            and_(
                ClimateData.municipality_code == municipality_code,
                ClimateData.date >= start_date,
                ClimateData.date <= end_date
            )
        ).order_by(ClimateData.date).all()
    
    @staticmethod
    def get_arbovirus_data_by_municipality_and_period(
        municipality_code: str,
        disease_type: str,
        start_year: int,
        end_year: int,
        start_week: int = 1,
        end_week: int = 53
    ) -> List[ArbovirusData]:
        """
        Obtém dados de arboviroses por município, doença e período
        
        Args:
            municipality_code: Código IBGE do município
            disease_type: Tipo de doença
            start_year: Ano inicial
            end_year: Ano final
            start_week: Semana inicial (padrão: 1)
            end_week: Semana final (padrão: 53)
            
        Returns:
            Lista de dados de arboviroses
        """
        return ArbovirusData.query.filter(
            and_(
                ArbovirusData.municipality_code == municipality_code,
                ArbovirusData.disease_type == disease_type.lower(),
                or_(
                    and_(ArbovirusData.year == start_year, ArbovirusData.epidemiological_week >= start_week),
                    and_(ArbovirusData.year > start_year, ArbovirusData.year < end_year),
                    and_(ArbovirusData.year == end_year, ArbovirusData.epidemiological_week <= end_week)
                )
            )
        ).order_by(ArbovirusData.year, ArbovirusData.epidemiological_week).all()
    
    @staticmethod
    def get_latest_predictions_by_municipality(
        municipality_code: str,
        disease_type: Optional[str] = None
    ) -> List[Prediction]:
        """
        Obtém as predições mais recentes por município
        
        Args:
            municipality_code: Código IBGE do município
            disease_type: Tipo de doença (opcional)
            
        Returns:
            Lista de predições mais recentes
        """
        query = Prediction.query.filter(Prediction.municipality_code == municipality_code)
        
        if disease_type:
            query = query.filter(Prediction.disease_type == disease_type.lower())
        
        # Subquery para obter a data mais recente por doença
        subquery = db.session.query(
            Prediction.disease_type,
            func.max(Prediction.prediction_date).label('max_date')
        ).filter(Prediction.municipality_code == municipality_code).group_by(
            Prediction.disease_type
        ).subquery()
        
        # Join com a subquery para obter apenas as predições mais recentes
        return query.join(
            subquery,
            and_(
                Prediction.disease_type == subquery.c.disease_type,
                Prediction.prediction_date == subquery.c.max_date
            )
        ).all()
    
    @staticmethod
    def get_municipalities_with_data() -> List[Dict[str, str]]:
        """
        Obtém lista de municípios que possuem dados
        
        Returns:
            Lista de dicionários com informações dos municípios
        """
        # Municípios com dados de clima
        climate_municipalities = db.session.query(
            ClimateData.municipality_code,
            ClimateData.municipality_name,
            ClimateData.state
        ).distinct().all()
        
        # Municípios com dados de arboviroses
        arbovirus_municipalities = db.session.query(
            ArbovirusData.municipality_code,
            ArbovirusData.municipality_name,
            ArbovirusData.state
        ).distinct().all()
        
        # Combinar e remover duplicatas
        all_municipalities = {}
        
        for mun in climate_municipalities:
            all_municipalities[mun[0]] = {
                'municipality_code': mun[0],
                'municipality_name': mun[1],
                'state': mun[2],
                'has_climate_data': True,
                'has_arbovirus_data': False
            }
        
        for mun in arbovirus_municipalities:
            if mun[0] in all_municipalities:
                all_municipalities[mun[0]]['has_arbovirus_data'] = True
            else:
                all_municipalities[mun[0]] = {
                    'municipality_code': mun[0],
                    'municipality_name': mun[1],
                    'state': mun[2],
                    'has_climate_data': False,
                    'has_arbovirus_data': True
                }
        
        return list(all_municipalities.values())
    
    @staticmethod
    def get_data_summary_by_state(state: str) -> Dict[str, Any]:
        """
        Obtém resumo dos dados por estado
        
        Args:
            state: UF do estado
            
        Returns:
            Dicionário com resumo dos dados
        """
        state_upper = state.upper()
        
        # Contar municípios com dados
        climate_municipalities = db.session.query(
            func.count(func.distinct(ClimateData.municipality_code))
        ).filter(ClimateData.state == state_upper).scalar()
        
        arbovirus_municipalities = db.session.query(
            func.count(func.distinct(ArbovirusData.municipality_code))
        ).filter(ArbovirusData.state == state_upper).scalar()
        
        prediction_municipalities = db.session.query(
            func.count(func.distinct(Prediction.municipality_code))
        ).filter(Prediction.state == state_upper).scalar()
        
        # Contar registros totais
        climate_records = ClimateData.query.filter(ClimateData.state == state_upper).count()
        arbovirus_records = ArbovirusData.query.filter(ArbovirusData.state == state_upper).count()
        prediction_records = Prediction.query.filter(Prediction.state == state_upper).count()
        
        # Obter período dos dados
        climate_date_range = db.session.query(
            func.min(ClimateData.date),
            func.max(ClimateData.date)
        ).filter(ClimateData.state == state_upper).first()
        
        arbovirus_year_range = db.session.query(
            func.min(ArbovirusData.year),
            func.max(ArbovirusData.year)
        ).filter(ArbovirusData.state == state_upper).first()
        
        return {
            'state': state_upper,
            'municipalities': {
                'with_climate_data': climate_municipalities or 0,
                'with_arbovirus_data': arbovirus_municipalities or 0,
                'with_predictions': prediction_municipalities or 0
            },
            'records': {
                'climate_data': climate_records,
                'arbovirus_data': arbovirus_records,
                'predictions': prediction_records
            },
            'data_periods': {
                'climate_data': {
                    'start_date': climate_date_range[0].isoformat() if climate_date_range[0] else None,
                    'end_date': climate_date_range[1].isoformat() if climate_date_range[1] else None
                },
                'arbovirus_data': {
                    'start_year': arbovirus_year_range[0] if arbovirus_year_range[0] else None,
                    'end_year': arbovirus_year_range[1] if arbovirus_year_range[1] else None
                }
            }
        }
    
    @staticmethod
    def bulk_insert_climate_data(data_list: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """
        Insere múltiplos registros de dados de clima
        
        Args:
            data_list: Lista de dicionários com dados de clima
            
        Returns:
            Tuple[int, List[str]]: (registros_inseridos, lista_de_erros)
        """
        inserted_count = 0
        errors = []
        
        for i, data in enumerate(data_list):
            try:
                climate_data = ClimateData(
                    municipality_code=data['municipality_code'],
                    municipality_name=data['municipality_name'],
                    state=data['state'].upper(),
                    date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
                    temperature_max=data.get('temperature_max'),
                    temperature_min=data.get('temperature_min'),
                    temperature_avg=data.get('temperature_avg'),
                    humidity=data.get('humidity'),
                    precipitation=data.get('precipitation'),
                    wind_speed=data.get('wind_speed'),
                    pressure=data.get('pressure')
                )
                
                db.session.add(climate_data)
                inserted_count += 1
                
            except Exception as e:
                errors.append(f"Erro no registro {i+1}: {str(e)}")
        
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            errors.append(f"Erro de integridade no banco: {str(e)}")
            inserted_count = 0
        except Exception as e:
            db.session.rollback()
            errors.append(f"Erro ao salvar no banco: {str(e)}")
            inserted_count = 0
        
        return inserted_count, errors
    
    @staticmethod
    def bulk_insert_arbovirus_data(data_list: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        """
        Insere múltiplos registros de dados de arboviroses
        
        Args:
            data_list: Lista de dicionários com dados de arboviroses
            
        Returns:
            Tuple[int, List[str]]: (registros_inseridos, lista_de_erros)
        """
        inserted_count = 0
        errors = []
        
        for i, data in enumerate(data_list):
            try:
                arbovirus_data = ArbovirusData(
                    municipality_code=data['municipality_code'],
                    municipality_name=data['municipality_name'],
                    state=data['state'].upper(),
                    epidemiological_week=int(data['epidemiological_week']),
                    year=int(data['year']),
                    disease_type=data['disease_type'].lower(),
                    cases_suspected=data.get('cases_suspected', 0),
                    cases_confirmed=data.get('cases_confirmed', 0),
                    cases_probable=data.get('cases_probable', 0),
                    incidence_rate=data.get('incidence_rate'),
                    alert_level=data.get('alert_level'),
                    population=data.get('population')
                )
                
                db.session.add(arbovirus_data)
                inserted_count += 1
                
            except Exception as e:
                errors.append(f"Erro no registro {i+1}: {str(e)}")
        
        try:
            db.session.commit()
        except IntegrityError as e:
            db.session.rollback()
            errors.append(f"Erro de integridade no banco: {str(e)}")
            inserted_count = 0
        except Exception as e:
            db.session.rollback()
            errors.append(f"Erro ao salvar no banco: {str(e)}")
            inserted_count = 0
        
        return inserted_count, errors
    
    @staticmethod
    def cleanup_old_data(days_to_keep: int = 365) -> Dict[str, int]:
        """
        Remove dados antigos do banco de dados
        
        Args:
            days_to_keep: Número de dias de dados para manter
            
        Returns:
            Dicionário com contagem de registros removidos
        """
        cutoff_date = datetime.now().date() - timedelta(days=days_to_keep)
        
        # Remover dados de clima antigos
        climate_deleted = ClimateData.query.filter(
            ClimateData.date < cutoff_date
        ).delete()
        
        # Remover predições antigas
        prediction_deleted = Prediction.query.filter(
            Prediction.prediction_date < cutoff_date
        ).delete()
        
        try:
            db.session.commit()
            return {
                'climate_data_deleted': climate_deleted,
                'predictions_deleted': prediction_deleted
            }
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Erro ao limpar dados antigos: {str(e)}")
    
    @staticmethod
    def get_database_statistics() -> Dict[str, Any]:
        """
        Obtém estatísticas gerais do banco de dados
        
        Returns:
            Dicionário com estatísticas do banco
        """
        stats = {
            'total_records': {
                'climate_data': ClimateData.query.count(),
                'arbovirus_data': ArbovirusData.query.count(),
                'predictions': Prediction.query.count()
            },
            'unique_municipalities': {
                'climate_data': db.session.query(func.count(func.distinct(ClimateData.municipality_code))).scalar(),
                'arbovirus_data': db.session.query(func.count(func.distinct(ArbovirusData.municipality_code))).scalar(),
                'predictions': db.session.query(func.count(func.distinct(Prediction.municipality_code))).scalar()
            },
            'states_covered': {
                'climate_data': db.session.query(func.count(func.distinct(ClimateData.state))).scalar(),
                'arbovirus_data': db.session.query(func.count(func.distinct(ArbovirusData.state))).scalar(),
                'predictions': db.session.query(func.count(func.distinct(Prediction.state))).scalar()
            },
            'disease_types': [disease[0] for disease in db.session.query(func.distinct(ArbovirusData.disease_type)).all()],
            'data_freshness': {
                'latest_climate_date': None,
                'latest_arbovirus_year_week': None,
                'latest_prediction_date': None
            }
        }
        
        # Obter datas mais recentes de forma segura
        latest_climate = db.session.query(func.max(ClimateData.date)).scalar()
        if latest_climate:
            stats['data_freshness']['latest_climate_date'] = latest_climate.isoformat()
        
        latest_arbovirus = db.session.query(
            func.max(ArbovirusData.year),
            func.max(ArbovirusData.epidemiological_week)
        ).first()
        if latest_arbovirus and latest_arbovirus[0]:
            stats['data_freshness']['latest_arbovirus_year_week'] = {
                'year': latest_arbovirus[0],
                'week': latest_arbovirus[1]
            }
        
        latest_prediction = db.session.query(func.max(Prediction.prediction_date)).scalar()
        if latest_prediction:
            stats['data_freshness']['latest_prediction_date'] = latest_prediction.isoformat()
        
        return stats

