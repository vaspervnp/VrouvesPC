"""The building each stage defends, with its yard and its people, on the K and P cells of
the map (render_stages.Map). Fronts face -y, towards the camera.
"""
import math

from blender_toon import R

TAN = math.tan(math.radians(62))


def fit_depth(y_front, y_back, h, slack=0.4):
    """how deep a block of height h can be so that its top stays over its own cells"""
    return max(2.0, (y_back - y_front) - h * TAN - slack)


def house(t, p, x0, x1, yf, depth, h, wall="plaster", roof="flat", roof_col="tile", windows=3,
          door=True, shutter="shutter", sign=None, sign_col="shutter", sign_txt="white"):
    cx = (x0 + x1) / 2
    w = x1 - x0
    t.box(p + "_wall", (cx, yf + depth / 2, h / 2), (w, depth, h), wall)
    if roof == "flat":
        t.box(p + "_roof", (cx, yf + depth / 2, h + 0.12), (w + 0.25, depth + 0.25, 0.25), wall)
        t.box(p + "_parapet", (cx, yf - 0.02, h + 0.38), (w + 0.25, 0.2, 0.3), wall)
    else:
        r = depth / math.sqrt(3) * 1.08
        sx = 0.5
        rf = t.cyl(p + "_roof", (cx, yf + depth / 2, h + r / 2 * sx), r, w + 0.5, roof_col, verts=3,
                   rot=(0, R(-90), 0))
        rf.scale = (sx, 1.0, 1.0)
    # windows with shutters, and the door in the middle
    slots = windows + (1 if door else 0)
    k = 0
    for i in range(slots):
        wx = x0 + w * (i + 0.5) / slots
        if door and i == slots // 2:
            t.box(p + "_door", (wx, yf - 0.03, 1.1), (1.0, 0.08, 2.2), shutter)
            t.sphere(p + "_knob", (wx + 0.3, yf - 0.09, 1.1), (0.07, 0.04, 0.07), "gold")
            continue
        t.box(p + "_win%d" % k, (wx, yf - 0.03, h * 0.55), (0.75, 0.06, 0.9), "glass")
        for sd in (-1, 1):
            t.box(p + "_sh%d_%d" % (k, sd), (wx + sd * 0.55, yf - 0.05, h * 0.55), (0.35, 0.06, 0.95), shutter)
        k += 1
    if sign:
        t.box(p + "_sign", (cx, yf - 0.08, h * 0.88), (min(w * 0.8, 0.5 * len(sign) + 0.6), 0.1, 0.65), sign_col)
        t.text(p + "_signtxt", sign, (cx, yf - 0.15, h * 0.88), 0.48, sign_txt, extrude=0.01)


def flag_gr(t, p, x, y, z, s=1.0):
    t.cyl(p + "_pole", (x, y, z / 2), 0.06, z, "silver", verts=8)
    fx = x + 0.75 * s
    t.box(p + "_flag", (fx, y, z - 0.45 * s), (1.5 * s, 0.04, 1.0 * s), "blue")
    for k in range(4):
        t.box(p + "_st%d" % k, (fx, y - 0.03, z - 0.07 * s - k * 0.22 * s), (1.5 * s, 0.02, 0.1 * s), "white")
    t.box(p + "_cant", (x + 0.3 * s, y - 0.04, z - 0.25 * s), (0.6 * s, 0.02, 0.55 * s), "blue")
    t.box(p + "_cr1", (x + 0.3 * s, y - 0.05, z - 0.25 * s), (0.6 * s, 0.02, 0.1 * s), "white")
    t.box(p + "_cr2", (x + 0.3 * s, y - 0.05, z - 0.25 * s), (0.1 * s, 0.02, 0.55 * s), "white")


def flag_eu(t, p, x, y, z, s=1.0):
    t.cyl(p + "_pole", (x, y, z / 2), 0.06, z, "silver", verts=8)
    fx = x + 0.75 * s
    t.box(p + "_flag", (fx, y, z - 0.45 * s), (1.5 * s, 0.04, 1.0 * s), "eu")
    for k in range(12):
        a = k * math.pi / 6
        t.sphere(p + "_s%d" % k, (fx + math.cos(a) * 0.3 * s, y - 0.04, z - 0.45 * s + math.sin(a) * 0.3 * s),
                 (0.04, 0.02, 0.04), "yellow")


