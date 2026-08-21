from app.grounding import DailyMedRetriever


def test_does_not_guess_from_category_phrase():
    assert DailyMedRetriever._extract_medication_candidate("Should I stop taking my prescribed blood thinner?") is None


def test_extracts_known_medicine():
    assert DailyMedRetriever._extract_medication_candidate("What is amoxicillin used for?") == "amoxicillin"


def test_extracts_brand_style_question():
    assert DailyMedRetriever._extract_medication_candidate("What does Zerodol SP do?") == "Zerodol SP"


def test_rejects_stopword_candidate():
    assert DailyMedRetriever._extract_medication_candidate("What should I take for pain?") is None
