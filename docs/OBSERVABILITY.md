# Observability

The application uses structured Python logging and request timing without intentionally recording raw user health questions.

Recommended production signals:

- request count
- HTTP error rate
- p50/p95 latency
- grounding success rate
- LLM failure rate
- safety-classification outcomes
- source coverage

Do not collect patient identifiers or sensitive health content for portfolio analytics. If external monitoring is added, configure retention and privacy controls before collecting telemetry.
