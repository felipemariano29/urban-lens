# Urban Lens

Urban Lens is a local enterprise-style RAG platform for urban intelligence. The project ingests public crime data, organizes it in a Medallion architecture, indexes governed evidence in Milvus, serves local LLM answers through FastAPI, and exposes a simple frontend for consultation.

## Scope

- Domain: public safety and urban intelligence
- Primary dataset: [DATA.POLICE.UK](https://data.police.uk/data/)
- Goal: support analysts and public managers with traceable natural-language answers
- Non-goal: real-time policing or autonomous operational decisions

## Core Stack

- Data lake: MinIO
- Governance metadata: PostgreSQL
- Vector index: Milvus
- Milvus UI: Attu
- Local AI: Ollama
- API: FastAPI
- Interface: Next.js frontend
- Experiment tracking: MLflow
- Runtime: Docker Compose
- Automation: Makefile

## Current Delivery State

The repository already contains:

- Bronze -> Silver -> Gold pipeline orchestration
- governance schema and metadata registration
- Gold outputs for analytics, RAG, and ML
- embedding generation and Milvus indexing
- local RAG API with evidence citations
- frontend integrated with the real API
- operational documentation and demo runbook for AC2 through Sprint 8

## Key Documents

| Document | Purpose |
| --- | --- |
| [docs/how-to-run.md](docs/how-to-run.md) | Local setup, services, and runtime entrypoint |
| [docs/implementation-guide.md](docs/implementation-guide.md) | Step-by-step execution of the governed pipeline |
| [docs/architecture/medallion-governance.md](docs/architecture/medallion-governance.md) | Medallion layer rules and product families |
| [docs/architecture/metadata-contract.md](docs/architecture/metadata-contract.md) | Governance, lineage, audit, and response contracts |
| [docs/governance-medallion-delivery-plan.md](docs/governance-medallion-delivery-plan.md) | Internal delivery plan and task closure |
| [docs/ac2-sprint-closure.md](docs/ac2-sprint-closure.md) | AC2 closure mapping for Sprints 1 to 8 |
| [docs/demo-professor.txt](docs/demo-professor.txt) | Live demo script and validation flow |

## Team

| Name | E-mail | RA |
| --- | --- | ---: |
| Diego Justino da Silva | diegojsilva01@outlook.com | 223705 |
| Diogo Francia | diogofrancia2@gmail.com | 222558 |
| Felipe Augusto de Almeida Mariano | felipemariano99@gmail.com | 210045 |
| Joao Rafael Jordao Pereira | jrafael1504@gmail.com | 211903 |
| Kaique Medeiros Govani | kaique.govani@hotmail.com | 210170 |
| Lucas Da Silva Marques | lucasses10@gmail.com | 223402 |
| Lucas de Moraes Silveira | lucasdmsilveira@gmail.com | 211668 |
| Lucas Ferreira Neto | ferreiranetolucas@gmail.com | 223026 |
| Mateus Nauhan Vieira Matos | mateusnauhan@gmail.com | 211931 |
| Milton Rogerio Dotto Penha Junior | miltonjmiltonj@gmail.com | 222284 |
| Nicolas Leonardi Barsalini | nicolasbarsalini2017@gmail.com | 222259 |
| Raphael Nobuyuki Haga Okuyama | raphaelokuyuama123@gmail.com | 222808 |
