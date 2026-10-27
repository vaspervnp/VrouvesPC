"""The cast and props of LET'S GO FOR VROUVES (PC), built from blender_toon's primitives.

Every model is built around the origin, standing on z = 0 and facing -y (towards the
camera), so a parent empty can turn it to face any way.

Imported inside Blender with tools/blender on sys.path.
"""
import math

import bpy

import blender_toon
from blender_toon import R, Toon

blender_toon.C.update({
    "hazmat": (1.0, 0.82, 0.08), "eu": (0.02, 0.18, 0.62), "toxic": (0.45, 1.0, 0.1),
    "olive": (0.45, 0.6, 0.22), "olive2": (0.36, 0.5, 0.18), "stone": (0.8, 0.76, 0.66),
    "stone2": (0.62, 0.6, 0.55), "dirt": (0.82, 0.45, 0.16), "dirt2": (0.55, 0.28, 0.1),
    "sack": (0.85, 0.68, 0.42), "green": (0.18, 0.62, 0.15), "cypress": (0.1, 0.42, 0.18),
    "cactus": (0.42, 0.72, 0.25), "steel": (0.4, 0.43, 0.5), "suit": (0.3, 0.32, 0.38),
    "goat_b": (0.55, 0.33, 0.15), "horn": (0.85, 0.8, 0.65), "smoke": (0.7, 0.7, 0.72),
    "fire": (1.0, 0.35, 0.05), "pitch": (0.3, 0.75, 0.2), "pitch2": (0.26, 0.66, 0.17),
    "court": (0.85, 0.42, 0.25), "plaster": (0.98, 0.95, 0.88), "tile": (0.82, 0.3, 0.15),
    "shutter": (0.1, 0.45, 0.85), "water": (0.35, 0.7, 1.0), "gold": (1.0, 0.78, 0.15),
    "tomato": (0.95, 0.15, 0.08), "feta": (1.0, 1.0, 0.95), "rusk": (0.78, 0.5, 0.2),
    "lime": (0.75, 1.0, 0.3), "purple": (0.55, 0.25, 0.75), "grass2": (0.17, 0.6, 0.1),
})


class Rig(Toon):
    """A Toon scene with an orthographic camera tilted TILT degrees from straight down.

    One map cell is CELL world units wide and CELL / cos(TILT) deep, so that on the
    picture every cell is a PX x PX square; heights show at sin(TILT)."""

    CELL = 2.2
    TILT = 62
    PX = 128

    def __init__(self, scene_name, line=1.5):
        self.prev_scene = bpy.context.window.scene
        super().__init__(scene_name, size=(256, 256), line=line)
        sc = self.sc
        sc.render.film_transparent = True
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        try:
            sc.eevee.taa_render_samples = 16
        except AttributeError:
            pass
        self.a = R(self.TILT)
        self.depth = self.CELL / math.cos(self.a)
        bpy.ops.object.light_add(type="SUN", location=(0, -10, 10), rotation=(R(40), R(-20), R(-30)))
        self.sun = self.put(bpy.context.object)
        self.sun.name = scene_name + "_sun"
        self.sun.data.energy = 3
        bpy.ops.object.camera_add()
        self.cam = self.put(bpy.context.object)
        self.cam.name = scene_name + "_cam"
        self.cam.data.type = "ORTHO"
        self.cam.rotation_euler = (self.a, 0, 0)
        self.cam.data.clip_start = 0.1
        self.cam.data.clip_end = 400
        sc.camera = self.cam
        self.keep = {self.sun.name, self.cam.name}

    def restore(self):
        bpy.context.window.scene = self.prev_scene

    def clear(self):
        for ob in list(self.col.objects):
            if ob.name not in self.keep:
                data = ob.data
                bpy.data.objects.remove(ob, do_unlink=True)
                if data is not None and data.users == 0:
                    if isinstance(data, bpy.types.Mesh):
                        bpy.data.meshes.remove(data)
                    elif isinstance(data, bpy.types.Curve):
                        bpy.data.curves.remove(data)

    # -------------------------------------------------------------- framing
    def frame(self, w_px, h_px, ax, ay, origin=(0.0, 0.0)):
        """picture of w_px x h_px with the ground point origin at pixel (ax, ay)"""
        sc = self.sc
        sc.render.resolution_x, sc.render.resolution_y = int(w_px), int(h_px)
        u = self.CELL / self.PX                     # world units per pixel
        self.cam.data.ortho_scale = max(w_px, h_px) * u
        dx = (w_px / 2 - ax) * u                    # centre of the picture, from the origin
        dy = (ay - h_px / 2) * u
        ca, sa = math.cos(self.a), math.sin(self.a)
        cx, cy, cz = origin[0] + dx, origin[1] + dy * ca, dy * sa
        dist = 120
        self.cam.location = (cx, cy - sa * dist, cz + ca * dist)

    def world(self, col, row, rows=14):
        """ground centre of a map cell"""
        return ((col + 0.5) * self.CELL, (rows - row - 0.5) * self.depth)

    # -------------------------------------------------------------- grouping
    def begin(self):
        self._before = set(self.col.objects.keys())

    def end(self, name, loc=(0, 0, 0), turn=0.0, scale=1.0):
        """parent everything built since begin() to an empty, turned turn degrees about z"""
        new = [self.col.objects[k] for k in self.col.objects.keys() if k not in self._before]
        bpy.ops.object.empty_add(location=(0, 0, 0))
        e = self.put(bpy.context.object)
        e.name = name
        for ob in new:
            if ob.parent is None:
                ob.parent = e
        e.location = loc
        e.rotation_euler = (0, 0, R(turn))
        e.scale = (scale, scale, scale)
        return e

    def render_to(self, path):
        self.sc.render.filepath = path
        bpy.ops.render.render(write_still=True)


