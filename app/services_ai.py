from .services_medication import rxnorm_search, fda_label
from .safety import classify
SAFETY='Medication information is educational. The assistant does not diagnose, prescribe, change doses, or confirm that a medicine is appropriate for a specific patient.'
def grounded_chat(message,medication=None):
 msg=message.strip(); kind=classify(msg)
 if not msg:return {'answer':'Please provide a medication or question.','sources':[],'safety':SAFETY,'escalated':False}
 if kind=='emergency':return {'answer':'This may be an emergency. Do not use an AI assistant to decide what to do. Seek urgent medical care or contact your local emergency or poison service now.','sources':[],'safety':SAFETY,'escalated':True,'reason':'emergency'}
 if kind=='prescribing':return {'answer':'I cannot prescribe, stop, start, or change a medication or dose. A prescriber or pharmacist must make that decision using your clinical details.','sources':[],'safety':SAFETY,'escalated':True,'reason':'prescribing_request'}
 terms=[x.strip() for x in (medication or '').split(',') if x.strip()][:3]; evidence=[]; sources=[]
 for term in terms:
  matches=rxnorm_search(term)
  if matches:
   evidence.append(matches[0]); sources.append('NIH RxNorm'); label=fda_label(matches[0]['name'])
   if label:evidence.append(label); sources.append('U.S. FDA openFDA')
 if evidence: answer='I found authoritative medication evidence for the supplied medication name. I can explain that evidence, but I will not invent clinical facts or give an individualized treatment decision.'
 else: answer='I could not verify a medication concept from the connected authoritative sources. I will not guess. Check the original package or prescription and consult a pharmacist.'
 return {'answer':answer,'evidence':evidence[:6],'sources':sorted(set(sources)),'safety':SAFETY,'escalated':False}
