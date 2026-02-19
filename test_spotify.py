from dotenv import load_dotenv
import os
import sys
import base64
import json
from urllib import request, parse

load_dotenv()

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

print("CLIENT ID set:", bool(CLIENT_ID))
print("CLIENT SECRET set:", bool(CLIENT_SECRET))

if not CLIENT_ID or not CLIENT_SECRET:
    print("Missing SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET in .env")
    sys.exit(2)

creds = f"{CLIENT_ID}:{CLIENT_SECRET}".encode("utf-8")
enc = base64.b64encode(creds).decode("ascii")
headers = {
    "Authorization": f"Basic {enc}",
    "Content-Type": "application/x-www-form-urlencoded",
}

data = parse.urlencode({"grant_type": "client_credentials"}).encode()
req = request.Request("https://accounts.spotify.com/api/token", data=data, headers=headers, method="POST")

try:
    with request.urlopen(req, timeout=15) as resp:
        status = resp.getcode()
        body = resp.read().decode("utf-8")
        print("HTTP", status)
        try:
            j = json.loads(body)
            print(json.dumps(j, indent=2))
        except Exception:
            print(body)
except Exception as e:
    print("Request failed:", e)
    sys.exit(1)