# ====================================================================== defenders

def rifle(t, p, x, y, z, ang=-35):
    t.box(p + "_stock", (x - 0.35, y - 0.55, z - 0.25), (0.18, 0.14, 0.45), "wood", rot=(0, R(ang), 0))
    t.cyl(p + "_barrel", (x + 0.15, y - 0.6, z + 0.35), 0.06, 1.3, "dark", rot=(0, R(ang), 0), verts=10)


def cretan(t, p="Cretan"):
    t.cretan(p, 0, 0, 0)
    t.sphere(p + "_hand", (0.45, -0.55, 1.3), (0.15, 0.15, 0.15), "skin")
    rifle(t, p, 0.4, 0, 1.5)
    for sd in (-1, 1):      # boots
        t.sphere(p + "_boot%d" % sd, (sd * 0.3, -0.15, 0.12), (0.22, 0.32, 0.14), "black")


def yiayia(t, p="Yiayia"):
    t.yiayia(p, 0, 0, 0)
    # the staff of chastisement
    t.cyl(p + "_staff", (0.72, -0.35, 1.25), 0.07, 2.5, "wood", rot=(0, R(-8), 0), verts=10)
    t.torus(p + "_crook", (0.62, -0.35, 2.52), 0.17, 0.07, "wood", rot=(R(90), 0, 0), half=True)
    t.sphere(p + "_hand", (0.7, -0.45, 1.35), (0.14, 0.14, 0.14), "skin")
    # the pot of bitter leaves
    t.cyl(p + "_pot", (-0.7, -0.45, 1.1), 0.32, 0.4, "black", r2=0.26)
    for k in range(5):
        a = k * 1.25
        t.sphere(p + "_leaf%d" % k, (-0.7 + math.cos(a) * 0.16, -0.45 + math.sin(a) * 0.14, 1.36),
                 (0.16, 0.12, 0.14), "green")
    t.sphere(p + "_flower", (-0.62, -0.55, 1.48), (0.07, 0.07, 0.07), "yellow")


def bride(t, p="Bride"):
    t.bride(p, 0, 0, 0)
    t.sphere(p + "_hand", (0.55, -0.6, 1.55), (0.13, 0.13, 0.13), "skin")
    t.box(p + "_gun", (0.62, -0.78, 1.68), (0.12, 0.35, 0.16), "dark")
    t.box(p + "_grip", (0.62, -0.66, 1.52), (0.1, 0.12, 0.25), "dark")
    # a bouquet in the other hand
    t.sphere(p + "_hand2", (-0.55, -0.55, 1.2), (0.13, 0.13, 0.13), "skin")
    for k in range(5):
        a = k * 1.25
        t.sphere(p + "_bq%d" % k, (-0.55 + math.cos(a) * 0.14, -0.6, 1.42 + math.sin(a) * 0.12),
                 (0.1, 0.1, 0.1), ("pink", "red", "white", "yellow", "pink")[k])


