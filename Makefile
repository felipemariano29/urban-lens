SHELL := /bin/bash

COMPOSE := $(shell \
	if command -v podman-compose >/dev/null 2>&1; then \
		echo "podman-compose"; \
	elif command -v docker-compose >/dev/null 2>&1; then \
		echo "docker-compose"; \
	else \
		echo ""; \
	fi)

.PHONY: help check-compose check-env up down reset logs

help:
	@printf "\n"
	@printf "\033[1;36m=======================================\033[0m\n"
	@printf "\033[1;32m 🚀 UrbanLens - Comandos disponíveis\033[0m\n"
	@printf "\033[1;36m=======================================\033[0m\n\n"

	@printf "\033[1;33m📦 Docker\033[0m\n"
	@printf "  \033[1;37mmake up\033[0m        → Subir os containers\n"
	@printf "  \033[1;37mmake down\033[0m      → Parar e remover containers\n"
	@printf "  \033[1;37mmake reset\033[0m     → Reset completo (remove volumes)\n"
	@printf "  \033[1;37mmake logs\033[0m      → Ver logs em tempo real\n\n"

	@printf "\033[1;33m📄 Utilidades\033[0m\n"
	@printf "  \033[1;37mmake help\033[0m      → Mostrar esta ajuda\n\n"

	@printf "\033[1;36m=======================================\033[0m\n\n"

check-compose:
	@if [ -z "$(COMPOSE)" ]; then \
		echo "❌ Nenhum compose compatível foi encontrado."; \
		echo "👉 Instale o podman-compose com:"; \
		echo "   sudo apt update && sudo apt install podman-compose"; \
		exit 1; \
	fi
	@if [ "$(COMPOSE)" = "podman-compose" ]; then \
		echo "✅ Usando podman-compose"; \
	else \
		echo "⚠️ Usando docker-compose"; \
	fi

check-env:
	@if [ ! -f .env ]; then \
		echo "❌ Arquivo .env não encontrado na raiz do projeto."; \
		echo "👉 Crie o arquivo em: $$(pwd)/.env"; \
		exit 1; \
	fi
	@echo "✅ Arquivo .env encontrado."

up: check-compose check-env
	@echo "🚀 Subindo containers..."
	@$(COMPOSE) up -d

down: check-compose check-env
	@echo "🛑 Parando containers..."
	@$(COMPOSE) down

reset: check-compose check-env
	@echo "♻️ Removendo containers e volumes..."
	@if [ "$(COMPOSE)" = "podman-compose" ]; then \
		$(COMPOSE) down -v; \
	else \
		$(COMPOSE) down -v --remove-orphans; \
	fi
	@echo "🚀 Subindo ambiente limpo..."
	@$(COMPOSE) up -d --build

logs: check-compose check-env
	@echo "📜 Exibindo logs..."
	@$(COMPOSE) logs -f