def villager(t, p, x, y, z0=0.0, body="red", hair="hair", look=(0, 0), hat=None):
    t.cyl(p + "_body", (x, y, z0 + 0.9), 0.5, 1.1, body, r2=0.42)
    head = ((x, y - 0.03, z0 + 1.85), (0.5, 0.46, 0.52))
    t.sphere(p + "_head", *head, "skin")
    t.sphere(p + "_hair", (x, y + 0.12, z0 + 2.05), (0.52, 0.46, 0.4), hair)
    t.face(p, head, 0.13, look, smile=0.15)
    if hat == "sariki":
        t.sphere(p + "_hat", (x, y, z0 + 2.25), (0.56, 0.5, 0.25), "black")
    elif hat == "cap":
        t.sphere(p + "_hat", (x, y, z0 + 2.2), (0.5, 0.46, 0.22), body)
        t.box(p + "_peak", (x, y - 0.5, z0 + 2.12), (0.5, 0.4, 0.06), body)


def table(t, p, x, y, cloth="white"):
    t.cyl(p + "_top", (x, y, 1.0), 0.6, 0.08, cloth)
    t.cyl(p + "_leg", (x, y, 0.5), 0.07, 1.0, "dark", verts=8)
    t.cyl(p + "_cup", (x + 0.15, y - 0.1, 1.12), 0.1, 0.16, "white", verts=10)
    t.cyl(p + "_cup2", (x - 0.25, y + 0.1, 1.12), 0.1, 0.16, "white", verts=10)


def chair(t, p, x, y):
    t.box(p + "_seat", (x, y, 0.6), (0.55, 0.55, 0.08), "shutter")
    t.box(p + "_back", (x, y + 0.27, 1.0), (0.55, 0.06, 0.8), "shutter")
    for i, (dx, dy) in enumerate([(-0.22, -0.22), (0.22, -0.22), (-0.22, 0.22), (0.22, 0.22)]):
        t.box(p + "_l%d" % i, (x + dx, y + dy, 0.3), (0.06, 0.06, 0.6), "wood")


def paving(mp, chars="P", mat="stone"):
    mp.patch("Yard", mp.cells(chars), mat, 0.04)


# ====================================================================== 1. the kafenio

def kafenio(mp):
    t = mp.t
    paving(mp, "KP", "stone")
    c0, r0, c1, r1 = mp.bounds("K")
    x0, x1, yf, yb = mp.rect(c0, r0, c1, r1)
    h = 3.6
    yh = yf + 2.6
    d = fit_depth(yh, yb, h + 1.0)
    house(t, "Kaf", x0 + 0.4, x1 - 0.4, yh, d, h, roof="gable", windows=2, sign="ΚΑΦΕΝΕΙΟ")
    flag_gr(t, "KafFlag", x1 - 1.4, yh + d - 1.0, h + 2.6, 0.9)
    # the awning, striped blue and white, over the porch
    for k in range(9):
        t.box("Awn%d" % k, (x0 + 0.9 + k * 1.05, yh - 1.0, 2.75), (0.52, 2.0, 0.08),
              "shutter" if k % 2 == 0 else "white", rot=(R(-12), 0, 0))
    for sd in (0, 1):
        t.cyl("AwnPost%d" % sd, (x0 + 0.6 + sd * (x1 - x0 - 1.2), yh - 1.9, 1.3), 0.07, 2.6, "wood", verts=8)
    # tables and chairs out front, on the free part of the porch; an old Cretan with his coffee
    _, _, py0, py1 = mp.rect(*mp.bounds("P"))
    for k in range(2):
        x = x0 + 1.4 + k * 3.0
        y = yf + 0.2 - k * 0.8
        table(t, "KafT%d" % k, x, y, "white" if k else "pink")
        chair(t, "KafC%d" % k, x + 1.0, y + 0.2)
    t.cretan("Pappous", x0 + 0.6, yf - 0.4, 0.0, look=(0.6, 0.2), beard=True)
    t.box("Tavli", (x0 + 4.4, yf - 0.6, 1.1), (0.6, 0.4, 0.06), "wood")


# ====================================================================== 2. the church

