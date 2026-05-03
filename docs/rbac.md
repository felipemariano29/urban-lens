# Urban Lens API — RBAC Reference

## Perfis de Acesso

| Perfil | Descrição |
|---|---|
| `viewer` | Acesso somente leitura a dados públicos operacionais |
| `operator` | Acesso a dados operacionais e dados internos do catálogo |
| `admin` | Acesso total, incluindo metadados técnicos e rotas internas |
| `internal_service` | Acesso equivalente ao `admin`, para autenticação machine-to-machine via API Key |

---

## Matriz de Permissões

| Endpoint | Método | `viewer` | `operator` | `admin` | `internal_service` |
|---|---|---|---|---|---|
| `/api/v1/health` | GET | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/query` | POST | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/metadata` (campos operacionais) | GET | ✅ | ✅ | ✅ | ✅ |
| `/api/v1/metadata` (campo `version`) | GET | ❌ | ✅ | ✅ | ✅ |
| `/api/v1/metadata` (campos técnicos: `id`, `object_path`, `created_at`) | GET | ❌ | ❌ | ✅ | ✅ |
| `/api/v1/metadata/runs` | GET | ❌ | ❌ | ✅ | ✅ |
| `/internal/*` | * | ❌ | ❌ | ✅ | ✅ |

---

## Autenticação

### JWT (Bearer Token)

Todos os perfis exceto `internal_service` autenticam via JWT:

```
Authorization: Bearer <token>
```

**Payload mínimo esperado:**

```json
{
  "sub": "user-id",
  "role": "viewer",
  "exp": 1234567890
}
```

**Roles válidas:** `viewer`, `operator`, `admin`, `internal_service`

**Segredo JWT:** variável de ambiente `URBAN_LENS_JWT_SECRET` (padrão dev: `dev-secret-change-in-prod`).

**Algoritmo:** HS256

#### Exemplo — gerar token de teste

```python
import jwt, time

token = jwt.encode(
    {"sub": "lucas", "role": "operator", "exp": int(time.time()) + 3600},
    "dev-secret-change-in-prod",
    algorithm="HS256",
)
```

---

### API Key (internal_service)

Serviços machine-to-machine usam o header `X-API-Key`:

```
X-API-Key: <chave>
```

A chave deve corresponder à variável de ambiente `URBAN_LENS_INTERNAL_API_KEY`.

---

## Campos Retornados por Perfil — `/api/v1/metadata`

| Campo | `viewer` | `operator` | `admin` / `internal_service` |
|---|---|---|---|
| `logical_name` | ✅ | ✅ | ✅ |
| `layer` | ✅ | ✅ | ✅ |
| `version` | ❌ | ✅ | ✅ |
| `id` | ❌ | ❌ | ✅ |
| `object_path` | ❌ | ❌ | ✅ |
| `created_at` | ❌ | ❌ | ✅ |

Campos técnicos (`id`, `object_path`, `created_at`) nunca são retornados para `viewer` ou `operator`.

---

## Códigos de Erro de Autorização

| Código | Situação |
|---|---|
| 401 | Token ausente, mal formado, expirado ou API Key inválida |
| 403 | Token válido, mas o perfil não tem permissão para o recurso |

**Envelope de erro:**

```json
{
  "error": "HTTP_403",
  "message": "Access denied: role 'viewer' is not authorised for this resource. Required: ['admin', 'internal_service'].",
  "details": []
}
```

---

## Logging de Acessos Negados

Toda tentativa de acesso negada (HTTP 403) gera um log `WARNING` com:

- `endpoint` — caminho da rota
- `method` — método HTTP
- `role` — perfil do solicitante
- `ip` — IP do cliente anonimizado (último octeto substituído por `xxx`, conforme LGPD)
- `request_id` — correlation ID da requisição (header `X-Request-ID`)

**Exemplo de log:**

```
WARNING  Access denied | endpoint=/api/v1/metadata/runs method=GET role=viewer ip=192.168.1.xxx request_id=a1b2c3d4-...
```

---

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `URBAN_LENS_JWT_SECRET` | Segredo HMAC para assinar/verificar JWTs | `dev-secret-change-in-prod` |
| `URBAN_LENS_INTERNAL_API_KEY` | API Key para `internal_service` | _(vazio — desabilitado)_ |
| `URBAN_LENS_CORS_ORIGINS` | Origens permitidas no CORS (separadas por vírgula) | `*` |
