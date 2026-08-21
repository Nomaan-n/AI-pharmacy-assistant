import json
from pathlib import Path
from app.safety import assess

cases = json.loads(Path(__file__).with_name('cases.json').read_text())
passed = 0
for case in cases:
    actual, _ = assess(case['question'])
    ok = actual == case['expected']
    passed += ok
    print(('PASS' if ok else 'FAIL'), case['question'], '=>', actual)
print(f'\nSafety evaluation: {passed}/{len(cases)} passed')
raise SystemExit(0 if passed == len(cases) else 1)
