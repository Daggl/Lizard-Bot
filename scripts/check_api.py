import httpx

BASE = "http://127.0.0.1:8000"
ENDPOINTS = [
    ("/api/ping", "ping"),
    ("/api/fonts", "fonts"),
    ("/api/guilds/123/config", "guild_config_123"),
]

def fetch(path):
    url = BASE + path
    try:
        r = httpx.get(url, timeout=5.0)
        print(path, r.status_code, r.text)
    except Exception as e:
        print(path, "error", e)

def main():
    for p, _ in ENDPOINTS:
        fetch(p)

if __name__ == "__main__":
    main()
