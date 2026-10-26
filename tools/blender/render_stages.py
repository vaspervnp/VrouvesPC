"""Render the background of every stage to art/stages/stageN.png, from inside Blender:

    import render_stages; render_stages.main()          # or main([1, 3])

The map comes from data/stages.json (tools/export_stages.py); every cell is a 128 x 128
square on the 2560 x 1792 picture, seen from the same tilted camera as the sprites.
The sacks are not drawn: the game draws them, full or empty.
"""
import json
import math
import os
import random

import bmesh
import bpy

import buildings
import models as m
from blender_toon import R

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "stages")


class Map:
    def __init__(self, t, stage, cols, rows):
        self.t, self.st = t, stage
        self.cols, self.rows = cols, rows
        self.grid = stage["grid"]
        self.S, self.D = t.CELL, t.depth

    def ch(self, c, r):
        if 0 <= c < self.cols and 0 <= r < self.rows:
            return self.grid[r][c]
        return "?"

    def centre(self, c, r):
        return ((c + 0.5) * self.S, (self.rows - r - 0.5) * self.D)

    def rect(self, c0, r0, c1, r1):
        """world x0, x1, y_front (bottom of the picture), y_back of a block of cells"""
        return (c0 * self.S, (c1 + 1) * self.S, (self.rows - r1 - 1) * self.D, (self.rows - r0) * self.D)

    def cells(self, chars):
        return [(c, r) for r in range(self.rows) for c in range(self.cols) if self.grid[r][c] in chars]

    def bounds(self, chars):
        cs = self.cells(chars)
        return (min(c for c, _ in cs), min(r for _, r in cs), max(c for c, _ in cs), max(r for _, r in cs))

    # -------------------------------------------------------------- flat layers
    def patch(self, name, cells, mat, z):
        """one flat mesh over a set of cells, corners shared so only its outline is inked"""
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        verts = {}

        def v(i, j):
            if (i, j) not in verts:
                verts[(i, j)] = bm.verts.new((i * self.S, (self.rows - j) * self.D, z))
            return verts[(i, j)]
        for (c, r) in cells:
            bm.faces.new((v(c, r + 1), v(c + 1, r + 1), v(c + 1, r), v(c, r)))
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(name, me)
        self.t.col.objects.link(ob)
        return self.t.put(ob, mat, smooth=False)


def ground(mp, rnd):
    t = mp.t
    W, H = mp.cols * mp.S, mp.rows * mp.D
    bpy.ops.mesh.primitive_plane_add(size=1, location=(W / 2, H / 2, 0))
    g = t.put(bpy.context.object, "grass", smooth=False)
    g.name = "Ground"
    g.scale = (W + 40, H + 60, 1)
    mp.patch("Road", mp.cells("#"), "dirt", 0.03)
    # pebbles and wheel ruts on the road
    for k, (c, r) in enumerate(mp.cells("#")):
        x, y = mp.centre(c, r)
        for j in range(2):
            t.sphere("Pebble%d_%d" % (k, j), (x + rnd.uniform(-0.9, 0.9), y + rnd.uniform(-1.8, 1.8), 0.05),
                     (0.12, 0.2, 0.05), "dirt2")
    # grass tufts and the vrouves themselves, in flower
    k = 0
    for (c, r) in mp.cells(".F"):
        if mp.ch(c, r) == "F":
            continue
        x, y = mp.centre(c, r)
        for _ in range(rnd.choice((0, 0, 1))):
            px, py = x + rnd.uniform(-0.8, 0.8), y + rnd.uniform(-1.8, 1.8)
            if rnd.random() < 0.6:
                for j in range(3):
                    t.sphere("Vr%d_%d" % (k, j), (px + j * 0.18 - 0.18, py, 0.12 + 0.08 * (j % 2)),
                             (0.09, 0.09, 0.09), "yellow")
                t.sphere("VrL%d" % k, (px, py - 0.1, 0.06), (0.3, 0.2, 0.06), "green")
            else:
                for j in range(3):
                    t.cyl("Tuft%d_%d" % (k, j), (px + j * 0.14 - 0.14, py, 0.18), 0.08, 0.36, "grass2",
                          r2=0, verts=4, rot=(0, R((j - 1) * 25), 0))
            k += 1


def props(mp, rnd):
    t = mp.t
    for (c, r) in mp.cells("TCGYWX"):
        ch = mp.ch(c, r)
        x, y = mp.centre(c, r)
        p = "%s_%d_%d" % (ch, c, r)
        if ch == "T":
            (m.olive_tree if (c + r) % 3 else m.round_tree)(t, p, x, y, 0.95)
        elif ch == "C":
            m.cactus(t, p, x, y, 0.9)
        elif ch == "G":
            m.goat(t, p, x, y, brown=(c + r) % 2 == 0, turn=rnd.choice((-30, 20, 160, 200)), s=0.95)
        elif ch == "Y":
            m.cypress(t, p, x, y, 1.0)
        elif ch == "X":
            m.grave(t, p, x, y, 0 if (c + r) % 4 < 2 else 1)
        elif ch == "W":
            m.wall_cell(t, p, x, y, mp.S, mp.D, mp.ch(c - 1, r) == "W", mp.ch(c + 1, r) == "W",
                        mp.ch(c, r - 1) == "W", mp.ch(c, r + 1) == "W")


def load():
    with open(os.path.join(ROOT, "data", "stages.json"), encoding="utf-8") as f:
        return json.load(f)


def main(which=None):
    data = load()
    os.makedirs(OUT, exist_ok=True)
    t = m.Rig("VPC_Stage")
    done = []
    try:
        for st in data["stages"]:
            if which and st["id"] not in which:
                continue
            t.clear()
            rnd = random.Random(st["id"] * 7919)
            mp = Map(t, st, data["cols"], data["rows"])
            ground(mp, rnd)
            props(mp, rnd)
            getattr(buildings, st["base"])(mp)
            W, H = mp.cols * t.PX, mp.rows * t.PX
            t.sc.render.film_transparent = False
            t.frame(W, H, W / 2, H / 2, origin=(mp.cols * mp.S / 2, mp.rows * mp.D / 2))
            t.render_to(os.path.join(OUT, "stage%d.png" % st["id"]))
            t.sc.render.film_transparent = True
            done.append(st["id"])
    finally:
        t.restore()
    return done
