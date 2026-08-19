# Security

Production must use HTTPS, PostgreSQL, secret environment variables, restricted CORS, edge rate limiting, least-privilege database credentials, backups, dependency updates, and log redaction.

Never commit OTP secrets, SMTP passwords, API keys, database credentials, prescription images, patient identifiers, or session tokens.

Every authenticated object lookup must enforce ownership. Prescription uploads are sensitive temporary data and should use private storage, short-lived access, malware/content-type validation, encryption, and automatic deletion.

The application must not claim diagnosis, prescribing, dose adjustment, or definitive identification from uncertain OCR/photo evidence.
