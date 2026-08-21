test:
	pytest -q

safety:
	python evaluation/run_safety_eval.py

app:
	uvicorn app.main:app --reload