def psssst(t, p="Psssst", z=1.9):
    t.psssst(p, 0, 0, z)
    t.cyl(p + "_laser", (0, -0.55, z - 0.35), 0.08, 0.35, "red", rot=(R(90), 0, 0), verts=10)
    t.sphere(p + "_tip", (0, -0.75, z - 0.35), (0.1, 0.1, 0.1), "pink")


def baker(t, p="Baker"):
    t.baker(p, 0, 0, 0)
    # a dakos ready to throw, in the other hand
    t.sphere(p + "_hand2", (-0.7, -0.45, 1.6), (0.13, 0.13, 0.13), "skin")
    dakos(t, p + "_dk", -0.7, -0.55, 1.85, s=0.55)


def dakos(t, p, x, y, z, s=1.0):
    t.cyl(p + "_rusk", (x, y, z), 0.42 * s, 0.22 * s, "rusk")
    t.sphere(p + "_tom", (x, y, z + 0.12 * s), (0.36 * s, 0.36 * s, 0.08 * s), "tomato")
    for k in range(3):
        a = k * 2.1
        t.box(p + "_feta%d" % k, (x + math.cos(a) * 0.14 * s, y + math.sin(a) * 0.14 * s, z + 0.2 * s),
              (0.14 * s, 0.14 * s, 0.1 * s), "feta", rot=(0, 0, a))
    t.sphere(p + "_olive", (x + 0.05 * s, y - 0.02 * s, z + 0.26 * s), (0.07 * s, 0.07 * s, 0.07 * s), "black")


def cauldron(t, p="Cauldron", dented=False, bubble=0):
    for j, a in enumerate((20, -25, 75)):
        t.cyl(p + "_log%d" % j, (0, 0, 0.14), 0.12, 1.5, "brown", rot=(0, R(90), R(a)), verts=10)
    for j, a in enumerate((90, 210, 330)):
        t.cyl(p + "_leg%d" % j, (math.cos(R(a)) * 0.55, math.sin(R(a)) * 0.45, 0.4), 0.05, 0.8, "dark",
              verts=8)
    if not dented:
        for j, (dx, h, col) in enumerate([(-0.6, 0.6, "flame"), (-0.3, 0.85, "orange"),
                                          (0.0, 0.55, "red"), (0.3, 0.8, "flame"), (0.55, 0.6, "orange")]):
            t.cyl(p + "_flame%d" % j, (dx, -0.45 - 0.08 * (j % 2), 0.15 + h / 2), 0.17, h, col,
                  verts=10, r2=0, rot=(0, R((j % 3 - 1) * 8), 0))
        t.cyl(p + "_pot", (0, 0, 0.95), 0.75, 0.8, "black", r2=0.64)
        t.torus(p + "_rim", (0, 0, 1.35), 0.7, 0.07, "dark")
        t.sphere(p + "_brew", (0, 0, 1.33), (0.66, 0.66, 0.12), "toxic")
        for j in range(4):
            a = j * 1.6 + bubble
            r = 0.25 + 0.1 * ((j + bubble) % 2)
            t.sphere(p + "_bub%d" % j, (math.cos(a) * r, math.sin(a) * r * 0.8, 1.42 + 0.04 * j),
                     (0.12, 0.12, 0.12), "lime")
        # a skull-and-crossbones label: "unlicensed"
        t.sphere(p + "_skull", (0, -0.74, 1.0), (0.17, 0.05, 0.17), "white")
        for sd in (-1, 1):
            t.sphere(p + "_skeye%d" % sd, (sd * 0.06, -0.78, 1.03), (0.04, 0.02, 0.045), "black")
            t.box(p + "_bone%d" % sd, (0, -0.76, 0.85), (0.38, 0.03, 0.06), "white", rot=(0, R(sd * 30), 0))
        t.sphere(p + "_steam", (0.15, 0.1, 1.85), (0.28, 0.2, 0.22), "lime")
        t.sphere(p + "_steam2", (-0.2, 0.15, 2.15), (0.2, 0.15, 0.16), "lime")
    else:
        pot = t.cyl(p + "_pot", (0.1, 0, 0.6), 0.8, 0.5, "black", r2=0.75, rot=(R(10), R(18), 0))
        t.torus(p + "_rim", (0.18, 0.05, 0.86), 0.72, 0.07, "dark", rot=(R(10), R(18), 0))
        t.sphere(p + "_puddle", (-0.6, -0.5, 0.03), (0.6, 0.45, 0.03), "toxic")
        t.sphere(p + "_smoke", (0, 0.1, 1.4), (0.3, 0.25, 0.25), "smoke")
        t.sphere(p + "_smoke2", (0.25, 0.15, 1.8), (0.22, 0.18, 0.18), "smoke")
        for k in range(3):      # dizzy stars
            a = k * 2.1
            t.sphere(p + "_star%d" % k, (math.cos(a) * 0.5, math.sin(a) * 0.4 - 0.2, 1.3),
                     (0.1, 0.1, 0.1), "yellow")
        pot.scale = (1.0, 1.0, 0.75)


