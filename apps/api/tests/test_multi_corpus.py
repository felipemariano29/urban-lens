"""Tests for multi-corpus retrieval architecture (Epic 7)."""

from __future__ import annotations

from urban_lens.rag.query_understanding import (
    CorpusSelection,
    QueryIntent,
    detect_query_intent,
    intent_to_corpus,
    preferred_knowledge_filters,
)


class TestQueryIntentDetection:
    """Test query intent classification including platform knowledge."""

    def test_platform_knowledge_mlflow(self) -> None:
        assert detect_query_intent("What MLflow experiments exist?") == "platform_knowledge"
        assert detect_query_intent("Show me the MLflow run metrics") == "platform_knowledge"
        assert detect_query_intent("Quais experimentos do MLflow estao disponiveis?") == "platform_knowledge"

    def test_platform_knowledge_urban_lens(self) -> None:
        assert detect_query_intent("How does Urban Lens work?") == "platform_knowledge"
        assert detect_query_intent("Como funciona o Urban-Lens?") == "platform_knowledge"
        assert detect_query_intent("What is the Urban Lens architecture?") == "platform_knowledge"

    def test_platform_knowledge_docs(self) -> None:
        assert detect_query_intent("Where is the documentation?") == "platform_knowledge"
        assert detect_query_intent("Show me the API endpoints") == "platform_knowledge"
        assert detect_query_intent("Como funciona a arquitetura?") == "platform_knowledge"

    def test_platform_knowledge_models(self) -> None:
        assert detect_query_intent("What are the model metrics?") == "platform_knowledge"
        assert detect_query_intent("Show forecast model hyperparameters") == "platform_knowledge"
        assert detect_query_intent("Quais sao as metricas do modelo treinado?") == "platform_knowledge"

    def test_platform_knowledge_exact_portuguese_questions(self) -> None:
        assert detect_query_intent("Quem e voce?") == "platform_knowledge"
        assert detect_query_intent("Quais modelos foram treinados e quais metricas foram utilizadas?") == "platform_knowledge"
        assert detect_query_intent("Qual foi o pre-processamento realizado nos dados?") == "platform_knowledge"

    def test_crime_type_listing_still_works(self) -> None:
        assert detect_query_intent("What crime types exist in London?") == "crime_type_listing"
        assert detect_query_intent("Quais tipos de crime foram registrados?") == "crime_type_listing"

    def test_dominant_crime_still_works(self) -> None:
        assert detect_query_intent("What is the dominant crime type?") == "dominant_crime"
        assert detect_query_intent("Qual e o crime mais comum?") == "dominant_crime"

    def test_comparison_still_works(self) -> None:
        assert detect_query_intent("Compare crime in 2023 vs 2024") == "comparison"
        assert detect_query_intent("Comparar crimes em janeiro versus fevereiro") == "comparison"

    def test_generic_fallback(self) -> None:
        assert detect_query_intent("Tell me about crime") == "generic"
        assert detect_query_intent("What happened last month?") == "generic"


class TestIntentToCorpus:
    """Test mapping from query intent to corpus selection."""

    def test_platform_knowledge_uses_knowledge_corpus(self) -> None:
        assert intent_to_corpus("platform_knowledge") == "knowledge"

    def test_crime_intents_use_crime_corpus(self) -> None:
        assert intent_to_corpus("crime_type_listing") == "crime"
        assert intent_to_corpus("dominant_crime") == "crime"
        assert intent_to_corpus("comparison") == "crime"

    def test_generic_uses_hybrid(self) -> None:
        assert intent_to_corpus("generic") == "hybrid"

    def test_faq_questions_prefer_platform_docs(self) -> None:
        filters = preferred_knowledge_filters("Qual foi o pre-processamento realizado nos dados?")
        assert filters == {"source_type": "docs", "document_category": "platform"}


class TestCorpusSelectionTypes:
    """Test corpus selection type annotations."""

    def test_corpus_selection_values(self) -> None:
        valid_selections: list[CorpusSelection] = ["crime", "knowledge", "hybrid"]
        for selection in valid_selections:
            assert selection in ("crime", "knowledge", "hybrid")

    def test_intent_values(self) -> None:
        valid_intents: list[QueryIntent] = [
            "crime_type_listing",
            "dominant_crime",
            "comparison",
            "platform_knowledge",
            "generic",
        ]
        for intent in valid_intents:
            assert intent in (
                "crime_type_listing",
                "dominant_crime",
                "comparison",
                "platform_knowledge",
                "generic",
            )
