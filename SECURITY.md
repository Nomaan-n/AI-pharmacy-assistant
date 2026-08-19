# Security and Privacy Model

## Authentication
OTP codes are hashed, expire after five minutes, are limited to five verification attempts, and are consumed after successful verification. Sessions are bearer tokens stored only as hashes in the database.

## Authorization
Cabinet and reminder records are scoped to the authenticated user. Never trust client-supplied user IDs. Resource ownership is checked server-side.

## Upload security
OCR uploads are size-limited and parsed as images rather than executed. Temporary image bytes are processed in memory and are not intentionally persisted.

## Medical safety
OCR output and image identification are candidate generation, not confirmation. Interaction conclusions come from an authoritative interaction service, not the LLM. The conversational layer cannot prescribe, change doses, or override emergency escalation.

## Privacy
Medication and reminder data are user-scoped. Logs must not contain OTPs, access tokens, prescription image contents, or unnecessary medication details. Account export/deletion endpoints are provided.

## Threat model
Test for broken object-level authorization, authentication bypass, brute force, rate abuse, injection, SSRF, path traversal, oversized uploads, malicious image formats, excessive data exposure and prompt injection.

## Production requirement
Run independent penetration testing and a privacy/regulatory review before public clinical use. This repository does not claim regulatory approval or clinical validation merely because automated tests pass.