def church_body(t, p, cx, yf, w, d, h, dome="shutter", tower=True):
    t.box(p + "_nave", (cx, yf + d / 2, h / 2), (w, d, h), "plaster")
    t.box(p + "_cornice", (cx, yf + d / 2, h + 0.1), (w + 0.2, d + 0.2, 0.2), "plaster")
    t.cyl(p + "_drum", (cx, yf + d * 0.55, h + 0.7), 1.2, 1.2, "plaster", verts=16)
    t.sphere(p + "_dome", (cx, yf + d * 0.55, h + 1.3), (1.3, 1.3, 1.1), dome)
    t.box(p + "_cross_v", (cx, yf + d * 0.55, h + 2.75), (0.1, 0.1, 0.8), "gold")
    t.box(p + "_cross_h", (cx, yf + d * 0.55, h + 2.85), (0.45, 0.1, 0.1), "gold")
    t.box(p + "_door", (cx, yf - 0.03, 1.1), (1.0, 0.08, 2.2), "wood")
    t.cyl(p + "_arch", (cx, yf - 0.04, 2.2), 0.5, 0.08, "wood", rot=(R(90), 0, 0))
    for sd in (-1, 1):
        t.box(p + "_win%d" % sd, (cx + sd * w * 0.3, yf - 0.03, h * 0.6), (0.4, 0.06, 0.9), "glass")
    if tower:
        tx = cx + w / 2 - 0.6
        t.box(p + "_tower", (tx, yf + 0.8, h + 1.0), (1.1, 1.1, 2.0), "plaster")
        t.box(p + "_bellarch", (tx, yf + 0.22, h + 1.1), (0.6, 0.06, 0.9), "dark")
        t.sphere(p + "_bell", (tx, yf + 0.5, h + 1.0), (0.22, 0.22, 0.25), "gold")
        t.sphere(p + "_tdome", (tx, yf + 0.8, h + 2.1), (0.6, 0.6, 0.45), dome)


def candles(t, p, x, y):
    t.box(p + "_stand", (x, y, 0.6), (1.0, 0.5, 1.2), "gold")
    for k in range(4):
        t.cyl(p + "_c%d" % k, (x - 0.36 + k * 0.24, y - 0.1, 1.4), 0.04, 0.4, "cream", verts=6)
        t.sphere(p + "_f%d" % k, (x - 0.36 + k * 0.24, y - 0.1, 1.65), (0.05, 0.05, 0.09), "flame")


def church(mp):
    t = mp.t
    paving(mp, "KP", "stone")
    c0, r0, c1, r1 = mp.bounds("K")
    x0, x1, yf, yb = mp.rect(c0, r0, c1, r1)
    h = 3.6
    d = fit_depth(yf, yb, h + 2.5)
    church_body(t, "Ch", (x0 + x1) / 2, yf + 0.6, x1 - x0 - 1.2, d, h)
    _, py0, _, py1 = mp.rect(*mp.bounds("P"))
    t.priest("Papas", x0 + 2.5, py0 + 3.5, 0, look=(0.5, 0.2))
    candles(t, "Cand", x1 - 2.2, py0 + 5.0)


# ====================================================================== 3. the town hall

