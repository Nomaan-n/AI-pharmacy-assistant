import os
from fastapi import Request
from fastapi.responses import JSONResponse
MAX_REQUEST_BYTES=int(os.getenv('MAX_REQUEST_BYTES','12000000'))
async def request_size_guard(request:Request,call_next):
 length=request.headers.get('content-length')
 if length and int(length)>MAX_REQUEST_BYTES:return JSONResponse({'detail':'Request too large'},status_code=413)
 return await call_next(request)