# ====================================================================== invaders

def eu_stars(t, p, x, y, z, r, s=0.05, axis="y"):
    for k in range(12):
        a = k * math.pi / 6
        if axis == "y":
            loc = (x + math.cos(a) * r, y, z + math.sin(a) * r)
        else:
            loc = (x + math.cos(a) * r, y + math.sin(a) * r, z)
        t.sphere(p + "_eu%d" % k, loc, (s, s, s), "yellow")


def drone(t, p="Drone", frame=0, z=1.7):
    """an F&M bio-drone: a grumpy one-eyed pod on four rotors"""
    head = ((0, 0, z), (0.58, 0.52, 0.45))
    t.sphere(p + "_body", *head, "steel")
    t.sphere(p + "_belly", (0, 0, z - 0.28), (0.42, 0.38, 0.2), "dark")
    t.cyl(p + "_band", (0, 0, z - 0.05), 0.6, 0.1, "eu")
    t.eye(p + "_eye", head, 0, 0.05, 0.27, look=(0, -0.3), pupil=0.55)
    # an angry brow, wobbling
    t.box(p + "_brow", (0, t.surface_y(head, 0, 0.32) - 0.06, z + 0.38), (0.55, 0.08, 0.1), "black",
          rot=(0, R(10 if frame else -10), 0))
    t.cyl(p + "_ant", (0.18, 0.1, z + 0.55), 0.03, 0.35, "dark", verts=6)
    t.sphere(p + "_bulb", (0.18, 0.1, z + 0.76), (0.09, 0.09, 0.09), "red" if frame else "pink")
    for k in range(4):
        a = R(45 + 90 * k)
        ax, ay = math.cos(a), math.sin(a)
        t.box(p + "_arm%d" % k, (ax * 0.55, ay * 0.5, z + 0.12), (0.5, 0.09, 0.07), "dark", rot=(0, 0, a))
        cx, cy = ax * 0.82, ay * 0.74
        t.cyl(p + "_rotor%d" % k, (cx, cy, z + 0.22), 0.3, 0.03, "silver", verts=20)
        spin = R(30 + 90 * frame + 45 * k)
        t.box(p + "_blade%d" % k, (cx, cy, z + 0.25), (0.55, 0.07, 0.02), "dark", rot=(0, 0, spin))
    # a herbicide drip under it
    t.cyl(p + "_nozzle", (0, 0, z - 0.45), 0.06, 0.2, "dark", verts=8)
    t.sphere(p + "_drip", (0, 0, z - 0.68 - 0.08 * frame), (0.07, 0.07, 0.11), "toxic")


