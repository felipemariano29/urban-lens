#!/bin/sh
set -eu

PGHOST="${POSTGRES_HOST:-postgres-db}"
PGPORT="${POSTGRES_PORT:-5432}"
export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "Aguardando PostgreSQL iniciar em ${PGHOST}:${PGPORT}..."
attempt=1
until pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; do
  if [ "${attempt}" -ge 30 ]; then
    echo "PostgreSQL nao ficou pronto a tempo." >&2
    exit 1
  fi

  echo "Tentativa ${attempt}/30: PostgreSQL ainda nao esta pronto."
  attempt=$((attempt + 1))
  sleep 2
done

for script in /sql/init/*.sql; do
  if [ ! -f "${script}" ]; then
    continue
  fi

  echo "Aplicando ${script##*/}..."
  psql -v ON_ERROR_STOP=1 -h "${PGHOST}" -p "${PGPORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -f "${script}"
done

echo "Setup do PostgreSQL concluido."
