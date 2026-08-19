from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)
def test_security_headers():
 r=client.get('/health'); assert r.headers['x-content-type-options']=='nosniff'; assert r.headers['x-frame-options']=='DENY'; assert 'x-request-id' in r.headers
def test_large_request_rejected():
 r=client.post('/api/chat',headers={'content-length':'20000000'},content=b'{}'); assert r.status_code==413
