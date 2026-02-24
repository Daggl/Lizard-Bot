import httpx

url = "http://127.0.0.1:8000/api/ping"
try:
    r = httpx.get(url, timeout=5.0)
    print(r.status_code)
    print(r.text)
except Exception as e:
    print("error", e)
    raise
