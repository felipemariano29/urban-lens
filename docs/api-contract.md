# Urban Lens API — Contrato Técnico v0.1.0

**Projeto:** Urban Lens — Inteligência de Segurança Urbana  
**Sprint:** S7 — Definição e Consolidação de Contrato de API  
**Versão do documento:** 1.0  
**Data:** 2026-05-03

---

## 1. Visão Geral

A API Urban Lens expõe os dados e capacidades da plataforma de inteligência de segurança urbana via HTTP/JSON. Permite busca semântica em dados de criminalidade, consulta ao catálogo de datasets e acesso a metadados de governança do pipeline de ML.

| Atributo | Valor |
|---|---|
| Base URL | `http://<host>/api/v1` |
| Versão | `0.1.0` |
| Formato | JSON (`Content-Type: application/json`) |
| Autenticação | Bearer JWT · X-API-Key |
| Documentação interativa | `GET /docs` (Swagger UI) · `GET /redoc` (ReDoc) |
| Schema OpenAPI | `GET /openapi.json` |

---

## 2. Autenticação

### 2.1 Bearer JWT

Todos os endpoints operacionais (exceto `/health`) requerem um JWT válido no header:

```
Authorization: Bearer <token>
```

**Payload mínimo exigido:**

```json
{
  "sub": "<user-id>",
  "role": "viewer",
  "exp": 1746000000
}
```

**Roles válidas:** `viewer` · `operator` · `admin` · `internal_service`

**Algoritmo:** HS256  
**Segredo:** variável de ambiente `URBAN_LENS_JWT_SECRET`

**Exemplo — gerar token (Python):**

```python
import jwt, time

token = jwt.encode(
    {"sub": "user-123", "role": "operator", "exp": int(time.time()) + 3600},
    "my-secret",
    algorithm="HS256",
)
```

### 2.2 API Key (machine-to-machine)

Serviços internos usam o header `X-API-Key`, que concede o perfil `internal_service`:

```
X-API-Key: <chave>
```

A chave deve corresponder à variável de ambiente `URBAN_LENS_INTERNAL_API_KEY`.

> Quando ambos `Authorization` e `X-API-Key` estão presentes, a API Key prevalece.

---

## 3. Endpoints

### 3.1 `GET /api/v1/health`

**Descrição:** Liveness/readiness probe. Verifica a conectividade com cada dependência.  
**Autenticação:** Não requerida.  
**Tags:** `System`

