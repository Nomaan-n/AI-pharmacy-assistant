# Production Readiness

Before public deployment:
1. Provision managed PostgreSQL and encrypted backups.
2. Configure a real OTP/notification provider through Render secrets.
3. Restrict CORS to the actual frontend origin.
4. Enable TLS-only access and secure headers at the platform edge.
5. Run dependency/container vulnerability scanning.
6. Run API authorization and penetration testing against a staging deployment.
7. Load-test OCR and AI endpoints with rate limits enabled.
8. Verify database backup restore, migration rollback and disaster recovery.
9. Establish log retention and deletion rules that exclude sensitive medical content.
10. Complete privacy, clinical and regulatory review before clinical/commercial claims.
11. Monitor health, latency, errors, external-source failures, OCR failures and safety escalations.
12. Maintain a documented incident-response process.