def town_hall(mp):
    t = mp.t
    paving(mp, "KP", "stone")
    c0, r0, c1, r1 = mp.bounds("K")
    x0, x1, yf, yb = mp.rect(c0, r0, c1, r1)
    h = 4.5
    d = fit_depth(yf, yb, h + 1.6)
    yfb = yf + 4.0
    d = min(d, yb - yfb - h * TAN - 1.5)
    cx = (x0 + x1) / 2
    w = x1 - x0 - 1.0
    t.box("TH_wall", (cx, yfb + d / 2, h / 2), (w, d, h), "cream")
    # the portico: columns and a pediment
    t.box("TH_step", (cx, yfb - 1.4, 0.15), (w * 0.7, 3.0, 0.3), "plaster")
    for k in range(5):
        x = cx - w * 0.3 + k * w * 0.15
        t.cyl("TH_col%d" % k, (x, yfb - 2.4, h / 2), 0.3, h, "plaster", verts=12)
    t.box("TH_beam", (cx, yfb - 1.4, h + 0.2), (w * 0.72, 3.0, 0.4), "plaster")
    r = 1.6
    ped = t.cyl("TH_ped", (cx, yfb - 2.85, h + 0.4 + r / 2 * 0.5), r, w * 0.72, "plaster", verts=3,
                rot=(R(90), R(-90), 0))
    ped.scale = (0.5, 1.6, 0.15)
    t.box("TH_roof", (cx, yfb + d / 2, h + 0.15), (w + 0.2, d + 0.2, 0.3), "tile")
    t.box("TH_sign", (cx, yfb - 2.95, h - 0.4), (5.2, 0.08, 0.6), "eu")
    t.text("TH_txt", "ΔΗΜΑΡΧΕΙΟ", (cx, yfb - 3.0, h - 0.4), 0.45, "white", extrude=0.01)
    flag_gr(t, "THgr", cx - 3.0, yfb + d - 0.5, h + 3.0, 0.9)
    flag_eu(t, "THeu", cx + 1.6, yfb + d - 0.5, h + 3.0, 0.9)
    # the plaza: the plane tree, the fountain, the mayor
    px0, px1, py0, py1 = mp.rect(*mp.bounds("P"))
    tx, ty = px0 + 2.2, py0 + 5.0
    t.cyl("Plane_trunk", (tx, ty, 1.5), 0.45, 3.0, "brown", verts=12)
    for k, (dx, dy, dz, s) in enumerate([(0, 0, 4.0, 1.9), (-1.2, 0.5, 3.4, 1.2), (1.3, 0.4, 3.5, 1.3)]):
        t.sphere("Plane_crown%d" % k, (tx + dx, ty + dy, dz), (s, s * 0.9, s * 0.8), "leaf")
    fx, fy = px0 + 2.2, py1 - 3.5
    t.cyl("Fount_basin", (fx, fy, 0.35), 1.1, 0.7, "stone", verts=20)
    t.cyl("Fount_water", (fx, fy, 0.66), 0.95, 0.06, "water", verts=20)
    t.cyl("Fount_spout", (fx, fy, 1.2), 0.15, 1.2, "stone", verts=10)
    t.sphere("Fount_jet", (fx, fy, 1.9), (0.25, 0.25, 0.3), "water")
    t.cretan("Mayor", cx + 2.5, yfb - 4.8, 0.3, look=(-0.4, 0.2), beard=True, sariki=False)
    t.torus("Mayor_chain", (cx + 2.5, yfb - 5.3, 1.6), 0.4, 0.05, "gold", rot=(R(70), 0, 0))


# ====================================================================== 4. the bakery