#### Resposta — 200 (tudo saudável)

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-04-28T12:00:00.000000+00:00",
  "dependencies": {
    "catalog": "ok",
    "rag_embedder": "ok",
    "rag_vector_store": "ok"
  }
}
```

#### Resposta — 207 (degradado parcial)

```json
{
  "status": "degraded",
  "version": "0.1.0",
  "timestamp": "2025-04-28T12:00:05.000000+00:00",
  "dependencies": {
    "catalog": "ok",
    "rag_embedder": "unavailable",
    "rag_vector_store": "ok"
  }
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `status` | `string` | `"healthy"` ou `"degraded"` |
| `version` | `string` | Versão da API |
| `timestamp` | `string` (ISO 8601 UTC) | Momento da verificação |
| `dependencies` | `object` | Mapa de dependência → `"ok"` ou `"unavailable"` |

| HTTP | Condição |
|---|---|
| 200 | Todas as dependências `"ok"` |
| 207 | Ao menos uma dependência `"unavailable"` |

---

### 3.2 `POST /api/v1/query`

**Descrição:** Busca semântica por similaridade sobre chunks de dados de criminalidade indexados no Milvus.  
**Autenticação:** JWT ou API Key — todos os perfis autenticados.  
**Tags:** `Query`

#### Request body (`application/json`)

```json
{
  "query": "burglary in Westminster January 2024",
  "filters": {
    "crime_type": "Burglary",
    "lsoa_code": "E01001234"
  },
  "top_k": 5
}
```

| Campo | Tipo | Obrigatório | Padrão | Restrições | Descrição |
|---|---|---|---|---|---|
| `query` | `string` | ✅ | — | — | Consulta em linguagem natural |
| `filters` | `object` | ❌ | `null` | Chaves: `lsoa_code`, `crime_type`, `reference_month` | Filtros adicionais aplicados à busca vetorial |
| `top_k` | `integer` | ❌ | `5` | `1 ≤ top_k ≤ 20` | Número de resultados a retornar |

#### Resposta — 200

```json
{
  "results": [
    {
      "id": "chunk-e01001234-2024-01",
      "score": 0.87,
      "content": "In January 2024, Westminster recorded 3 burglaries in LSOA E01001234.",
      "metadata": {
        "chunk_type": "area_month",
        "reference_month": "2024-01",
        "lsoa_code": "E01001234",
        "crime_type": "Burglary",
        "title": "Westminster 2024-01",
        "dataset_version_id": "v1"
      }
    }
  ]
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `results` | `array[QueryResult]` | Lista ranqueada por similaridade |
| `results[].id` | `string` | Identificador único do chunk |
| `results[].score` | `float` | Score de similaridade de cosseno (0–1) |
| `results[].content` | `string` | Texto do chunk |
| `results[].metadata.chunk_type` | `string?` | Granularidade (`area_month`, `area_year`) |
| `results[].metadata.reference_month` | `string?` | Mês de referência (`YYYY-MM`) |
| `results[].metadata.lsoa_code` | `string?` | Código LSOA (ONS) |
| `results[].metadata.crime_type` | `string?` | Categoria do crime |
| `results[].metadata.title` | `string?` | Título descritivo do chunk |
| `results[].metadata.dataset_version_id` | `string?` | Versão do dataset de origem |

| HTTP | Condição |
|---|---|
| 200 | Busca concluída (pode retornar lista vazia) |
| 401 | Token ausente, mal-formado ou expirado |
| 403 | Perfil sem permissão |
| 422 | Payload inválido (`top_k` fora do intervalo, `query` ausente) |
| 502 | Backend RAG (Milvus/Ollama) indisponível |

---

### 3.3 `GET /api/v1/metadata`

**Descrição:** Lista entradas do catálogo de governança de dados. Os campos retornados variam conforme o perfil do chamador.  
**Autenticação:** JWT ou API Key — todos os perfis autenticados.  
**Tags:** `Catalog`

#### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `source` | `string` | ❌ | Filtra por `logical_name` do dataset |

#### Resposta — 200

A estrutura dos objetos depende do perfil. Ver seção [5. Visibilidade de Campos por Perfil](#5-visibilidade-de-campos-por-perfil).

**viewer:**
```json
[
  {
    "logical_name": "gold/rag/crime_chunks",
    "layer": "gold"
  }
]
```

**operator:**
```json
[
  {
    "logical_name": "gold/rag/crime_chunks",
    "layer": "gold",
    "version": "2024-01"
  }
]
```

**admin / internal_service:**
```json
[
  {
    "logical_name": "gold/rag/crime_chunks",
    "layer": "gold",
    "version": "2024-01",
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "object_path": "gold/rag/crime_chunks/2024-01.parquet",
    "created_at": "2024-01-15T10:00:00"
  }
]
```

| HTTP | Condição |
|---|---|
| 200 | Lista retornada (pode ser vazia) |
| 401 | Token inválido |
| 403 | Perfil sem permissão |
| 502 | Banco de dados (PostgreSQL) indisponível |

---

### 3.4 `GET /api/v1/metadata/runs`

**Descrição:** Lista runs de treinamento do MLflow para o pipeline Urban Lens. Acesso restrito a `admin` e `internal_service`.  
**Autenticação:** JWT (`admin`) ou API Key (`internal_service`).  
**Tags:** `MLflow Metadata`

#### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|---|---|---|---|
| `experiment_name` | `string` | ❌ | Nome do experimento MLflow (padrão: `urban-lens-medallion`) |
| `dataset_version` | `string` | ❌ | Filtra pelo parâmetro `training_dataset_version_id` (ex: `2024-01`) |
| `start_date` | `string` (ISO 8601) | ❌ | Runs iniciadas a partir desta data |
| `end_date` | `string` (ISO 8601) | ❌ | Runs iniciadas até esta data |

> `start_date` não pode ser posterior a `end_date` — retorna 422 se violado.

#### Resposta — 200

```json
[
  {
    "run_id": "a1b2c3d4e5f6",
    "experiment_id": "1",
    "experiment_name": "urban-lens-medallion",
    "run_name": "training-2024-01",
    "status": "FINISHED",
    "start_time": "2024-01-10T08:00:00+00:00",
    "end_time": "2024-01-10T08:45:00+00:00",
    "artifact_uri": "mlflow-artifacts:/1/a1b2c3d4e5f6/artifacts",
    "metrics": {
      "mae": 1.23,
      "rmse": 1.87,
      "mape": 0.15
    },
    "params": {
      "training_dataset_version_id": "2024-01",
      "n_estimators": "300"
    },
    "dataset_version": "2024-01"
  }
]
```

| HTTP | Condição |
|---|---|
| 200 | Lista retornada (pode ser vazia) |
| 401 | Token inválido |
| 403 | Perfil sem permissão (`viewer` ou `operator`) |
| 404 | `experiment_name` não encontrado no MLflow |
| 422 | `start_date` > `end_date` |

---

### 3.5 `GET /internal/status` *(restrito)*

**Descrição:** Status operacional interno. Oculto do Swagger público.  
**Autenticação:** JWT (`admin`) ou API Key (`internal_service`).  
**Tags:** `Internal`

#### Resposta — 200

```json
{ "status": "ok", "role": "admin" }
```

| HTTP | Condição |
|---|---|
| 200 | Acesso autorizado |
| 401 | Sem autenticação |
| 403 | Perfil não autorizado |

---

## 4. Envelope de Erro Padrão

Todos os erros — independente da causa — retornam o mesmo envelope JSON:

```json
{
  "error": "<CÓDIGO>",
  "message": "<descrição legível>",
  "details": []
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `error` | `string` | Código de erro: `VALIDATION_ERROR`, `HTTP_401`, `HTTP_403`, `HTTP_404`, `HTTP_502`, `INTERNAL_ERROR` |
| `message` | `string` | Mensagem em inglês descrevendo o problema |
| `details` | `array` | Lista de erros por campo (preenchida em erros 422) |

### Exemplos por código de status

**401 — credencial ausente ou inválida:**
```json
{ "error": "HTTP_401", "message": "Missing authentication credentials.", "details": [] }
```

**403 — perfil sem permissão:**
```json
{
  "error": "HTTP_403",
  "message": "Access denied: role 'viewer' is not authorised for this resource. Required: ['admin', 'internal_service'].",
  "details": []
}
```

**422 — validação de entrada:**
```json
{
  "error": "VALIDATION_ERROR",
  "message": "One or more request fields are invalid.",
  "details": [
    { "type": "missing", "loc": ["body", "query"], "msg": "Field required" }
  ]
}
```

**502 — backend indisponível:**
```json
{ "error": "HTTP_502", "message": "RAG backend returned an error. Please try again later.", "details": [] }
```

---

## 5. Visibilidade de Campos por Perfil

### 5.1 `/api/v1/metadata` (Catálogo)

| Campo | `viewer` | `operator` | `admin` | `internal_service` |
|---|---|---|---|---|
| `logical_name` | ✅ | ✅ | ✅ | ✅ |
| `layer` | ✅ | ✅ | ✅ | ✅ |
| `version` | ❌ | ✅ | ✅ | ✅ |
| `id` | ❌ | ❌ | ✅ | ✅ |
| `object_path` | ❌ | ❌ | ✅ | ✅ |
| `created_at` | ❌ | ❌ | ✅ | ✅ |

### 5.2 Acesso por endpoint

| Endpoint | `viewer` | `operator` | `admin` | `internal_service` |
|---|---|---|---|---|
| `GET /api/v1/health` | ✅ | ✅ | ✅ | ✅ |
| `POST /api/v1/query` | ✅ | ✅ | ✅ | ✅ |
| `GET /api/v1/metadata` | ✅ | ✅ | ✅ | ✅ |
| `GET /api/v1/metadata/runs` | ❌ | ❌ | ✅ | ✅ |
| `GET /internal/*` | ❌ | ❌ | ✅ | ✅ |

---

## 6. Headers HTTP

### Request

| Header | Obrigatório | Descrição |
|---|---|---|
| `Authorization` | Condicional | `Bearer <JWT>` — obrigatório nos endpoints protegidos (exceto quando X-API-Key é usado) |
| `X-API-Key` | Condicional | Chave de serviço para `internal_service` |
| `Content-Type` | Sim (POST) | `application/json` |
| `X-Request-ID` | ❌ | ID de correlação customizado; se ausente, um UUID é gerado automaticamente |

### Response

| Header | Sempre presente | Descrição |
|---|---|---|
| `X-Request-ID` | ✅ | Correlation ID da requisição (gerado ou ecoado do request) |
| `Content-Type` | ✅ | `application/json` |

---

## 7. Configuração e Variáveis de Ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `URBAN_LENS_JWT_SECRET` | Segredo HMAC para assinar/verificar JWTs | `dev-secret-change-in-prod` |
| `URBAN_LENS_INTERNAL_API_KEY` | API Key para `internal_service` | _(vazio — desabilitado)_ |
| `URBAN_LENS_CORS_ORIGINS` | Origens CORS permitidas (vírgula-separado) | `*` |
| `URBAN_LENS_MILVUS_URI` | URI do Milvus (vector store) | `http://localhost:19530` |
| `URBAN_LENS_OLLAMA_BASE_URL` | URL base do Ollama (embedder) | `http://localhost:11434` |
| `URBAN_LENS_EMBEDDING_MODEL` | Modelo de embedding Ollama | `nomic-embed-text` |
| `URBAN_LENS_POSTGRES_DSN` | DSN PostgreSQL (catálogo e governança) | `postgresql://urban_lens:urban_lens@localhost:5432/urban_lens` |
| `MLFLOW_TRACKING_URI` | URI do servidor MLflow | `http://localhost:5005` |

---

## 8. Modelos Pydantic

### 8.1 QueryRequest

```python
class QueryRequest(BaseModel):
    query: str                        # obrigatório
    filters: dict[str, str] | None    # opcional
    top_k: int = 5                    # 1 ≤ top_k ≤ 20
```

### 8.2 QueryResponse

```python
class QueryResponse(BaseModel):
    results: list[QueryResult]

class QueryResult(BaseModel):
    id: str
    score: float
    content: str
    metadata: QueryResultMetadata

class QueryResultMetadata(BaseModel):
    chunk_type: str | None
    reference_month: str | None
    lsoa_code: str | None
    crime_type: str | None
    title: str | None
    dataset_version_id: str | None
```

### 8.3 RunMetadataResponse

```python
class RunMetadataResponse(BaseModel):
    run_id: str
    experiment_id: str
    experiment_name: str
    run_name: str | None
    status: str                # RUNNING | FINISHED | FAILED | KILLED
    start_time: datetime | None
    end_time: datetime | None
    artifact_uri: str | None
    metrics: RunMetricsSchema  # mae, rmse, mape
    params: dict[str, str]
    dataset_version: str | None
```

### 8.4 ErrorEnvelope

```python
class ErrorEnvelope(BaseModel):
    error: str          # ex: VALIDATION_ERROR, HTTP_401
    message: str
    details: list       # preenchido em erros 422
```

---

## 9. Resiliência

Os serviços de backend (RAG e catálogo) são chamados com **retry exponencial**:

| Parâmetro | Valor |
|---|---|
| Tentativas máximas | 3 |
| Delay inicial | 0,5 s |
| Backoff | Exponencial (× 2 a cada tentativa) |
| Delay máximo (3ª tentativa) | 2,0 s |

Se todas as tentativas falharem, o endpoint retorna `502 Bad Gateway`.

---

## 10. Observabilidade

- **Correlation ID:** toda requisição recebe um `X-Request-ID` (UUID v4 gerado ou ecoado do header de entrada).
- **Logs estruturados:** cada chamada aos serviços registra duração em ms e `request_id`.
- **Logs de acesso negado (403):** registra endpoint, método HTTP, perfil, IP anonimizado (último octeto substituído por `xxx`, conforme LGPD) e `request_id`.

---

## 11. Como Executar

```bash
# Instalar dependências
pip install -e .

# Configurar variáveis (mínimo para desenvolvimento)
export URBAN_LENS_JWT_SECRET="dev-secret-change-in-prod"

# Iniciar servidor
uvicorn urban_lens.api.main:app --reload --port 8000

# Swagger UI
open http://localhost:8000/docs
```

---

## 12. Referências

- [RBAC — Matriz de Perfis e Permissões](rbac.md)
- [Swagger UI](http://localhost:8000/docs)
- [ReDoc](http://localhost:8000/redoc)
- [OpenAPI JSON](http://localhost:8000/openapi.json)
