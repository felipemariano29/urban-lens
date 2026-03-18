# SOP — AI-Assisted Task Execution Agent

Standard Operating Procedure for AI agents working on Urban-Lens tasks.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT",
"SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this
document are to be interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119).

---

## 1. Scope

This SOP defines the mandatory workflow an AI agent MUST follow when
assisting with development tasks in the Urban-Lens repository. The agent
receives a task identifier, retrieves the task details, analyzes the
repository, proposes a solution, and awaits explicit human approval before
making any changes.

---

## 2. Language Policy

| Context | Language | Requirement Level |
|---------|----------|-------------------|
| Issue tracker (comments, status updates, descriptions) | Portuguese (pt-BR) | REQUIRED |
| Repository artifacts (code, commits, docs, comments in code) | English (en) | REQUIRED |

The agent MUST write all issue interactions in Portuguese.
The agent MUST write all repository content in English.

---

## 3. Workflow

### Phase 1 — Task Retrieval

1. The user provides a task ID.
2. The agent MUST call `get_issue` with the provided task ID.
3. The agent MUST read the returned title, description, acceptance criteria,
   and any linked resources.
4. If `get_issue` fails or returns insufficient data, the agent MUST inform
   the user and MUST NOT proceed.

### Phase 2 — Task Comprehension

1. The agent MUST summarize the task objective in its own words and present
   it to the user.
2. The summary SHOULD include:
   - what the task asks for;
   - acceptance criteria (if any);
   - identified constraints or dependencies.

### Phase 3 — Repository Analysis

1. The agent MUST inspect the current repository state to understand the
   existing codebase, structure, and conventions.
2. The agent SHOULD focus on files and modules directly related to the task.
3. The agent MUST identify:
   - which files need to be created, modified, or removed;
   - any dependencies or side effects;
   - alignment with the project stack and conventions defined in `AGENTS.md`.

### Phase 4 — Solution Proposal

1. The agent MUST present a clear, concise proposal to the user containing:
   - a list of files to be changed and a brief description of each change;
   - rationale for the approach;
   - any risks, trade-offs, or open questions.
2. The agent MUST NOT make any file changes at this stage.

### Phase 5 — Human Approval Gate

1. The agent MUST wait for explicit user approval before proceeding.
2. Acceptable approval signals include clear affirmative responses
   (e.g., "yes", "go ahead", "approved", "continue").
3. If the user requests modifications to the proposal, the agent MUST
   return to Phase 4 with an updated proposal.
4. If the user rejects the proposal, the agent MUST stop and MUST NOT
   apply any changes.

### Phase 6 — Implementation

1. Upon approval, the agent MUST implement the changes as proposed.
2. The agent MUST follow the repository conventions defined in `AGENTS.md`:
   - stack: MinIO, PostgreSQL, Milvus, Ollama, FastAPI, MLflow;
   - infrastructure via Docker Compose;
   - data layers: Bronze → Silver → Gold;
   - metadata and audit in PostgreSQL;
   - embeddings and vector search in Milvus;
   - local inference via Ollama only.
3. All code and documentation written in the repository MUST be in English.
4. The agent SHOULD commit changes with clear, descriptive messages in
   English.

### Phase 7 — Issue Update

1. After implementation, the agent SHOULD update the issue with a comment
   in Portuguese summarizing:
   - o que foi feito;
   - arquivos alterados;
   - próximos passos (se houver).

---

## 4. Constraints

- The agent MUST NOT push changes to remote repositories.
- The agent MUST NOT call external LLM APIs; all inference MUST use Ollama
  locally.
- The agent MUST NOT delete or overwrite data without explicit user
  approval.
- The agent MUST NOT skip the Human Approval Gate (Phase 5) under any
  circumstances.
- The agent SHOULD prefer minimal, focused changes over large refactors
  unless the task explicitly requires otherwise.

---

## 5. Error Handling

- If the agent encounters an ambiguous or contradictory task, it MUST ask
  the user for clarification before proposing a solution.
- If the agent cannot complete a phase, it MUST report the failure with
  context and MUST NOT proceed to the next phase.
- If the repository state conflicts with the task requirements, the agent
  MUST flag the conflict to the user and await guidance.
