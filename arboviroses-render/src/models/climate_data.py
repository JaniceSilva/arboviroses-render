from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class ClimateData(db.Model):
    __tablename__ = 'climate_data'
    
    id = db.Column(db.Integer, primary_key=True)
    municipality_code = db.Column(db.String(10), nullable=False)  # Código IBGE do município
    municipality_name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)  # UF
    date = db.Column(db.Date, nullable=False)
    
    # Dados meteorológicos
    temperature_max = db.Column(db.Float)  # Temperatura máxima (°C)
    temperature_min = db.Column(db.Float)  # Temperatura mínima (°C)
    temperature_avg = db.Column(db.Float)  # Temperatura média (°C)
    humidity = db.Column(db.Float)  # Umidade relativa (%)
    precipitation = db.Column(db.Float)  # Precipitação (mm)
    wind_speed = db.Column(db.Float)  # Velocidade do vento (km/h)
    pressure = db.Column(db.Float)  # Pressão atmosférica (hPa)
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ClimateData {self.municipality_name} - {self.date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'municipality_code': self.municipality_code,
            'municipality_name': self.municipality_name,
            'state': self.state,
            'date': self.date.isoformat() if self.date else None,
            'temperature_max': self.temperature_max,
            'temperature_min': self.temperature_min,
            'temperature_avg': self.temperature_avg,
            'humidity': self.humidity,
            'precipitation': self.precipitation,
            'wind_speed': self.wind_speed,
            'pressure': self.pressure,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

