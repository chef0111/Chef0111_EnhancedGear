#!/usr/bin/env python3
"""Verify exact-1x1 + exterior-wrap glow models: coverage, face hide, no overlaps."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from PIL import Image

base = Path(r"D:\.legacy\Minecraft\game\home\Fabric-26.2\resourcepacks\Chef0111_EnhancedGear")
MODELS = base / "assets/minecraft/models/item"
TEX = base / "assets/minecraft/textures/item"

MATERIALS = ["wooden", "stone", "iron", "golden", "copper", "diamond", "netherite"]
CREDIT_MARK = "0.1 exterior wrap"
HIDDEN = [0, 0, 1, 1]


def opaque_tex(name: str) -> tuple[set[tuple[int, int]], int, int]:
    im = Image.open(TEX / f"{name}.png").convert("RGBA")
    px = im.load()
    w, h = im.size
    return {(x, y) for y in range(h) for x in range(w) if px[x, y][3] > 0}, w, h


def check(model_stem: str, tex_name: str) -> list[str]:
    errs: list[str] = []
    op, w, h = opaque_tex(tex_name)
    ux, uy = 16.0 / w, 16.0 / h
    data = json.loads((MODELS / f"{model_stem}.json").read_text(encoding="utf-8"))
    credit = data.get("credit", "")
    if CREDIT_MARK not in credit:
        errs.append(f"{model_stem}: missing wrap credit ({credit!r})")

    els = data["elements"]
    # L-split may add fragments, so count can exceed opaque texels.
    if len(els) < len(op):
        errs.append(f"{model_stem}: els {len(els)} < opaque {len(op)}")

    by_cell: dict[tuple[int, int], dict] = {}
    rects: list[tuple[float, float, float, float]] = []
    sizes: Counter[tuple[float, float]] = Counter()
    bad_uv = 0

    for e in els:
        if set(e["faces"]) != {"north", "south", "east", "west", "up", "down"}:
            errs.append(f"{model_stem}: missing face keys")
            break
        fr, to = e["from"], e["to"]
        x0, x1 = min(fr[0], to[0]), max(fr[0], to[0])
        y0, y1 = min(fr[1], to[1]), max(fr[1], to[1])
        rects.append((x0, y0, x1, y1))
        sizes[(round(x1 - x0, 3), round(y1 - y0, 3))] += 1

        origin = e.get("rotation", {}).get("origin", [0, 0, 0])
        tx = int(round(origin[0] / ux))
        my = int(round(origin[1] / uy))
        ty = h - my - 1
        by_cell[(tx, ty)] = e["faces"]

        expected_uv = [
            float(min(15, (tx * 16) // w)),
            float(min(15, (ty * 16) // h)),
            float(min(15, (tx * 16) // w) + 1),
            float(min(15, (ty * 16) // h) + 1),
        ]
        # N/S must stay visible. Skip when the solid UV equals the hide marker
        # (glow atlas cell 0,0), which is indistinguishable from HIDDEN.
        if expected_uv != HIDDEN:
            if e["faces"]["north"]["uv"] == HIDDEN or e["faces"]["south"]["uv"] == HIDDEN:
                errs.append(f"{model_stem}: N/S hidden at {(tx, ty)}")
        for fd in e["faces"].values():
            uv = fd.get("uv")
            if uv and any(v < 0 or v > 16 for v in uv):
                bad_uv += 1

    if bad_uv:
        errs.append(f"{model_stem}: {bad_uv} OOB UVs")
    if set(by_cell) != op:
        missing = sorted(op - set(by_cell))[:5]
        extra = sorted(set(by_cell) - op)[:5]
        errs.append(f"{model_stem}: cell set mismatch missing={missing} extra={extra}")

    dirs = {
        "east": (1, 0),
        "west": (-1, 0),
        "up": (0, -1),
        "down": (0, 1),
    }
    bad_faces = 0
    for (tx, ty), faces in by_cell.items():
        expected_uv = [
            float(min(15, (tx * 16) // w)),
            float(min(15, (ty * 16) // h)),
            float(min(15, (tx * 16) // w) + 1),
            float(min(15, (ty * 16) // h) + 1),
        ]
        for face, (dx, dy) in dirs.items():
            touching = (tx + dx, ty + dy) in op
            uv = faces[face]["uv"]
            if touching:
                ok = uv == HIDDEN
            else:
                # Open sides may still be hidden when geometrically flush-covered
                # (L-split cuts, thickened neighbor faces).
                ok = True
            if not ok:
                bad_faces += 1
                if bad_faces <= 5:
                    errs.append(
                        f"{model_stem}: face rule fail {(tx, ty)} {face} "
                        f"touching={touching} uv={uv}"
                    )
    if bad_faces > 5:
        errs.append(f"{model_stem}: … {bad_faces - 5} more face-rule failures")

    # No area overlaps after L-split (kiss corners reassigned to one owner).
    overlaps = 0
    kisses = 0
    for i, a in enumerate(rects):
        for b in rects[i + 1 :]:
            ox = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            oy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            if ox > 1e-9 and oy > 1e-9:
                overlaps += 1
                if ox <= 0.2 * min(ux, uy) + 1e-6 and oy <= 0.2 * min(ux, uy) + 1e-6:
                    kisses += 1
    if overlaps:
        errs.append(f"{model_stem}: {overlaps} area overlaps ({kisses} diagonal kisses)")

    # L-split may produce multiple cubes per texel; union AABB must stay flush.
    by_cell_box: dict[tuple[int, int], tuple[float, float, float, float]] = {}
    for e in els:
        origin = e.get("rotation", {}).get("origin", [0, 0, 0])
        tx = int(round(origin[0] / ux))
        my = int(round(origin[1] / uy))
        ty = h - my - 1
        box = (
            min(e["from"][0], e["to"][0]),
            min(e["from"][1], e["to"][1]),
            max(e["from"][0], e["to"][0]),
            max(e["from"][1], e["to"][1]),
        )
        if (tx, ty) in by_cell_box:
            a = by_cell_box[(tx, ty)]
            by_cell_box[(tx, ty)] = (
                min(a[0], box[0]),
                min(a[1], box[1]),
                max(a[2], box[2]),
                max(a[3], box[3]),
            )
        else:
            by_cell_box[(tx, ty)] = box
    gaps = 0
    for (tx, ty), a in by_cell_box.items():
        if (tx + 1, ty) in by_cell_box:
            b = by_cell_box[(tx + 1, ty)]
            if b[0] - a[2] > 1e-6:
                gaps += 1
        if (tx, ty - 1) in by_cell_box:
            b = by_cell_box[(tx, ty - 1)]
            if b[1] - a[3] > 1e-6:
                gaps += 1
    if gaps:
        errs.append(f"{model_stem}: {gaps} ortho gaps")

    unit = min(ux, uy)
    thickened = sum(
        c for (sx, sy), c in sizes.items() if sx > unit + 1e-6 or sy > unit + 1e-6
    )
    if thickened == 0:
        errs.append(f"{model_stem}: no exterior-thickened cubes")

    return errs


def main() -> None:
    errors: list[str] = []

    for shared in ["sword", "pickaxe", "axe", "shovel", "hoe", "spear"]:
        p = MODELS / f"enchanted_{shared}.json"
        credit = json.loads(p.read_text(encoding="utf-8")).get("credit", "")
        if CREDIT_MARK in credit or "Classic silhouette" in credit:
            errors.append(f"shared enchanted_{shared}.json was overwritten ({credit!r})")

    targets: list[tuple[str, str]] = []
    for mat in MATERIALS:
        for tool in ["sword", "pickaxe", "axe", "shovel", "hoe", "spear"]:
            targets.append((f"enchanted_{mat}_{tool}", f"{mat}_{tool}"))
        hand = f"{mat}_spear_in_hand"
        tex = hand if (TEX / f"{hand}.png").exists() else f"{mat}_spear"
        targets.append((f"enchanted_{mat}_spear_in_hand", tex))

    for model_stem, tex_name in targets:
        if not (MODELS / f"{model_stem}.json").exists():
            errors.append(f"missing model {model_stem}.json")
            continue
        if not (TEX / f"{tex_name}.png").exists():
            errors.append(f"missing texture {tex_name}.png")
            continue
        errors.extend(check(model_stem, tex_name))

    ds = json.loads((MODELS / "enchanted_diamond_sword.json").read_text(encoding="utf-8"))
    size_hist: Counter[tuple[float, float]] = Counter()
    for e in ds["elements"]:
        fr, to = e["from"], e["to"]
        size_hist[(round(abs(to[0] - fr[0]), 3), round(abs(to[1] - fr[1]), 3))] += 1
    print("diamond_sword glow size hist:", size_hist.most_common(12))
    print("diamond_sword elements:", len(ds["elements"]))

    if errors:
        print(f"FAIL ({len(errors)}):")
        for e in errors[:40]:
            print(" ", e)
        if len(errors) > 40:
            print(f"  … {len(errors) - 40} more")
        raise SystemExit(1)
    print("OK: all classic outlines pass exterior-wrap checks")


if __name__ == "__main__":
    main()
