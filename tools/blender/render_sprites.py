"""Render every sprite of the game to art/sprites/*.png, from inside Blender:

    import sys; sys.path.insert(0, r"<repo>/tools/blender")
    import render_sprites; render_sprites.main()            # or main(["guard_down_0"])

All sprites share the camera of the stage backgrounds (models.Rig): 128 pixels per map
cell, and the ground point under the sprite's centre at ANCHOR on its picture.
"""
import os

import models as m

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "art", "sprites")

# picture size and where the ground point of the model sits on it
BIG = (256, 256, 128, 200)
SMALL = (128, 128, 64, 96)
WIDE = (320, 256, 160, 200)

DIRS = {"down": 0, "right": 90, "up": 180, "left": -90}


def turned(builder, turn, scale=1.0, **kw):
    def build(t):
        t.begin()
        builder(t, **kw)
        t.end("grp", turn=turn, scale=scale)
    return build


def sprite_list():
    s = {
        "cretan": (m.cretan, BIG),
        "yiayia": (m.yiayia, BIG),
        "bride": (m.bride, BIG),
        "psssst": (m.psssst, BIG),
        "baker": (m.baker, BIG),
        "cauldron": (lambda t: m.cauldron(t), BIG),
        "cauldron_b": (lambda t: m.cauldron(t, bubble=1), BIG),
        "cauldron_dented": (lambda t: m.cauldron(t, dented=True), BIG),
        "sack_full": (turned(m.sack, 0, 1.15, full=True), BIG),
        "sack_empty": (turned(m.sack, 0, 1.15, full=False), BIG),
        "dakos": (lambda t: m.dakos(t, "Dk", 0, 0, 0.5, s=0.8), SMALL),
        "heart": (lambda t: m.heart(t, "Ht", s=0.6), SMALL),
        "heart_crit": (lambda t: m.heart(t, "Ht", s=1.1, col="red"), SMALL),
        "fx_spark": (lambda t: m.spiky_star(t, "Sp", 0.15, 0.45, "yellow", n=6), SMALL),
        "fx_zap": (lambda t: m.spiky_star(t, "Zp", 0.15, 0.5, "cyan", n=6, col2="white"), SMALL),
        "fx_bash": (lambda t: m.spiky_star(t, "Bs", 0.35, 0.95, "yellow", n=9, col2="orange"), BIG),
        "fx_boom": (lambda t: m.spiky_star(t, "Bm", 0.55, 1.35, "orange", n=11, col2="red"), BIG),
        "fx_puff": (lambda t: m.cloud(t, "Pf", "toxic", 1.0), BIG),
        "fx_puff_b": (lambda t: m.cloud(t, "Pf", "lime", 1.25, seed=0.5), BIG),
        "fx_poof": (lambda t: m.cloud(t, "Po", "white", 0.8), BIG),
        "fx_poof_b": (lambda t: m.cloud(t, "Po", "smoke", 1.0, seed=0.5), BIG),
    }
    for d, turn in DIRS.items():
        for f in (0, 1):
            s["drone_%s_%d" % (d, f)] = (turned(m.drone, turn, frame=f), BIG)
            s["guard_%s_%d" % (d, f)] = (turned(m.guard, turn, frame=f), BIG)
            s["tank_%s_%d" % (d, f)] = (turned(m.tank, turn, frame=f), WIDE)
    return s


def main(names=None):
    os.makedirs(OUT, exist_ok=True)
    t = m.Rig("VPC_Sprites")
    done = []
    try:
        for name, (build, (w, h, ax, ay)) in sprite_list().items():
            if names and name not in names:
                continue
            t.clear()
            build(t)
            t.frame(w, h, ax, ay)
            t.render_to(os.path.join(OUT, name + ".png"))
            done.append(name)
    finally:
        t.restore()
    return done
