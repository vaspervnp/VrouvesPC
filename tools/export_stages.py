"""Copy the stage data of the CPC original (../VrouvesCPC/tools/gen_assets.py) into
data/stages.json for the Godot game: maps, ground (one or two roads) and air waypoints, sacks, waves,
toughness and the defenders each stage has.

    python3 tools/export_stages.py [path/to/VrouvesCPC]
"""
import json
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), "VrouvesCPC")
sys.path.insert(0, os.path.join(CPC, "tools"))

# gen_assets imports Pillow only to write previews; the data does not need it
if "PIL" not in sys.modules:
    pil = types.ModuleType("PIL")
    pil.Image = types.ModuleType("PIL.Image")
    sys.modules["PIL"] = pil
    sys.modules["PIL.Image"] = pil.Image

import gen_assets as g  # noqa: E402

BASE_NAMES = ["kafenio", "church", "town_hall", "bakery", "school", "pitch", "cemetery",
              "sheepfold", "olive_press", "wedding"]


def main():
    stages = []
    for k, st in enumerate(g.STAGES):
        unlock = g.UNLOCKS[min(k, len(g.UNLOCKS) - 1)][0]
        grid = g.carve_path(st.map, st.ground)
        if st.ground2:
            grid = g.carve_path(grid, st.ground2)
        stages.append({
            "id": k + 1,
            "base": BASE_NAMES[k],
            "map": [r.ljust(g.MW, '.')[:g.MW] for r in st.map],
            "grid": grid,
            "ground": [list(p) for p in st.ground],
            # a second road for the walkers (every other one takes it), or none
            "ground2": [list(p) for p in st.ground2] if st.ground2 else [],
            "air": [list(p) for p in st.air],
            "sacks": [list(p) for p in st.sacks],
            "waves": [[list(grp) for grp in w] for w in getattr(g, st.waves)],
            "toughness": st.toughness,
            "defenders": sorted(unlock),
            "strings": {key: list(v) for key, v in st.strings.items()},
        })
    out = os.path.join(ROOT, "data", "stages.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"cols": g.MW, "rows": g.MH, "stages": stages}, f, ensure_ascii=False, indent=1)
    print("wrote", out, len(stages), "stages")


if __name__ == "__main__":
    main()
