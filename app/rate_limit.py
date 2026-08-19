import time
from collections import defaultdict, deque
from fastapi import HTTPException
_buckets=defaultdict(deque)
LIMITS={"/api/auth/request-otp":(5,300),"/api/ocr/image":(20,300),"/api/ocr/prescription":(10,300),"/api/identify/photo":(10,300),"/api/chat":(30,300)}
def check(key,path):
    limit,window=LIMITS.get(path,(120,60)); now=time.time(); q=_buckets[(key,path)]
    while q and q[0] <= now-window: q.popleft()
    if len(q)>=limit: raise HTTPException(429,"Rate limit exceeded. Try again later.")
    q.append(now)
