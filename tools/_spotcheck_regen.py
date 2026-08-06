#!/usr/bin/env python3
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

root = Path(__file__).resolve().parents[1] / "assets/minecraft/models/item"


def analyze(name: str) -> None:
    data = json.loads((root / name).read_text(encoding="utf-8"))
    els = data["elements"]
    sizes = Counter()
    bad_uv = 0
    overlaps = 0
    minx = miny = 1e9
    maxx = maxy = -1e9
    rects = []
    for el in els:
        fr, to = el["from"], el["to"]
        sx = round(to[0] - fr[0], 3)
        sy = round(to[1] - fr[1], 3)
        sizes[(sx, sy)] += 1
        minx, maxx = min(minx, fr[0], to[0]), max(maxx, fr[0], to[0])
        miny, maxy = min(miny, fr[1], to[1]), max(maxy, fr[1], to[1])
        rects.append((fr[0], fr[1], to[0], to[1]))
        for fd in el["faces"].values():
            uv = fd.get("uv")
            if uv and any(v < 0 or v > 16 for v in uv):
                bad_uv += 1
    for i, a in enumerate(rects):
        for b in rects[i + 1 :]:
            ox = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            oy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            if ox > 1e-9 and oy > 1e-9:
                overlaps += 1
    print(f"=== {name} ({len(els)} els) ===")
    print(f"  span X [{minx:.3f}, {maxx:.3f}] = {maxx-minx:.3f}")
    print(f"  span Y [{miny:.3f}, {maxy:.3f}] = {maxy-miny:.3f}")
    print(f"  bad_uv={bad_uv} overlaps={overlaps}")
    print(f"  sizes: {sizes.most_common(8)}")


for n in [
    "enchanted_diamond_sword.json",
    "enchanted_diamond_spear.json",
    "enchanted_diamond_spear_in_hand.json",
    "defaults/diamond_sword.json",
]:
    analyze(n)
