# Adaptação do Projeto Arboviroses para Render

## Fase 1: Preparar ambiente e analisar projeto atual
- [x] Extrair e examinar projeto atual
- [x] Analisar estrutura de arquivos
- [x] Examinar configuração atual do Render
- [x] Examinar scheduler de jobs
- [x] Examinar dependências
- [x] Examinar modelos de banco de dados
- [x] Examinar collectors de dados

## Fase 2: Configurar banco de dados PostgreSQL para Render
- [x] Adicionar psycopg2 ao requirements.txt
- [x] Configurar variáveis de ambiente para PostgreSQL
- [x] Atualizar configuração de banco no main.py
- [x] Criar script de inicialização do banco

## Fase 3: Adaptar aplicação para PostgreSQL
- [x] Verificar compatibilidade dos modelos com PostgreSQL
- [x] Ajustar queries específicas se necessário
- [x] Testar migrações de banco

## Fase 4: Configurar cron jobs no Render
- [x] Criar serviços separados para cron jobs
- [x] Configurar render.yaml com múltiplos serviços
- [x] Adaptar scheduler para execução em background
- [x] Configurar variáveis de ambiente compartilhadas

## Fase 5: Testar e validar configurações
- [x] Testar conexão com PostgreSQL
- [x] Validar execução dos jobs
- [x] Verificar logs e monitoramento

## Fase 6: Entregar projeto adaptado ao usuário
- [ ] Documentar mudanças realizadas
- [ ] Criar guia de deploy no Render
- [ ] Entregar arquivos atualizados