def guard(t, p="Guard", frame=0):
    sw = 0.18 if frame == 0 else -0.18
    for sd in (-1, 1):
        y = sd * sw
        t.cyl(p + "_leg%d" % sd, (sd * 0.26, y, 0.38), 0.17, 0.6, "hazmat", verts=12)
        t.sphere(p + "_boot%d" % sd, (sd * 0.26, y - 0.08, 0.1), (0.2, 0.28, 0.12), "black")
    t.sphere(p + "_body", (0, 0, 1.15), (0.62, 0.55, 0.62), "hazmat")
    t.cyl(p + "_belt", (0, 0, 0.82), 0.6, 0.12, "black")
    # the herbicide tank on the back, with its hose
    t.cyl(p + "_tank", (0, 0.55, 1.3), 0.3, 0.9, "toxic")
    t.sphere(p + "_tank_top", (0, 0.55, 1.75), (0.3, 0.3, 0.12), "toxic")
    t.torus(p + "_hose", (0.5, 0.2, 1.2), 0.35, 0.05, "dark", rot=(0, R(90), 0))
    # EU badge on the chest
    t.cyl(p + "_badge", (0, -0.55, 1.3), 0.17, 0.05, "eu", rot=(R(90), 0, 0))
    eu_stars(t, p, 0, -0.59, 1.3, 0.11, 0.022)
    # the hood and the gas mask with its big goggles
    head = ((0, -0.02, 2.0), (0.55, 0.5, 0.52))
    t.sphere(p + "_hood", *head, "hazmat")
    for sd in (-1, 1):
        y = t.surface_y(head, sd * 0.2, 0.08)
        t.torus(p + "_goggle%d" % sd, (sd * 0.2, y - 0.03, 2.08), 0.15, 0.05, "dark", rot=(R(90), 0, 0))
    t.eye(p + "_eye_l", head, -0.2, 0.08, 0.13, look=(0.2, -0.3), pupil=0.4)
    t.eye(p + "_eye_r", head, 0.2, 0.08, 0.13, look=(-0.2, -0.3), pupil=0.4)
    y = t.surface_y(head, 0, -0.2)
    t.cyl(p + "_snout", (0, y - 0.1, 1.86), 0.14, 0.25, "steel", rot=(R(90), 0, 0), verts=12)
    t.cyl(p + "_filter", (0, y - 0.25, 1.86), 0.16, 0.08, "black", rot=(R(90), 0, 0), verts=12)
    # the weed-whacker, held across
    t.sphere(p + "_hand", (0.55, -0.45, 1.15), (0.14, 0.14, 0.14), "dark")
    t.cyl(p + "_pole", (0.4, -0.75, 0.8), 0.04, 1.4, "silver", rot=(R(-35), R(-20), 0), verts=8)
    t.cyl(p + "_head", (0.2, -1.2, 0.2), 0.2, 0.1, "red", verts=16)
    t.box(p + "_line", (0.2, -1.2, 0.18), (0.6, 0.03, 0.02), "white", rot=(0, 0, R(30 + 50 * frame)))


