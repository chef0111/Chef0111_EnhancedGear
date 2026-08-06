#!/usr/bin/env python3
import json
from pathlib import Path
from collections import Counter

base = Path(r"D:\.legacy\Minecraft\game\home\Fabric-26.2\resourcepacks\Chef0111_EnhancedGear\assets\minecraft\models\item")


def analyze(name: str) -> None:
    data = json.loads((base / name).read_text(encoding="utf-8"))
    els = data["elements"]
    sizes = Counter()
    face_hist = Counter()
    for e in els:
        x0, y0, _ = e["from"]
        x1, y1, _ = e["to"]
        dx = round(abs(x1 - x0), 2)
        dy = round(abs(y1 - y0), 2)
        sizes[(dx, dy)] += 1
        face_hist[len(e["faces"])] += 1
    print(f"{name}: {len(els)} els, face_hist={dict(face_hist)}")
    print(f"  sizes={dict(sizes)}")
    print(f"  group={data.get('groups', [{}])[0].get('name')}")
    print(f"  sample faces={sorted(els[0]['faces'])} from={els[0]['from']} to={els[0]['to']}")


analyze("enchanted_axe.json")
analyze("enchanted_copper_axe.json")
analyze("enchanted_diamond_sword.json")

# Check no E-W / U-D double faces between adjacent pieces for copper axe
data = json.loads((base / "enchanted_copper_axe.json").read_text(encoding="utf-8"))
# Approximate cell occupancy from each rect
occupied_faces = []
for e in data["elements"]:
    x0, y0, _ = e["from"]
    x1, y1, _ = e["to"]
    # undo 0.1 pad: fx0=tx0+0.1, fx1=tx1+0.1, fy0=my0-0.1, fy1=my1-0.1
    tx0 = int(round(min(x0, x1) - 0.1))
    tx1 = int(round(max(x0, x1) - 0.1))
    my0 = int(round(min(y0, y1) + 0.1))
    my1 = int(round(max(y0, y1) + 0.1))
    occupied_faces.append((tx0, tx1, my0, my1, set(e["faces"])))

overlaps = 0
for i, (ax0, ax1, ay0, ay1, af) in enumerate(occupied_faces):
    for bx0, bx1, by0, by1, bf in occupied_faces[i + 1 :]:
        # horizontal adjacency
        if ay0 < by1 and by0 < ay1:
            if ax1 == bx0 and "east" in af and "west" in bf:
                overlaps += 1
            if bx1 == ax0 and "east" in bf and "west" in af:
                overlaps += 1
        # vertical adjacency
        if ax0 < bx1 and bx0 < ax1:
            if ay1 == by0 and "up" in af and "down" in bf:
                overlaps += 1
            if by1 == ay0 and "up" in bf and "down" in af:
                overlaps += 1
print("adjacent textured-face overlaps:", overlaps)

# customs still present
for rel in ["dragon_saber.json", "enchanted_sword.json", "enchanted_axe.json"]:
    assert (base / rel).exists(), rel
print("customs ok")
