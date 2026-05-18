ifeq ($(OS),Windows_NT)
    SHELL := C:/Windows/System32/bash.exe
    SYSTEM_PYTHON ?= python
else
    SHELL := /bin/bash
    SYSTEM_PYTHON ?= python3
endif
PYTHON ?= $(shell if [ -x .venv/bin/python3 ]; then echo .venv/bin/python3; elif [ -x .venv/bin/python ]; then echo .venv/bin/python; elif [ -x .venv/Scripts/python.exe ]; then echo .venv/Scripts/python; else echo $(SYSTEM_PYTHON); fi)
PIP_CONFIG_FILE ?= /dev/null
PIP_INDEX_URL ?= https://pypi.org/simple
SOURCE_NAME ?= data.police.uk
ACTOR ?= system
VERSION ?=
ENV_EXPORT = __MLFLOW_TRACKING_URI="$${MLFLOW_TRACKING_URI:-}"; \
	__MLFLOW_HOST_PORT="$${MLFLOW_HOST_PORT:-}"; \
	set -a; . ./.env; set +a; \
	if [ -n "$$__MLFLOW_TRACKING_URI" ]; then export MLFLOW_TRACKING_URI="$$__MLFLOW_TRACKING_URI"; fi; \
	if [ -n "$$__MLFLOW_HOST_PORT" ]; then export MLFLOW_HOST_PORT="$$__MLFLOW_HOST_PORT"; fi;
PYTHON_RUN = $(ENV_EXPORT) PYTHONPATH="$(CURDIR)/src:$${PYTHONPATH:-}"
PIP_RUN = PIP_CONFIG_FILE="$(PIP_CONFIG_FILE)" PIP_INDEX_URL="$(PIP_INDEX_URL)"

ifeq ($(OS),Windows_NT)
	COMPOSE := docker compose
else
	COMPOSE := $(shell \
		if command -v podman-compose >/dev/null 2>&1; then \
			echo "podman-compose"; \
		elif command -v docker-compose >/dev/null 2>&1; then \
			echo "docker-compose"; \
		elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then \
			echo "docker compose"; \
		else \
			echo ""; \
		fi)
endif
COMPOSE_MODE ?= cpu
COMPOSE_FILES := -f docker-compose.yml
ifeq ($(COMPOSE_MODE),gpu)
	COMPOSE_FILES += -f docker-compose.gpu.yml
endif
ifeq ($(COMPOSE_MODE),obs)
	COMPOSE_FILES += -f docker-compose.observability.yml
endif
ifeq ($(COMPOSE_MODE),full)
	COMPOSE_FILES += -f docker-compose.observability.yml
endif
DOCKER_ENGINE_OK := $(shell docker info >/dev/null 2>&1 && echo 1 || echo 0)

.PHONY: help check-compose check-docker-engine check-env check-python require-% venv install setup fullstack urls up up-cpu up-gpu up-obs up-full up-core down destroy reset logs logs-core logs-app logs-mlflow logs-obs ps snapshots ingest ingest-all ingest-year ingest-file ingest-manual process-snapshot bronze-to-silver silver-to-gold train train-latest train-forecast experiment-forecast mlflow-url index-embeddings index-embeddings-latest index-docs index-mlflow eval-rag test frontend frontend-install

