# Guia de Deploy no Render - Projeto Arboviroses

## 📋 Resumo das Adaptações

Este projeto foi adaptado para funcionar no Render com as seguintes melhorias:

### ✅ Banco de Dados PostgreSQL
- Migração de SQLite para PostgreSQL
- Configuração automática via variáveis de ambiente
- Otimizações específicas para PostgreSQL
- Script de inicialização do banco

### ✅ Cron Jobs Automatizados
- 4 serviços de cron jobs configurados
- Coleta automática de dados climáticos (diária)
- Coleta automática de dados InfoDengue (diária)
- Coleta histórica semanal
- Predições mensais

### ✅ Configuração de Produção
- Variáveis de ambiente seguras
- Logs estruturados
- Monitoramento de performance
- Scripts de teste e validação

## 🚀 Passos para Deploy

### 1. Preparar Repositório

```bash
# Fazer commit das mudanças
git add .
git commit -m "Adaptação para Render com PostgreSQL e cron jobs"
git push origin main
```

### 2. Criar Serviços no Render

1. **Acesse o Render Dashboard**: https://dashboard.render.com
2. **Conecte seu repositório GitHub**
3. **Crie um novo Blueprint**: 
   - Clique em "New +"
   - Selecione "Blueprint"
   - Conecte seu repositório
   - O Render detectará automaticamente o `render.yaml`

### 3. Configurar Banco de Dados

O banco PostgreSQL será criado automaticamente conforme configurado no `render.yaml`:

```yaml
databases:
  - name: arboviroses-db
    databaseName: arboviroses
    user: arboviroses_user
```

### 4. Verificar Serviços Criados

Após o deploy, você terá 5 serviços:

1. **arboviroses-backend-final** (Web Service)
   - API principal da aplicação
   - URL: `https://arboviroses-backend-final.onrender.com`

2. **climate-collector-job** (Cron Job)
   - Executa diariamente às 06:00 UTC
   - Coleta dados climáticos

3. **infodengue-collector-job** (Cron Job)
   - Executa diariamente às 07:00 UTC
   - Coleta dados do InfoDengue

4. **historical-collector-job** (Cron Job)
   - Executa semanalmente às segundas 05:00 UTC
   - Coleta dados históricos

5. **monthly-prediction-job** (Cron Job)
   - Executa mensalmente no dia 1 às 08:00 UTC
   - Gera predições

### 5. Inicializar Banco de Dados

Após o primeiro deploy, execute o script de inicialização:

```bash
# No terminal do Render ou localmente com DATABASE_URL configurada
python init_render_db.py
```

### 6. Verificar Funcionamento

1. **Teste a API**:
   ```bash
   curl https://arboviroses-backend-final.onrender.com/api/health
   ```

2. **Verifique os logs dos cron jobs** no dashboard do Render

3. **Monitore a coleta de dados** através dos endpoints da API

## 🔧 Configurações Importantes

### Variáveis de Ambiente

As seguintes variáveis são configuradas automaticamente:

- `DATABASE_URL`: String de conexão PostgreSQL
- `SECRET_KEY`: Chave secreta gerada automaticamente
- `FLASK_ENV`: Definida como "production"

### Horários dos Cron Jobs (UTC)

- **06:00**: Coleta de dados climáticos
- **07:00**: Coleta de dados InfoDengue  
- **05:00 (segundas)**: Coleta histórica
- **08:00 (dia 1)**: Predições mensais

### Endpoints da API

- `GET /api/health` - Status da aplicação
- `GET /api/climate` - Dados climáticos
- `GET /api/arbovirus` - Dados de arboviroses
- `GET /api/predictions` - Predições
- `GET /api/dashboard` - Dashboard
- `GET /api/jobs/status` - Status dos jobs

## 📊 Monitoramento

### Logs

- Acesse os logs de cada serviço no dashboard do Render
- Logs estruturados com timestamps e níveis
- Monitoramento de erros e performance

### Performance

- Métricas de execução dos jobs
- Tempo de resposta da API
- Uso de recursos do banco

### Alertas

Configure alertas no Render para:
- Falhas nos cron jobs
- Erros na API
- Problemas de conectividade com banco

## 🛠️ Manutenção

### Atualizações

```bash
# Para atualizar o código
git push origin main
# O Render fará deploy automaticamente
```

### Backup do Banco

- Configure backup automático no dashboard do Render
- Recomendado: backup diário com retenção de 7 dias

### Monitoramento de Dados

- Verifique regularmente se os jobs estão coletando dados
- Monitore o crescimento das tabelas
- Execute otimizações quando necessário

## 🔍 Troubleshooting

### Problemas Comuns

1. **Cron job não executa**:
   - Verifique logs do serviço
   - Confirme timezone (UTC)
   - Teste script localmente

2. **Erro de conexão com banco**:
   - Verifique se DATABASE_URL está configurada
   - Teste conexão com script de inicialização

3. **API retorna erro 500**:
   - Verifique logs da aplicação
   - Confirme se tabelas foram criadas
   - Teste endpoints individualmente

### Scripts de Diagnóstico

```bash
# Testar configurações
python test_config.py

# Inicializar banco
python init_render_db.py

# Testar job específico
python src/jobs/run_climate_job.py
```

## 📞 Suporte

Para problemas específicos:

1. Verifique logs no dashboard do Render
2. Execute scripts de diagnóstico
3. Consulte documentação do Render
4. Entre em contato com suporte técnico

---

**✅ Projeto adaptado com sucesso para o Render!**

Todos os componentes estão configurados para execução automática e monitoramento contínuo.

