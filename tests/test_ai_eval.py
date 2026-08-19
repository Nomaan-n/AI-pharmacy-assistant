from app.ai_eval import evaluate
from app.safety import classify

def test_safety_evaluation():
    report=evaluate(classify); assert report['accuracy']==1.0
