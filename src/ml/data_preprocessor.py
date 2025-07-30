"""
Preprocessador de dados para modelos de machine learning
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.models.user import db
from src.models.climate_data import ClimateData
from src.models.arbovirus_data import ArbovirusData
from src.utils.database_manager import DatabaseManager
from flask import Flask

class DataPreprocessor:
    """Preprocessador de dados para modelos de ML"""
    
    def __init__(self):
        self.scaler_climate = StandardScaler()
        self.scaler_target = MinMaxScaler()
        self.feature_columns = []
        self.target_columns = []
        
    def create_app(self) -> Flask:
        """Criar aplicação Flask para acesso ao banco"""
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')}"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        return app
    
    def load_climate_data(self, municipality_code: str, start_date: date, end_date: date) -> pd.DataFrame:
        """
        Carrega dados de clima do banco de dados
        
        Args:
            municipality_code: Código IBGE do município
            start_date: Data inicial
            end_date: Data final
            
        Returns:
            DataFrame com dados de clima
        """
        app = self.create_app()
        
        with app.app_context():
            climate_data = DatabaseManager.get_climate_data_by_municipality_and_period(
                municipality_code, start_date, end_date
            )
            
            if not climate_data:
                return pd.DataFrame()
            
            # Converter para DataFrame
            data_list = []
            for record in climate_data:
                data_dict = record.to_dict()
                data_list.append(data_dict)
            
            df = pd.DataFrame(data_list)
            
            # Converter data para datetime
            df['date'] = pd.to_datetime(df['date'])
            
            # Ordenar por data
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
    
    def load_arbovirus_data(self, municipality_code: str, disease_type: str, start_year: int, end_year: int) -> pd.DataFrame:
        """
        Carrega dados de arboviroses do banco de dados
        
        Args:
            municipality_code: Código IBGE do município
            disease_type: Tipo de doença
            start_year: Ano inicial
            end_year: Ano final
            
        Returns:
            DataFrame com dados de arboviroses
        """
        app = self.create_app()
        
        with app.app_context():
            arbovirus_data = DatabaseManager.get_arbovirus_data_by_municipality_and_period(
                municipality_code, disease_type, start_year, end_year
            )
            
            if not arbovirus_data:
                return pd.DataFrame()
            
            # Converter para DataFrame
            data_list = []
            for record in arbovirus_data:
                data_dict = record.to_dict()
                data_list.append(data_dict)
            
            df = pd.DataFrame(data_list)
            
            # Criar coluna de data baseada no ano e semana epidemiológica
            df['date'] = df.apply(
                lambda row: self.epidemiological_week_to_date(row['year'], row['epidemiological_week']),
                axis=1
            )
            
            # Ordenar por data
            df = df.sort_values('date').reset_index(drop=True)
            
            return df
    
    def epidemiological_week_to_date(self, year: int, week: int) -> date:
        """
        Converte ano e semana epidemiológica para data
        
        Args:
            year: Ano
            week: Semana epidemiológica
            
        Returns:
            Data correspondente ao início da semana
        """
        # Primeiro dia do ano
        jan_1 = date(year, 1, 1)
        
        # Encontrar o primeiro domingo do ano (início da semana epidemiológica)
        days_to_sunday = (6 - jan_1.weekday()) % 7
        first_sunday = jan_1 + timedelta(days=days_to_sunday)
        
        # Calcular data da semana epidemiológica
        target_date = first_sunday + timedelta(weeks=week-1)
        
        return target_date
    
    def merge_climate_arbovirus_data(self, climate_df: pd.DataFrame, arbovirus_df: pd.DataFrame, 
                                   time_window: int = 7) -> pd.DataFrame:
        """
        Combina dados de clima e arboviroses com janela temporal
        
        Args:
            climate_df: DataFrame com dados de clima
            arbovirus_df: DataFrame com dados de arboviroses
            time_window: Janela temporal em dias para agregar dados de clima
            
        Returns:
            DataFrame combinado
        """
        if climate_df.empty or arbovirus_df.empty:
            return pd.DataFrame()
        
        merged_data = []
        
        for _, arbovirus_row in arbovirus_df.iterrows():
            arbovirus_date = arbovirus_row['date']
            
            # Converter para datetime se necessário
            if isinstance(arbovirus_date, date):
                arbovirus_date = pd.to_datetime(arbovirus_date)
            
            # Definir janela temporal para dados de clima
            start_date = arbovirus_date - pd.Timedelta(days=time_window)
            end_date = arbovirus_date
            
            # Filtrar dados de clima na janela temporal
            climate_window = climate_df[
                (climate_df['date'] >= start_date) & 
                (climate_df['date'] <= end_date)
            ]
            
            if not climate_window.empty:
                # Agregar dados de clima na janela temporal
                climate_agg = {
                    'temperature_max_mean': climate_window['temperature_max'].mean(),
                    'temperature_max_std': climate_window['temperature_max'].std(),
                    'temperature_min_mean': climate_window['temperature_min'].mean(),
                    'temperature_min_std': climate_window['temperature_min'].std(),
                    'temperature_avg_mean': climate_window['temperature_avg'].mean(),
                    'temperature_avg_std': climate_window['temperature_avg'].std(),
                    'humidity_mean': climate_window['humidity'].mean(),
                    'humidity_std': climate_window['humidity'].std(),
                    'precipitation_sum': climate_window['precipitation'].sum(),
                    'precipitation_mean': climate_window['precipitation'].mean(),
                    'wind_speed_mean': climate_window['wind_speed'].mean(),
                    'wind_speed_std': climate_window['wind_speed'].std(),
                    'pressure_mean': climate_window['pressure'].mean(),
                    'pressure_std': climate_window['pressure'].std(),
                }
                
                # Combinar com dados de arboviroses
                merged_row = {**arbovirus_row.to_dict(), **climate_agg}
                merged_data.append(merged_row)
        
        if not merged_data:
            return pd.DataFrame()
        
        merged_df = pd.DataFrame(merged_data)
        
        # Preencher valores NaN com 0 para desvios padrão (quando há apenas 1 observação)
        std_columns = [col for col in merged_df.columns if col.endswith('_std')]
        merged_df[std_columns] = merged_df[std_columns].fillna(0)
        
        return merged_df
    
    def create_time_series_features(self, df: pd.DataFrame, target_col: str, 
                                  lag_features: List[int] = [1, 2, 3, 4]) -> pd.DataFrame:
        """
        Cria features de série temporal (lags, rolling means, etc.)
        
        Args:
            df: DataFrame com dados
            target_col: Nome da coluna alvo
            lag_features: Lista de lags para criar
            
        Returns:
            DataFrame com features de série temporal
        """
        df_features = df.copy()
        
        # Ordenar por data
        df_features = df_features.sort_values('date').reset_index(drop=True)
        
        # Garantir que a coluna date seja datetime
        if not pd.api.types.is_datetime64_any_dtype(df_features['date']):
            df_features['date'] = pd.to_datetime(df_features['date'])
        
        # Criar features de lag
        for lag in lag_features:
            df_features[f'{target_col}_lag_{lag}'] = df_features[target_col].shift(lag)
        
        # Criar rolling means
        for window in [2, 4, 8]:
            df_features[f'{target_col}_rolling_mean_{window}'] = (
                df_features[target_col].rolling(window=window, min_periods=1).mean()
            )
        
        # Criar features temporais
        df_features['month'] = df_features['date'].dt.month
        df_features['quarter'] = df_features['date'].dt.quarter
        df_features['day_of_year'] = df_features['date'].dt.dayofyear
        df_features['week_of_year'] = df_features['date'].dt.isocalendar().week
        
        # Features cíclicas para sazonalidade
        df_features['month_sin'] = np.sin(2 * np.pi * df_features['month'] / 12)
        df_features['month_cos'] = np.cos(2 * np.pi * df_features['month'] / 12)
        df_features['week_sin'] = np.sin(2 * np.pi * df_features['week_of_year'] / 52)
        df_features['week_cos'] = np.cos(2 * np.pi * df_features['week_of_year'] / 52)
        
        return df_features
    
    def prepare_training_data(self, municipality_code: str, disease_type: str, 
                            years_back: int = 2) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """
        Prepara dados para treinamento do modelo
        
        Args:
            municipality_code: Código IBGE do município
            disease_type: Tipo de doença
            years_back: Número de anos para voltar nos dados
            
        Returns:
            Tuple com (DataFrame preparado, colunas de features, colunas alvo)
        """
        # Definir período de dados
        end_date = date.today()
        start_date = end_date - timedelta(days=years_back * 365)
        end_year = end_date.year
        start_year = start_date.year
        
        print(f"📊 Carregando dados de {start_date} a {end_date}...")
        
        # Carregar dados de clima
        climate_df = self.load_climate_data(municipality_code, start_date, end_date)
        print(f"   - Dados de clima: {len(climate_df)} registros")
        
        # Carregar dados de arboviroses
        arbovirus_df = self.load_arbovirus_data(municipality_code, disease_type, start_year, end_year)
        print(f"   - Dados de arboviroses: {len(arbovirus_df)} registros")
        
        if climate_df.empty or arbovirus_df.empty:
            print("⚠️  Dados insuficientes para treinamento")
            return pd.DataFrame(), [], []
        
        # Combinar dados
        merged_df = self.merge_climate_arbovirus_data(climate_df, arbovirus_df)
        print(f"   - Dados combinados: {len(merged_df)} registros")
        
        if merged_df.empty:
            print("⚠️  Falha ao combinar dados")
            return pd.DataFrame(), [], []
        
        # Criar features de série temporal
        target_col = 'cases_suspected'  # Usar casos suspeitos como alvo principal
        df_with_features = self.create_time_series_features(merged_df, target_col)
        
        # Remover linhas com NaN (devido aos lags)
        df_clean = df_with_features.dropna().reset_index(drop=True)
        print(f"   - Dados limpos: {len(df_clean)} registros")
        
        # Definir colunas de features e alvo
        feature_columns = [
            # Features climáticas agregadas
            'temperature_max_mean', 'temperature_max_std',
            'temperature_min_mean', 'temperature_min_std',
            'temperature_avg_mean', 'temperature_avg_std',
            'humidity_mean', 'humidity_std',
            'precipitation_sum', 'precipitation_mean',
            'wind_speed_mean', 'wind_speed_std',
            'pressure_mean', 'pressure_std',
            # Features de série temporal
            'cases_suspected_lag_1', 'cases_suspected_lag_2', 'cases_suspected_lag_3', 'cases_suspected_lag_4',
            'cases_suspected_rolling_mean_2', 'cases_suspected_rolling_mean_4', 'cases_suspected_rolling_mean_8',
            # Features temporais
            'month', 'quarter', 'day_of_year', 'week_of_year',
            'month_sin', 'month_cos', 'week_sin', 'week_cos'
        ]
        
        target_columns = ['cases_suspected', 'cases_confirmed', 'incidence_rate']
        
        # Filtrar apenas colunas que existem no DataFrame
        available_features = [col for col in feature_columns if col in df_clean.columns]
        available_targets = [col for col in target_columns if col in df_clean.columns]
        
        print(f"   - Features disponíveis: {len(available_features)}")
        print(f"   - Alvos disponíveis: {len(available_targets)}")
        
        self.feature_columns = available_features
        self.target_columns = available_targets
        
        return df_clean, available_features, available_targets
    
    def split_and_scale_data(self, df: pd.DataFrame, feature_columns: List[str], 
                           target_columns: List[str], test_size: float = 0.2) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Divide e escala os dados para treinamento
        
        Args:
            df: DataFrame com dados
            feature_columns: Lista de colunas de features
            target_columns: Lista de colunas alvo
            test_size: Proporção dos dados para teste
            
        Returns:
            Tuple com (X_train, X_test, y_train, y_test)
        """
        # Extrair features e targets
        X = df[feature_columns].values
        y = df[target_columns].values
        
        # Dividir dados
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, shuffle=False  # Não embaralhar para manter ordem temporal
        )
        
        # Escalar features
        X_train_scaled = self.scaler_climate.fit_transform(X_train)
        X_test_scaled = self.scaler_climate.transform(X_test)
        
        # Escalar targets
        y_train_scaled = self.scaler_target.fit_transform(y_train)
        y_test_scaled = self.scaler_target.transform(y_test)
        
        print(f"📊 Dados divididos:")
        print(f"   - Treinamento: {X_train_scaled.shape[0]} amostras")
        print(f"   - Teste: {X_test_scaled.shape[0]} amostras")
        print(f"   - Features: {X_train_scaled.shape[1]}")
        print(f"   - Targets: {y_train_scaled.shape[1]}")
        
        return X_train_scaled, X_test_scaled, y_train_scaled, y_test_scaled
    
    def inverse_transform_predictions(self, predictions: np.ndarray) -> np.ndarray:
        """
        Reverte a escala das predições
        
        Args:
            predictions: Predições escaladas
            
        Returns:
            Predições na escala original
        """
        return self.scaler_target.inverse_transform(predictions)
    
    def get_feature_importance_names(self) -> List[str]:
        """
        Retorna nomes das features para análise de importância
        
        Returns:
            Lista com nomes das features
        """
        return self.feature_columns.copy()

def test_preprocessor():
    """Testa o preprocessador de dados"""
    preprocessor = DataPreprocessor()
    
    # Testar com São Paulo e dengue
    municipality_code = "3550308"
    disease_type = "dengue"
    
    print(f"🧪 Testando preprocessador para {municipality_code} - {disease_type}")
    
    df, features, targets = preprocessor.prepare_training_data(
        municipality_code, disease_type, years_back=1
    )
    
    if not df.empty:
        print(f"✅ Dados preparados com sucesso!")
        print(f"   - Shape: {df.shape}")
        print(f"   - Features: {features}")
        print(f"   - Targets: {targets}")
        
        # Testar divisão e escala
        X_train, X_test, y_train, y_test = preprocessor.split_and_scale_data(
            df, features, targets
        )
        
        print(f"✅ Dados divididos e escalados com sucesso!")
        
    else:
        print(f"❌ Falha ao preparar dados")

if __name__ == "__main__":
    test_preprocessor()

