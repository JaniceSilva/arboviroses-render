"""
Utilitário para enviar métricas customizadas ao CloudWatch
"""
import boto3
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CloudWatchMetrics:
    """Classe para gerenciar métricas customizadas no CloudWatch"""
    
    def __init__(self, namespace: str = "ArbovirosesPredictor"):
        """
        Inicializa o cliente CloudWatch
        
        Args:
            namespace: Namespace para as métricas
        """
        self.namespace = namespace
        self.cloudwatch = None
        
        # Verificar se está rodando na AWS
        try:
            self.cloudwatch = boto3.client('cloudwatch')
            # Testar conexão
            self.cloudwatch.list_metrics(Namespace=self.namespace, MaxRecords=1)
            self.enabled = True
            logger.info(f"CloudWatch metrics habilitado para namespace: {self.namespace}")
        except Exception as e:
            self.enabled = False
            logger.warning(f"CloudWatch metrics desabilitado: {str(e)}")
    
    def put_metric(self, metric_name: str, value: float, unit: str = 'Count', 
                   dimensions: Optional[Dict[str, str]] = None) -> bool:
        """
        Envia uma métrica para o CloudWatch
        
        Args:
            metric_name: Nome da métrica
            value: Valor da métrica
            unit: Unidade da métrica
            dimensions: Dimensões da métrica
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        if not self.enabled:
            logger.debug(f"Métrica não enviada (CloudWatch desabilitado): {metric_name}={value}")
            return False
        
        try:
            metric_data = {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.utcnow()
            }
            
            if dimensions:
                metric_data['Dimensions'] = [
                    {'Name': k, 'Value': v} for k, v in dimensions.items()
                ]
            
            self.cloudwatch.put_metric_data(
                Namespace=self.namespace,
                MetricData=[metric_data]
            )
            
            logger.debug(f"Métrica enviada: {metric_name}={value} {unit}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao enviar métrica {metric_name}: {str(e)}")
            return False
    
    def put_multiple_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        """
        Envia múltiplas métricas de uma vez
        
        Args:
            metrics: Lista de dicionários com dados das métricas
            
        Returns:
            Número de métricas enviadas com sucesso
        """
        if not self.enabled:
            logger.debug(f"Métricas não enviadas (CloudWatch desabilitado): {len(metrics)} métricas")
            return 0
        
        if not metrics:
            return 0
        
        try:
            metric_data = []
            
            for metric in metrics:
                data = {
                    'MetricName': metric['name'],
                    'Value': metric['value'],
                    'Unit': metric.get('unit', 'Count'),
                    'Timestamp': datetime.utcnow()
                }
                
                if 'dimensions' in metric:
                    data['Dimensions'] = [
                        {'Name': k, 'Value': v} for k, v in metric['dimensions'].items()
                    ]
                
                metric_data.append(data)
            
            # CloudWatch aceita máximo 20 métricas por chamada
            sent_count = 0
            for i in range(0, len(metric_data), 20):
                batch = metric_data[i:i+20]
                
                self.cloudwatch.put_metric_data(
                    Namespace=self.namespace,
                    MetricData=batch
                )
                
                sent_count += len(batch)
            
            logger.info(f"Enviadas {sent_count} métricas para CloudWatch")
            return sent_count
            
        except Exception as e:
            logger.error(f"Erro ao enviar métricas múltiplas: {str(e)}")
            return 0
    
    def record_job_execution(self, job_name: str, success: bool, duration_seconds: float, 
                           records_processed: int = 0) -> bool:
        """
        Registra métricas de execução de job
        
        Args:
            job_name: Nome do job
            success: Se o job foi executado com sucesso
            duration_seconds: Duração em segundos
            records_processed: Número de registros processados
            
        Returns:
            True se enviado com sucesso
        """
        dimensions = {'JobName': job_name}
        
        metrics = [
            {
                'name': 'JobExecution',
                'value': 1.0,
                'unit': 'Count',
                'dimensions': dimensions
            },
            {
                'name': 'JobSuccess' if success else 'JobFailure',
                'value': 1.0,
                'unit': 'Count',
                'dimensions': dimensions
            },
            {
                'name': 'JobDuration',
                'value': duration_seconds,
                'unit': 'Seconds',
                'dimensions': dimensions
            }
        ]
        
        if records_processed > 0:
            metrics.append({
                'name': 'RecordsProcessed',
                'value': records_processed,
                'unit': 'Count',
                'dimensions': dimensions
            })
        
        return self.put_multiple_metrics(metrics) > 0
    
    def record_ml_metrics(self, model_name: str, accuracy: float, training_time: float, 
                         predictions_made: int = 0) -> bool:
        """
        Registra métricas de machine learning
        
        Args:
            model_name: Nome do modelo
            accuracy: Acurácia do modelo (0-1)
            training_time: Tempo de treinamento em segundos
            predictions_made: Número de predições feitas
            
        Returns:
            True se enviado com sucesso
        """
        dimensions = {'ModelName': model_name}
        
        metrics = [
            {
                'name': 'ModelAccuracy',
                'value': accuracy * 100,  # Converter para porcentagem
                'unit': 'Percent',
                'dimensions': dimensions
            },
            {
                'name': 'TrainingTime',
                'value': training_time,
                'unit': 'Seconds',
                'dimensions': dimensions
            }
        ]
        
        if predictions_made > 0:
            metrics.append({
                'name': 'PredictionsMade',
                'value': predictions_made,
                'unit': 'Count',
                'dimensions': dimensions
            })
        
        return self.put_multiple_metrics(metrics) > 0
    
    def record_api_metrics(self, endpoint: str, response_time: float, status_code: int) -> bool:
        """
        Registra métricas de API
        
        Args:
            endpoint: Nome do endpoint
            response_time: Tempo de resposta em milissegundos
            status_code: Código de status HTTP
            
        Returns:
            True se enviado com sucesso
        """
        dimensions = {
            'Endpoint': endpoint,
            'StatusCode': str(status_code)
        }
        
        metrics = [
            {
                'name': 'APIRequest',
                'value': 1.0,
                'unit': 'Count',
                'dimensions': {'Endpoint': endpoint}
            },
            {
                'name': 'APIResponseTime',
                'value': response_time,
                'unit': 'Milliseconds',
                'dimensions': {'Endpoint': endpoint}
            }
        ]
        
        # Adicionar métrica específica por status code
        if 200 <= status_code < 300:
            metric_name = 'APISuccess'
        elif 400 <= status_code < 500:
            metric_name = 'APIClientError'
        elif 500 <= status_code < 600:
            metric_name = 'APIServerError'
        else:
            metric_name = 'APIUnknownStatus'
        
        metrics.append({
            'name': metric_name,
            'value': 1.0,
            'unit': 'Count',
            'dimensions': dimensions
        })
        
        return self.put_multiple_metrics(metrics) > 0
    
    def record_data_quality_metrics(self, data_source: str, total_records: int, 
                                   valid_records: int, invalid_records: int) -> bool:
        """
        Registra métricas de qualidade de dados
        
        Args:
            data_source: Fonte dos dados
            total_records: Total de registros
            valid_records: Registros válidos
            invalid_records: Registros inválidos
            
        Returns:
            True se enviado com sucesso
        """
        dimensions = {'DataSource': data_source}
        
        quality_percentage = (valid_records / total_records * 100) if total_records > 0 else 0
        
        metrics = [
            {
                'name': 'DataQuality',
                'value': quality_percentage,
                'unit': 'Percent',
                'dimensions': dimensions
            },
            {
                'name': 'TotalRecords',
                'value': total_records,
                'unit': 'Count',
                'dimensions': dimensions
            },
            {
                'name': 'ValidRecords',
                'value': valid_records,
                'unit': 'Count',
                'dimensions': dimensions
            },
            {
                'name': 'InvalidRecords',
                'value': invalid_records,
                'unit': 'Count',
                'dimensions': dimensions
            }
        ]
        
        return self.put_multiple_metrics(metrics) > 0

# Instância global para uso em toda a aplicação
cloudwatch_metrics = CloudWatchMetrics()

def record_job_execution(job_name: str, success: bool, duration_seconds: float, 
                        records_processed: int = 0) -> bool:
    """Função de conveniência para registrar execução de job"""
    return cloudwatch_metrics.record_job_execution(job_name, success, duration_seconds, records_processed)

def record_ml_metrics(model_name: str, accuracy: float, training_time: float, 
                     predictions_made: int = 0) -> bool:
    """Função de conveniência para registrar métricas de ML"""
    return cloudwatch_metrics.record_ml_metrics(model_name, accuracy, training_time, predictions_made)

def record_api_metrics(endpoint: str, response_time: float, status_code: int) -> bool:
    """Função de conveniência para registrar métricas de API"""
    return cloudwatch_metrics.record_api_metrics(endpoint, response_time, status_code)

def record_data_quality_metrics(data_source: str, total_records: int, 
                               valid_records: int, invalid_records: int) -> bool:
    """Função de conveniência para registrar métricas de qualidade de dados"""
    return cloudwatch_metrics.record_data_quality_metrics(data_source, total_records, valid_records, invalid_records)

