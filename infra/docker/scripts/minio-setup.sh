#!/bin/sh
set -eu

echo "Aguardando o MinIO iniciar..."
sleep 8

/usr/bin/mc alias set myminio "http://minio-storage:9000" "${MINIO_ROOT_USER}" "${MINIO_ROOT_PASSWORD}"
/usr/bin/mc mb "myminio/${MINIO_DEFAULT_BUCKET}" --ignore-existing

echo "Setup do MinIO concluido."
