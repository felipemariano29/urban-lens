# Urban Lens - Setup Completo para Agentes

## Objetivo

Este documento existe para que qualquer membro do time possa pedir ao seu agente de codigo para ler este arquivo e executar o setup completo do projeto, deixando o ambiente local pronto para subir, validar e rodar o fluxo principal do Urban Lens.

Este runbook substitui ambiguidades de outros documentos e concentra o caminho mais confiavel para ambiente local em Windows.

## Escopo do setup

Ao final deste processo, o ambiente deve estar com:

- stack Docker subida
- API FastAPI operacional
- frontend Next.js operacional
- PostgreSQL, MinIO, MLflow, Milvus, Attu e Ollama funcionando
- pacote Python da API instalado localmente
- testes Python executados
- smoke test do pipeline realizado com snapshot local
- embeddings indexados no Milvus
- treinamento baseline executado no MLflow

Para reduzir erros de primeira execucao, o setup recomendado passa por um snapshot demo pequeno e deterministico antes de qualquer tentativa de consulta no frontend.

## Fonte de verdade

Para setup local, priorizar estes arquivos:

- `Makefile`
- `infra/compose/docker-compose.yml`
- `.env.example`
- `apps/api/pyproject.toml`
- este documento

Se outro documento contradizer este runbook, siga este runbook e valide o comportamento no codigo.

## Instrucoes para qualquer agente

Se voce for um agente executando este setup:

1. Verifique a arvore Git antes de qualquer alteracao.
2. Nao sobrescreva `.env` existente sem confirmar o conteudo atual.
3. Se `.env` nao existir, crie-o a partir de `.env.example` e preencha com os valores de desenvolvimento fornecidos pela equipe.
4. Execute os comandos na ordem indicada.
5. Se algum comando falhar por permissao, rede, Docker ou download de dependencias, tente diagnosticar e corrigir antes de parar.
6. So considere o setup concluido quando os servicos estiverem saudaveis, os testes passarem e o smoke test principal tiver sido executado.
7. Registre claramente quais passos foram executados, quais falharam e o estado final do ambiente.
8. Se encontrar divergencia entre documentacao e codigo, priorize o codigo e este runbook.

## Modelo de comportamento esperado do agente

O agente deve atuar com este contrato operacional:

1. Ler este arquivo por completo antes de executar comandos.
2. Verificar o estado atual do repositorio e do ambiente local.
3. Confirmar se existe `.env` valido.
4. Executar o setup de forma incremental, validando cada etapa antes da proxima.
5. Em caso de falha, tentar diagnostico objetivo com logs, status de containers e mensagens de erro.
6. Nao declarar sucesso parcial como setup concluido.

## Pre-requisitos obrigatorios

Antes de comecar, a maquina local precisa ter:

- Windows com PowerShell
- Docker Desktop instalado e rodando
- backend Linux/WSL2 ativo no Docker Desktop
- Git for Windows instalado
- `make` disponivel no terminal
- Python `3.11+`
- Node.js `22+` apenas se for rodar frontend fora do Docker
- acesso a internet para baixar imagens Docker e modelos do Ollama na primeira subida

## Observacao importante sobre Windows

O `Makefile` usa `C:/PROGRA~1/Git/bin/bash.exe` quando detecta Windows. Isso significa que o Git for Windows precisa estar instalado. Se `make` falhar logo no inicio com erro de shell, verifique a instalacao do Git.

## Variaveis de ambiente

### Regra

Nao commitar `.env` com segredos no repositorio.

### Como obter o `.env`

Use uma destas opcoes:

1. Receber o `.env` de desenvolvimento compartilhado pela equipe.
2. Criar `.env` a partir de `.env.example` e preencher os valores de desenvolvimento informados pelo grupo.

### Variaveis esperadas

O `.env` precisa contemplar pelo menos:

- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_HOST_PORT`
- `MINIO_ROOT_USER`
- `MINIO_ROOT_PASSWORD`
- `MINIO_DEFAULT_BUCKET`
- `MINIO_API_HOST_PORT`
- `MINIO_CONSOLE_HOST_PORT`
- `URBAN_LENS_S3_ENDPOINT_URL`
- `URBAN_LENS_S3_ACCESS_KEY`
- `URBAN_LENS_S3_SECRET_KEY`
- `URBAN_LENS_S3_BUCKET`
- `URBAN_LENS_S3_REGION`
- `URBAN_LENS_S3_SECURE`
- `URBAN_LENS_POSTGRES_DSN`
- `URBAN_LENS_ARTIFACT_DIR`
- `MLFLOW_TRACKING_URI`
- `MLFLOW_HOST_PORT`
- `PGADMIN_DEFAULT_EMAIL`
- `PGADMIN_DEFAULT_PASSWORD`
- `PGADMIN_HOST_PORT`
- `RAG_API_HOST_PORT`
- `MILVUS_GRPC_PORT`
- `MILVUS_REST_PORT`
- `URBAN_LENS_MILVUS_URI`
- `OLLAMA_HOST_PORT`
- `OLLAMA_NUM_PARALLEL`
- `URBAN_LENS_OLLAMA_BASE_URL`
- `URBAN_LENS_EMBEDDING_MODEL`
- `URBAN_LENS_CHAT_MODEL`
- `OLLAMA_MODELS`
- `URBAN_LENS_JWT_SECRET`
- `URBAN_LENS_INTERNAL_API_KEY`

### Variaveis recomendadas, embora nem sempre aparecam no exemplo

Estas ajudam a evitar comportamento de fallback inseguro ou inconsistente:

- `URBAN_LENS_WEB_SESSION_SECRET`
- `URBAN_LENS_CORS_ORIGINS`

## Ordem oficial de execucao

Execute tudo a partir da raiz do repositorio.

### 1. Validar a arvore Git

```powershell
git status --short
```

Esperado:

- sem alteracoes pendentes relacionadas ao setup

### 2. Garantir que o `.env` exista

Se nao existir:

```powershell
Copy-Item .env.example .env
```

Depois disso, preencher os valores de desenvolvimento compartilhados pela equipe.

### 3. Criar ambiente virtual Python local

```powershell
make venv
```

### 4. Instalar dependencias Python da API

```powershell
make install
```

Observacao:

- o comando correto instala `apps/api[dev]`
- nao use `pip install -e ".[dev]"` na raiz, porque o pacote Python do projeto esta em `apps/api`

### 5. Subir a stack Docker

Modo padrao recomendado:

```powershell
make up-cpu
```

Se houver suporte real a GPU e necessidade de Ollama com GPU:

```powershell
make up-gpu
```

### 6. Verificar status dos containers

```powershell
make ps
make urls
```

Containers esperados:

- `postgres-db`
- `postgres-setup`
- `pgadmin`
- `minio-storage`
- `minio-setup`
- `mlflow-server`
- `milvus-standalone`
- `attu`
- `ollama`
- `ollama-setup`
- `rag-api`
- `urban-lens-web`

Observacoes:

- `postgres-setup`, `minio-setup` e `ollama-setup` podem aparecer como finalizados com sucesso
- na primeira subida, `ollama-setup` pode demorar varios minutos porque baixa modelos

### 7. Inspecionar logs se algum servico nao ficar saudavel

```powershell
make logs-core
```

Se necessario:

```powershell
make logs-app
make logs
```

### 8. Validar endpoints principais

Verificacoes minimas:

```powershell
curl http://localhost:8000/api/v1/health
curl http://localhost:5005/
curl http://localhost:9091/healthz
```

Validacao manual por navegador:

- Frontend: `http://localhost:3000`
- Swagger: `http://localhost:8000/docs`
- MLflow: `http://localhost:5005`
- MinIO Console: `http://localhost:9003`
- Attu: `http://localhost:3001`
- pgAdmin: `http://localhost:5050`

### 9. Rodar testes Python

```powershell
make test
```

### 10. Executar smoke test do pipeline com dados locais

Usar o alvo dedicado de demo:

```powershell
make demo-rag-setup ACTOR=smoke-test
```

Por padrao, esse alvo usa:

- `DEMO_SNAPSHOT_DIR=data/demo-2026-01`
- `DEMO_VERSION=2026-01`

Esse passo deve:

- processar apenas os CSVs suportados da familia `street`
- registrar metadados no PostgreSQL
- publicar artefatos Bronze, Silver e Gold no MinIO
- localizar o `crime_chunks` Gold correspondente ao demo ingerido
- gerar embeddings com Ollama
- publicar vetores no Milvus

Se for necessario usar outro snapshot demo:

```powershell
make demo-rag-setup DEMO_SNAPSHOT_DIR=data/demo-2025-06 DEMO_VERSION=2025-06 ACTOR=smoke-test
```

### 11. Indexar documentacao no Milvus

```powershell
make index-docs ACTOR=smoke-test
```

### 12. Rodar treinamento baseline e publicar no MLflow

```powershell
make train-latest ACTOR=smoke-test
```

### 13. Confirmar que o ambiente esta pronto

Checklist final:

- `make ps` sem servicos principais quebrados
- `GET /api/v1/health` responde `200` ou `207`
- frontend abre em `http://localhost:3000`
- Swagger abre em `http://localhost:8000/docs`
- `make test` passa
- `make demo-rag-setup` conclui com sucesso
- `make train-latest` conclui com sucesso
- MLflow mostra runs
- Attu consegue visualizar colecoes do Milvus

## URLs esperadas por padrao

