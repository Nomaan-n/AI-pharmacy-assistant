"""Run lightweight deterministic safety regression checks."""
import json
from app.safety import classify_message

with open("evaluation/safety_cases.json", encoding="utf-8") as handle:
    cases = json.load(handle)

passed = 0
for case in cases:
    result = classify_message(case["message"])
    ok = result.category == case["expect"]
    print(f"{'PASS' if ok else 'FAIL'} | {case['message']} | {result.category}")
    passed += ok

print(f"Safety regression: {passed}/{len(cases)} passed")
raise SystemExit(0 if passed == len(cases) else 1)
