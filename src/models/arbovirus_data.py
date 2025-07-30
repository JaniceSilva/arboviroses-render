from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from src.models.user import db

class ArbovirusData(db.Model):
    __tablename__ = 'arbovirus_data'
    
    id = db.Column(db.Integer, primary_key=True)
    municipality_code = db.Column(db.String(10), nullable=False)  # Código IBGE do município
    municipality_name = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(2), nullable=False)  # UF
    epidemiological_week = db.Column(db.Integer, nullable=False)  # Semana epidemiológica
    year = db.Column(db.Integer, nullable=False)
    
    # Dados de arboviroses
    disease_type = db.Column(db.String(20), nullable=False)  # dengue, chikungunya, zika
    cases_suspected = db.Column(db.Integer, default=0)  # Casos suspeitos
    cases_confirmed = db.Column(db.Integer, default=0)  # Casos confirmados
    cases_probable = db.Column(db.Integer, default=0)  # Casos prováveis
    incidence_rate = db.Column(db.Float)  # Taxa de incidência por 100.000 habitantes
    alert_level = db.Column(db.Integer)  # Nível de alerta (0-4)
    
    # Dados populacionais
    population = db.Column(db.Integer)  # População do município
    
    # Metadados
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ArbovirusData {self.municipality_name} - {self.disease_type} - {self.year}W{self.epidemiological_week}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'municipality_code': self.municipality_code,
            'municipality_name': self.municipality_name,
            'state': self.state,
            'epidemiological_week': self.epidemiological_week,
            'year': self.year,
            'disease_type': self.disease_type,
            'cases_suspected': self.cases_suspected,
            'cases_confirmed': self.cases_confirmed,
            'cases_probable': self.cases_probable,
            'incidence_rate': self.incidence_rate,
            'alert_level': self.alert_level,
            'population': self.population,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

