# AGENTS.md — Urban-Lens

## Visão Geral

Urban-Lens é uma plataforma RAG enterprise local voltada para inteligência urbana. Transforma dados públicos de crimes e segurança (fonte principal: DATA.POLICE.UK) em respostas rastreáveis via consulta em linguagem natural, com governança, auditoria e evidências.

Não é sistema de policiamento em tempo real nem de decisão automática. É apoio a analistas de inteligência, gestores municipais e oficiais que precisem consultar históricos, tendências e contexto.

## Equipe

| Papel | Responsável |
|-------|-------------|
| Product Owner | Felipe Mariano |
| Scrum Master | Kaique Govani |

## Stack

| Camada | Componente | Papel |
|--------|-----------|-------|
| Dados | MinIO | Data Lake (Bronze → Silver → Gold) |
| Metadados | PostgreSQL | Catálogo, auditoria, versionamento, rastreabilidade |
| Busca semântica | Milvus | Embeddings e indexação vetorial |
| IA local | Ollama | Geração de respostas e embeddings |
| Aplicação | FastAPI | API com Swagger como entregável acadêmico |
| Interface | Gradio ou frontend simples (em aberto) | Consulta do usuário final |
| MLOps | MLflow | Tracking de experimentos, prompts e métricas |
| Infra | Docker Compose + Makefile | Execução local e reprodutibilidade |

## Fluxo RAG

1. Coleta e armazenamento dos dados no MinIO
2. Tratamento nas camadas Bronze → Silver → Gold
3. Registro de catálogo, versões e metadados no PostgreSQL
4. Geração de embeddings para conteúdos relevantes
5. Indexação no Milvus
6. Pergunta recebida pela interface
7. Recuperação de contexto relevante via API
8. Montagem do prompt e inferência local via Ollama
9. Resposta com referência direta aos dados utilizados

## Usuários-Alvo

- **Analista de inteligência**: explorar tendências, padrões, comparar períodos e áreas
- **Gestor municipal**: síntese executiva para priorizar ações
- **Operacional**: entender ocorrências similares e contexto histórico

## Governança

- Qualidade dos dados com camadas claras (Bronze/Silver/Gold)
- Rastreabilidade: cada resposta aponta para dados concretos
- Auditoria: histórico de cargas, origem, versão e estado
- Versionamento de datasets, transformações e artefatos
- Catálogo documentado do acervo

## MVP (Sprint 1)

Objetivo: provar o fluxo ponta a ponta com escopo mínimo.

- Carga manual de subconjunto do DATA.POLICE.UK
- Organização mínima em Bronze, Silver e Gold
- Catálogo básico e versionamento inicial
- Geração de embeddings e indexação vetorial
- Consulta simples via API e interface
- Resposta com evidências (tabela ou ranking simples)

## Perguntas de Negócio Esperadas

- Quais regiões tiveram aumento de determinado crime em um período?
- Quais categorias mais cresceram em certa área?
- Quais registros sustentam a conclusão?
- Existe histórico semelhante para o caso consultado?
- Qual panorama resumido de uma região ou período?

## Pontos em Aberto

- Nome/posicionamento da empresa fictícia
- Escolha final da interface (Gradio vs frontend simples)
- Definição exata da primeira coleção de dados e filtros do MVP
- Tipos de documento textual para enriquecer o RAG
- Critérios de qualidade da resposta e formato mínimo das evidências
- Avaliação futura de datasets brasileiros

## Convenções para Agentes de Código

- Stack obrigatória: MinIO, PostgreSQL, Milvus, Ollama, FastAPI, MLflow
- Toda infraestrutura deve rodar via Docker Compose
- API deve expor documentação Swagger
- Respostas do RAG devem sempre incluir referência às fontes utilizadas
- Dados seguem o modelo de camadas: Bronze (bruto), Silver (tratado), Gold (consumo)
- Metadados e auditoria sempre no PostgreSQL, nunca apenas em memória
- Embeddings e busca vetorial no Milvus
- Inferência local via Ollama — sem chamadas a APIs externas de LLM
