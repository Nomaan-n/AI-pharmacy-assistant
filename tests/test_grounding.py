from app.grounding import DailyMedRetriever

def test_medication_extraction_known_name():
    assert DailyMedRetriever._extract_medication_candidate('What are side effects of ibuprofen?') == 'ibuprofen'

def test_context_selection():
    text = 'INDICATIONS AND USAGE This is an example. WARNINGS Use caution. ADVERSE REACTIONS Nausea may occur.'
    context = DailyMedRetriever._select_relevant_context(text, 'What are side effects?')
    assert 'ADVERSE REACTIONS' in context
