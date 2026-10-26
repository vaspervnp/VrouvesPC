"""The title picture of LET'S GO FOR VROUVES (PC): the villagers of Zoniana lined up in
front of the kafenio and their sacks of vrouves, facing the F&M invaders coming down the
road. The game writes the title over the sky.

Run inside Blender with tools/blender on sys.path; renders to art/title.png.
"""
import math
import os

import bpy

import models as m
from blender_toon import R, Toon

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "title.png")

# grouping of models, borrowed from the sprite rig
Toon.begin = m.Rig.begin
Toon.end = m.Rig.end

prev = bpy.context.window.scene
t = Toon("VrouvesTitle", size=(1280, 1024), line=2.2, sky=(0.35, 0.65, 1.0))

# land, mountains, a smiling sun
bpy.ops.mesh.primitive_plane_add(size=120, location=(0, 30, 0))
t.put(bpy.context.object, "grass").name = "Ground"
for i, (x, y, s) in enumerate([(-30, 70, 22), (-8, 78, 28), (16, 72, 24), (38, 70, 20)]):
    t.cyl("Mount%d" % i, (x, y, s * 0.5), s, s, "mount", verts=7, r2=0)
    t.cyl("Snow%d" % i, (x, y, s * 0.86), s * 0.29, s * 0.28, "snow", verts=7, r2=0)
t.sphere("Sun", (17, 50, 22), (3.0, 0.6, 3.0), "yellow")
t.torus("Sun_smile", (17, 49.3, 21.3), 1.2, 0.15, "black", rot=(R(90), 0, 0), half=True)
for sd in (-1, 1):
    t.sphere("Sun_eye%d" % sd, (17 + sd * 1.0, 49.3, 22.7), (0.3, 0.12, 0.42), "black")

# the road winding down from the hills
t.box("Road", (12.5, 20, 0.02), (4.0, 50, 0.04), "dirt", rot=(0, 0, R(-22)))
for k in range(12):
    t.sphere("Pebble%d" % k, (9 + k * 1.0 + math.sin(k) * 0.8, 2 + k * 2.6, 0.06), (0.18, 0.25, 0.06), "dirt2")

# the kafenio on the left
t.box("Kaf", (-10, 14, 2.6), (9, 5, 5.2), "plaster")
roof = t.cyl("Kaf_roof", (-10, 14, 5.75), 3.2, 9.6, "tile", verts=3, rot=(0, R(-90), 0))
roof.scale = (0.38, 1.0, 1.0)
t.box("Kaf_sign", (-10, 11.4, 4.3), (5.0, 0.12, 0.9), "shutter")
t.text("Kaf_txt", "ΚΑΦΕΝΕΙΟ", (-10, 11.3, 4.3), 0.7, "white", extrude=0.01)
for k, x in enumerate((-13.0, -7.0)):
    t.box("Kaf_win%d" % k, (x, 11.45, 2.2), (1.4, 0.06, 1.6), "glass")
    for sd in (-1, 1):
        t.box("Kaf_sh%d_%d" % (k, sd), (x + sd * 1.0, 11.4, 2.2), (0.6, 0.06, 1.7), "shutter")
t.box("Kaf_door", (-10, 11.45, 1.3), (1.4, 0.08, 2.6), "shutter")
for k in range(7):
    t.box("Awn%d" % k, (-13.6 + k * 1.2, 10.4, 3.4), (0.6, 2.2, 0.1), "shutter" if k % 2 == 0 else "white",
          rot=(R(-14), 0, 0))
m.olive_tree(t, "Olive", -17, 12, 1.8)
m.cypress(t, "Cyp", -4.5, 16, 1.5)

# the sacks of vrouves in front of the kafenio
for k, (x, y) in enumerate([(-12.5, 8.5), (-11.2, 8.0), (-9.8, 8.6), (-11.8, 9.6), (-10.4, 9.8)]):
    t.begin()
    m.sack(t, "Sack%d" % k)
    t.end("SackG%d" % k, (x, y, 0), turn=(k - 2) * 12, scale=1.1)

# the defenders in a row, looking right at the invaders
z0 = 0.0
t.cretan("Cretan", -6.5, 5.0, z0, look=(0.7, 0))
m.rifle(t, "CretanR", -6.1, 5.0, 1.5)
t.yiayia("Yiayia", -9.6, 4.2, z0, look=(0.6, 0.2))
t.cyl("Yiayia_staff", (-8.9, 3.85, 1.25), 0.07, 2.5, "wood", rot=(0, R(-8), 0), verts=10)
t.bride("Bride", -3.4, 4.0, z0, look=(0.8, 0.1))
t.baker("Baker", -12.8, 5.5, z0, look=(0.7, 0.2))
t.psssst("Ps", -5.0, 3.0, 3.9, look=(0.8, -0.2))
t.begin()
m.cauldron(t, "Caul")
t.end("CaulG", (-0.5, 2.6, 0), scale=0.9)

# the invaders on the road
t.begin()
m.tank(t, "Tank", frame=0)
t.end("TankG", (9.5, 9.0, 0), turn=60, scale=1.5)
t.begin()
m.guard(t, "Guard", frame=1)
t.end("GuardG", (5.0, 4.5, 0), turn=55, scale=1.15)
t.begin()
m.guard(t, "Guard2", frame=0)
t.end("Guard2G", (7.0, 7.0, 0), turn=60, scale=1.1)
for k, (x, y, z) in enumerate([(4.0, 8.0, 3.2), (8.5, 4.0, 4.4), (12.5, 12.0, 5.0)]):
    t.begin()
    m.drone(t, "Drone%d" % k, frame=k % 2, z=0)
    t.end("DroneG%d" % k, (x, y, z), turn=50 + k * 10, scale=1.2)

t.camera((0.0, -14.0, 6.5), (R(80), 0, 0), lens=26, shift_y=0.1)
t.render(OUT)
bpy.context.window.scene = prev
result = {"out": OUT, "objects": len(t.col.objects)}
