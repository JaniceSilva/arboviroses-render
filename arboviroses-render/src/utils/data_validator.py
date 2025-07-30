"""
Utilitários para validação de dados de entrada
"""
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple

class DataValidator:
    """Classe para validação de dados de entrada"""
    
    # Códigos IBGE válidos (formato: 7 dígitos)
    IBGE_CODE_PATTERN = re.compile(r'^\d{7}$')
    
    # Estados brasileiros válidos
    VALID_STATES = {
        'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
        'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
        'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
    }
    
    # Tipos de doenças válidos
    VALID_DISEASES = {'dengue', 'chikungunya', 'zika'}
    
    @staticmethod
    def validate_municipality_code(code: str) -> Tuple[bool, str]:
        """
        Valida código IBGE do município
        
        Args:
            code: Código IBGE a ser validado
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem_erro)
        """
        if not code:
            return False, "Código IBGE é obrigatório"
        
        if not isinstance(code, str):
            return False, "Código IBGE deve ser uma string"
        
        if not DataValidator.IBGE_CODE_PATTERN.match(code):
            return False, "Código IBGE deve ter exatamente 7 dígitos"
        
        return True, ""
    
    @staticmethod
    def validate_state(state: str) -> Tuple[bool, str]:
        """
        Valida UF do estado
        
        Args:
            state: UF a ser validada
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem_erro)
        """
        if not state:
            return False, "UF é obrigatória"
        
        if not isinstance(state, str):
            return False, "UF deve ser uma string"
        
        state_upper = state.upper()
        if state_upper not in DataValidator.VALID_STATES:
            return False, f"UF inválida. Valores válidos: {', '.join(sorted(DataValidator.VALID_STATES))}"
        
        return True, ""
    
    @staticmethod
    def validate_disease_type(disease: str) -> Tuple[bool, str]:
        """
        Valida tipo de doença
        
        Args:
            disease: Tipo de doença a ser validado
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem_erro)
        """
        if not disease:
            return False, "Tipo de doença é obrigatório"
        
        if not isinstance(disease, str):
            return False, "Tipo de doença deve ser uma string"
        
        disease_lower = disease.lower()
        if disease_lower not in DataValidator.VALID_DISEASES:
            return False, f"Tipo de doença inválido. Valores válidos: {', '.join(sorted(DataValidator.VALID_DISEASES))}"
        
        return True, ""
    
    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, str, Optional[date]]:
        """
        Valida formato de data
        
        Args:
            date_str: Data em formato string (YYYY-MM-DD)
            
        Returns:
            Tuple[bool, str, Optional[date]]: (é_válido, mensagem_erro, objeto_date)
        """
        if not date_str:
            return False, "Data é obrigatória", None
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            return True, "", date_obj
        except ValueError:
            return False, "Formato de data inválido. Use YYYY-MM-DD", None
    
    @staticmethod
    def validate_epidemiological_week(week: int, year: int) -> Tuple[bool, str]:
        """
        Valida semana epidemiológica
        
        Args:
            week: Número da semana epidemiológica
            year: Ano
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem_erro)
        """
        if not isinstance(week, int):
            return False, "Semana epidemiológica deve ser um número inteiro"
        
        if not isinstance(year, int):
            return False, "Ano deve ser um número inteiro"
        
        if week < 1 or week > 53:
            return False, "Semana epidemiológica deve estar entre 1 e 53"
        
        current_year = datetime.now().year
        if year < 2000 or year > current_year + 1:
            return False, f"Ano deve estar entre 2000 e {current_year + 1}"
        
        return True, ""
    
    @staticmethod
    def validate_numeric_range(value: float, min_val: float = None, max_val: float = None, field_name: str = "Valor") -> Tuple[bool, str]:
        """
        Valida se um valor numérico está dentro de um intervalo
        
        Args:
            value: Valor a ser validado
            min_val: Valor mínimo permitido
            max_val: Valor máximo permitido
            field_name: Nome do campo para mensagens de erro
            
        Returns:
            Tuple[bool, str]: (é_válido, mensagem_erro)
        """
        if value is None:
            return True, ""  # Valores opcionais são permitidos
        
        if not isinstance(value, (int, float)):
            return False, f"{field_name} deve ser um número"
        
        if min_val is not None and value < min_val:
            return False, f"{field_name} deve ser maior ou igual a {min_val}"
        
        if max_val is not None and value > max_val:
            return False, f"{field_name} deve ser menor ou igual a {max_val}"
        
        return True, ""
    
    @staticmethod
    def validate_climate_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Valida dados de clima
        
        Args:
            data: Dicionário com dados de clima
            
        Returns:
            Tuple[bool, List[str]]: (é_válido, lista_de_erros)
        """
        errors = []
        
        # Validações obrigatórias
        required_fields = ['municipality_code', 'municipality_name', 'state', 'date']
        for field in required_fields:
            if field not in data or not data[field]:
                errors.append(f"Campo obrigatório ausente: {field}")
        
        # Validar código IBGE
        if 'municipality_code' in data:
            is_valid, error = DataValidator.validate_municipality_code(data['municipality_code'])
            if not is_valid:
                errors.append(error)
        
        # Validar estado
        if 'state' in data:
            is_valid, error = DataValidator.validate_state(data['state'])
            if not is_valid:
                errors.append(error)
        
        # Validar data
        if 'date' in data:
            is_valid, error, _ = DataValidator.validate_date(data['date'])
            if not is_valid:
                errors.append(error)
        
        # Validar campos numéricos opcionais
        numeric_validations = [
            ('temperature_max', -50, 60, "Temperatura máxima"),
            ('temperature_min', -50, 60, "Temperatura mínima"),
            ('temperature_avg', -50, 60, "Temperatura média"),
            ('humidity', 0, 100, "Umidade"),
            ('precipitation', 0, 1000, "Precipitação"),
            ('wind_speed', 0, 200, "Velocidade do vento"),
            ('pressure', 800, 1200, "Pressão atmosférica")
        ]
        
        for field, min_val, max_val, field_name in numeric_validations:
            if field in data:
                is_valid, error = DataValidator.validate_numeric_range(
                    data[field], min_val, max_val, field_name
                )
                if not is_valid:
                    errors.append(error)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_arbovirus_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Valida dados de arboviroses
        
        Args:
            data: Dicionário com dados de arboviroses
            
        Returns:
            Tuple[bool, List[str]]: (é_válido, lista_de_erros)
        """
        errors = []
        
        # Validações obrigatórias
        required_fields = ['municipality_code', 'municipality_name', 'state', 
                          'epidemiological_week', 'year', 'disease_type']
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Campo obrigatório ausente: {field}")
        
        # Validar código IBGE
        if 'municipality_code' in data:
            is_valid, error = DataValidator.validate_municipality_code(data['municipality_code'])
            if not is_valid:
                errors.append(error)
        
        # Validar estado
        if 'state' in data:
            is_valid, error = DataValidator.validate_state(data['state'])
            if not is_valid:
                errors.append(error)
        
        # Validar tipo de doença
        if 'disease_type' in data:
            is_valid, error = DataValidator.validate_disease_type(data['disease_type'])
            if not is_valid:
                errors.append(error)
        
        # Validar semana epidemiológica
        if 'epidemiological_week' in data and 'year' in data:
            try:
                week = int(data['epidemiological_week'])
                year = int(data['year'])
                is_valid, error = DataValidator.validate_epidemiological_week(week, year)
                if not is_valid:
                    errors.append(error)
            except (ValueError, TypeError):
                errors.append("Semana epidemiológica e ano devem ser números inteiros")
        
        # Validar campos numéricos opcionais
        numeric_validations = [
            ('cases_suspected', 0, 1000000, "Casos suspeitos"),
            ('cases_confirmed', 0, 1000000, "Casos confirmados"),
            ('cases_probable', 0, 1000000, "Casos prováveis"),
            ('incidence_rate', 0, 10000, "Taxa de incidência"),
            ('alert_level', 0, 4, "Nível de alerta"),
            ('population', 1, 50000000, "População")
        ]
        
        for field, min_val, max_val, field_name in numeric_validations:
            if field in data:
                is_valid, error = DataValidator.validate_numeric_range(
                    data[field], min_val, max_val, field_name
                )
                if not is_valid:
                    errors.append(error)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_prediction_data(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Valida dados de predição
        
        Args:
            data: Dicionário com dados de predição
            
        Returns:
            Tuple[bool, List[str]]: (é_válido, lista_de_erros)
        """
        errors = []
        
        # Validações obrigatórias
        required_fields = ['municipality_code', 'municipality_name', 'state', 
                          'prediction_date', 'prediction_period', 'disease_type', 'predicted_cases']
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Campo obrigatório ausente: {field}")
        
        # Validar código IBGE
        if 'municipality_code' in data:
            is_valid, error = DataValidator.validate_municipality_code(data['municipality_code'])
            if not is_valid:
                errors.append(error)
        
        # Validar estado
        if 'state' in data:
            is_valid, error = DataValidator.validate_state(data['state'])
            if not is_valid:
                errors.append(error)
        
        # Validar tipo de doença
        if 'disease_type' in data:
            is_valid, error = DataValidator.validate_disease_type(data['disease_type'])
            if not is_valid:
                errors.append(error)
        
        # Validar data de predição
        if 'prediction_date' in data:
            is_valid, error, _ = DataValidator.validate_date(data['prediction_date'])
            if not is_valid:
                errors.append(error)
        
        # Validar campos numéricos obrigatórios
        if 'predicted_cases' in data:
            is_valid, error = DataValidator.validate_numeric_range(
                data['predicted_cases'], 0, 1000000, "Casos preditos"
            )
            if not is_valid:
                errors.append(error)
        
        # Validar campos numéricos opcionais
        numeric_validations = [
            ('predicted_incidence_rate', 0, 10000, "Taxa de incidência predita"),
            ('predicted_alert_level', 0, 4, "Nível de alerta predito"),
            ('confidence_interval_lower', 0, 1000000, "Limite inferior do intervalo de confiança"),
            ('confidence_interval_upper', 0, 1000000, "Limite superior do intervalo de confiança"),
            ('confidence_score', 0, 1, "Score de confiança"),
            ('model_accuracy', 0, 1, "Acurácia do modelo")
        ]
        
        for field, min_val, max_val, field_name in numeric_validations:
            if field in data:
                is_valid, error = DataValidator.validate_numeric_range(
                    data[field], min_val, max_val, field_name
                )
                if not is_valid:
                    errors.append(error)
        
        return len(errors) == 0, errors