help:
	@printf "\n"
	@printf "\033[1;36m=======================================\033[0m\n"
	@printf "\033[1;32m UrbanLens - Comandos disponiveis\033[0m\n"
	@printf "\033[1;36m=======================================\033[0m\n\n"

	@printf "\033[1;33mDocker\033[0m\n"
	@printf "  \033[1;37mmake fullstack\033[0m -> Subir stack completa no Docker e mostrar URLs\n"
	@printf "  \033[1;37mmake up\033[0m        -> Subir os containers (modo atual: COMPOSE_MODE=$(COMPOSE_MODE))\n"
	@printf "  \033[1;37mmake up-cpu\033[0m    -> Subir a stack completa sem overlay de GPU\n"
	@printf "  \033[1;37mmake up-gpu\033[0m    -> Subir a stack completa com overlay de GPU para Ollama\n"
	@printf "  \033[1;37mmake up-obs\033[0m    -> Subir stack com observabilidade (Prometheus, Grafana, Loki)\n"
	@printf "  \033[1;37mmake up-full\033[0m   -> Subir stack completa com observabilidade\n"
	@printf "  \033[1;37mmake up-core\033[0m   -> Subir Postgres + MinIO + MLflow\n"
	@printf "  \033[1;37mmake down\033[0m      -> Parar containers sem remover estado local\n"
	@printf "  \033[1;37mmake destroy\033[0m   -> Remover containers e rede local\n"
	@printf "  \033[1;37mmake reset\033[0m     -> Reset completo (remove volumes)\n"
	@printf "  \033[1;37mmake logs\033[0m      -> Ver logs de toda a stack em tempo real\n"
	@printf "  \033[1;37mmake logs-core\033[0m -> Ver logs dos servicos principais de dados e backend\n"
	@printf "  \033[1;37mmake logs-app\033[0m  -> Ver logs da aplicacao web e API\n"
	@printf "  \033[1;37mmake logs-obs\033[0m  -> Ver logs da observabilidade (Prometheus, Grafana, Loki)\n\n"

	@printf "\033[1;33mFrontend\033[0m\n"
	@printf "  \033[1;37mmake frontend\033[0m  -> Rodar frontend Next.js localmente fora do Docker\n"
	@printf "  \033[1;37mmake frontend-install\033[0m -> Instalar dependencias do frontend local\n\n"

	@printf "\033[1;33mExperimentos / MLflow\033[0m\n"
	@printf "  \033[1;37mmake train\033[0m     -> Treinar usando os datasets Gold ML mais recentes\n"
	@printf "  \033[1;37mmake train-latest\033[0m [VERSION=2026-01] [ACTOR=system]\n"
	@printf "                      -> Treinar os 3 modelos sem informar ids/keys manualmente\n"
	@printf "  \033[1;37mmake train-forecast \\\033[0mTRAINING_OBJECT_KEY=... TRAINING_DATASET_VERSION_ID=... SCORING_OBJECT_KEY=... SCORING_DATASET_VERSION_ID=...\n"
	@printf "                      -> Treinar os 3 modelos e publicar previsoes\n"
	@printf "  \033[1;37mmake experiment-forecast\033[0m ... -> Alias de train-forecast\n"
	@printf "  \033[1;37mmake logs-mlflow\033[0m       -> Ver logs do MLflow\n"
	@printf "  \033[1;37mmake urls\033[0m      -> Mostrar URLs dos servicos locais\n"
	@printf "  \033[1;37mmake mlflow-url\033[0m        -> Mostrar URL do dashboard MLflow\n\n"

	@printf "\033[1;33mEmbeddings e Indexacao\033[0m\n"
	@printf "  \033[1;37mmake index-embeddings-latest\033[0m [VERSION=2026-01] [ACTOR=system]\n"
	@printf "                      -> Indexar o crime_chunks mais recente no Milvus\n"
	@printf "  \033[1;37mmake index-embeddings\033[0m RAG_OBJECT_KEY=... RAG_DATASET_VERSION_ID=... [ACTOR=system]\n"
	@printf "                      -> Indexar um crime_chunks especifico no Milvus\n"
	@printf "  \033[1;37mmake index-docs\033[0m [DOCS_DIR=docs/] [ACTOR=system]\n"
	@printf "                      -> Indexar todos os Markdowns de docs/ no Milvus\n"
	@printf "  \033[1;37mmake index-mlflow\033[0m [MAX_RUNS=50]\n"
	@printf "                      -> Indexar runs do MLflow no knowledge corpus\n"
	@printf "  \033[1;37mmake eval-rag\033[0m [DATASET=path.json] [TAGS=crime platform] [MLFLOW=1]\n"
	@printf "                      -> Executar avaliacao do RAG e logar no MLflow\n\n"

	@printf "\033[1;33mPipeline de Dados\033[0m\n"
	@printf "  \033[1;37mmake snapshots\033[0m -> Listar snapshots disponiveis em data/\n"
	@printf "  \033[1;37mmake ingest\033[0m SNAPSHOT_DIR=... [ACTOR=system]\n"
	@printf "                      -> Executar pipeline de ingestao de snapshot ate Gold\n"
	@printf "  \033[1;37mmake ingest-all\033[0m [ACTOR=system]\n"
	@printf "                      -> Ingerir todos os snapshots disponiveis em data/\n"
	@printf "  \033[1;37mmake ingest-year\033[0m YEAR=2025 [ACTOR=system]\n"
	@printf "                      -> Ingerir todos os snapshots de um ano especifico\n"
	@printf "  \033[1;37mmake ingest-file\033[0m CSV_PATH=... FORCE_NAME=... [ACTOR=system]\n"
	@printf "                      -> Ingerir um CSV manualmente no Bronze\n"
	@printf "  \033[1;37mmake ingest-manual\033[0m CSV_PATH=... FORCE_NAME=... [SOURCE_NAME=data.police.uk] [ACTOR=system]\n"
	@printf "                      -> Ingerir um CSV manualmente no Bronze\n"
	@printf "  \033[1;37mmake process-snapshot\033[0m SNAPSHOT_DIR=... [SOURCE_NAME=data.police.uk] [ACTOR=system]\n"
	@printf "                      -> Processar um diretorio mensal ate Gold ML/RAG\n"
	@printf "  \033[1;37mmake bronze-to-silver\033[0m BRONZE_OBJECT_KEY=... BRONZE_DATASET_VERSION_ID=... [ACTOR=system]\n"
	@printf "                      -> Transformar Bronze em Silver\n"
	@printf "  \033[1;37mmake silver-to-gold\033[0m SILVER_OBJECT_KEY=... SILVER_DATASET_VERSION_ID=... [ACTOR=system]\n"
	@printf "                      -> Publicar Gold analytics/RAG/ML\n\n"

	@printf "\033[1;33mUtilidades\033[0m\n"
	@printf "  \033[1;37mmake setup\033[0m     -> Criar .venv, instalar dependencias e subir stack\n"
	@printf "  \033[1;37mmake venv\033[0m      -> Criar ambiente virtual local em .venv\n"
	@printf "  \033[1;37mmake install\033[0m   -> Instalar dependencias Python em modo dev\n"
	@printf "  \033[1;37mmake ps\033[0m        -> Mostrar status dos containers\n"
	@printf "  \033[1;37mmake help\033[0m      -> Mostrar esta ajuda\n\n"

	@printf "\033[1;36m=======================================\033[0m\n\n"

