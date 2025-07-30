"""
Otimizador de performance específico para PostgreSQL
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class PostgreSQLOptimizer:
    """Classe para otimização específica do PostgreSQL"""
    
    def __init__(self):
        self.database_url = os.getenv('DATABASE_URL')
        
    def get_connection(self):
        """Obtém conexão otimizada com PostgreSQL"""
        if not self.database_url:
            raise ValueError("DATABASE_URL não configurada")
        
        # Parse da URL
        parsed = urlparse(self.database_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=parsed.path[1:],  # Remove '/' inicial
            user=parsed.username,
            password=parsed.password,
            cursor_factory=RealDictCursor,
            connect_timeout=30
        )
        
        # Configurações de otimização
        with conn.cursor() as cur:
            # Configurar timezone
            cur.execute("SET timezone = 'UTC'")
            
            # Otimizações de performance
            cur.execute("SET work_mem = '256MB'")  # Memória para operações de ordenação
            cur.execute("SET maintenance_work_mem = '512MB'")  # Memória para manutenção
            cur.execute("SET effective_cache_size = '1GB'")  # Cache estimado do sistema
            
        conn.commit()
        return conn
    
    def create_indexes(self):
        """Cria índices otimizados para PostgreSQL"""
        indexes = [
            # Índices para climate_data
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_climate_municipality_date 
               ON climate_data(municipality_code, date)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_climate_date 
               ON climate_data(date)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_climate_state 
               ON climate_data(state)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_climate_created_at 
               ON climate_data(created_at)""",
            
            # Índices para arbovirus_data
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_arbovirus_municipality_week 
               ON arbovirus_data(municipality_code, epidemiological_week, year)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_arbovirus_disease 
               ON arbovirus_data(disease_type)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_arbovirus_year_week 
               ON arbovirus_data(year, epidemiological_week)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_arbovirus_created_at 
               ON arbovirus_data(created_at)""",
            
            # Índices para predictions
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_municipality_date 
               ON predictions(municipality_code, prediction_date)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_disease 
               ON predictions(disease_type)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_date 
               ON predictions(prediction_date)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_predictions_created_at 
               ON predictions(created_at)""",
            
            # Índices compostos para queries comuns
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_climate_state_date 
               ON climate_data(state, date)""",
            """CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_arbovirus_state_disease_year 
               ON arbovirus_data(state, disease_type, year)""",
        ]
        
        created_count = 0
        
        try:
            conn = self.get_connection()
            
            for index_sql in indexes:
                try:
                    with conn.cursor() as cur:
                        cur.execute(index_sql)
                    conn.commit()
                    created_count += 1
                    logger.info(f"Índice criado com sucesso")
                except psycopg2.Error as e:
                    logger.warning(f"Erro ao criar índice: {str(e)}")
                    conn.rollback()
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Erro ao conectar com banco: {str(e)}")
        
        logger.info(f"Criados {created_count} índices PostgreSQL")
        return created_count
    
    def analyze_performance(self) -> Dict[str, Any]:
        """Analisa performance do PostgreSQL"""
        analysis = {}
        
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cur:
                # Estatísticas das tabelas
                tables = ['climate_data', 'arbovirus_data', 'predictions', 'user']
                
                for table in tables:
                    try:
                        # Contar registros
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cur.fetchone()[0]
                        
                        # Tamanho da tabela
                        cur.execute(f"""
                            SELECT pg_size_pretty(pg_total_relation_size('{table}')) as size,
                                   pg_total_relation_size('{table}') as size_bytes
                        """)
                        size_info = cur.fetchone()
                        
                        # Estatísticas da tabela
                        cur.execute(f"""
                            SELECT schemaname, tablename, attname, n_distinct, correlation
                            FROM pg_stats 
                            WHERE tablename = '{table}'
                            LIMIT 5
                        """)
                        stats = cur.fetchall()
                        
                        analysis[table] = {
                            'record_count': count,
                            'size': size_info['size'] if size_info else 'N/A',
                            'size_bytes': size_info['size_bytes'] if size_info else 0,
                            'column_stats': [dict(row) for row in stats]
                        }
                        
                    except psycopg2.Error as e:
                        logger.warning(f"Erro ao analisar tabela {table}: {str(e)}")
                        analysis[table] = {'error': str(e)}
                
                # Informações do banco
                cur.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size,
                           pg_database_size(current_database()) as db_size_bytes
                """)
                db_size = cur.fetchone()
                
                # Configurações importantes
                cur.execute("""
                    SELECT name, setting, unit, context 
                    FROM pg_settings 
                    WHERE name IN ('shared_buffers', 'work_mem', 'maintenance_work_mem', 
                                   'effective_cache_size', 'max_connections')
                """)
                settings = cur.fetchall()
                
                # Índices existentes
                cur.execute("""
                    SELECT schemaname, tablename, indexname, indexdef
                    FROM pg_indexes 
                    WHERE schemaname = 'public'
                    ORDER BY tablename, indexname
                """)
                indexes = cur.fetchall()
                
                analysis['database'] = {
                    'size': db_size['db_size'] if db_size else 'N/A',
                    'size_bytes': db_size['db_size_bytes'] if db_size else 0,
                    'settings': [dict(row) for row in settings],
                    'indexes': [dict(row) for row in indexes]
                }
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Erro na análise do PostgreSQL: {str(e)}")
            analysis['error'] = str(e)
        
        return analysis
    
    def optimize_queries(self):
        """Executa otimizações de queries no PostgreSQL"""
        optimizations = [
            # Atualizar estatísticas
            "ANALYZE",
            
            # Vacuum para limpeza
            "VACUUM (ANALYZE)",
        ]
        
        try:
            conn = self.get_connection()
            conn.autocommit = True  # Necessário para VACUUM
            
            with conn.cursor() as cur:
                for optimization in optimizations:
                    try:
                        cur.execute(optimization)
                        logger.info(f"Otimização executada: {optimization}")
                    except psycopg2.Error as e:
                        logger.warning(f"Erro na otimização '{optimization}': {str(e)}")
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Erro ao executar otimizações: {str(e)}")
    
    def check_connection(self) -> bool:
        """Verifica se a conexão com PostgreSQL está funcionando"""
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
            
            conn.close()
            
            return result[0] == 1
            
        except Exception as e:
            logger.error(f"Erro ao verificar conexão: {str(e)}")
            return False
    
    def generate_performance_report(self) -> str:
        """Gera relatório de performance do PostgreSQL"""
        analysis = self.analyze_performance()
        
        report = []
        report.append("📊 Relatório de Performance - PostgreSQL")
        report.append("=" * 50)
        
        # Informações do banco
        if 'database' in analysis and 'error' not in analysis['database']:
            db_info = analysis['database']
            report.append(f"\n💾 Banco de Dados:")
            report.append(f"   Tamanho: {db_info['size']}")
            report.append(f"   Índices: {len(db_info['indexes'])}")
        
        # Estatísticas das tabelas
        report.append(f"\n📋 Tabelas:")
        for table, info in analysis.items():
            if table != 'database' and 'error' not in info:
                report.append(f"   {table}:")
                report.append(f"      Registros: {info['record_count']:,}")
                report.append(f"      Tamanho: {info['size']}")
        
        # Recomendações
        report.append(f"\n💡 Recomendações:")
        report.append("   ✅ Executar ANALYZE regularmente")
        report.append("   ✅ Monitorar crescimento das tabelas")
        report.append("   ✅ Verificar uso dos índices")
        report.append("   ✅ Configurar backup automático")
        
        return "\n".join(report)

# Instância global
postgres_optimizer = PostgreSQLOptimizer()

