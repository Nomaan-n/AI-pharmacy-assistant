# Evaluation Plan

The project uses layered evaluation rather than a single accuracy number.

## Safety

Measure correct handling of emergency symptoms, treatment-change requests, and other high-risk prompts.

## Grounding

Measure whether the retrieved medication context contains the evidence needed for the answer and whether a source is returned.

## Robustness

Include misspellings, brand/generic names, empty input, unrelated questions, API failures, and malformed model output.

## Performance

Record request latency and retrieval latency separately. Do not log raw health questions by default.

## Release gate

A release should not proceed if safety regression tests fail or if source attribution unexpectedly disappears for grounded medication questions.
