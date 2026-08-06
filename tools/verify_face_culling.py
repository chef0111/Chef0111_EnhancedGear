#!/usr/bin/env python3
"""Verify glow models: full silhouette + original-style touching-face hiding."""
import json
from pathlib import Path
from PIL import Image
from collections import Counter

base = Path(r"D:\.legacy\Minecraft\game\home\Fabric-26.2\resourcepacks\Chef0111_EnhancedGear")


def opaque_tex(name: str):
    im = Image.open(base / f"assets/minecraft/textures/item/{name}.png").convert("RGBA")
    px = im.load()
    w, h = im.size
    return {(x, y) for y in range(h) for x in range(w) if px[x, y][3] > 0}, w, h


def check(item: str) -> list[str]:
    errs = []
    op, w, h = opaque_tex(item)
    data = json.loads(
        (base / f"assets/minecraft/models/item/enchanted_{item}.json").read_text(encoding="utf-8")
    )
    if len(data["elements"]) != len(op):
        errs.append(f"{item}: els {len(data['elements'])} != opaque {len(op)}")

    by_cell = {}
    for e in data["elements"]:
        if set(e["faces"]) != {"north", "south", "east", "west", "up", "down"}:
            errs.append(f"{item}: missing face keys")
            break
        x0, y0, _ = e["from"]
        tx = int(round(min(x0, e["to"][0]) - 0.1))
        my = int(round(min(y0, e["to"][1]) + 0.1))
        ty = h - my - 1
        by_cell[(tx, ty)] = e["faces"]
        # N/S always visible
        if e["faces"]["north"]["uv"] == [0, 0, 1, 1] or e["faces"]["south"]["uv"] == [0, 0, 1, 1]:
            errs.append(f"{item}: N/S hidden at {(tx, ty)}")

    if set(by_cell) != op:
        errs.append(f"{item}: cell set mismatch")

    # Touching-face rule
    dirs = {
        "east": (1, 0),
        "west": (-1, 0),
        "up": (0, -1),  # lower texture y
        "down": (0, 1),
    }
    bad = 0
    for (tx, ty), faces in by_cell.items():
        for face, (dx, dy) in dirs.items():
            touching = (tx + dx, ty + dy) in op
            hidden = faces[face]["uv"] == [0, 0, 1, 1]
            if touching != hidden:
                bad += 1
                if bad <= 5:
                    errs.append(
                        f"{item}: face rule fail {(tx, ty)} {face} touching={touching} hidden={hidden}"
                    )
    if bad:
        errs.append(f"{item}: {bad} face-rule mismatches total")

    vis = Counter(
        sum(1 for f in e["faces"].values() if f["uv"] != [0, 0, 1, 1]) for e in data["elements"]
    )
    print(f"OK-ish {item}: els={len(data['elements'])} visible-face hist={dict(vis)} errs={len(errs)}")
    return errs


errors = []
for item in ["diamond_sword", "copper_axe", "netherite_pickaxe", "iron_shovel", "wooden_hoe"]:
    errors.extend(check(item))

print("ERRORS", len(errors))
for e in errors:
    print(" -", e)
if not errors:
    print("ALL CHECKS PASSED")
