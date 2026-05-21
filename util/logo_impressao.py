import os
import base64
import mimetypes

def img_base64(path):
    if not path or not os.path.exists(path):
        return None

    with open(path, "rb") as img:
        encoded = base64.b64encode(img.read()).decode()

    mime, _ = mimetypes.guess_type(path)

    return f"data:{mime};base64,{encoded}"