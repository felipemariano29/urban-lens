# Contributing

## Commit policy

All changes in this repository must follow these rules:

- always prefer small, focused commits
- every commit must use Conventional Commits
- do not mix unrelated changes in the same commit
- prefer a short sequence of reviewable commits instead of one large commit

## Recommended commit style

Examples:

- `feat(api): add model catalog endpoint`
- `fix(docker): add healthcheck for rag-api`
- `chore(makefile): split cpu and gpu startup targets`
- `docs(roadmap): add next phase implementation plan`

## Practical guidance

- one commit per logical change
- one commit for docs/process changes
- one commit for infrastructure changes
- one commit for API contract changes
- one commit for frontend adjustments that depend on a backend change

If a change becomes too broad to explain with one clear Conventional Commit message, it should probably be split before committing.
