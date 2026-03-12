# Product Vision — Urban-Lens

## 1. Domain

Urban-Lens operates in the domain of **urban intelligence driven by public crime and safety data** to support decision-making.

The platform focuses on historical analysis and strategic support for municipal governments, intelligence units, and public safety observatories. It is not a real-time policing system nor an automated operational decision tool. Its scope is to consolidate dispersed public datasets into a governed, queryable knowledge base that analysts and managers can consult through natural language.

Primary data source: [DATA.POLICE.UK](https://data.police.uk/), with potential future expansion to similar Brazilian datasets.

## 2. Vision Statement

Urban-Lens is a locally executed RAG (Retrieval-Augmented Generation) platform for urban intelligence. It transforms dispersed public crime and safety data into traceable, evidence-backed analytical responses through natural language queries — with governance, auditability, and traceability built into every layer.

## 3. Business Problem

Public crime and safety data is widely available yet remains underutilized because it is:

- **Dispersed** — spread across multiple sources, formats, and systems with no unified query layer.
- **Poorly contextualized** — raw records lack the semantic structure needed to produce actionable insights.
- **Hard to trace** — analytical conclusions are rarely linked back to the concrete data points that support them.
- **Inaccessible to non-technical users** — existing tools require technical expertise, creating dependency on intermediaries and introducing delays.

This reduces the capacity for historical analysis, territorial prioritization, and production of actionable intelligence. Analysts spend excessive time collecting and organizing data before they can analyze it. Managers receive delayed, unstandardized reports. Operational staff lack a consolidated view and must query multiple systems to build context.

## 4. Value Proposition

Urban-Lens addresses these problems through a unique combination of:

- **Local RAG pipeline** — retrieval-augmented generation running entirely on local infrastructure via Ollama, ensuring data sovereignty and eliminating dependency on external LLM APIs.
- **Medallion architecture** — a Bronze → Silver → Gold data lake in MinIO that enforces data quality progression, from raw ingestion to consumption-ready datasets.
- **Full governance stack** — metadata cataloging, versioning, auditability, and traceability managed in PostgreSQL, so every response can be traced back to its source data.
- **Semantic search** — vector embeddings indexed in Milvus enable natural language queries over structured and unstructured content.
- **Evidence-first responses** — every answer includes direct references to the data and documents used, supporting accountability and trust.
- **Simple user experience** — technical complexity stays in the backend; the user interacts through a straightforward query interface with optional filters (period, region, category) and receives structured, evidence-backed responses.

## 5. Objectives

### General Objective

Develop a complete local RAG platform with data governance capable of ingesting public urban safety data, organizing it in a Medallion architecture, and answering natural language questions with traceable, evidence-based responses.

### Specific Objectives

1. Ingest and store public crime data from DATA.POLICE.UK in a governed data lake (MinIO) following the Bronze → Silver → Gold model.
2. Maintain a metadata catalog with versioning, audit trails, and lineage tracking in PostgreSQL.
3. Generate embeddings for relevant content — including tabular data, text documents, data dictionaries, and methodological notes — and index them in Milvus for semantic retrieval.
4. Implement a RAG pipeline that retrieves relevant context and generates responses via local inference (Ollama), always citing the source data.
5. Expose the platform through a documented API (FastAPI with Swagger) and a simple query interface for end users.
6. Track experiments, prompts, and quality metrics through MLflow to support iterative improvement.
7. Ensure the entire solution runs locally via Docker Compose, guaranteeing reproducibility and portability.

---

*Source material: [urban_lens_visao_consolidada.pdf](urban_lens_visao_consolidada.pdf) (group alignment document), project README, and AGENTS.md.*
