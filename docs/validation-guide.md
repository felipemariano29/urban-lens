# Urban Lens - Guia de Validação Pós-Reestruturação

Este guia verifica se todas as funcionalidades estão operando corretamente após a reestruturação para o layout `apps/infra`.

## Pré-requisitos

- Docker Desktop rodando
- Python 3.12+ instalado
- Node.js 22+ instalado (para frontend local)
- Arquivo `.env` configurado na raiz

---

## 1. Verificar Estrutura de Diretórios

```bash
# Confirmar nova estrutura
ls -la apps/
# Deve mostrar: api/ web/

ls -la infra/
# Deve mostrar: compose/ docker/
```

---

## 2. Instalar Dependências Python

```bash
# Criar/ativar venv
make venv

# Instalar pacote API (novo path)
make install
# Ou manualmente:
# pip install -e "apps/api[dev]"
```

**Verificação:**
```bash
python -c "from urban_lens.api.main import app; print('API OK')"
```

---

## 3. Subir Stack Docker

```bash
# Stack básica (CPU)
make up-cpu

# Verificar containers rodando
make ps
```

**Containers esperados:**
- postgres-db
- pgadmin
- minio-storage
- minio-setup (completed)
- mlflow-server
- milvus-standalone
- attu
- ollama
- ollama-setup (completed)
- rag-api
- urban-lens-web

---

## 4. Verificar Health dos Serviços

```bash
# Ver URLs
make urls
```

**Testar endpoints:**

```bash
# API Health
curl http://localhost:8000/api/v1/health

# MLflow
curl http://localhost:5005/

# MinIO
curl http://localhost:9000/minio/health/live

# Milvus
curl http://localhost:9091/healthz
```

---

## 5. Validar Frontend

**Via Docker:**
```bash
# Acessar no browser
open http://localhost:3000
```

**Localmente (alternativa):**
```bash
make frontend-install
make frontend
# Acessar http://localhost:3000
```

---

## 6. Testar API Key e Autenticação

```bash
# Gerar API key (via pgAdmin ou SQL)
# Ou usar a internal API key do .env

# Testar autenticação
curl -H "X-Api-Key: <sua-api-key>" \
  http://localhost:8000/api/v1/access/me
```

---

## 7. Testar RAG Pipeline

```bash
# Indexar dados (se houver dados Gold)
make index-embeddings-latest

# Testar chat
curl -X POST http://localhost:8000/api/v1/query/chat \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: <sua-api-key>" \
  -d '{"message": "What crimes were reported in January 2024?"}'
```

---

## 8. Validar Observabilidade (Opcional)

```bash
# Subir stack com observabilidade
make up-obs

# Verificar serviços
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3100/ready      # Loki

# Acessar Grafana
open http://localhost:3002
# Login: admin / admin
```

---

## 9. Rodar Testes Automatizados

```bash
# Testes Python
make test

# Ou diretamente
python -m pytest apps/api/tests -v
```

---

## 10. Validar MLflow

```bash
# Acessar UI
make mlflow-url
open http://localhost:5005

# Verificar experimentos (se existirem)
```

---

## 11. Testar Pipelines de Dados

```bash
# Listar snapshots disponíveis
make snapshots

# Processar um snapshot (se houver dados)
make process-snapshot SNAPSHOT_DIR=data/2024-01

# Treinar modelo (se houver dados Gold)
make train-latest
```

---

## 12. Validar Novos Features

### Multi-Corpus (Epic 7)
```bash
# Testar detecção de intent
python -c "
from urban_lens.rag.query_understanding import detect_query_intent, intent_to_corpus
print(detect_query_intent('How does Urban Lens work?'))  # platform_knowledge
print(detect_query_intent('What crimes in London?'))     # generic/crime
print(intent_to_corpus('platform_knowledge'))            # knowledge
"
```

### Métricas Prometheus (Epic 8)
```bash
curl http://localhost:8000/metrics | head -20
```

### API Key Management (Epic 3)
```bash
# Listar keys (requer role admin)
curl -H "X-Api-Key: <admin-key>" \
  http://localhost:8000/api/v1/access/keys
```

---

## Troubleshooting

### Containers não sobem
```bash
make logs
# Verificar erros específicos
make logs-core
```

### API retorna 500
```bash
# Verificar logs da API
docker logs rag-api -f
```

### Frontend não conecta na API
```bash
# Verificar variável de ambiente
docker exec urban-lens-web env | grep API
```

### Milvus não está healthy
```bash
# Verificar logs
docker logs milvus-standalone
# Pode precisar de mais tempo para inicializar
```

### Paths quebrados após reestruturação
```bash
# Verificar PYTHONPATH no Makefile
grep PYTHONPATH Makefile
# Deve apontar para apps/api/src
```

---

## Checklist Final

- [ ] `make up-cpu` sobe todos os containers
- [ ] `make ps` mostra todos healthy
- [ ] API responde em http://localhost:8000/api/v1/health
- [ ] Frontend carrega em http://localhost:3000
- [ ] `make test` passa sem erros
- [ ] Chat RAG funciona (se dados indexados)
- [ ] Métricas expostas em /metrics
- [ ] Grafana acessível (se `make up-obs`)

---

## Comandos Úteis

```bash
make help          # Ver todos os comandos disponíveis
make urls          # Ver URLs dos serviços
make logs          # Ver logs de todos os containers
make down          # Parar containers
make reset         # Reset completo (remove volumes)
```
