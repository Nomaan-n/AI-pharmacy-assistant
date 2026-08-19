# Validation Plan

Automated tests validate API behavior and safety routing. They do not constitute clinical validation.

## OCR benchmark
Create a de-identified, consented corpus covering printed labels, prescriptions, Indian brand packaging, low light, glare, blur, rotation, mixed languages, handwriting and abbreviations. Record character error rate, word error rate and field-level extraction accuracy.

## Medicine identification benchmark
Measure top-1/top-5 candidate precision, recall, false confirmation rate and abstention rate. A false positive confirmation is safety-critical and should have a stricter threshold than a missed candidate.

## Prescription parsing
Measure medicine-name, strength, route, frequency, duration and quantity extraction separately. Ambiguous handwriting must produce an abstention/uncertain state.

## Interaction engine
Use authoritative test fixtures and verify exact input normalization, pair coverage, unavailable-source behavior and no-LLM fallback.

## AI safety evaluation
Run adversarial cases for overdose, emergency symptoms, dose changes, pregnancy, pediatrics, contraindications, interaction questions, prompt injection and unsupported medication names.

## Release gate
Do not label a feature clinically validated without a documented dataset, methodology, independent review and measured results.
