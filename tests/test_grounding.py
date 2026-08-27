import pytest
from app.india_drugs import IndiaDrugRegistry

def test_brand_normalization_does_not_merge_different_products():
    assert IndiaDrugRegistry.normalize_brand("Zerodol-SP") != IndiaDrugRegistry.normalize_brand("Zerodol Spas")

def test_composition_normalization_is_exact():
    assert IndiaDrugRegistry.normalize_composition("aceclofenac + paracetamol + serratiopeptidase") == IndiaDrugRegistry.normalize_composition("aceclofenac paracetamol serratiopeptidase")
    assert IndiaDrugRegistry.normalize_composition("aceclofenac + drotaverine hydrochloride") != IndiaDrugRegistry.normalize_composition("aceclofenac + paracetamol + serratiopeptidase")

def test_rxnorm_candidate_requires_high_confidence_and_name_match():
    from app.universal_drugs import UniversalDrugResolver
    safe={"score":"99.0","rxnormName":"Amoxicillin 500 MG Oral Capsule"}; wrong={"score":"99.0","rxnormName":"Amoxicillin-Clavulanate 875 MG Oral Tablet"}; low={"score":"84.0","rxnormName":"Amoxicillin 500 MG Oral Capsule"}
    assert UniversalDrugResolver._rxnorm_candidate_is_safe("amoxicillin",safe)
    assert not UniversalDrugResolver._rxnorm_candidate_is_safe("amoxicillin",wrong)
    assert not UniversalDrugResolver._rxnorm_candidate_is_safe("amoxicillin",low)

def test_openfda_matching_is_exact_for_identity():
    from app.universal_drugs import UniversalDrugResolver
    assert UniversalDrugResolver._openfda_match("amoxicillin",["amoxicillin"])
    assert not UniversalDrugResolver._openfda_match("amoxicillin",["amoxicillin clavulanate"])

def test_verified_brand_keys_keep_similar_indian_products_separate():
    from app.grounding import DailyMedRetriever
    assert DailyMedRetriever.VERIFIED_BRANDS["zerodolsp"]["generic_name"] != DailyMedRetriever.VERIFIED_BRANDS["zerodolspas"]["generic_name"]
    assert DailyMedRetriever.VERIFIED_BRANDS["suhagra50"]["strength"] == "50 mg"
    assert DailyMedRetriever.VERIFIED_BRANDS["suhagra100"]["strength"] == "100 mg"

def test_brand_key_normalization_handles_user_typing_variants():
    from app.grounding import DailyMedRetriever
    assert DailyMedRetriever._brand_key("Suhagra-50") == "suhagra50"
    assert DailyMedRetriever._brand_key("Zerodol SP") == "zerodolsp"
    assert DailyMedRetriever._brand_key("Zerodol Spas") == "zerodolspas"

def test_public_discovery_is_not_marked_as_indian_brand():
    from app.grounding import DailyMedRetriever
    assert not DailyMedRetriever._india_context({"brand_name":"Example","generic_name":"Example ingredient","source_type":"PubChem/NLM"})
