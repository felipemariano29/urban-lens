# Urban Lens

## Integrantes

| Nome | E-mail | RA |
|---|---|---:|
| Diego Justino da Silva | diegojsilva01@outlook.com | 223705 |
| Diogo Francia | diogofrancia2@gmail.com | 222558 |
| Felipe Augusto de Almeida Mariano | felipemariano99@gmail.com | 210045 |
| João Rafael Jordão Pereira | jrafael1504@gmail.com | 211903 |
| Kaique Medeiros Govani | kaique.govani@hotmail.com | 210170 |
| Lucas Da Silva Marques | lucasses10@gmail.com | 223402 |
| Lucas de Moraes Silveira | lucasdmsilveira@gmail.com | 211668 |
| Lucas Ferreira Neto | ferreiranetolucas@gmail.com | 223026 |
| Mateus Nauhan Vieira Matos | mateusnauhan@gmail.com | 211931 |
| Milton Rogerio Dotto Penha Junior | miltonjmiltonj@gmail.com | 222284 |
| Nicolas Leonardi Barsalini | nicolasbarsalini2017@gmail.com | 222259 |
| Raphael Nobuyuki Haga Okuyama | raphaelokuyuama123@gmail.com | 222808 |

---

## 1. Sobre o projeto

O **Urban Lens** é uma plataforma **RAG (Retrieval-Augmented Generation)** local, desenvolvida para apoiar a **inteligência da prefeitura** na análise de dados públicos de segurança urbana. A solução tem como objetivo organizar, tratar, indexar e disponibilizar consultas em linguagem natural sobre dados públicos, permitindo que gestores e analistas obtenham respostas rápidas e contextualizadas para apoiar decisões de prevenção, planejamento territorial e formulação de políticas públicas.

A proposta do projeto utiliza como base dados públicos do [DATA.POLICE.UK](https://data.police.uk/data/), com foco em análise histórica e apoio estratégico, e não em operação policial em tempo real.

---

## 2. Problema de negócio

Prefeituras e núcleos de inteligência urbana frequentemente possuem dificuldade em transformar grandes volumes de dados públicos em informações úteis, auditáveis e acessíveis para tomada de decisão.

Mesmo quando os dados estão disponíveis, eles geralmente se encontram:
- dispersos;
- pouco padronizados;
- difíceis de consultar;
- sem mecanismos de busca semântica;
- sem uma interface simples para uso por gestores e analistas.

Dessa forma, o projeto propõe uma plataforma capaz de consolidar esses dados em uma arquitetura governada, com recuperação inteligente de contexto e geração de respostas por meio de um modelo de linguagem local.

---

## 3. Objetivo

Desenvolver uma plataforma completa de **RAG local com governança de dados**, capaz de:

- ingerir dados públicos de segurança urbana;
- armazená-los em arquitetura **Medallion**;
- organizar metadados e versionamento;
- gerar embeddings e indexação vetorial;
- responder perguntas em linguagem natural;
- disponibilizar uma interface simples para consulta;
- manter toda a solução executável localmente com containers.

---

## 4. Domínio escolhido

O domínio escolhido para o projeto é **Inteligência Territorial para Prefeituras**, com foco em análise de segurança urbana baseada em dados públicos.

### Aplicações esperadas
A solução poderá apoiar a prefeitura em tarefas como:
- priorização territorial;
- análise histórica de ocorrências;
- identificação de padrões por bairro ou período;
- apoio à definição de ações preventivas;
- geração de relatórios para gestores públicos.

---

## 5. Empresa fictícia

**Urban Lens Analytics**

A empresa fictícia **Urban Lens Analytics** atua no desenvolvimento de soluções de inteligência urbana orientadas por dados, oferecendo ferramentas para análise territorial, observação de tendências e apoio estratégico à administração pública.

### Produto
**Urban Lens**

Produto voltado para consulta inteligente de dados e documentos, utilizando RAG e interface simples para auxiliar o núcleo de inteligência da prefeitura.

---

## 6. Arquitetura da solução

A arquitetura do projeto segue o modelo proposto em sala, contemplando as seguintes camadas:

### Camada de Dados
- **MinIO**: Data Lake com arquitetura Medallion
  - **Bronze**: dados brutos
  - **Silver**: dados tratados e padronizados
  - **Gold**: dados consolidados para consumo analítico

- **PostgreSQL**
  - metadados
  - auditoria
  - controle de versionamento

- **Milvus**
  - armazenamento vetorial
  - embeddings
  - recuperação semântica

### Camada de IA
- **Ollama**
  - inferência local com LLM
  - modelo de embeddings

- **Pipeline RAG**
  - chunking
  - embedding
  - indexação
  - recuperação
  - geração de resposta

### Camada de MLOps
- **MLflow**
  - tracking de experimentos
  - métricas
  - versionamento de prompts
  - acompanhamento de testes

### Camada de Aplicação
- **FastAPI**
  - endpoints da aplicação
  - integração com o pipeline RAG

- **Gradio**
  - interface simples de consulta para o usuário final

### Infraestrutura
- **Docker**
- **Docker Compose**
- **Makefile**

---

## 7. Tecnologias utilizadas

- Python
- FastAPI
- Gradio
- PostgreSQL
- MinIO
- Milvus
- Ollama
- MLflow
- Docker
- Docker Compose
- Makefile

---

## 8. Fonte de dados

O projeto utilizará dados públicos do **DATA.POLICE.UK**, que disponibiliza informações históricas relacionadas à segurança pública, como:
- crimes em nível de rua;
- outcomes;
- stop and search;
- prioridades de neighbourhood;
- informações por força policial e região.

Esses dados serão usados para apoiar análises históricas e territoriais no contexto da inteligência municipal.

---

## 9. Público-alvo

A solução é voltada principalmente para:
- analistas de inteligência da prefeitura;
- gestores públicos;
- secretarias municipais;
- observatórios urbanos;
- equipes de planejamento territorial.

## 📚 Documentation Hub

| Documento | Descrição |
|----------|------------|
| [How to run](docs/how-to-run.md) | Setup e subir o ambiente |
| [Populate DB](docs/how-to-populate-db.md) | Script de inicialiazação do banco de dados |
| [Product Vision](docs/product-vision.md) | Overview do projeto |
| [Full Document (PDF)](docs/urban_lens_visao_consolidada.pdf) | Especificação de projeto completa |
