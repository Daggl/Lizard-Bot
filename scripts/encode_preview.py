from PIL import Image
import base64, os
p = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out_test_welcome.png'))
out = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out_test_welcome_preview.png'))
img = Image.open(p)
width = 900
ratio = img.height / img.width
img = img.resize((width, int(width * ratio)))
img.save(out)
with open(out, 'rb') as f:
    b = f.read()
print(base64.b64encode(b).decode('ascii'))
