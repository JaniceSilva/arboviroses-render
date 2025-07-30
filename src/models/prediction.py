from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    municipality_code = db.Column(db.String(10), nullable=False)  # Código IBGE do município
    municipality_name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)  # UF
    
    # Período da predição
    prediction_date = db.Column(db.Date, nullable=False)  # Data para qual a predição foi feita
    prediction_period = db.Column(db.String(20), nullable=False)  # Período da predição (ex: "2025-01", "2025-Q1")
    
    # Dados da predição
    disease_type = db.Column(db.String(20), nullable=False)  # dengue, chikungunya, zika
    predicted_cases = db.Column(db.Float, nullable=False)  # Número de casos preditos
    predicted_incidence_rate = db.Column(db.Float)  # Taxa de incidência predita por 100.000 habitantes
    predicted_alert_level = db.Column(db.Integer)  # Nível de alerta predito (0-4)
    confidence_interval_lower = db.Column(db.Float)  # Limite inferior do intervalo de confiança
    confidence_interval_upper = db.Column(db.Float)  # Limite superior do intervalo de confiança
    confidence_score = db.Column(db.Float)  # Score de confiança da predição (0-1)
    
    # Metadados do modelo
    model_version = db.Column(db.String(50))  # Versão do modelo usado
    model_accuracy = db.Column(db.Float)  # Acurácia do modelo
    features_used = db.Column(db.Text)  # JSON com as features usadas na predição
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Prediction {self.municipality_name} - {self.disease_type} - {self.prediction_period}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'municipality_code': self.municipality_code,
            'municipality_name': self.municipality_name,
            'state': self.state,
            'prediction_date': self.prediction_date.isoformat() if self.prediction_date else None,
            'prediction_period': self.prediction_period,
            'disease_type': self.disease_type,
            'predicted_cases': self.predicted_cases,
            'predicted_incidence_rate': self.predicted_incidence_rate,
            'predicted_alert_level': self.predicted_alert_level,
            'confidence_interval_lower': self.confidence_interval_lower,
            'confidence_interval_upper': self.confidence_interval_upper,
            'confidence_score': self.confidence_score,
            'model_version': self.model_version,
            'model_accuracy': self.model_accuracy,
            'features_used': self.features_used,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

