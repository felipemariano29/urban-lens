FROM python:3.12-slim

WORKDIR /mlflow

RUN python -m pip install --no-cache-dir "mlflow>=3.11" "psycopg[binary]>=3.2" "boto3>=1.37"

EXPOSE 5000

CMD ["sh", "-c", "mlflow server --host ${MLFLOW_HOST:-0.0.0.0} --port ${MLFLOW_PORT:-5000} --backend-store-uri ${MLFLOW_BACKEND_STORE_URI} --serve-artifacts --artifacts-destination ${MLFLOW_ARTIFACT_ROOT}"]
