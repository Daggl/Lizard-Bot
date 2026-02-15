import base64, sys, os
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out_test_welcome.png'))
with open(p, 'rb') as f:
    b = f.read()
print(base64.b64encode(b).decode('ascii'))
