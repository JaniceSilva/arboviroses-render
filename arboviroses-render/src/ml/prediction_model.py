"""
Modelo de predição de arboviroses usando deep learning
"""
import os
import sys
import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
import joblib
import json

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.ml.data_preprocessor import DataPreprocessor
from src.models.user import db
from src.models.prediction import Prediction
from flask import Flask

class ArbovirusPredictionModel:
    """Modelo de predição de arboviroses usando deep learning"""
    
    def __init__(self, model_name: str = "arbovirus_predictor"):
        self.model_name = model_name
        self.model = None
        self.preprocessor = DataPreprocessor()
        self.is_trained = False
        self.model_metrics = {}
        
        # Diretório para salvar modelos
        self.model_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'models'
        )
        os.makedirs(self.model_dir, exist_ok=True)
    
    def create_app(self) -> Flask:
        """Criar aplicação Flask para acesso ao banco"""
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'database', 'app.db')}"
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        return app
    
    def build_model(self, input_shape: int, output_shape: int) -> keras.Model:
        """
        Constrói o modelo de deep learning
        
        Args:
            input_shape: Número de features de entrada
            output_shape: Número de saídas (targets)
            
        Returns:
            Modelo Keras compilado
        """
        model = keras.Sequential([
            # Camada de entrada
            layers.Dense(128, activation='relu', input_shape=(input_shape,)),
            layers.Dropout(0.3),
            
            # Camadas ocultas
            layers.Dense(64, activation='relu'),
            layers.Dropout(0.2),
            
            layers.Dense(32, activation='relu'),
            layers.Dropout(0.2),
            
            layers.Dense(16, activation='relu'),
            
            # Camada de saída
            layers.Dense(output_shape, activation='linear')  # Linear para regressão
        ])
        
        # Compilar modelo
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae', 'mse']
        )
        
        return model
    
    def generate_synthetic_data(self, municipality_code: str, disease_type: str, 
                              num_samples: int = 100) -> pd.DataFrame:
        """
        Gera dados sintéticos para treinamento quando dados reais são insuficientes
        
        Args:
            municipality_code: Código IBGE do município
            disease_type: Tipo de doença
            num_samples: Número de amostras sintéticas
            
        Returns:
            DataFrame com dados sintéticos
        """
        print(f"🔬 Gerando {num_samples} amostras sintéticas para treinamento...")
        
        # Definir ranges realistas baseados em conhecimento epidemiológico
        np.random.seed(42)  # Para reprodutibilidade
        
        synthetic_data = []
        base_date = datetime(2023, 1, 1)
        
        for i in range(num_samples):
            # Data sequencial
            current_date = base_date + timedelta(weeks=i)
            
            # Features climáticas com sazonalidade
            month = current_date.month
            
            # Temperatura (mais alta no verão)
            temp_seasonal = 25 + 10 * np.sin(2 * np.pi * (month - 1) / 12)
            temperature_max_mean = temp_seasonal + np.random.normal(0, 3)
            temperature_min_mean = temperature_max_mean - np.random.uniform(5, 15)
            temperature_avg_mean = (temperature_max_mean + temperature_min_mean) / 2
            
            # Umidade (mais alta no verão)
            humidity_seasonal = 65 + 15 * np.sin(2 * np.pi * (month - 1) / 12)
            humidity_mean = max(30, min(95, humidity_seasonal + np.random.normal(0, 10)))
            
            # Precipitação (mais alta no verão)
            precip_seasonal = 100 + 80 * np.sin(2 * np.pi * (month - 1) / 12)
            precipitation_sum = max(0, precip_seasonal + np.random.normal(0, 50))
            
            # Outras variáveis climáticas
            wind_speed_mean = np.random.uniform(5, 25)
            pressure_mean = np.random.uniform(1000, 1020)
            
            # Features de série temporal (lags simulados)
            base_cases = max(0, 50 + 30 * np.sin(2 * np.pi * (month - 1) / 12) + np.random.normal(0, 20))
            
            # Correlação com clima (mais casos com temperatura e umidade altas)
            climate_factor = (temperature_avg_mean - 20) / 10 + (humidity_mean - 50) / 50
            climate_factor = max(0, climate_factor)
            
            cases_suspected = max(0, base_cases * (1 + climate_factor * 0.5))
            cases_confirmed = max(0, cases_suspected * np.random.uniform(0.1, 0.3))
            incidence_rate = cases_suspected / 100000 * 100  # Por 100k habitantes
            
            # Criar registro sintético
            record = {
                'date': current_date,
                'municipality_code': municipality_code,
                'municipality_name': 'São Paulo',
                'state': 'SP',
                'disease_type': disease_type,
                'epidemiological_week': current_date.isocalendar()[1],
                'year': current_date.year,
                'cases_suspected': int(cases_suspected),
                'cases_confirmed': int(cases_confirmed),
                'cases_probable': int(cases_suspected * 0.1),
                'incidence_rate': incidence_rate,
                'alert_level': min(4, max(1, int(incidence_rate / 10))),
                'population': 12000000,
                
                # Features climáticas agregadas
                'temperature_max_mean': temperature_max_mean,
                'temperature_max_std': np.random.uniform(1, 3),
                'temperature_min_mean': temperature_min_mean,
                'temperature_min_std': np.random.uniform(1, 3),
                'temperature_avg_mean': temperature_avg_mean,
                'temperature_avg_std': np.random.uniform(1, 2),
                'humidity_mean': humidity_mean,
                'humidity_std': np.random.uniform(5, 15),
                'precipitation_sum': precipitation_sum,
                'precipitation_mean': precipitation_sum / 7,
                'wind_speed_mean': wind_speed_mean,
                'wind_speed_std': np.random.uniform(2, 5),
                'pressure_mean': pressure_mean,
                'pressure_std': np.random.uniform(2, 8),
                
                # Features temporais
                'month': month,
                'quarter': (month - 1) // 3 + 1,
                'day_of_year': current_date.timetuple().tm_yday,
                'week_of_year': current_date.isocalendar()[1],
                'month_sin': np.sin(2 * np.pi * month / 12),
                'month_cos': np.cos(2 * np.pi * month / 12),
                'week_sin': np.sin(2 * np.pi * current_date.isocalendar()[1] / 52),
                'week_cos': np.cos(2 * np.pi * current_date.isocalendar()[1] / 52),
            }
            
            synthetic_data.append(record)
        
        df = pd.DataFrame(synthetic_data)
        
        # Criar features de lag
        df = df.sort_values('date').reset_index(drop=True)
        for lag in [1, 2, 3, 4]:
            df[f'cases_suspected_lag_{lag}'] = df['cases_suspected'].shift(lag)
        
        # Criar rolling means
        for window in [2, 4, 8]:
            df[f'cases_suspected_rolling_mean_{window}'] = (
                df['cases_suspected'].rolling(window=window, min_periods=1).mean()
            )
        
        # Remover linhas com NaN
        df = df.dropna().reset_index(drop=True)
        
        print(f"✅ Dados sintéticos gerados: {len(df)} registros")
        return df
    
    def train_model(self, municipality_code: str, disease_type: str, 
                   use_synthetic_data: bool = True, epochs: int = 100) -> Dict[str, Any]:
        """
        Treina o modelo de predição
        
        Args:
            municipality_code: Código IBGE do município
            disease_type: Tipo de doença
            use_synthetic_data: Se deve usar dados sintéticos
            epochs: Número de épocas de treinamento
            
        Returns:
            Dicionário com métricas de treinamento
        """
        print(f"🤖 Iniciando treinamento do modelo para {municipality_code} - {disease_type}")
        
        if use_synthetic_data:
            # Usar dados sintéticos
            df = self.generate_synthetic_data(municipality_code, disease_type)
            
            # Definir features e targets
            feature_columns = [
                'temperature_max_mean', 'temperature_max_std',
                'temperature_min_mean', 'temperature_min_std',
                'temperature_avg_mean', 'temperature_avg_std',
                'humidity_mean', 'humidity_std',
                'precipitation_sum', 'precipitation_mean',
                'wind_speed_mean', 'wind_speed_std',
                'pressure_mean', 'pressure_std',
                'cases_suspected_lag_1', 'cases_suspected_lag_2', 'cases_suspected_lag_3', 'cases_suspected_lag_4',
                'cases_suspected_rolling_mean_2', 'cases_suspected_rolling_mean_4', 'cases_suspected_rolling_mean_8',
                'month', 'quarter', 'day_of_year', 'week_of_year',
                'month_sin', 'month_cos', 'week_sin', 'week_cos'
            ]
            
            target_columns = ['cases_suspected', 'cases_confirmed', 'incidence_rate']
            
            self.preprocessor.feature_columns = feature_columns
            self.preprocessor.target_columns = target_columns
            
        else:
            # Tentar usar dados reais
            df, feature_columns, target_columns = self.preprocessor.prepare_training_data(
                municipality_code, disease_type
            )
            
            if df.empty:
                print("⚠️  Dados reais insuficientes, usando dados sintéticos")
                return self.train_model(municipality_code, disease_type, use_synthetic_data=True, epochs=epochs)
        
        # Dividir e escalar dados
        X_train, X_test, y_train, y_test = self.preprocessor.split_and_scale_data(
            df, feature_columns, target_columns
        )
        
        # Construir modelo
        self.model = self.build_model(X_train.shape[1], y_train.shape[1])
        
        print(f"📊 Arquitetura do modelo:")
        self.model.summary()
        
        # Callbacks para treinamento
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=20,
                restore_best_weights=True
            ),
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=10,
                min_lr=1e-6
            )
        ]
        
        # Treinar modelo
        print(f"🏋️  Treinando modelo por {epochs} épocas...")
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_test, y_test),
            epochs=epochs,
            batch_size=32,
            callbacks=callbacks,
            verbose=1
        )
        
        # Avaliar modelo
        train_loss = self.model.evaluate(X_train, y_train, verbose=0)
        test_loss = self.model.evaluate(X_test, y_test, verbose=0)
        
        # Fazer predições
        y_train_pred = self.model.predict(X_train, verbose=0)
        y_test_pred = self.model.predict(X_test, verbose=0)
        
        # Reverter escala
        y_train_actual = self.preprocessor.inverse_transform_predictions(y_train)
        y_train_pred_actual = self.preprocessor.inverse_transform_predictions(y_train_pred)
        y_test_actual = self.preprocessor.inverse_transform_predictions(y_test)
        y_test_pred_actual = self.preprocessor.inverse_transform_predictions(y_test_pred)
        
        # Calcular métricas
        train_metrics = self.calculate_metrics(y_train_actual, y_train_pred_actual)
        test_metrics = self.calculate_metrics(y_test_actual, y_test_pred_actual)
        
        self.model_metrics = {
            'training': {
                'loss': float(train_loss[0]),
                'mae': float(train_loss[1]),
                'mse': float(train_loss[2]),
                **train_metrics
            },
            'validation': {
                'loss': float(test_loss[0]),
                'mae': float(test_loss[1]),
                'mse': float(test_loss[2]),
                **test_metrics
            },
            'training_history': {
                'loss': [float(x) for x in history.history['loss']],
                'val_loss': [float(x) for x in history.history['val_loss']],
                'mae': [float(x) for x in history.history['mae']],
                'val_mae': [float(x) for x in history.history['val_mae']]
            },
            'municipality_code': municipality_code,
            'disease_type': disease_type,
            'training_samples': len(X_train),
            'test_samples': len(X_test),
            'features': len(feature_columns),
            'targets': len(target_columns),
            'synthetic_data': use_synthetic_data,
            'trained_at': datetime.now().isoformat()
        }
        
        self.is_trained = True
        
        print(f"✅ Treinamento concluído!")
        print(f"   - Loss de treino: {train_loss[0]:.4f}")
        print(f"   - Loss de validação: {test_loss[0]:.4f}")
        print(f"   - MAE de validação: {test_loss[1]:.4f}")
        
        return self.model_metrics
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """
        Calcula métricas de avaliação
        
        Args:
            y_true: Valores reais
            y_pred: Valores preditos
            
        Returns:
            Dicionário com métricas
        """
        metrics = {}
        
        for i, target in enumerate(self.preprocessor.target_columns):
            y_true_col = y_true[:, i]
            y_pred_col = y_pred[:, i]
            
            metrics[f'{target}_mse'] = float(mean_squared_error(y_true_col, y_pred_col))
            metrics[f'{target}_mae'] = float(mean_absolute_error(y_true_col, y_pred_col))
            metrics[f'{target}_r2'] = float(r2_score(y_true_col, y_pred_col))
        
        return metrics
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """
        Faz predições usando o modelo treinado
        
        Args:
            features: Array com features de entrada
            
        Returns:
            Array com predições
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Modelo não foi treinado ainda")
        
        # Escalar features
        features_scaled = self.preprocessor.scaler_climate.transform(features)
        
        # Fazer predição
        predictions_scaled = self.model.predict(features_scaled, verbose=0)
        
        # Reverter escala
        predictions = self.preprocessor.inverse_transform_predictions(predictions_scaled)
        
        return predictions
    
    def save_model(self) -> str:
        """
        Salva o modelo treinado
        
        Returns:
            Caminho do arquivo salvo
        """
        if not self.is_trained:
            raise ValueError("Modelo não foi treinado ainda")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_path = os.path.join(self.model_dir, f"{self.model_name}_{timestamp}")
        
        # Salvar modelo Keras
        self.model.save(f"{model_path}.keras")
        
        # Salvar preprocessador
        joblib.dump(self.preprocessor, f"{model_path}_preprocessor.pkl")
        
        # Salvar métricas
        with open(f"{model_path}_metrics.json", 'w') as f:
            json.dump(self.model_metrics, f, indent=2)
        
        print(f"💾 Modelo salvo em: {model_path}")
        return model_path
    
    def load_model(self, model_path: str):
        """
        Carrega um modelo salvo
        
        Args:
            model_path: Caminho do modelo (sem extensão)
        """
        # Carregar modelo Keras
        self.model = keras.models.load_model(f"{model_path}.keras")
        
        # Carregar preprocessador
        self.preprocessor = joblib.load(f"{model_path}_preprocessor.pkl")
        
        # Carregar métricas
        with open(f"{model_path}_metrics.json", 'r') as f:
            self.model_metrics = json.load(f)
        
        self.is_trained = True
        print(f"📂 Modelo carregado de: {model_path}")
    
    def generate_predictions_for_municipality(self, municipality_code: str, disease_type: str, 
                                            weeks_ahead: int = 4) -> List[Dict[str, Any]]:
        """
        Gera predições para as próximas semanas
        
        Args:
            municipality_code: Código IBGE do município
            disease_type: Tipo de doença
            weeks_ahead: Número de semanas para predizer
            
        Returns:
            Lista com predições
        """
        if not self.is_trained:
            raise ValueError("Modelo não foi treinado ainda")
        
        print(f"🔮 Gerando predições para {weeks_ahead} semanas...")
        
        # Para demonstração, usar valores médios das features
        # Em produção, isso viria de dados reais ou previsões meteorológicas
        predictions = []
        base_date = datetime.now()
        
        for week in range(1, weeks_ahead + 1):
            prediction_date = base_date + timedelta(weeks=week)
            
            # Features sintéticas para demonstração
            month = prediction_date.month
            
            # Simular features climáticas sazonais
            temp_seasonal = 25 + 10 * np.sin(2 * np.pi * (month - 1) / 12)
            humidity_seasonal = 65 + 15 * np.sin(2 * np.pi * (month - 1) / 12)
            precip_seasonal = 100 + 80 * np.sin(2 * np.pi * (month - 1) / 12)
            
            features = np.array([[
                temp_seasonal + 5, 2,  # temperature_max_mean, std
                temp_seasonal - 5, 2,  # temperature_min_mean, std
                temp_seasonal, 1,      # temperature_avg_mean, std
                humidity_seasonal, 10, # humidity_mean, std
                precip_seasonal, precip_seasonal/7,  # precipitation_sum, mean
                15, 3,                 # wind_speed_mean, std
                1013, 5,               # pressure_mean, std
                50, 45, 40, 35,        # lags (valores simulados)
                45, 42, 40,            # rolling means
                month, (month-1)//3+1, prediction_date.timetuple().tm_yday, prediction_date.isocalendar()[1],
                np.sin(2 * np.pi * month / 12), np.cos(2 * np.pi * month / 12),
                np.sin(2 * np.pi * prediction_date.isocalendar()[1] / 52), 
                np.cos(2 * np.pi * prediction_date.isocalendar()[1] / 52)
            ]])
            
            # Fazer predição
            pred = self.predict(features)[0]
            
            prediction = {
                'municipality_code': municipality_code,
                'disease_type': disease_type,
                'prediction_date': prediction_date.date(),
                'epidemiological_week': prediction_date.isocalendar()[1],
                'year': prediction_date.year,
                'predicted_cases_suspected': max(0, int(pred[0])),
                'predicted_cases_confirmed': max(0, int(pred[1])),
                'predicted_incidence_rate': max(0, float(pred[2])),
                'confidence_interval_lower': max(0, float(pred[0] * 0.8)),
                'confidence_interval_upper': float(pred[0] * 1.2),
                'alert_level': min(4, max(1, int(pred[2] / 10))),
                'model_version': self.model_name,
                'created_at': datetime.now()
            }
            
            predictions.append(prediction)
        
        return predictions

def test_model():
    """Testa o modelo de predição"""
    print("🧪 Testando modelo de predição de arboviroses...")
    
    model = ArbovirusPredictionModel()
    
    # Treinar modelo com dados sintéticos
    municipality_code = "3550308"  # São Paulo
    disease_type = "dengue"
    
    metrics = model.train_model(municipality_code, disease_type, use_synthetic_data=True, epochs=50)
    
    print(f"📊 Métricas de treinamento:")
    print(f"   - Loss de validação: {metrics['validation']['loss']:.4f}")
    print(f"   - MAE de validação: {metrics['validation']['mae']:.4f}")
    
    # Salvar modelo
    model_path = model.save_model()
    
    # Gerar predições
    predictions = model.generate_predictions_for_municipality(municipality_code, disease_type)
    
    print(f"🔮 Predições geradas:")
    for pred in predictions:
        print(f"   - {pred['prediction_date']}: {pred['predicted_cases_suspected']} casos suspeitos")
    
    return model, predictions

if __name__ == "__main__":
    test_model()

