#!/bin/sh
set -eu

echo "Atualizando schema do MLflow, se necessario..."
mlflow db upgrade "${MLFLOW_BACKEND_STORE_URI}"

exec mlflow server \
  --host "${MLFLOW_HOST:-0.0.0.0}" \
  --port "${MLFLOW_PORT:-5000}" \
  --backend-store-uri "${MLFLOW_BACKEND_STORE_URI}" \
  --serve-artifacts \
  --artifacts-destination "${MLFLOW_ARTIFACT_ROOT}" \
  --allowed-hosts '*'