def tank(t, p="Tank", frame=0):
    for sd in (-1, 1):
        x = sd * 0.72
        t.box(p + "_tread%d" % sd, (x, 0, 0.32), (0.42, 1.9, 0.55), "dark")
        for k in range(4):
            y = -0.7 + k * 0.46
            t.cyl(p + "_wheel%d_%d" % (sd, k), (x + sd * 0.22, y, 0.3), 0.19, 0.06, "steel",
                  rot=(0, R(90), 0), verts=12)
        for k in range(6):      # the tread lugs move with the frame
            y = -0.9 + ((k * 0.36 + frame * 0.18) % 1.9)
            t.box(p + "_lug%d_%d" % (sd, k), (x, y, 0.62), (0.44, 0.08, 0.04), "black")
    t.box(p + "_hull", (0, 0.05, 0.85), (1.15, 1.55, 0.55), "eu")
    t.box(p + "_deck", (0, 0.1, 1.15), (1.0, 1.3, 0.08), "steel")
    eu_stars(t, p, 0, -0.75, 0.85, 0.18, 0.04)
    # the mower drum in front, blades spinning
    t.cyl(p + "_drum", (0, -1.12, 0.38), 0.28, 1.5, "red", rot=(0, R(90), 0), verts=16)
    for k in range(4):
        a = R(k * 90 + frame * 45)
        t.box(p + "_blade%d" % k, (0, -1.12 + math.sin(a) * 0.3, 0.38 + math.cos(a) * 0.3),
              (1.5, 0.05, 0.14), "silver", rot=(a, 0, 0))
    for sd in (-1, 1):
        t.box(p + "_arm%d" % sd, (sd * 0.62, -0.85, 0.55), (0.08, 0.5, 0.08), "steel", rot=(R(-30), 0, 0))
    # the turret, and the bureaucrat in the hatch
    t.cyl(p + "_turret", (0, 0.25, 1.35), 0.48, 0.35, "eu", verts=20)
    t.cyl(p + "_nozzle", (0.32, -0.45, 1.4), 0.07, 0.9, "silver", rot=(R(90), 0, 0), verts=10)
    t.sphere(p + "_spray", (0.32, -0.95, 1.35 - 0.05 * frame), (0.1, 0.1, 0.12), "toxic")
    t.cyl(p + "_suit", (0, 0.25, 1.72), 0.3, 0.45, "suit", r2=0.24)
    t.box(p + "_tie", (0, -0.03, 1.72), (0.08, 0.04, 0.32), "red")
    head = ((0, 0.2, 2.2), (0.36, 0.33, 0.36))
    t.sphere(p + "_head", *head, "skin")
    y = t.surface_y(head, 0, 0.05)
    for sd in (-1, 1):
        t.box(p + "_shade%d" % sd, (sd * 0.13, y - 0.02, 2.24), (0.2, 0.04, 0.12), "black")
    t.box(p + "_bridge", (0, y - 0.03, 2.27), (0.1, 0.03, 0.03), "black")
    t.torus(p + "_frown", (0, t.surface_y(head, 0, -0.18) + 0.0, 2.02), 0.08, 0.025, "black",
            rot=(R(-90), 0, 0), half=True)
    t.sphere(p + "_hair", (0.05, 0.22, 2.48), (0.36, 0.3, 0.12), "hair", rot=(0, R(-12), 0))
    t.sphere(p + "_hand", (0.32, -0.05, 1.85), (0.1, 0.1, 0.1), "skin")
    t.box(p + "_paper", (0.38, -0.12, 2.05), (0.22, 0.02, 0.3), "white", rot=(0, R(-15), 0))


# ====================================================================== props

def sack(t, p="Sack", full=True, label=True):
    if full:
        t.sphere(p + "_bag", (0, 0, 0.55), (0.55, 0.5, 0.58), "sack")
        t.torus(p + "_tie", (0, 0, 0.98), 0.38, 0.05, "brown")
        for k in range(7):
            a = k * 0.9
            t.sphere(p + "_leaf%d" % k, (math.cos(a) * 0.25, math.sin(a) * 0.2, 1.12 + 0.05 * (k % 3)),
                     (0.2, 0.14, 0.18), "green", rot=(0, R(k * 25), 0))
        for k in range(5):
            a = k * 1.3 + 0.4
            t.sphere(p + "_fl%d" % k, (math.cos(a) * 0.22, math.sin(a) * 0.16 - 0.08, 1.3 + 0.04 * k),
                     (0.07, 0.07, 0.07), "yellow")
        if label:
            t.text(p + "_lbl", "ΒΡΟΥΒΕΣ", (0, -0.5, 0.55), 0.17, "brown", extrude=0.005)
    else:
        t.sphere(p + "_bag", (0, 0, 0.12), (0.6, 0.5, 0.13), "sack")
        t.sphere(p + "_fold", (0.25, -0.1, 0.22), (0.25, 0.2, 0.08), "sack")
        t.sphere(p + "_leaf", (-0.3, -0.2, 0.2), (0.12, 0.09, 0.05), "green")


def olive_tree(t, p, x, y, s=1.0):
    t.cyl(p + "_trunk", (x, y, 0.8 * s), 0.22 * s, 1.6 * s, "brown", rot=(0, R(8), 0), verts=10)
    t.cyl(p + "_trunk2", (x + 0.2 * s, y, 1.4 * s), 0.14 * s, 0.9 * s, "brown", rot=(0, R(-30), 0), verts=8)
    for k, (dx, dy, dz, r) in enumerate([(0, 0, 2.3, 0.85), (-0.55, 0.1, 2.0, 0.6), (0.6, -0.05, 2.1, 0.65),
                                         (0.1, 0.25, 2.75, 0.55)]):
        t.sphere(p + "_crown%d" % k, (x + dx * s, y + dy * s, dz * s), (r * s, r * 0.9 * s, r * 0.8 * s),
                 "olive" if k % 2 == 0 else "olive2")


