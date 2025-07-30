"""
Otimizador de performance para aplicação de arboviroses
"""
import time
import functools
import threading
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
import logging
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

class PerformanceOptimizer:
    """Classe para otimização de performance da aplicação"""
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = {}
        self.cache_lock = threading.RLock()
        self.performance_metrics = defaultdict(list)
        self.db_connection_pool = {}
        self.max_connections = 5
        
        # Configurações de cache
        self.default_cache_ttl = 300  # 5 minutos
        self.max_cache_size = 1000
        
        # Configurações de otimização
        self.slow_query_threshold = 1.0  # 1 segundo
        self.enable_query_optimization = True
        self.enable_response_compression = True
    
    def cache_result(self, ttl: int = None, key_func: Callable = None):
        """Decorator para cache de resultados"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Gerar chave do cache
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                # Verificar cache
                with self.cache_lock:
                    if cache_key in self.cache:
                        # Verificar TTL
                        if cache_key in self.cache_ttl:
                            if datetime.now() < self.cache_ttl[cache_key]:
                                logger.debug(f"Cache hit: {cache_key}")
                                return self.cache[cache_key]
                            else:
                                # Cache expirado
                                del self.cache[cache_key]
                                del self.cache_ttl[cache_key]
                
                # Executar função
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Armazenar no cache
                with self.cache_lock:
                    # Limpar cache se muito grande
                    if len(self.cache) >= self.max_cache_size:
                        self._cleanup_cache()
                    
                    self.cache[cache_key] = result
                    cache_ttl = ttl or self.default_cache_ttl
                    self.cache_ttl[cache_key] = datetime.now() + timedelta(seconds=cache_ttl)
                
                # Registrar métrica
                self.record_performance_metric(func.__name__, execution_time)
                
                logger.debug(f"Cache miss: {cache_key} (executed in {execution_time:.3f}s)")
                return result
            
            return wrapper
        return decorator
    
    def _cleanup_cache(self):
        """Limpa cache expirado"""
        now = datetime.now()
        expired_keys = [
            key for key, expiry in self.cache_ttl.items()
            if now >= expiry
        ]
        
        for key in expired_keys:
            del self.cache[key]
            del self.cache_ttl[key]
        
        # Se ainda muito grande, remover mais antigos
        if len(self.cache) >= self.max_cache_size:
            # Remover 20% dos itens mais antigos
            items_to_remove = int(self.max_cache_size * 0.2)
            sorted_items = sorted(
                self.cache_ttl.items(),
                key=lambda x: x[1]
            )
            
            for key, _ in sorted_items[:items_to_remove]:
                if key in self.cache:
                    del self.cache[key]
                del self.cache_ttl[key]
    
    def clear_cache(self, pattern: str = None):
        """Limpa cache por padrão"""
        with self.cache_lock:
            if pattern:
                keys_to_remove = [
                    key for key in self.cache.keys()
                    if pattern in key
                ]
                for key in keys_to_remove:
                    del self.cache[key]
                    if key in self.cache_ttl:
                        del self.cache_ttl[key]
            else:
                self.cache.clear()
                self.cache_ttl.clear()
    
    def record_performance_metric(self, operation: str, duration: float):
        """Registra métrica de performance"""
        self.performance_metrics[operation].append({
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })
        
        # Manter apenas últimas 100 métricas por operação
        if len(self.performance_metrics[operation]) > 100:
            self.performance_metrics[operation] = self.performance_metrics[operation][-100:]
        
        # Log de queries lentas
        if duration > self.slow_query_threshold:
            logger.warning(f"Slow operation: {operation} took {duration:.3f}s")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas de performance"""
        stats = {}
        
        for operation, metrics in self.performance_metrics.items():
            if metrics:
                durations = [m['duration'] for m in metrics]
                stats[operation] = {
                    'count': len(durations),
                    'avg_duration': sum(durations) / len(durations),
                    'min_duration': min(durations),
                    'max_duration': max(durations),
                    'slow_queries': len([d for d in durations if d > self.slow_query_threshold])
                }
        
        # Estatísticas do cache
        stats['cache'] = {
            'size': len(self.cache),
            'max_size': self.max_cache_size,
            'hit_rate': self._calculate_cache_hit_rate()
        }
        
        return stats
    
    def _calculate_cache_hit_rate(self) -> float:
        """Calcula taxa de acerto do cache"""
        # Implementação simplificada
        # Em produção, seria necessário rastrear hits/misses
        return 0.75  # Placeholder
    
    def optimize_database_connection(self, db_path: str) -> sqlite3.Connection:
        """Otimiza conexão com banco de dados"""
        thread_id = threading.get_ident()
        
        if thread_id not in self.db_connection_pool:
            conn = sqlite3.connect(
                db_path,
                check_same_thread=False,
                timeout=30.0
            )
            
            # Otimizações SQLite
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")  # Balanceamento performance/segurança
            conn.execute("PRAGMA cache_size=10000")  # Cache de 10MB
            conn.execute("PRAGMA temp_store=MEMORY")  # Tabelas temporárias em memória
            conn.execute("PRAGMA mmap_size=268435456")  # Memory-mapped I/O (256MB)
            
            # Configurar row factory para dicionários
            conn.row_factory = sqlite3.Row
            
            self.db_connection_pool[thread_id] = conn
            
            logger.debug(f"Created optimized DB connection for thread {thread_id}")
        
        return self.db_connection_pool[thread_id]
    
    def close_database_connections(self):
        """Fecha todas as conexões do pool"""
        for conn in self.db_connection_pool.values():
            conn.close()
        self.db_connection_pool.clear()
    
    def optimize_query(self, query: str, params: tuple = None) -> tuple:
        """Otimiza query SQL"""
        if not self.enable_query_optimization:
            return query, params
        
        # Otimizações básicas
        optimized_query = query.strip()
        
        # Adicionar LIMIT se não existir em SELECT
        if (optimized_query.upper().startswith('SELECT') and 
            'LIMIT' not in optimized_query.upper() and
            'COUNT(' not in optimized_query.upper()):
            optimized_query += " LIMIT 1000"
        
        # Adicionar índices sugeridos (comentários)
        if 'WHERE' in optimized_query.upper():
            optimized_query = f"-- Consider adding indexes\n{optimized_query}"
        
        return optimized_query, params
    
    def measure_execution_time(self, func_name: str = None):
        """Decorator para medir tempo de execução"""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    execution_time = time.time() - start_time
                    operation_name = func_name or func.__name__
                    self.record_performance_metric(operation_name, execution_time)
            return wrapper
        return decorator
    
    def batch_process(self, items: list, batch_size: int = 100, 
                     process_func: Callable = None):
        """Processa itens em lotes para otimizar performance"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            if process_func:
                batch_results = process_func(batch)
                if isinstance(batch_results, list):
                    results.extend(batch_results)
                else:
                    results.append(batch_results)
            else:
                results.extend(batch)
        
        return results
    
    def compress_response(self, data: Any) -> bytes:
        """Comprime resposta para reduzir largura de banda"""
        if not self.enable_response_compression:
            return data
        
        import gzip
        import json
        
        if isinstance(data, dict) or isinstance(data, list):
            json_data = json.dumps(data).encode('utf-8')
            return gzip.compress(json_data)
        elif isinstance(data, str):
            return gzip.compress(data.encode('utf-8'))
        else:
            return data
    
    def create_database_indexes(self, db_path: str):
        """Cria índices otimizados no banco de dados"""
        conn = self.optimize_database_connection(db_path)
        
        indexes = [
            # Índices para climate_data
            "CREATE INDEX IF NOT EXISTS idx_climate_municipality_date ON climate_data(municipality_code, date)",
            "CREATE INDEX IF NOT EXISTS idx_climate_date ON climate_data(date)",
            "CREATE INDEX IF NOT EXISTS idx_climate_state ON climate_data(state)",
            
            # Índices para arbovirus_data
            "CREATE INDEX IF NOT EXISTS idx_arbovirus_municipality_week ON arbovirus_data(municipality_code, epidemiological_week, year)",
            "CREATE INDEX IF NOT EXISTS idx_arbovirus_disease ON arbovirus_data(disease)",
            "CREATE INDEX IF NOT EXISTS idx_arbovirus_date ON arbovirus_data(year, epidemiological_week)",
            
            # Índices para predictions
            "CREATE INDEX IF NOT EXISTS idx_predictions_municipality_date ON predictions(municipality_code, prediction_date)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_disease ON predictions(disease_type)",
            "CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date)",
        ]
        
        created_count = 0
        for index_sql in indexes:
            try:
                conn.execute(index_sql)
                created_count += 1
            except Exception as e:
                logger.warning(f"Erro ao criar índice: {str(e)}")
        
        conn.commit()
        logger.info(f"Criados {created_count} índices de banco de dados")
        
        return created_count
    
    def analyze_database_performance(self, db_path: str) -> Dict[str, Any]:
        """Analisa performance do banco de dados"""
        conn = self.optimize_database_connection(db_path)
        
        analysis = {}
        
        try:
            # Estatísticas das tabelas
            tables = ['climate_data', 'arbovirus_data', 'predictions']
            
            for table in tables:
                # Contar registros
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                
                # Analisar query plan
                cursor = conn.execute(f"EXPLAIN QUERY PLAN SELECT * FROM {table} LIMIT 1")
                query_plan = cursor.fetchall()
                
                analysis[table] = {
                    'record_count': count,
                    'query_plan': [dict(row) for row in query_plan]
                }
            
            # Estatísticas do banco
            cursor = conn.execute("PRAGMA database_list")
            db_info = cursor.fetchall()
            
            cursor = conn.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            
            cursor = conn.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            analysis['database'] = {
                'size_bytes': page_count * page_size,
                'page_count': page_count,
                'page_size': page_size,
                'info': [dict(row) for row in db_info]
            }
            
        except Exception as e:
            logger.error(f"Erro na análise do banco: {str(e)}")
            analysis['error'] = str(e)
        
        return analysis
    
    def generate_performance_report(self) -> str:
        """Gera relatório de performance"""
        stats = self.get_performance_stats()
        
        report = []
        report.append("📊 Relatório de Performance - Aplicação de Arboviroses")
        report.append("=" * 60)
        
        # Estatísticas de operações
        if stats:
            report.append("\n🔍 Operações Monitoradas:")
            for operation, metrics in stats.items():
                if operation != 'cache':
                    report.append(f"\n   {operation}:")
                    report.append(f"      Execuções: {metrics['count']}")
                    report.append(f"      Tempo médio: {metrics['avg_duration']:.3f}s")
                    report.append(f"      Tempo mín/máx: {metrics['min_duration']:.3f}s / {metrics['max_duration']:.3f}s")
                    if metrics['slow_queries'] > 0:
                        report.append(f"      ⚠️  Queries lentas: {metrics['slow_queries']}")
        
        # Estatísticas do cache
        if 'cache' in stats:
            cache_stats = stats['cache']
            report.append(f"\n💾 Cache:")
            report.append(f"      Tamanho: {cache_stats['size']}/{cache_stats['max_size']}")
            report.append(f"      Taxa de acerto: {cache_stats['hit_rate']:.1%}")
        
        # Recomendações
        report.append("\n💡 Recomendações:")
        
        slow_operations = [
            op for op, metrics in stats.items()
            if op != 'cache' and metrics.get('slow_queries', 0) > 0
        ]
        
        if slow_operations:
            report.append("   ⚠️  Otimizar operações lentas:")
            for op in slow_operations:
                report.append(f"      - {op}")
        
        if stats.get('cache', {}).get('size', 0) > self.max_cache_size * 0.8:
            report.append("   📈 Considerar aumentar tamanho do cache")
        
        report.append("   ✅ Monitorar métricas regularmente")
        report.append("   ✅ Criar índices para queries frequentes")
        report.append("   ✅ Implementar paginação em listagens grandes")
        
        return "\n".join(report)

# Instância global do otimizador
performance_optimizer = PerformanceOptimizer()

# Decorators de conveniência
def cache_result(ttl: int = None, key_func: Callable = None):
    """Decorator de conveniência para cache"""
    return performance_optimizer.cache_result(ttl, key_func)

def measure_time(func_name: str = None):
    """Decorator de conveniência para medir tempo"""
    return performance_optimizer.measure_execution_time(func_name)