check-compose:
ifeq ($(strip $(COMPOSE)),)
	@echo [ERR] Nenhum compose compativel foi encontrado.
	@echo [INFO] Instale o podman-compose com:
	@echo    sudo apt update && sudo apt install podman-compose
	@docker compose version
else ifeq ($(COMPOSE),podman-compose)
	@echo [OK] Usando podman-compose
else ifeq ($(COMPOSE),docker compose)
	@echo [OK] Usando docker compose
else
	@echo [WARN] Usando docker-compose
endif

check-docker-engine:
ifeq ($(DOCKER_ENGINE_OK),1)
	@echo [OK] Docker Engine disponivel.
else
	@echo [ERR] Docker Engine indisponivel.
	@echo [INFO] Inicie o Docker Desktop e aguarde o engine ficar pronto.
	@echo [INFO] No Windows, confirme tambem que o backend Linux/WSL2 esta ativo.
	$(error Docker Engine indisponivel. Inicie o Docker Desktop e tente novamente.)
endif

check-env:
	@if [ ! -f .env ]; then \
		echo "[ERR] Arquivo .env nao encontrado na raiz do projeto."; \
		echo "[INFO] Crie o arquivo em: $$(pwd)/.env"; \
		exit 1; \
	fi
	@echo "[OK] Arquivo .env encontrado."