def round_tree(t, p, x, y, s=1.0):
    t.cyl(p + "_trunk", (x, y, 0.6 * s), 0.2 * s, 1.2 * s, "brown", verts=10)
    t.sphere(p + "_crown", (x, y, 1.9 * s), (0.95 * s, 0.9 * s, 0.9 * s), "leaf")
    t.sphere(p + "_crown2", (x + 0.35 * s, y - 0.2 * s, 2.2 * s), (0.45 * s, 0.4 * s, 0.4 * s), "leaf")
    t.sphere(p + "_fruit", (x - 0.4 * s, y - 0.6 * s, 1.8 * s), (0.12 * s, 0.1 * s, 0.12 * s), "orange")
    t.sphere(p + "_fruit2", (x + 0.3 * s, y - 0.7 * s, 1.6 * s), (0.12 * s, 0.1 * s, 0.12 * s), "orange")


def cypress(t, p, x, y, s=1.0):
    t.cyl(p + "_trunk", (x, y, 0.25 * s), 0.15 * s, 0.5 * s, "brown", verts=8)
    t.sphere(p + "_body", (x, y, 1.9 * s), (0.5 * s, 0.5 * s, 1.75 * s), "cypress")


def cactus(t, p, x, y, s=1.0):
    pads = [(0, 0, 0.5, 0, 0.42), (-0.35, 0, 1.05, 30, 0.32), (0.32, 0, 1.15, -25, 0.34),
            (0.05, 0, 1.55, 5, 0.28)]
    for k, (dx, dy, dz, rot, r) in enumerate(pads):
        t.sphere(p + "_pad%d" % k, (x + dx * s, y + dy * s, dz * s), (r * s, 0.12 * s, r * 1.2 * s), "cactus",
                 rot=(0, R(rot), 0))
    for k, (dx, dz) in enumerate([(-0.55, 1.4), (0.55, 1.5), (0.05, 1.9)]):
        t.sphere(p + "_fig%d" % k, (x + dx * s, y, dz * s), (0.1 * s, 0.1 * s, 0.13 * s), "pink")


def goat(t, p, x, y, brown=False, turn=0, s=1.0):
    col = "goat_b" if brown else "white"
    t.begin()
    t.sphere(p + "_body", (0, 0.1, 0.75), (0.65, 0.42, 0.42), col)
    for k, (dx, dy) in enumerate([(-0.4, -0.1), (0.4, -0.1), (-0.4, 0.3), (0.4, 0.3)]):
        t.cyl(p + "_leg%d" % k, (dx, dy, 0.3), 0.07, 0.6, "dark", verts=8)
    head = ((0.62, -0.15, 1.15), (0.3, 0.28, 0.3))
    t.sphere(p + "_head", *head, col)
    t.eye(p + "_eye_l", head, -0.1, 0.06, 0.08, look=(0.3, 0), pupil=0.35)
    t.eye(p + "_eye_r", head, 0.1, 0.06, 0.08, look=(0.3, 0), pupil=0.35)
    for sd in (-1, 1):
        t.cyl(p + "_horn%d" % sd, (0.62 + sd * 0.15, -0.05, 1.5), 0.06, 0.35, "horn", r2=0.01,
              rot=(R(25), R(sd * 20), 0), verts=8)
        t.sphere(p + "_ear%d" % sd, (0.62 + sd * 0.32, -0.1, 1.2), (0.16, 0.05, 0.07), col)
    t.cyl(p + "_beard", (0.62, -0.38, 0.88), 0.07, 0.25, "white" if brown else "goat_b", r2=0.01,
          rot=(R(180), 0, 0), verts=8)
    t.sphere(p + "_chew", (0.75, -0.45, 0.95), (0.12, 0.06, 0.05), "green")    # a mouthful of greens
    t.sphere(p + "_tail", (-0.65, 0.1, 1.05), (0.1, 0.08, 0.15), col)
    return t.end(p, (x, y, 0), turn, s)


