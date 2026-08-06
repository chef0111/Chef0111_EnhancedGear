#!/usr/bin/env python3
import json
from pathlib import Path
from collections import Counter

data = json.loads(
    Path(
        r"D:\.legacy\Minecraft\game\home\Fabric-26.2\resourcepacks\Chef0111_EnhancedGear\assets\minecraft\models\item\enchanted_sword.json"
    ).read_text(encoding="utf-8")
)

boxes = []
for i, e in enumerate(data["elements"]):
    x0, y0, z0 = e["from"]
    x1, y1, z1 = e["to"]
    xa, xb = sorted([x0, x1])
    ya, yb = sorted([y0, y1])
    if xb - xa > 1.5 or yb - ya > 1.5:
        continue
    cx = (xa + xb) / 2
    cy = (ya + yb) / 2
    boxes.append((round(cx), round(cy), xa, ya, xb, yb, e))

print("Horizontal adjacent edge deltas (neg=overlap, pos=gap, 0=flush):")
deltas = Counter()
for i, (acx, acy, a0, b0, a1, b1, ea) in enumerate(boxes):
    for bcx, bcy, c0, d0, c1, d1, eb in boxes[i + 1 :]:
        if acy != bcy:
            continue
        if abs(bcx - acx) != 1:
            continue
        if acx < bcx:
            left_r, right_l = a1, c0
            left, right = ea, eb
        else:
            left_r, right_l = c1, a0
            left, right = eb, ea
        delta = round(right_l - left_r, 3)
        deltas[delta] += 1
        lv_e = left["faces"]["east"]["uv"] != [0, 0, 1, 1]
        rv_w = right["faces"]["west"]["uv"] != [0, 0, 1, 1]
        if deltas[delta] <= 3:
            print(
                f"  dens {acx},{acy}->{bcx},{bcy} delta={delta} "
                f"L_east_vis={lv_e} R_west_vis={rv_w} "
                f"L=[{min(left['from'][0], left['to'][0]):.2f},{max(left['from'][0], left['to'][0]):.2f}] "
                f"R=[{min(right['from'][0], right['to'][0]):.2f},{max(right['from'][0], right['to'][0]):.2f}]"
            )

print("delta hist", dict(deltas))

print("\nVertical adjacent edge deltas:")
vdeltas = Counter()
for i, (acx, acy, a0, b0, a1, b1, ea) in enumerate(boxes):
    for bcx, bcy, c0, d0, c1, d1, eb in boxes[i + 1 :]:
        if acx != bcx:
            continue
        if abs(bcy - acy) != 1:
            continue
        if acy < bcy:
            bottom_t, top_b = b1, d0
            bottom, top = ea, eb
        else:
            bottom_t, top_b = d1, b0
            bottom, top = eb, ea
        delta = round(top_b - bottom_t, 3)
        vdeltas[delta] += 1
        if vdeltas[delta] <= 3:
            print(f"  dens {acx},{acy}->{bcx},{bcy} delta={delta}")

print("vdelta hist", dict(vdeltas))

# Classify each ~1x1 by neighbor flags vs box relative to integer cell
print("\nRule: for each cell, compare box edges to integer [px,px+1]/")
rules = Counter()
for cx, cy, xa, ya, xb, yb, e in boxes:
    px, py = cx, cy  # already rounded centers used as pixel
    # recompute better: nearest int of floor(center)
    px = int((xa + xb) / 2)
    py = int((ya + yb) / 2)
    left = round(xa - px, 3)  # expected 0 for flush, -0.1 expand, +0.1 inset
    right = round(xb - (px + 1), 3)
    down = round(ya - py, 3)
    up = round(yb - (py + 1), 3)
    vis = {k: v["uv"] != [0, 0, 1, 1] for k, v in e["faces"].items()}
    # infer neighbors from face visibility (hidden => touching)
    touch = (
        not vis["west"],
        not vis["east"],
        not vis["down"],
        not vis["up"],
    )
    rules[(touch, left, right, down, up)] += 1

print("top patterns (touchW,E,D,U) + (left,right,down,up offsets):")
for k, v in rules.most_common(25):
    print(f"  {v}: touch={k[0]} off={k[1:]}")
