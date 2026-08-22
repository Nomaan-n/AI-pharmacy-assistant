import pytest

from app.india_drugs import IndiaDrugRegistry


def test_brand_normalization_does_not_merge_different_products():
    assert IndiaDrugRegistry.normalize_brand("Zerodol-SP") != IndiaDrugRegistry.normalize_brand("Zerodol Spas")


def test_composition_normalization_is_exact():
    assert IndiaDrugRegistry.normalize_composition("aceclofenac + paracetamol + serratiopeptidase") == IndiaDrugRegistry.normalize_composition("aceclofenac paracetamol serratiopeptidase")
    assert IndiaDrugRegistry.normalize_composition("aceclofenac + drotaverine hydrochloride") != IndiaDrugRegistry.normalize_composition("aceclofenac + paracetamol + serratiopeptidase")


def test_rxnorm_candidate_requires_high_confidence_and_name_match():
    from app.universal_drugs import UniversalDrugResolver

    safe = {"score": "99.0", "rxnormName": "Amoxicillin 500 MG Oral Capsule"}
    wrong = {"score": "99.0", "rxnormName": "Amoxicillin-Clavulanate 875 MG Oral Tablet"}
    low_score = {"score": "84.0", "rxnormName": "Amoxicillin 500 MG Oral Capsule"}

    assert UniversalDrugResolver._rxnorm_candidate_is_safe("amoxicillin", safe)
    assert not UniversalDrugResolver._rxnorm_candidate_is_safe("amoxicillin", wrong)
    assert not UniversalDrugResolver._rxnorm_candidate_is_safe("amoxicillin", low_score)


def test_openfda_matching_is_exact_for_identity():
    from app.universal_drugs import UniversalDrugResolver

    assert UniversalDrugResolver._openfda_match("amoxicillin", "generic_name", ["Some Brand"], ["amoxicillin"])
    assert not UniversalDrugResolver._openfda_match("amoxicillin", "generic_name", ["Some Brand"], ["amoxicillin clavulanate"])


def test_known_indian_brands_are_exact_and_distinct():
    assert IndiaDrugRegistry.normalize_brand("Zerodol-SP") != IndiaDrugRegistry.normalize_brand("Zerodol-Spas")
    assert IndiaDrugRegistry.normalize_brand("Suhagra-50") == IndiaDrugRegistry.normalize_brand("Suhagra 50")
    assert IndiaDrugRegistry.normalize_brand("Augmentin 625 Duo") != IndiaDrugRegistry.normalize_brand("Augmentin 1g Duo")


def test_brand_aliases_keep_strengths_separate():
    from app.india_drugs import BRAND_ALIASES
    assert BRAND_ALIASES["zerodolspas"] == "zerodolspas"
    assert BRAND_ALIASES["suhagra50mg"] == "suhagra50"
    assert BRAND_ALIASES["suhagra100mg"] == "suhagra100"
    assert BRAND_ALIASES["augmentin625"] == "augmentin625duo"
    assert BRAND_ALIASES["augmentin1g"] == "augmentin1gduo"
