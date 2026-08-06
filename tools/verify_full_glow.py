#!/usr/bin/env python3
import json
from pathlib import Path
from PIL import Image
from collections import Counter

base = Path(r"D:\.legacy\Minecraft\game\home\Fabric-26.2\resourcepacks\Chef0111_EnhancedGear")


def opaque_tex(name: str):
    im = Image.open(base / f"assets/minecraft/textures/item/{name}.png").convert("RGBA")
    px = im.load()
    w, h = im.size
    op = {(x, y) for y in range(h) for x in range(w) if px[x, y][3] > 0}
    return op, w, h


def model_cells(name: str):
    data = json.loads((base / f"assets/minecraft/models/item/{name}.json").read_text(encoding="utf-8"))
    cells = set()
    for e in data["elements"]:
        assert set(e["faces"]) == {"north", "south", "east", "west", "up", "down"}, e["faces"].keys()
        x0, y0, _ = e["from"]
        x1, y1, _ = e["to"]
        tx0 = int(round(min(x0, x1) - 0.1))
        tx1 = int(round(max(x0, x1) - 0.1))
        my0 = int(round(min(y0, y1) + 0.1))
        my1 = int(round(max(y0, y1) + 0.1))
        h = 16
        # convert model y range back to texture y
        ty0 = h - my1
        ty1 = h - my0
        for x in range(tx0, tx1):
            for y in range(ty0, ty1):
                cells.add((x, y))
        # face sanity: north/south not hidden
        assert e["faces"]["north"]["uv"] != [0, 0, 1, 1]
        assert e["faces"]["south"]["uv"] != [0, 0, 1, 1]
    return cells, data


errors = []
for item in ["diamond_sword", "copper_axe", "netherite_pickaxe", "iron_shovel"]:
    op, w, h = opaque_tex(item)
    cells, data = model_cells(f"enchanted_{item}")
    if cells != op:
        missing = op - cells
        extra = cells - op
        errors.append(f"{item}: mismatch missing={len(missing)} extra={len(extra)}")
        # print ascii
        grid = [[" "] * 16 for _ in range(16)]
        for x, y in op:
            grid[y][x] = "O"
        for x, y in cells:
            grid[y][x] = "#" if (x, y) in op else "X"
        print(item)
        for row in grid:
            print("".join(row))
    else:
        face_hist = Counter(sum(1 for f in e["faces"].values() if f["uv"] != [0, 0, 1, 1]) for e in data["elements"])
        print(f"OK {item}: {len(cells)} cells == opaque, els={len(data['elements'])}, visible-face hist={dict(face_hist)}")

# customs untouched
for rel in [
    "assets/minecraft/models/item/dragon_saber.json",
    "assets/minecraft/models/item/enchanted_sword.json",
    "assets/minecraft/models/item/enchanted_axe.json",
]:
    if not (base / rel).exists():
        errors.append(f"missing {rel}")

print("ERRORS", len(errors))
for e in errors:
    print(" -", e)