check-python:
	@if ! command -v "$(PYTHON)" >/dev/null 2>&1; then \
		echo "[ERR] Python nao encontrado: $(PYTHON)"; \
		exit 1; \
	fi
	@echo "[OK] Python encontrado: $(PYTHON)"

require-%:
	@if [ -z "$($*)" ]; then \
		echo "[ERR] Variavel obrigatoria ausente: $*"; \
		exit 1; \
	fi

install: check-python
	@echo "[INFO] Instalando dependencias Python..."
	@$(PIP_RUN) $(PYTHON) -m pip install -e ".[dev]"

venv:
	@if [ -x .venv/bin/python3 ] || [ -x .venv/bin/python ] || [ -x .venv/Scripts/python.exe ]; then \
		echo "[OK] Ambiente virtual .venv ja existe."; \
	else \
		echo "[INFO] Criando ambiente virtual em .venv..."; \
		$(SYSTEM_PYTHON) -m venv .venv; \
	fi

setup:
	@$(MAKE) venv
ifeq ($(OS),Windows_NT)
	@$(MAKE) install PYTHON=.venv/Scripts/python
else
	@$(MAKE) install PYTHON=.venv/bin/python
endif
	@$(MAKE) fullstack

fullstack:
	@$(MAKE) up
	@$(MAKE) urls

up-cpu:
	@$(MAKE) up COMPOSE_MODE=cpu

up-gpu:
	@$(MAKE) up COMPOSE_MODE=gpu

up-obs:
	@$(MAKE) up COMPOSE_MODE=obs

up-full:
	@$(MAKE) up COMPOSE_MODE=full

up: check-compose check-docker-engine check-env
	@echo "[INFO] Subindo containers com COMPOSE_MODE=$(COMPOSE_MODE)..."
	@$(COMPOSE) $(COMPOSE_FILES) up -d

up-core: check-compose check-docker-engine check-env
	@echo "[INFO] Subindo Postgres, MinIO e MLflow com COMPOSE_MODE=$(COMPOSE_MODE)..."
	@$(COMPOSE) $(COMPOSE_FILES) up -d postgres minio minio-setup mlflow

frontend-install:
	@if [ -f package.json ]; then \
		if command -v pnpm >/dev/null 2>&1; then \
			echo "[INFO] Instalando dependencias do frontend com pnpm..."; \
			pnpm install; \
		elif command -v npm >/dev/null 2>&1; then \
			echo "[INFO] Instalando dependencias do frontend com npm..."; \
			npm install; \
		else \
			echo "[ERR] npm ou pnpm nao encontrado. Instale Node.js primeiro."; \
			exit 1; \
		fi; \
	else \
		echo "[WARN] package.json nao encontrado. Pulando instalacao do frontend."; \
	fi

frontend:
	@if [ -f package.json ]; then \
		if command -v pnpm >/dev/null 2>&1; then \
			echo "[INFO] Iniciando frontend Next.js com pnpm..."; \
			pnpm dev; \
		elif command -v npm >/dev/null 2>&1; then \
			echo "[INFO] Iniciando frontend Next.js com npm..."; \
			npm run dev; \
		else \
			echo "[ERR] npm ou pnpm nao encontrado. Instale Node.js primeiro."; \
			exit 1; \
		fi; \
	else \
		echo "[WARN] package.json nao encontrado. Frontend nao disponivel nesta branch."; \
	fi

down: check-compose check-docker-engine check-env
	@echo "[INFO] Parando containers sem remover dados..."
	@$(COMPOSE) $(COMPOSE_FILES) stop

destroy: check-compose check-docker-engine check-env
	@echo "[INFO] Removendo containers e rede local..."
	@$(COMPOSE) $(COMPOSE_FILES) down

