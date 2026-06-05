from urban_lens.chat.routing import classify_query_intent


def test_classify_query_intent_routes_predictive_question() -> None:
    intent = classify_query_intent("What is the forecast for burglary next month in this area?")
    assert intent == "predictive_future"


def test_classify_query_intent_routes_factual_question() -> None:
    intent = classify_query_intent("Which area has the most burglary incidents this month?")
    assert intent == "factual_past_or_present"
