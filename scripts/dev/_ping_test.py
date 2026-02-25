import socket, json, sys
try:
    s = socket.create_connection(("127.0.0.1", 8765), timeout=1)
    s.sendall((json.dumps({"action": "ping"}) + "\n").encode())
    data = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        data += chunk
        if b"\n" in data:
            break
    line = data.split(b"\n", 1)[0]
    try:
        print(line.decode())
    except Exception:
        print(repr(line))
except Exception as e:
    print("ERROR:", e)
