# Evaluation

Run the deterministic safety regression suite with:

```bash
python evaluation/run_safety_eval.py
```

The cases are intentionally small and reproducible. They are not clinical validation. Add new cases whenever safety behavior changes.

For production evaluation, track retrieval hit rate, source coverage, unsafe-request handling, latency, and model errors over a versioned test set.