reset: check-compose check-docker-engine check-env
	@echo "[INFO] Removendo containers e volumes..."
	@if [ "$(COMPOSE)" = "podman-compose" ]; then \
		$(COMPOSE) $(COMPOSE_FILES) down -v; \
	else \
		$(COMPOSE) $(COMPOSE_FILES) down -v --remove-orphans; \
	fi
	@echo "[INFO] Subindo ambiente limpo..."
	@$(COMPOSE) $(COMPOSE_FILES) up -d --build

logs: check-compose check-docker-engine check-env
	@echo "[INFO] Exibindo logs..."
	@$(COMPOSE) $(COMPOSE_FILES) logs -f

logs-core: check-compose check-docker-engine check-env
	@echo "[INFO] Exibindo logs de postgres, minio, mlflow, milvus, ollama e rag-api..."
	@$(COMPOSE) $(COMPOSE_FILES) logs -f postgres minio mlflow milvus ollama rag-api

logs-app: check-compose check-docker-engine check-env
	@echo "[INFO] Exibindo logs de frontend e rag-api..."
	@$(COMPOSE) $(COMPOSE_FILES) logs -f frontend rag-api

logs-mlflow: check-compose check-docker-engine check-env
	@echo "[INFO] Exibindo logs do MLflow..."
	@$(COMPOSE) $(COMPOSE_FILES) logs -f mlflow

logs-obs: check-compose check-docker-engine check-env
	@echo "[INFO] Exibindo logs da observabilidade (prometheus, grafana, loki)..."
	@$(COMPOSE) -f docker-compose.yml -f docker-compose.observability.yml logs -f prometheus grafana loki promtail

ps: check-compose check-docker-engine check-env
	@$(COMPOSE) $(COMPOSE_FILES) ps

snapshots:
	@if [ ! -d data ]; then \
		echo "[ERR] Diretorio data/ nao encontrado."; \
		exit 1; \
	fi
	@echo "[INFO] Snapshots disponiveis em data/:"
	@find data -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort

urls: check-env
	@$(ENV_EXPORT) \
		echo "pgAdmin:        http://localhost:$${PGADMIN_HOST_PORT:-5050}"; \
	echo "MinIO API:      http://localhost:$${MINIO_API_HOST_PORT:-9000}"; \
	echo "MinIO Console:  http://localhost:$${MINIO_CONSOLE_HOST_PORT:-9001}"; \
		echo "MLflow:         http://localhost:$${MLFLOW_HOST_PORT:-5005}"; \
	echo "Milvus gRPC:    localhost:$${MILVUS_GRPC_PORT:-19530}"; \
	echo "Milvus REST:    http://localhost:$${MILVUS_REST_PORT:-9091}"; \
	echo "Attu:           http://localhost:$${ATTU_HOST_PORT:-3001}"; \
	echo "Ollama:         http://localhost:$${OLLAMA_HOST_PORT:-11434}"; \
	echo "RAG API:        http://localhost:$${RAG_API_HOST_PORT:-8000}"; \
	echo "Frontend:       http://localhost:$${WEB_HOST_PORT:-3000}"

mlflow-url: check-env
	@$(ENV_EXPORT) echo "MLflow: http://localhost:$${MLFLOW_HOST_PORT:-5005}"

ingest: process-snapshot

ingest-all: check-env check-python
	@set -euo pipefail; \
	SNAPSHOTS=$$(find data -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort); \
	if [ -z "$$SNAPSHOTS" ]; then \
		echo "[ERR] Nenhum snapshot encontrado em data/."; \
		exit 1; \
	fi; \
	for snapshot in $$SNAPSHOTS; do \
		echo "[INFO] Ingerindo data/$$snapshot"; \
		$(MAKE) ingest SNAPSHOT_DIR="data/$$snapshot" SOURCE_NAME="$(SOURCE_NAME)" ACTOR="$(ACTOR)" PYTHON="$(PYTHON)"; \
	done

