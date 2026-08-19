# Intended Use and Safety Boundaries

AI Pharmacy Assistant is designed as an educational medication-information and medication-organization tool. It can search medication concepts, retrieve source-backed information, process user-supplied images into OCR candidates, organize a personal medicine cabinet, check medication concepts against an authoritative interaction service, and explain retrieved evidence.

It is not intended to diagnose disease, prescribe medication, independently confirm a prescription, determine patient-specific dosing, replace a pharmacist/clinician, or make emergency treatment decisions.

## Verification states
- OCR candidate: text extracted from an image; not verified.
- Concept candidate: possible medication concept returned by a normalized database.
- Concept verified: a source database has a matching concept.
- Physical product verified: NOT established by RxNorm alone.
- Prescription verified: NOT established by OCR alone.
- Patient suitability verified: NOT established by this system.

## Safety principle
Authoritative sources determine medication facts and interaction results. AI may explain retrieved evidence but must not invent missing facts. Uncertain or unavailable evidence is surfaced explicitly.

## Regulatory note
Intended use and regulatory classification must be reviewed by qualified counsel and appropriate regulatory/clinical professionals before commercial clinical deployment. Software that analyzes medical images or provides patient-specific clinical decision support may have additional regulatory implications.
