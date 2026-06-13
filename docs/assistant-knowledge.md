# Urban Lens Assistant Knowledge

## Quem e voce

O Urban Lens e um assistente RAG local voltado para inteligencia urbana. Ele consulta evidencias indexadas da plataforma para responder perguntas sobre dados de criminalidade, sobre o pipeline analitico e sobre o processo de treinamento dos modelos. As respostas devem ser rastreaveis, citar evidencias e operar sem chamadas externas de LLM, usando Ollama, Milvus, PostgreSQL, MinIO, MLflow e FastAPI dentro da stack local.

## Quais modelos foram treinados e quais metricas foram utilizadas

O pipeline baseline de previsao do Urban Lens avalia tres candidatos supervisionados de regressao: Ridge, RandomForestRegressor e ExtraTreesRegressor. Todos sao treinados sobre o mesmo conjunto Gold ML e comparados no mesmo holdout temporal. As metricas utilizadas sao MAE, RMSE e MAPE. O melhor modelo e selecionado pelo menor MAE no holdout e os resultados ficam registrados no MLflow e no catalogo de metadados.

## Qual foi o pre-processamento realizado nos dados

O pre-processamento ocorre em duas etapas. Na etapa Silver, os CSVs de crimes do DATA.POLICE.UK sao normalizados: nomes de colunas viram snake_case, crime_type e last_outcome_category viram chaves estaveis em lowercase, longitude e latitude sao convertidas para numerico, reference_month e inferido, record_hash deterministico e calculado e duplicatas sao removidas. Na etapa Gold ML, sao criadas features de atraso incident_count_lag_1, incident_count_lag_2 e incident_count_lag_3, medias moveis moving_avg_3 e moving_avg_6, tendencia trend_lag1_vs_lag3, campos sazonais month_number e quarter e razoes de qualidade como has_previous_outcome_ratio e missing_context_ratio. No treinamento, variaveis categoricas usam SimpleImputer com most_frequent e OneHotEncoder com handle_unknown=ignore, enquanto variaveis numericas usam SimpleImputer com fill_value=0.0.
