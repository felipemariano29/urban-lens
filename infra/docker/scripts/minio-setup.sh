#!/bin/sh
set -eu

echo "Aguardando o MinIO iniciar..."
sleep 8

/usr/bin/mc alias set myminio "http://minio-storage:9000" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"

# Criar bucket padrao da aplicacao.
/usr/bin/mc mb "myminio/${MINIO_DEFAULT_BUCKET}" --ignore-existing

# Criar bucket para o Milvus.
/usr/bin/mc mb "myminio/milvus" --ignore-existing

# Permitir download anonimo para o bucket usado pelo Milvus standalone.
/usr/bin/mc anonymous set download "myminio/milvus"

echo "Setup do MinIO concluido."