def grave(t, p, x, y, kind=0):
    if kind == 0:   # a whitewashed slab with an iron cross
        t.box(p + "_slab", (x, y + 0.1, 0.15), (0.9, 1.5, 0.3), "plaster")
        t.box(p + "_cross_v", (x, y + 0.75, 0.9), (0.12, 0.12, 1.2), "dark")
        t.box(p + "_cross_h", (x, y + 0.75, 1.15), (0.6, 0.12, 0.12), "dark")
        t.cyl(p + "_lamp", (x + 0.3, y - 0.45, 0.42), 0.12, 0.25, "red", verts=10)
        t.sphere(p + "_flame", (x + 0.3, y - 0.45, 0.62), (0.05, 0.05, 0.09), "flame")
    else:           # a rounded headstone with flowers
        t.box(p + "_stone", (x, y + 0.5, 0.55), (0.8, 0.25, 1.1), "stone2")
        t.cyl(p + "_top", (x, y + 0.5, 1.1), 0.4, 0.25, "stone2", rot=(R(90), 0, 0))
        t.box(p + "_cross", (x, y + 0.36, 0.75), (0.08, 0.03, 0.4), "dark")
        t.box(p + "_cross2", (x, y + 0.36, 0.82), (0.25, 0.03, 0.08), "dark")
        for k in range(3):
            t.sphere(p + "_fl%d" % k, (x - 0.25 + 0.25 * k, y - 0.05, 0.18), (0.1, 0.1, 0.1),
                     ("red", "yellow", "pink")[k])


def wall_cell(t, p, x, y, w, d, left, right, up, down):
    """a dry stone wall through a cell, joined to the walls next to it"""
    h = 0.75
    cw, cd = 0.7, 0.7 * d / w
    t.box(p + "_c", (x, y, h / 2), (cw, cd, h), "stone")
    if left:
        t.box(p + "_l", (x - w / 4 - cw / 8, y, h / 2), (w / 2 - cw / 4 + 0.02, cd, h), "stone")
    if right:
        t.box(p + "_r", (x + w / 4 + cw / 8, y, h / 2), (w / 2 - cw / 4 + 0.02, cd, h), "stone")
    if up:
        t.box(p + "_u", (x, y + d / 4 + cd / 8, h / 2), (cw, d / 2 - cd / 4 + 0.02, h), "stone")
    if down:
        t.box(p + "_d", (x, y - d / 4 - cd / 8, h / 2), (cw, d / 2 - cd / 4 + 0.02, h), "stone")
    for k in range(3):
        t.sphere(p + "_rock%d" % k, (x - 0.25 + 0.25 * k, y - cd / 2 + 0.02, 0.2 + 0.25 * (k % 2)),
                 (0.16, 0.05, 0.11), "stone2")


# ====================================================================== effects and shots

def spiky_star(t, p, r_in, r_out, col, n=8, z=1.0, col2=None):
    t.sphere(p + "_core", (0, 0, z), (r_in, r_in * 0.3, r_in), col)
    for k in range(n):
        a = k * 2 * math.pi / n
        t.cyl(p + "_spike%d" % k, (math.cos(a) * (r_in + r_out) / 2, -0.05, z + math.sin(a) * (r_in + r_out) / 2),
              r_in * 0.45, r_out - r_in * 0.4, col2 or col, r2=0, verts=4,
              rot=(0, R(90) - a, 0))


def cloud(t, p, col, s=1.0, z=0.8, n=6, seed=0):
    for k in range(n):
        a = k * 2 * math.pi / n + seed
        r = 0.45 * s
        t.sphere(p + "_puff%d" % k, (math.cos(a) * r, math.sin(a) * r * 0.5, z + math.sin(a * 2) * 0.15 * s),
                 (0.42 * s, 0.38 * s, 0.38 * s), col)
    t.sphere(p + "_mid", (0, 0, z + 0.2 * s), (0.5 * s, 0.45 * s, 0.45 * s), col)


def heart(t, p, s=1.0, col="pink", z=1.0):
    for sd in (-1, 1):
        t.sphere(p + "_lobe%d" % sd, (sd * 0.2 * s, 0, z + 0.1 * s), (0.25 * s, 0.12 * s, 0.25 * s), col)
    t.cyl(p + "_tip", (0, 0, z - 0.15 * s), 0.38 * s, 0.4 * s, col, r2=0, rot=(R(180), 0, 0), verts=4)
