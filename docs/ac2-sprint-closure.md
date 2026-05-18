# AC2 Sprint Closure

This document maps the expected scope from Sprint 1 through Sprint 8 to the current Urban Lens repository state. It is the formal closure artifact for the AC2 delivery slice.

## Scope Baseline

Reference used for this closure:

- course presentation PDF at `C:/Users/felip/Desktop/Faculdade/Big Data/Aula - Apresentacao (Atualizado).pdf`
- internal execution plan in [governance-medallion-delivery-plan.md](governance-medallion-delivery-plan.md)

This closure considers the project only up to:

- Sprint 1 to Sprint 8 from the course presentation
- the AC2 deliverables associated with API and interface

## Closure Summary

| Sprint | Expected deliverable | Current evidence in repository | Status |
| --- | --- | --- | --- |
| Sprint 1 | Product definition and initial backlog | [AGENTS.md](../AGENTS.md), [README.md](../README.md), architecture and product docs in `docs/` | Attended |
| Sprint 2 | Base architecture and initial Compose | [docker-compose.yml](../docker-compose.yml), [how-to-run.md](how-to-run.md) | Attended |
| Sprint 3 | Medallion governance and ingestion pipeline | [architecture/medallion-governance.md](architecture/medallion-governance.md), [architecture/metadata-contract.md](architecture/metadata-contract.md), [../sql/init/001_governance_schema.sql](../sql/init/001_governance_schema.sql), [../src/urban_lens/workflows](../src/urban_lens/workflows) | Attended |
| Sprint 4 | Training pipeline plus MLflow integration | [../src/urban_lens/forecasting/training.py](../src/urban_lens/forecasting/training.py), [../src/urban_lens/workflows/forecast.py](../src/urban_lens/workflows/forecast.py), [implementation-guide.md](implementation-guide.md) | Attended |
| Sprint 5 | Embeddings pipeline and vector indexing | [../src/urban_lens/cli/index_embeddings.py](../src/urban_lens/cli/index_embeddings.py), [../src/urban_lens/workflows/embeddings.py](../src/urban_lens/workflows/embeddings.py), [../docker-compose.yml](../docker-compose.yml) with Milvus and Attu | Attended |
| Sprint 6 | RAG core working via script | [../scripts/demo/demo_rag.py](../scripts/demo/demo_rag.py), [rag-end-to-end.md](rag-end-to-end.md), [../apps/api/src/urban_lens/api/routers/query.py](../apps/api/src/urban_lens/api/routers/query.py) | Attended |
| Sprint 7 | FastAPI with `/query` and `/metadata`, validated contracts | [../src/urban_lens/api/routers/query.py](../src/urban_lens/api/routers/query.py), [../src/urban_lens/api/routers/catalog.py](../src/urban_lens/api/routers/catalog.py), [api-contract.md](api-contract.md) | Attended |
| Sprint 8 | Functional interface | [../apps/web/components/urban-lens](../apps/web/components/urban-lens), [../apps/web/hooks/use-urban-lens.ts](../apps/web/hooks/use-urban-lens.ts), [../apps/web/app/api/v1](../apps/web/app/api/v1), [demo-professor.txt](demo-professor.txt) | Attended |

## Sprint-by-Sprint Notes

### Sprint 1

Expected:

- domain definition
- fictitious company
- business problem
- Scrum roles
- initial backlog

Current state:

- domain, fictitious company, target users, and product framing are documented in [AGENTS.md](../AGENTS.md) and [README.md](../README.md)
- internal planning and backlog structure are documented in [governance-medallion-delivery-plan.md](governance-medallion-delivery-plan.md) and related docs

Assessment:

- Attended for the delivery scope required by AC2

### Sprint 2

Expected:

- general architecture
- architecture diagram
- initial Docker Compose

Current state:

- architecture is documented in [architecture/medallion-governance.md](architecture/medallion-governance.md)
- runtime services are provisioned in [../docker-compose.yml](../docker-compose.yml)
- operational startup is documented in [how-to-run.md](how-to-run.md)

Assessment:

- Attended

### Sprint 3

Expected:

- Bronze / Silver / Gold organization
- ingestion pipeline
- versioning in the data lake

Current state:

- governance contract and Medallion rules are documented
- Bronze, Silver, and Gold workflows exist in [../src/urban_lens/workflows](../src/urban_lens/workflows)
- metadata, lineage, and audit are persisted through the governance schema

Assessment:

- Attended

### Sprint 4

Expected:

- ML problem definition
- training scripts
- MLflow integration

Current state:

- training and evaluation pipeline exists in [../src/urban_lens/forecasting/training.py](../src/urban_lens/forecasting/training.py)
- forecast workflow and publication exist in [../src/urban_lens/workflows/forecast.py](../src/urban_lens/workflows/forecast.py)
- MLflow is part of the stack and documented in runtime guides

Assessment:

- Attended

### Sprint 5

Expected:

- Milvus setup
- Ollama integration
- embedding generation
- vector indexing

Current state:

- Milvus and Ollama are provisioned in Compose
- embeddings are generated and indexed through [../src/urban_lens/workflows/embeddings.py](../src/urban_lens/workflows/embeddings.py)
- Attu was added for collection inspection during validation and demo

Assessment:

- Attended

### Sprint 6

Expected:

- vector search
- prompt construction
- LLM integration
- RAG working through a script

Current state:

- semantic retrieval and chat flow are implemented in the API and RAG services
- the governed RAG contract is documented in [rag-end-to-end.md](rag-end-to-end.md)
- a runnable demonstration exists in [../scripts/demo/demo_rag.py](../scripts/demo/demo_rag.py)

Assessment:

- Attended

### Sprint 7

Expected:

- FastAPI
- `/query`
- `/metadata`
- input/output validation
- documented API

Current state:

- `/api/v1/query` and `/api/v1/metadata` exist and are documented
- response and request contracts are defined in API schemas
- Swagger is available through the FastAPI app

Assessment:

- Attended

### Sprint 8

Expected:

- Gradio or simple frontend
- functional interface

Current state:

- the project uses a simple frontend instead of Gradio
- the frontend is integrated with the real FastAPI routes through Next.js proxy handlers
- health checks, query submission, evidence rendering, filters, and local conversation history are implemented

Assessment:

- Attended

## Remaining Items Outside This Closure

These items do not block AC2 closure through Sprint 8, but remain relevant for the broader final project:

- deeper predictive-answer UX in the interface
- stronger end-to-end automated validation
- final cleanup of legacy documents outside the core operational set
- Sprint 9 onward evaluation and final pitch preparation

## Conclusion

For the scope defined up to Sprint 8, the repository state is considered aligned with the expected delivery. The project is stronger in backend, governance, and pipeline implementation than in product polish, but the required AC2 slice is covered by the current codebase and documentation.
