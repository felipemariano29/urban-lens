# Backlog Inicial

Visão consolidada do backlog ativo do Urban-Lens após a simplificação e fusão de tasks no Linear.

Critérios usados nesta visão:

- Inclui apenas itens ativos (`Backlog` ou `Todo`)
- Não inclui itens em `Done` ou `Duplicate`
- Mantém a distribuição por preferência de domínio
- Reflete a consolidação mais recente, incluindo MLflow com Lucas Ferreira

| Assignee | Foco principal | Epics ativas | Entregas ativas |
| --- | --- | --- | --- |
| Felipe Mariano | Produto e arquitetura macro | `RAG-12` Produto e Planejamento<br>`RAG-13` Arquitetura e Infraestrutura | `RAG-225` Definir e documentar arquitetura da solução |
| Kaique Govani | Governança, Medallion e contratos transversais | `RAG-14` Governança e Medallion | `RAG-229` Definir arquitetura Medallion e governança<br>`RAG-230` Implementar pipeline Medallion<br>`RAG-231` Documentar governança Medallion<br>`RAG-266` Definir contrato de metadados, lineage e acesso |
| Lucas Ferreira | MLflow, experimentação e avaliação | `RAG-20` MLflow e Avaliação | `RAG-251` Configurar MLflow e organizar tracking<br>`RAG-272` Definir benchmark, treinar e comparar modelos<br>`RAG-253` Consolidar e documentar resultados |
| Lucas Marques | Metadados, embeddings e indexação | `RAG-15` Metadados e Catálogo<br>`RAG-16` Embeddings e Indexação | `RAG-237` Implementar pipeline de embeddings e indexação |
| Mateus Nauhan | RAG core, evidências e metadados técnicos no chat | `RAG-17` RAG Core | `RAG-233` Documentar modelo relacional de metadados<br>`RAG-239` Implementar pipeline de busca e recuperação<br>`RAG-240` Implementar geração de resposta com evidências<br>`RAG-242` Documentar fluxo RAG ponta a ponta<br>`RAG-269` Definir contrato de contexto, evidências e citações<br>`RAG-275` Integrar metadados técnicos e restrições de acesso no chat |
| João Rafael | API como entregável, documentação e entrega final | `RAG-18` API FastAPI<br>`RAG-23` Pitch e Entrega | `RAG-234` Preparar entregável AC1<br>`RAG-247` Definir e consolidar contrato e entregável da API<br>`RAG-256` Atualizar README com automação<br>`RAG-264` Consolidar documentação e entregáveis finais |
| Lucas de Moraes Silveira | Implementação backend e integração frontend/API | Nenhuma | `RAG-243` Implementar API FastAPI<br>`RAG-278` Integrar interface com API de consulta<br>`RAG-279` Implementar autorização por perfil nos endpoints |
| Diogo Francia | Direção de frontend e apresentação | `RAG-19` Interface | `RAG-248` Definir experiência e contrato da interface<br>`RAG-262` Preparar narrativa, slides e vídeo<br>`RAG-263` Validar demo e ensaiar |
| Milton Penha | Implementação visual e validação da interface | Nenhuma | `RAG-249` Implementar interface visual de consulta<br>`RAG-250` Testar e documentar interface |
| Raphael Okuyama | Infraestrutura e backend de metadados | Nenhuma | `RAG-227` Criar docker-compose com MinIO e PostgreSQL<br>`RAG-232` Modelar e implementar schema de metadados<br>`RAG-274` Expor metadados de experimentos via API interna |
| Nicolas Barsalini | Automação e base operacional do ambiente | `RAG-21` Automação | `RAG-226` Estruturar repositório e documentar setup do ambiente<br>`RAG-254` Criar Makefile com comandos operacionais |
| Diego Justino | Qualidade, testes e validação final | `RAG-22` Validação Final | `RAG-241` Validar fluxo RAG ponta a ponta<br>`RAG-255` Criar smoke tests dos fluxos principais<br>`RAG-257` Validar sistema ponta a ponta e refinar |

## Notas

- O bloco de MLflow foi consolidado em três entregas operacionais e ficou sob responsabilidade de `Lucas Ferreira`.
- O frontend foi segmentado entre definição da experiência (`Diogo`), implementação visual (`Milton`) e integração com a API (`Lucas de Moraes`).
- Governança transversal foi reduzida para uma entrega central em `RAG-266`.
- Tasks absorvidas na simplificação permanecem no Linear como `Duplicate`, preservando rastreabilidade sem poluir o backlog ativo.
