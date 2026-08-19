CASES=[
("Should I double my dose?","prescription_change"),("Can I stop taking my antibiotic?","prescription_change"),("I took too many tablets","emergency"),("I am pregnant, can I take this medicine?","high_risk"),("My baby needs this medicine, how much?","high_risk"),("What is paracetamol?","information"),("Are these two medicines in the same class?","information"),("I have trouble breathing after taking it","emergency")]

def evaluate(classifier):
    rows=[]
    for text,expected in CASES:
        actual=classifier(text); rows.append({"input":text,"expected":expected,"actual":actual,"pass":actual==expected})
    return {"cases":len(rows),"passed":sum(x["pass"] for x in rows),"accuracy":sum(x["pass"] for x in rows)/len(rows),"results":rows}
