# Personas e Usuários — Urban-Lens

## Stakeholders Principais

| Stakeholder | Interesse no projeto |
|-------------|---------------------|
| Analista de inteligência urbana | Usuário principal — consome respostas analíticas diariamente |
| Oficial de polícia / segurança | Usuário secundário — consulta históricos e contexto operacional |
| Gestor público / municipal | Usuário secundário — precisa de sínteses executivas para priorização |
| Equipe de desenvolvimento (grupo acadêmico) | Constrói e mantém a plataforma |
| Orientador / banca avaliadora | Avalia entregáveis acadêmicos e qualidade técnica |

---

## Persona 1 — Analista de Inteligência Urbana (Usuário Principal)

**Nome fictício:** Carla Mendes
**Cargo:** Analista de inteligência no observatório de segurança urbana
**Experiência:** 5 anos trabalhando com dados de criminalidade e relatórios para gestores

### Perfil

- Trabalha com planilhas, relatórios e dashboards de segurança pública
- Tem familiaridade com dados tabulares mas não é programadora
- Precisa cruzar informações de múltiplas fontes para produzir análises
- Rotina envolve responder demandas urgentes de gestores e produzir relatórios periódicos

### Objetivos

- Consultar tendências de crimes por região, período e categoria de forma rápida
- Comparar períodos e identificar padrões de aumento ou redução
- Obter respostas fundamentadas em dados concretos, não em suposições
- Produzir relatórios com evidências rastreáveis

### Dores

- Dados dispersos em múltiplas bases e formatos, sem camada unificada de consulta
- Tempo excessivo gasto em coleta e organização manual antes de conseguir analisar
- Dificuldade em rastrear qual dado sustenta cada conclusão de um relatório
- Falta de ferramenta que permita perguntas em linguagem natural sobre os dados disponíveis

### Cenários de Uso

| Cenário | Exemplo de consulta |
|---------|-------------------|
| Análise de tendência | "Quais regiões tiveram aumento de roubo nos últimos 6 meses?" |
| Comparação territorial | "Compare a evolução de crimes violentos entre Westminster e Camden" |
| Investigação de padrão | "Existe sazonalidade em furtos de veículos nesta área?" |
| Produção de relatório | "Resuma o panorama de segurança da região X no último trimestre" |

---

## Persona 2 — Oficial de Polícia / Segurança (Usuário Secundário)

**Nome fictício:** James Harlow
**Cargo:** Sargento de polícia em unidade de inteligência local
**Experiência:** 12 anos de serviço, últimos 3 em análise de inteligência criminal

### Perfil

- Foco operacional — precisa de informação rápida e contextualizada
- Não tem tempo para explorar dashboards complexos
- Valoriza respostas diretas com referência a casos e registros concretos
- Usa informação para briefings, planejamento de patrulha e alocação de recursos

### Objetivos

- Entender rapidamente o contexto histórico de uma área ou tipo de ocorrência
- Identificar ocorrências similares a um caso em investigação
- Obter dados que sustentem decisões de alocação de recursos
- Acessar informação sem depender de analistas ou equipe técnica

### Dores

- Informação chega filtrada e atrasada por depender de intermediários
- Sistemas existentes exigem conhecimento técnico para extrair dados úteis
- Falta de visão consolidada — precisa consultar múltiplos sistemas para montar o contexto
- Respostas genéricas sem apontar quais registros ou dados sustentam a conclusão

### Cenários de Uso

| Cenário | Exemplo de consulta |
|---------|-------------------|
| Contexto operacional | "Quais tipos de crime mais frequentes nesta área no último mês?" |
| Casos similares | "Há registros de ocorrências parecidas com este caso na região?" |
| Briefing rápido | "Resumo de atividade criminal na área X esta semana" |
| Alocação | "Quais horários e locais concentram mais ocorrências de roubo?" |

---

## Persona 3 — Gestor Público / Municipal (Usuário Secundário)

**Nome fictício:** Ricardo Alves
**Cargo:** Coordenador de segurança urbana na prefeitura
**Experiência:** 8 anos em gestão pública, responsável por políticas de segurança

### Perfil

- Perfil executivo — precisa de sínteses, não de dados brutos
- Toma decisões de priorização territorial e alocação de orçamento
- Apresenta resultados para secretários e prefeito
- Valoriza rankings, comparações e visualizações simples

### Objetivos

- Receber sínteses executivas sobre a situação de segurança por região
- Identificar onde concentrar atenção e recursos
- Acompanhar evolução de indicadores ao longo do tempo
- Ter evidências concretas para justificar decisões políticas

### Dores

- Relatórios chegam com atraso e sem padronização
- Dificuldade em obter visão comparativa entre regiões de forma rápida
- Dados disponíveis são técnicos demais para consumo executivo
- Falta de rastreabilidade entre a recomendação recebida e o dado que a sustenta

### Cenários de Uso

| Cenário | Exemplo de consulta |
|---------|-------------------|
| Priorização | "Quais 5 regiões merecem mais atenção este mês e por quê?" |
| Evolução | "Como evoluiu a segurança na região Y nos últimos 12 meses?" |
| Ranking | "Ranking de categorias de crime por volume na cidade" |
| Justificativa | "Quais dados sustentam a necessidade de reforço na área Z?" |

---

## Mapa de Dores e Necessidades por Persona

| Dor / Necessidade | Analista | Oficial | Gestor |
|-------------------|:--------:|:-------:|:------:|
| Dados dispersos e difíceis de consolidar | ✅ | ✅ | ✅ |
| Consulta em linguagem natural | ✅ | ✅ | ✅ |
| Rastreabilidade dado → resposta | ✅ | ✅ | ✅ |
| Respostas rápidas sem intermediários | — | ✅ | ✅ |
| Comparação entre regiões/períodos | ✅ | — | ✅ |
| Síntese executiva e rankings | — | — | ✅ |
| Identificação de padrões e tendências | ✅ | ✅ | — |
| Contexto histórico de ocorrências | ✅ | ✅ | — |
| Evidências para relatórios/decisões | ✅ | — | ✅ |
