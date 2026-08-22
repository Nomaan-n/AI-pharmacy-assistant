from app.grounding import DailyMedRetriever
from app.india_drugs import IndiaDrugRegistry


def test_does_not_guess_from_category_phrase():
    assert DailyMedRetriever._extract_medication_candidate("Should I stop taking my prescribed blood thinner?") is None


def test_extracts_known_medicine():
    assert DailyMedRetriever._extract_medication_candidate("What is amoxicillin used for?") == "amoxicillin"


def test_extracts_brand_style_question():
    assert DailyMedRetriever._extract_medication_candidate("What does Zerodol SP do?") == "zerodol sp"


def test_rejects_stopword_candidate():
    assert DailyMedRetriever._extract_medication_candidate("What should I take for pain?") is None


def test_brand_normalization_does_not_merge_different_products():
    assert IndiaDrugRegistry.normalize_brand("Zerodol SP") != IndiaDrugRegistry.normalize_brand("Zerodol Spas")


def test_composition_normalization_is_exact():
    assert IndiaDrugRegistry.normalize_composition("aceclofenac + paracetamol + serratiopeptidase") == IndiaDrugRegistry.normalize_composition("aceclofenac paracetamol serratiopeptidase")
    assert IndiaDrugRegistry.normalize_composition("aceclofenac + drotaverine hydrochloride") != IndiaDrugRegistry.normalize_composition("aceclofenac + paracetamol + serratiopeptidase")