ingest-year: check-env check-python require-YEAR
	@set -euo pipefail; \
	SNAPSHOTS=$$(find data -mindepth 1 -maxdepth 1 -type d -name "$(YEAR)-*" -exec basename {} \; | sort); \
	if [ -z "$$SNAPSHOTS" ]; then \
		echo "[ERR] Nenhum snapshot encontrado para o ano $(YEAR) em data/."; \
		exit 1; \
	fi; \
	for snapshot in $$SNAPSHOTS; do \
		echo "[INFO] Ingerindo data/$$snapshot"; \
		$(MAKE) ingest SNAPSHOT_DIR="data/$$snapshot" SOURCE_NAME="$(SOURCE_NAME)" ACTOR="$(ACTOR)" PYTHON="$(PYTHON)"; \
	done

ingest-file: ingest-manual

ingest-manual: check-env check-python require-CSV_PATH require-FORCE_NAME
	@$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.ingest_manual \
		--csv-path "$(CSV_PATH)" \
		--source-name "$(SOURCE_NAME)" \
		--force-name "$(FORCE_NAME)" \
		--actor "$(ACTOR)"

process-snapshot: check-env check-python require-SNAPSHOT_DIR
	@$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.process_snapshot \
		--snapshot-dir "$(SNAPSHOT_DIR)" \
		--source-name "$(SOURCE_NAME)" \
		--actor "$(ACTOR)"

bronze-to-silver: check-env check-python require-BRONZE_OBJECT_KEY require-BRONZE_DATASET_VERSION_ID
	@$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.bronze_to_silver \
		--bronze-object-key "$(BRONZE_OBJECT_KEY)" \
		--bronze-dataset-version-id "$(BRONZE_DATASET_VERSION_ID)" \
		--actor "$(ACTOR)"

silver-to-gold: check-env check-python require-SILVER_OBJECT_KEY require-SILVER_DATASET_VERSION_ID
	@$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.silver_to_gold \
		--silver-object-key "$(SILVER_OBJECT_KEY)" \
		--silver-dataset-version-id "$(SILVER_DATASET_VERSION_ID)" \
		--actor "$(ACTOR)"

train: train-latest

train-latest: check-env check-python
	@set -euo pipefail; \
	DATASETS=$$($(PYTHON_RUN) TARGET_VERSION="$(VERSION)" $(PYTHON) -c $$'import os\nfrom urban_lens.core.settings import AppConfig\nfrom urban_lens.governance.store import MetadataStore\nconfig = AppConfig.from_env()\nstore = MetadataStore(config.postgres_dsn)\nrequested_version = os.getenv("TARGET_VERSION") or None\ntraining_rows = store.list_dataset_versions(logical_name="forecast_training_set", layer="gold")\nscoring_rows = store.list_dataset_versions(logical_name="forecast_scoring_set", layer="gold")\nif not training_rows:\n    raise SystemExit("No Gold datasets found for forecast_training_set.")\nif not scoring_rows:\n    raise SystemExit("No Gold datasets found for forecast_scoring_set.")\ntraining_versions = {str(row["version"]): row for row in training_rows}\nscoring_versions = {str(row["version"]): row for row in scoring_rows}\nif requested_version:\n    if requested_version not in training_versions or requested_version not in scoring_versions:\n        raise SystemExit(f"Gold ML training/scoring datasets not found for version {requested_version}.")\n    selected_version = requested_version\nelse:\n    common_versions = sorted(set(training_versions) & set(scoring_versions))\n    if not common_versions:\n        raise SystemExit("No common Gold ML training/scoring dataset versions were found.")\n    selected_version = common_versions[-1]\ntraining = training_versions[selected_version]\nscoring = scoring_versions[selected_version]\nprint("\\t".join([str(training["object_path"]), str(training["id"]), str(scoring["object_path"]), str(scoring["id"]), str(selected_version)]))'); \
	IFS=$$'\t' read -r TRAINING_OBJECT_KEY TRAINING_DATASET_VERSION_ID SCORING_OBJECT_KEY SCORING_DATASET_VERSION_ID SELECTED_VERSION <<< "$$DATASETS"; \
	echo "[INFO] Usando datasets Gold ML versao $$SELECTED_VERSION"; \
	$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.train_forecast_model \
		--training-object-key "$$TRAINING_OBJECT_KEY" \
		--training-dataset-version-id "$$TRAINING_DATASET_VERSION_ID" \
		--scoring-object-key "$$SCORING_OBJECT_KEY" \
		--scoring-dataset-version-id "$$SCORING_DATASET_VERSION_ID" \
		--actor "$(ACTOR)"

