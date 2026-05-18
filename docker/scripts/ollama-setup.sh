#!/bin/sh
set -eu

OLLAMA_HOST_ADDRESS="${OLLAMA_HOST_ADDRESS:-ollama:11434}"
OLLAMA_MODELS="${OLLAMA_MODELS:-nomic-embed-text,llama3,mistral,qwen2.5,phi3}"

echo "Aguardando Ollama iniciar em ${OLLAMA_HOST_ADDRESS}..."
attempt=1
until OLLAMA_HOST="${OLLAMA_HOST_ADDRESS}" ollama list >/dev/null 2>&1; do
  if [ "${attempt}" -ge 30 ]; then
    echo "Ollama nao ficou pronto a tempo." >&2
    exit 1
  fi

  echo "Tentativa ${attempt}/30: Ollama ainda nao esta pronto."
  attempt=$((attempt + 1))
  sleep 2
done

OLD_IFS=$IFS
IFS=','
set -- ${OLLAMA_MODELS}
IFS=$OLD_IFS

for raw_model in "$@"; do
  model=$(printf '%s' "${raw_model}" | tr -d '[:space:]')
  if [ -z "${model}" ]; then
    continue
  fi

  echo "Baixando modelo ${model}..."
  OLLAMA_HOST="${OLLAMA_HOST_ADDRESS}" ollama pull "${model}"
done

echo "Setup do Ollama concluido."
