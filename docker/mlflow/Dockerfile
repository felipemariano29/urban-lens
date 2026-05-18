FROM python:3.12-slim

WORKDIR /mlflow

COPY docker/mlflow/entrypoint.sh /entrypoint.sh

RUN python -m pip install --no-cache-dir "mlflow>=3.11" "psycopg[binary]>=3.2" "boto3>=1.37"
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
