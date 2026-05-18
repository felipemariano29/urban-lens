#!/bin/sh
set -eu

echo "Aguardando Ollama iniciar..."
sleep 20

echo "Baixando modelo de embeddings..."
OLLAMA_HOST=ollama:11434 ollama pull nomic-embed-text

echo "Baixando modelo LLM para chat..."
OLLAMA_HOST=ollama:11434 ollama pull llama3

echo "Setup do Ollama concluido."
