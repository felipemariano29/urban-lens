# Urban-Lens

Urban-Lens is a local-first platform for urban intelligence, focused on organizing and enabling access to public crime and safety data for analytical and strategic purposes.

This repository contains the initial operational setup of the project, providing the minimal infrastructure required for local development and team onboarding.

---

## Current Scope

At this stage, the platform includes the following core services:

* **PostgreSQL** → relational database for metadata and governance structures
* **MinIO** → object storage for future data lake layers (Bronze, Silver, Gold)

This setup establishes the foundation for future components such as ingestion pipelines, vector search, and RAG workflows.

---

## Repository Structure

```bash
.
├── AGENTS.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── Makefile
├── README.md
└── docs
    ├── product-vision.md
    └── urban_lens_visao_consolidada.pdf
    └── how-to-run.md (you are here)   
```

---

## Prerequisites

Make sure you have the following installed on your machine:

* Docker
* Docker Compose
* GNU Make
* Git

Recommended:

* 8 GB+ RAM
* 2+ CPU cores

---

## Environment Setup

1. Clone the repository:

```bash
git clone https://github.com/felipemariano29/urban-lens.git
cd urbanlens
```

2. Create your environment file:

```bash
cp .env.example .env
```

3. (Optional) Adjust environment variables if needed.

---

## Running the Project

Start the services using:

```bash
make up
```

Or directly with Docker Compose:

```bash
docker compose up -d
```

---

## Verifying Services

Check running containers:

```bash
make ps
```

View logs:

```bash
make logs
```

---

## Available Services

### MinIO

* API: http://localhost:9000
* Console: http://localhost:9001

Credentials are defined in `.env`.

---

### PostgreSQL

* Host: localhost
* Port: 5432

Credentials are defined in `.env`.

---

## Useful Commands

```bash
make help
make up
make down
make restart
make reset
make logs
make ps
```

---

## Troubleshooting

### Containers do not start

```bash
docker compose logs -f
```

---

### Port already in use

Check if these ports are occupied:

* 5432 (PostgreSQL)
* 9000 (MinIO API)
* 9001 (MinIO Console)

---

### Missing `.env` file

```bash
cp .env.example .env
```

---

### Reset environment

If something is broken:

```bash
make reset
```

---

## Purpose of This Setup

This repository provides a **minimal, reproducible local environment** to:

* standardize development setup
* enable team onboarding
* prepare the foundation for data ingestion and analysis pipelines
* support future expansion of the Urban-Lens platform

---

## Next Steps (Future Work)

* Data ingestion pipelines
* Medallion architecture (Bronze / Silver / Gold)
* Vector database integration
* RAG pipeline implementation
* API layer (FastAPI)
* Local LLM inference (Ollama)

---

## Reference Documents

* `docs/product-vision.md`
* `docs/urban_lens_visao_consolidada.pdf`