train-forecast: check-env check-python require-TRAINING_OBJECT_KEY require-TRAINING_DATASET_VERSION_ID require-SCORING_OBJECT_KEY require-SCORING_DATASET_VERSION_ID
	@$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.train_forecast_model \
		--training-object-key "$(TRAINING_OBJECT_KEY)" \
		--training-dataset-version-id "$(TRAINING_DATASET_VERSION_ID)" \
		--scoring-object-key "$(SCORING_OBJECT_KEY)" \
		--scoring-dataset-version-id "$(SCORING_DATASET_VERSION_ID)" \
		--actor "$(ACTOR)"

experiment-forecast: train-forecast

index-embeddings: check-env check-python require-RAG_OBJECT_KEY require-RAG_DATASET_VERSION_ID
	@$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.index_embeddings \
		--rag-object-key "$(RAG_OBJECT_KEY)" \
		--rag-dataset-version-id "$(RAG_DATASET_VERSION_ID)" \
		--batch-size "$(or $(BATCH_SIZE),32)" \
		--actor "$(ACTOR)"

index-docs: check-python
	@$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.index_docs \
		--docs-dir "$(or $(DOCS_DIR),docs)" \
		--batch-size "$(or $(BATCH_SIZE),32)" \
		--actor "$(ACTOR)"

index-mlflow: check-env check-python
	@echo "[INFO] Indexando runs do MLflow no knowledge corpus..."
	@$(PYTHON_RUN) $(PYTHON) pipelines/index_mlflow_runs.py \
		--max-runs "$(or $(MAX_RUNS),50)"

eval-rag: check-env check-python
	@echo "[INFO] Executando avaliacao do RAG..."
	@$(PYTHON_RUN) $(PYTHON) pipelines/evaluate_rag.py \
		$(if $(DATASET),--dataset "$(DATASET)",) \
		$(if $(TAGS),--tags $(TAGS),) \
		$(if $(MLFLOW),--mlflow,)

test: check-python
	@$(PYTHON_RUN) $(PYTHON) -m pytest

index-embeddings-latest: check-env check-python
	@set -euo pipefail; \
	DATASET=$$($(PYTHON_RUN) TARGET_VERSION="$(VERSION)" $(PYTHON) -c $$'import os\nfrom urban_lens.core.settings import AppConfig\nfrom urban_lens.governance.store import MetadataStore\nconfig = AppConfig.from_env()\nstore = MetadataStore(config.postgres_dsn)\nrequested_version = os.getenv("TARGET_VERSION") or None\nrows = store.list_dataset_versions(logical_name="crime_chunks", layer="gold")\nif not rows:\n    raise SystemExit("No Gold RAG crime_chunks datasets found.")\nversions = {str(r["version"]): r for r in rows}\nif requested_version:\n    if requested_version not in versions:\n        raise SystemExit(f"crime_chunks dataset not found for version {requested_version}.")\n    selected = versions[requested_version]\nelse:\n    selected = sorted(versions.values(), key=lambda r: str(r["version"]))[-1]\nprint("\\t".join([str(selected["object_path"]), str(selected["id"])]))'); \
	IFS=$$'\t' read -r RAG_OBJECT_KEY RAG_DATASET_VERSION_ID <<< "$$DATASET"; \
	echo "Indexando crime_chunks $$RAG_DATASET_VERSION_ID"; \
	$(PYTHON_RUN) $(PYTHON) -m urban_lens.cli.index_embeddings \
		--rag-object-key "$$RAG_OBJECT_KEY" \
		--rag-dataset-version-id "$$RAG_DATASET_VERSION_ID" \
		--batch-size "$(or $(BATCH_SIZE),32)" \
		--actor "$(ACTOR)"