def bakery(mp):
    t = mp.t
    paving(mp, "KP", "stone")
    c0, r0, c1, r1 = mp.bounds("K")
    x0, x1, yf, yb = mp.rect(c0, r0, c1, r1)
    h = 3.6
    d = fit_depth(yf, yb, h + 1.0)
    house(t, "Bak", x0 + 0.4, x1 - 2.6, yf + 0.6, d, h, wall="stone", roof="gable", windows=1,
          shutter="wood", sign="ΦΟΥΡΝΟΣ", sign_col="wood", sign_txt="cream")
    # the wood-fired oven, its mouth glowing, smoke from the chimney
    ox, oy = x1 - 1.4, yf + 3.5
    t.sphere("Oven", (ox, oy, 0.6), (1.3, 1.6, 1.4), "plaster")
    t.sphere("Oven_mouth", (ox, oy - 1.45, 0.65), (0.5, 0.2, 0.45), "black")
    t.sphere("Oven_fire", (ox, oy - 1.5, 0.45), (0.35, 0.15, 0.2), "fire")
    t.cyl("Oven_chimney", (ox + 0.3, oy + 0.5, 2.1), 0.2, 1.0, "stone", verts=10)
    for k in range(3):
        t.sphere("Oven_smoke%d" % k, (ox + 0.4 + k * 0.25, oy + 0.6, 2.9 + k * 0.5),
                 (0.3 + k * 0.08, 0.25, 0.25), "smoke")
    # the woodpile and racks of dakos drying in the yard
    px0, px1, py0, py1 = mp.rect(*mp.bounds("P"))
    for k in range(6):
        t.cyl("Log%d" % k, (x0 + 1.2 + (k % 3) * 0.45, py0 + 2.4, 0.22 + (k // 3) * 0.38), 0.2, 1.6,
              "brown", rot=(R(90), 0, 0), verts=10)
    for j in range(2):
        rx = x0 + 4.5 + j * 3.2
        t.box("Rack%d" % j, (rx, py0 + 2.4, 0.9), (2.4, 0.9, 0.08), "wood")
        for sd in (-1, 1):
            t.box("RackL%d_%d" % (j, sd), (rx + sd * 1.1, py0 + 2.4, 0.45), (0.1, 0.1, 0.9), "wood")
        for k in range(3):
            t.cyl("RackD%d_%d" % (j, k), (rx - 0.75 + k * 0.75, py0 + 2.4, 1.02), 0.3, 0.15, "rusk")


# ====================================================================== 5. the school

def school(mp):
    t = mp.t
    c0, r0, c1, r1 = mp.bounds("K")
    x0, x1, yf, yb = mp.rect(c0, r0, c1, r1)
    paving(mp, "K", "plaster")
    mp.patch("Court", mp.cells("P"), "court", 0.05)
    h = 3.6
    d = fit_depth(yf, yb, h + 1.0)
    house(t, "Sch", x0 + 0.4, x1 - 0.4, yf + 0.6, d, h, wall="cream", roof="gable", windows=4,
          sign="ΣΧΟΛΕΙΟ", sign_col="red")
    px0, px1, py0, py1 = mp.rect(*mp.bounds("P"))
    # court lines and a basketball hoop
    cx = (px0 + px1) / 2
    t.box("Court_mid", (cx, (py0 + py1) / 2, 0.07), (0.1, py1 - py0 - 1.0, 0.02), "white")
    t.cyl("Court_circle", (cx, (py0 + py1) / 2, 0.07), 1.6, 0.02, "white", verts=24)
    t.cyl("Court_circle2", (cx, (py0 + py1) / 2, 0.075), 1.45, 0.02, "court", verts=24)
    hx = px1 - 1.0
    t.cyl("Hoop_pole", (hx, (py0 + py1) / 2, 1.6), 0.08, 3.2, "silver", verts=8)
    t.box("Hoop_board", (hx - 0.1, (py0 + py1) / 2, 3.2), (0.08, 1.4, 0.9), "white")
    t.torus("Hoop_ring", (hx - 0.5, (py0 + py1) / 2, 2.85), 0.32, 0.04, "orange")
    t.sphere("Ball", (cx - 3.0, py0 + 2.0, 0.3), (0.3, 0.3, 0.3), "orange")
    flag_gr(t, "SchFlag", px0 + 1.0, py1 - 1.5, 4.5, 0.9)
    # the teacher with her pointer
    tx, ty = px0 + 3.0, py0 + 3.5
    t.cyl("Teacher_body", (tx, ty, 1.0), 0.55, 1.3, "purple", r2=0.4)
    head = ((tx, ty - 0.03, 2.0), (0.5, 0.46, 0.52))
    t.sphere("Teacher_head", *head, "skin")
    t.sphere("Teacher_bun", (tx, ty + 0.3, 2.45), (0.3, 0.3, 0.3), "hair")
    t.sphere("Teacher_hair", (tx, ty + 0.1, 2.2), (0.52, 0.45, 0.35), "hair")
    t.face("Teacher", head, 0.12, (0.4, 0), smile=0.16)
    for sd in (-1, 1):
        t.torus("Teacher_gl%d" % sd, (tx + sd * 0.17, t.surface_y(head, sd * 0.17, 0.1) - 0.08, 2.1),
                0.13, 0.02, "dark", rot=(R(90), 0, 0))
    t.cyl("Teacher_stick", (tx + 0.7, ty - 0.3, 1.8), 0.03, 1.4, "wood", rot=(0, R(-40), 0), verts=6)


# ====================================================================== 6. the pitch

def pitch(mp):
    t = mp.t
    f = mp.cells("F")
    stripes = [(c, r) for (c, r) in f if c % 2 == 0]
    mp.patch("Pitch_a", [cr for cr in f if cr not in stripes], "pitch", 0.02)
    mp.patch("Pitch_b", stripes, "pitch2", 0.02)
    fc0, fr0, fc1, fr1 = mp.bounds("F")
    x0, x1, y0, y1 = mp.rect(fc0, fr0, fc1, fr1)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    lw = 0.12
    for (a, b, c, d) in [(x0 + 0.3, x1 - 0.3, y0 + 0.3, y0 + 0.3), (x0 + 0.3, x1 - 0.3, y1 - 0.3, y1 - 0.3),
                         (x0 + 0.3, x1 - 0.3, cy, cy)]:
        t.box("Line_h%.1f" % c, ((a + b) / 2, c, 0.04), (b - a, lw, 0.02), "white")
    for xx in (x0 + 0.3, x1 - 0.3):
        t.box("Line_v%.1f" % xx, (xx, cy, 0.04), (lw, y1 - y0 - 0.6, 0.02), "white")
    t.torus("Centre", (cx, cy, 0.04), 2.2, 0.06, "white", scale=(1, 1.4, 0.3))
    for k, gy in enumerate((y1 - 0.3, y0 + 0.3)):   # the goals
        for sd in (-1, 1):
            t.cyl("Post%d_%d" % (k, sd), (cx + sd * 1.6, gy, 0.9), 0.07, 1.8, "white", verts=8)
        t.cyl("Bar%d" % k, (cx, gy, 1.8), 0.07, 3.3, "white", rot=(0, R(90), 0), verts=8)
    t.sphere("Football", (cx + 1.2, cy - 2.0, 0.25), (0.25, 0.25, 0.25), "white")
    t.sphere("Football_p", (cx + 1.2, cy - 2.2, 0.32), (0.1, 0.05, 0.1), "black")
    paving(mp, "P", "grass2")
    # the stands, full of villagers
    c0, r0, c1, r1 = mp.bounds("K")
    sx0, sx1, sy0, sy1 = mp.rect(c0, r0, c1, r1)
    cols = ["red", "shutter", "yellow", "black", "white", "pink", "orange", "purple", "cyan"]
    for row in range(3):
        z = 0.4 + row * 0.8
        y = sy0 + 1.6 + row * 2.4
        t.box("Stand%d" % row, ((sx0 + sx1) / 2, y + 0.3, z / 2), (sx1 - sx0 - 0.4, 2.4, z), "stone")
        for k in range(9):
            x = sx0 + 1.4 + k * (sx1 - sx0 - 2.8) / 8 + (row % 2) * 0.6
            if x > sx1 - 0.8:
                continue
            villager(t, "Fan%d_%d" % (row, k), x, y + 0.3, z, cols[(k * 3 + row * 2) % len(cols)],
                     hair=("hair", "black", "silver")[(k + row) % 3], look=(0, 0.3),
                     hat="sariki" if (k + row) % 4 == 0 else None)
    # the coach and the bench on the touchline
    _, _, py0, py1 = mp.rect(*mp.bounds("P"))
    villager(t, "Coach", sx0 + 2.0, py0 + 2.0, 0, "red", hair="black", look=(0.4, 0.3), hat="cap")
    t.box("Bench", (sx1 - 4.0, py0 + 2.8, 0.5), (4.0, 0.7, 0.1), "wood")
    t.box("Bench_back", (sx1 - 4.0, py0 + 3.2, 0.9), (4.0, 0.1, 0.7), "wood")


# ====================================================================== 7. the cemetery church

def cemetery(mp):
    t = mp.t
    paving(mp, "KP", "stone")
    c0, r0, c1, r1 = mp.bounds("K")
    x0, x1, yf, yb = mp.rect(c0, r0, c1, r1)
    h = 3.2
    d = fit_depth(yf, yb, h + 2.5)
    church_body(t, "Chap", (x0 + x1) / 2 + 0.6, yf + 1.0, x1 - x0 - 3.2, d, h, dome="stone2", tower=False)
    for k, (dx, dy) in enumerate([(0.9, 2.0), (x1 - x0 - 0.9, 2.5)]):
        t.sphere("CCyp%d" % k, (x0 + dx, yf + dy, 2.0), (0.5, 0.5, 1.9), "cypress")
    _, _, py0, py1 = mp.rect(*mp.bounds("P"))
    t.priest("Papas", x0 + 3.0, py0 + 2.4, 0, look=(0.4, 0.2))
    t.yiayia("Mavrofora", x0 + 6.5, py0 + 2.4, 0, look=(-0.5, 0.2))
    for k in range(3):      # the oil lamps
        lx = x1 - 3.6 + k * 1.0
        t.cyl("Lamp%d" % k, (lx, yf + 0.9, 0.35), 0.15, 0.7, "gold", verts=10)
        t.sphere("LampF%d" % k, (lx, yf + 0.9, 0.82), (0.08, 0.08, 0.14), "flame")