- Frontend: `http://localhost:3000`
- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- pgAdmin: `http://localhost:5050`
- MinIO API: `http://localhost:9012`
- MinIO Console: `http://localhost:9003`
- MLflow: `http://localhost:5005`
- Milvus gRPC: `localhost:19530`
- Milvus REST: `http://localhost:9091`
- Attu: `http://localhost:3001`
- Ollama: `http://localhost:11434`

## Comandos uteis

### Subir ambiente

```powershell
make up
make up-cpu
make up-gpu
```

### Derrubar ambiente

```powershell
make down
make destroy
```

### Resetar ambiente completamente

```powershell
make reset
```

Atencao:

- `make reset` remove volumes e apaga dados locais de containers

### Ver logs

```powershell
make logs
make logs-core
make logs-app
make logs-mlflow
```

### Rodar frontend local fora do Docker

```powershell
make frontend-install
make frontend
```

## Troubleshooting objetivo

### Erro: `.env` nao encontrado

Acao:

```powershell
Copy-Item .env.example .env
```

Depois preencher os valores corretos da equipe.

### Erro: Docker Engine indisponivel

Acao:

- abrir Docker Desktop
- esperar o engine ficar pronto
- confirmar backend Linux/WSL2 ativo

### Erro: `make` falha no Windows com shell inexistente

Acao:

- instalar Git for Windows
- reiniciar terminal

### Erro: `ollama-setup` falha

Causas comuns:

- sem internet
- download interrompido
- modelo indisponivel
- pouco espaco em disco

Acao:

```powershell
make logs-core
```

Se o problema persistir, validar:

- se o container `ollama` esta saudavel
- se `OLLAMA_MODELS` no `.env` esta correto

### Erro: API sobe mas health retorna degradado

Isso significa que a API respondeu, mas alguma dependencia falhou.

Validar:

- PostgreSQL
- Ollama
- Milvus

Comandos:

```powershell
make ps
make logs-core
```

### Erro: testes Python falham por import

Acao:

```powershell
make install
```

Conferir tambem:

- Python `3.11+`
- ambiente virtual criado corretamente

### Erro: pipeline falha apos infraestrutura subir

Conferir no `.env`:

- `URBAN_LENS_POSTGRES_DSN`
- `URBAN_LENS_S3_ENDPOINT_URL`
- `URBAN_LENS_S3_BUCKET`
- `MLFLOW_TRACKING_URI`
- `URBAN_LENS_MILVUS_URI`
- `URBAN_LENS_OLLAMA_BASE_URL`

### Erro: frontend abre, mas ao perguntar aparece `API RAG indisponivel`

Esse e o sintoma mais comum quando a stack sobe, mas o RAG ainda nao esta pronto.

Causas mais provaveis:

- snapshot demo nao foi ingerido
- `crime_chunks` ainda nao foi indexado no Milvus
- Ollama nao terminou de baixar os modelos
- API foi iniciada sem as variaveis de ambiente corretas

Acao recomendada:

```powershell
make demo-rag-setup ACTOR=smoke-test
make logs-core
curl http://localhost:8000/api/v1/health
```

Conferir especialmente:

- se `rag_embedder` esta `ok`
- se `rag_vector_store` esta `ok`
- se o `ollama-setup` terminou com sucesso
- se existe a colecao `crime_chunks` no Attu

### Erro: frontend abre mas nao conversa com a API

Validar:

- `rag-api` esta healthy
- frontend depende de `URBAN_LENS_API_BASE_URL`
- no Docker, o valor interno deve apontar para `http://rag-api:8000`

## Observacoes sobre autenticacao

Para o setup da stack e do pipeline, o mais importante e que estas variaveis existam no `.env`:

- `URBAN_LENS_JWT_SECRET`
- `URBAN_LENS_INTERNAL_API_KEY`

Sem isso, partes do fluxo autenticado ou integracoes internas podem ficar inconsistentes.

## Rota correta para chat

Se for testar o endpoint de chat diretamente na API, use:

```text
POST /api/v1/chat/query
```

Nao usar:

```text
/api/v1/query/chat
```

## Criterio de conclusao

Considere o setup completo apenas quando:

1. a stack estiver subida e saudavel
2. os testes Python passarem
3. o `make demo-rag-setup` tiver sido executado com sucesso
4. os embeddings demo tiverem sido indexados
5. o treinamento baseline tiver sido executado
6. frontend e Swagger estiverem acessiveis

## Resultado esperado

Ao final, o projeto deve estar pronto para:

- demonstracao local da plataforma
- inspecao da API via Swagger
- consulta pelo frontend
- validacao de embeddings no Milvus via Attu
- validacao de experimentos no MLflow
- execucao do pipeline governado Bronze -> Silver -> Gold
