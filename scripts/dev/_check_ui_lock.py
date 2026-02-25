import socket, sys
try:
    s = socket.create_connection(("127.0.0.1", 8766), timeout=1)
    print("LOCK_BOUND")
    s.close()
except Exception as e:
    print("NO_LOCK", e)
