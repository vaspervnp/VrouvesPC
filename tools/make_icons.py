"""Make the icons from the Blender render art/icon_1024.png (tools/blender/icon_blender.py):
art/icon.png (256, the Godot project and macOS export), art/icon.ico (Windows, 16-256)
and installer/Assets/icon.ico + icon.png for the setup program.

    .venv/bin/python tools/make_icons.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = Image.open(os.path.join(ROOT, "art", "icon_1024.png")).convert("RGBA")
sizes = [16, 24, 32, 48, 64, 128, 256]

src.resize((256, 256), Image.LANCZOS).save(os.path.join(ROOT, "art", "icon.png"))
src.resize((512, 512), Image.LANCZOS).save(os.path.join(ROOT, "art", "icon_512.png"))
src.save(os.path.join(ROOT, "art", "icon.ico"), sizes=[(s, s) for s in sizes])

assets = os.path.join(ROOT, "installer", "Assets")
os.makedirs(assets, exist_ok=True)
src.save(os.path.join(assets, "icon.ico"), sizes=[(s, s) for s in sizes])
src.resize((256, 256), Image.LANCZOS).save(os.path.join(assets, "icon.png"))
print("icons written")
