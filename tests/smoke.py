"""Run inside web container after compose up; tests the public Nginx entry point."""
import json
import os
import uuid
import time
from pathlib import Path
import http.client

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.conf import settings


def request(path, headers=None):
    connection = http.client.HTTPConnection("nginx", timeout=10)
    try:
        connection.request("GET", path, headers={"Host": "localhost", **(headers or {})})
        response = connection.getresponse()
        return response.status, dict(response.headers), response.read()
    finally:
        connection.close()


for attempt in range(30):
    try:
        if request("/healthz")[0] == 200:
            break
    except (OSError, http.client.HTTPException):
        pass
    time.sleep(1)
else:
    raise RuntimeError("Nginx/backend readiness did not succeed within 30 seconds")
code, headers, body = request('/catalog.json')
assert code == 200, (code, body)
document = json.loads(body)
assert document['protoVersion'] == 1 and isinstance(document['apps'], list)
assert request('/catalog.json', {'If-None-Match': headers['ETag']})[0] == 304
# Nginx must overwrite a caller-supplied address, rather than trusting it.
assert request('/catalog.json', {'X-Real-IP': 'garbage'})[0] == 200
assert request('/static/admin/css/base.css')[0] == 200
name = 'smoke-' + uuid.uuid4().hex + '.apk'
path = Path(settings.MEDIA_ROOT) / 'assets' / name
path.parent.mkdir(parents=True, exist_ok=True)
try:
    path.write_bytes(b'0123456789')
    code, headers, body = request('/media/assets/' + name, {'Range': 'bytes=2-5'})
    assert (code, body) == (206, b'2345'), (code, body)
finally:
    path.unlink(missing_ok=True)
print('PASS: Nginx health, TVIP JSON, 304, address overwrite, admin static, media byte ranges')
