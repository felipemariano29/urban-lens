FROM python:3.12-slim

WORKDIR /app

COPY apps/api/pyproject.toml README.md ./
COPY apps/api/src ./src
COPY infra/docker/api/entrypoint.sh /entrypoint.sh

RUN python -m pip install --no-cache-dir .
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
