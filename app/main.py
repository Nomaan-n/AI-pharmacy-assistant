import os, asyncio, logging, time, uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .db import init_db
from .api import router as api_router
from .services_medication import rxnorm_search, interactions
from .reminder_worker import reminder_worker
from .core import request_size_guard
_worker_task=None
CURATED=[{'name':'Paracetamol','category':'Pain & fever','uses':['Fever','Mild to moderate pain'],'warning':'Do not exceed the product-label dose. Too much can seriously damage the liver.','tip':'Check combination cold or pain medicines for paracetamol.'},{'name':'Ibuprofen','category':'Pain & inflammation','uses':['Pain','Fever','Inflammation'],'warning':'NSAIDs can cause stomach, kidney and cardiovascular problems in some people.','tip':'Ask a pharmacist if you have ulcers, kidney disease, heart disease, take blood thinners, or are pregnant.'},{'name':'Cetirizine','category':'Allergy relief','uses':['Sneezing','Runny nose','Itching'],'warning':'Some people become sleepy or less alert.','tip':'See how it affects you before driving.'},{'name':'Loratadine','category':'Allergy relief','uses':['Sneezing','Runny nose','Itching'],'warning':'Drowsiness can occur in some people.','tip':'Check the label and other medicines with a pharmacist.'},{'name':'Omeprazole','category':'Acid reflux','uses':['Heartburn','Acid reflux'],'warning':'Persistent or severe symptoms need professional assessment.','tip':'Use according to product instructions or professional advice.'},{'name':'Amoxicillin','category':'Antibiotic','uses':['Certain bacterial infections'],'warning':'It does not treat viral illnesses. Serious allergic reactions are possible.','tip':'Use antibiotics only when appropriately prescribed or supplied.'},{'name':'Metformin','category':'Diabetes medicine','uses':['Type 2 diabetes','Blood glucose control'],'warning':'Suitability and dosing depend on the individual.','tip':'Take exactly as prescribed.'},{'name':'Atorvastatin','category':'Cholesterol medicine','uses':['Lowering cholesterol','Reducing cardiovascular risk'],'warning':'Unexplained severe muscle pain or weakness should be assessed promptly.','tip':'Tell your clinician about other medicines and supplements.'}]
@asynccontextmanager
async def lifespan(app):
 global _worker_task
 init_db(); _worker_task=asyncio.create_task(reminder_worker())
 try: yield
 finally:
  if _worker_task:_worker_task.cancel()
app=FastAPI(lifespan=lifespan,title='AI Pharmacy Assistant',version='4.1.0',description='Safety-first medication information and verification assistant.')
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','*').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=['GET','POST','DELETE'],allow_headers=['Authorization','Content-Type','X-Request-ID'])
app.middleware('http')(request_size_guard)
@app.middleware('http')
async def request_observability(request:Request,call_next):
 rid=request.headers.get('X-Request-ID') or uuid.uuid4().hex; started=time.perf_counter()
 try: response=await call_next(request)
 except Exception: logging.getLogger('pharmacy').exception('request_failed request_id=%s path=%s',rid,request.url.path); raise
 response.headers['X-Request-ID']=rid; response.headers['X-Content-Type-Options']='nosniff'; response.headers['X-Frame-Options']='DENY'; response.headers['Referrer-Policy']='no-referrer'; response.headers['Cache-Control']='no-store' if request.url.path.startswith('/api') else 'public, max-age=300'
 logging.getLogger('pharmacy').info('request_id=%s method=%s path=%s status=%s latency_ms=%.1f',rid,request.method,request.url.path,response.status_code,(time.perf_counter()-started)*1000)
 return response
@app.get('/',include_in_schema=False)
def root(): return FileResponse('static/index.html')
@app.get('/health')
def health(): return {'status':'healthy','version':app.version,'database':'configured' if os.getenv('DATABASE_URL') else 'local-fallback','safety':'enabled','observability':'enabled'}
@app.get('/metrics')
def metrics(): return {'service':'ai-pharmacy-assistant','status':'ok','observability':'request-id-and-structured-logging','safety':'authoritative-source-first'}
@app.get('/api/medicines')
def medicines(): return {'count':len(CURATED),'medicines':CURATED,'source':'Curated educational dataset + NIH RxNorm','live_lookup':True}
@app.get('/api/medicine/{medicine_name}')
def medicine(medicine_name:str):
 item=next((x for x in CURATED if x['name'].lower()==medicine_name.strip().lower()),None); matches=rxnorm_search(medicine_name)
 if item:return {**item,'found':True,'matches':matches[:20],'source':'Curated educational dataset + NIH RxNorm','verified_concept_only':True}
 return {'name':medicine_name,'found':bool(matches),'matches':matches[:20],'source':'NIH RxNorm','verified_concept_only':True}
@app.get('/api/search')
def search(q:str=Query(min_length=1,max_length=80)):
 results=rxnorm_search(q); return {'query':q,'count':len(results),'results':results,'source':'NIH RxNorm','verified_concept_only':True}
@app.get('/api/verify/{medicine_name}')
def verify_legacy(medicine_name:str):
 matches=rxnorm_search(medicine_name); return {'verified':bool(matches),'query':medicine_name,'match':matches[0] if matches else None,'confidence':'candidate' if matches else 'none','source':'NIH RxNorm','notice':'A medication concept match does not verify the physical package, prescription, dose, or patient suitability.'}
@app.get('/api/interactions')
def interactions_get(names:str=Query(min_length=3,max_length=500)):
 requested=[x.strip() for x in names.split(',') if x.strip()][:20]; recognized=[]
 for n in requested:
  m=rxnorm_search(n)
  if m:recognized.append(m[0])
 return {'requested':requested,'recognized':recognized,'result':interactions([x.get('rxcui') for x in recognized])}
app.include_router(api_router)
app.mount('/static',StaticFiles(directory='static'),name='static')
