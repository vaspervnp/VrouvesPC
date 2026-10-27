"""The application icon: Psssst hovering over a sack of vrouves in flower, on a round
badge. Run inside Blender with tools/blender on sys.path; renders art/icon_1024.png with a
transparent background (tools/make_icons.py makes the .ico, .png and Linux sizes).
"""
import os

import bpy

import models as m
from blender_toon import R, Toon

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "icon_1024.png")

Toon.begin = m.Rig.begin
Toon.end = m.Rig.end

prev = bpy.context.window.scene
t = Toon("VrouvesIcon", size=(1024, 1024), line=4.5)
t.sc.render.film_transparent = True

# the badge: a green disc with a gold rim, standing up facing the camera
t.cyl("Badge", (0, 1.6, 2.1), 2.3, 0.3, "grass", rot=(R(70), 0, 0), verts=64)
t.torus("Rim", (0, 1.45, 2.15), 2.3, 0.16, "gold", rot=(R(70), 0, 0))
# the sack, big and full
t.begin()
m.sack(t, "Sack", label=False)
t.end("SackG", (0, 0.2, 0.35), scale=1.7)
# Psssst over it, winking at the greens
t.begin()
t.psssst("Ps", 0, 0, 0, look=(0.2, -0.5))
t.end("PsG", (0.15, -0.6, 3.1), turn=-10, scale=1.25)
for k, (x, z) in enumerate([(-1.4, 3.6), (1.45, 3.4), (-1.6, 1.2), (1.5, 1.4)]):
    t.sphere("Fl%d" % k, (x, -0.1, z), (0.13, 0.08, 0.13), "yellow")

t.camera((0, -11.3, 6.3), (R(70), 0, 0), lens=60)
t.sc.camera.data.type = "ORTHO"
t.sc.camera.data.ortho_scale = 5.5
t.render(OUT)
bpy.context.window.scene = prev
result = {"out": OUT}
