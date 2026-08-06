#!/usr/bin/env python3
"""Generate Classic-Tools 3D defaults + enchantment outlines for vanilla tools.

Glow = exact 1x1 pad from latest commit, then +0.1 on every exterior side.
Diagonal staircase kisses are removed by L-splitting one cube so the union
silhouette stays solid (no gaps, no double-coverage). Body keeps the unwrapped
1x1 pad so FP/GUI stay locked. 32x32 spear_in_hand scales into 0..16 space.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TEX_DIR = ROOT / "assets" / "minecraft" / "textures" / "item"
MODELS = ROOT / "assets" / "minecraft" / "models" / "item"
DEFAULTS = MODELS / "defaults"
NO_GUI = MODELS / "no_gui_outline"
ITEMS = ROOT / "assets" / "minecraft" / "items"

MATERIALS = ["wooden", "stone", "iron", "golden", "copper", "diamond", "netherite"]
TOOLS_3D = ["sword", "pickaxe", "axe", "shovel", "hoe"]
ALL_TOOLS = TOOLS_3D + ["spear"]

TOOL_TEX_KEY = {
    "sword": "sword",
    "pickaxe": "pickaxe",
    "axe": "axe",
    "shovel": "shovel",
    "hoe": "hoe",
}

TOOL_DISPLAY_PARENT = {
    "sword": "item/sword_display",
    "pickaxe": "item/pickaxe_display",
    "axe": "item/axe_display",
    "shovel": "item/shovel_display",
    "hoe": "item/hoe_display",
}

HANDHELD_DISPLAY = {
    "thirdperson_righthand": {
        "rotation": [0, -90, 55],
        "translation": [0, 4, 0.5],
        "scale": [0.85, 0.85, 0.85],
    },
    "thirdperson_lefthand": {
        "rotation": [0, 90, -55],
        "translation": [0, 4, 0.5],
        "scale": [0.85, 0.85, 0.85],
    },
    "firstperson_righthand": {
        "rotation": [0, -90, 25],
        "translation": [1.13, 3.2, 1.13],
        "scale": [0.68, 0.68, 0.68],
    },
    "firstperson_lefthand": {
        "rotation": [0, 90, -25],
        "translation": [1.13, 3.2, 1.13],
        "scale": [0.68, 0.68, 0.68],
    },
    "ground": {"translation": [0, 3, 0], "scale": [0.5, 0.5, 0.5]},
    "gui": {"scale": [1.05, 1.05, 1]},
    "head": {"rotation": [0, 180, 0], "translation": [0, 13, 7]},
    "fixed": {"rotation": [0, 180, 0], "scale": [1.02, 1.02, 1.02]},
}

NO_GUI_DISPLAY = {
    **HANDHELD_DISPLAY,
    "gui": {"scale": [1, 1, 1]},
}

NEIGHBORS_8 = [
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
    (1, 1),
    (1, -1),
    (-1, 1),
    (-1, -1),
]


def load_opaque(path: Path) -> tuple[int, int, set[tuple[int, int]]]:
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    px = im.load()
    opaque: set[tuple[int, int]] = set()
    for y in range(h):
        for x in range(w):
            if px[x, y][3] > 0:
                opaque.add((x, y))
    return w, h, opaque


def outline_cells(opaque: set[tuple[int, int]], w: int, h: int) -> set[tuple[int, int]]:
    """1px outline ring around opaque texels (8-neighbor), allowing 1px outside bounds."""
    out: set[tuple[int, int]] = set()
    for x, y in opaque:
        for dx, dy in NEIGHBORS_8:
            n = (x + dx, y + dy)
            if n not in opaque and -1 <= n[0] <= w and -1 <= n[1] <= h:
                out.add(n)
    return out


def merge_runs(cells: set[tuple[int, int]]) -> list[tuple[int, int, int, int]]:
    """Merge horizontally adjacent cells into (x0, y, x1_exclusive, y+1) boxes."""
    by_row: dict[int, list[int]] = {}
    for x, y in cells:
        by_row.setdefault(y, []).append(x)
    boxes: list[tuple[int, int, int, int]] = []
    for y, xs in sorted(by_row.items()):
        xs = sorted(set(xs))
        start = xs[0]
        prev = xs[0]
        for x in xs[1:]:
            if x == prev + 1:
                prev = x
                continue
            boxes.append((start, y, prev + 1, y + 1))
            start = prev = x
        boxes.append((start, y, prev + 1, y + 1))
    return boxes


def tex_uv(x0: int, y0: int, x1: int, y1: int, w: int = 16, h: int = 16) -> list[float]:
    """Clamp UV sample into 0..16 atlas space for glow / item textures."""
    u0 = max(0, min(w, x0))
    v0 = max(0, min(h, y0))
    u1 = max(0, min(w, x1))
    v1 = max(0, min(h, y1))
    if u0 == u1:
        u1 = min(w, u0 + 1)
    if v0 == v1:
        v1 = min(h, v0 + 1)
    return [float(u0), float(v0), float(u1), float(v1)]


# Exact 1x1 pad from Chef originals / latest commit:
#   [tx+0.1, my-0.1] -> [tx+1.1, my+0.9]
# Body keeps that pad. Glow wraps +THICKEN on every exterior side so the
# silhouette outline reads 0.1 thicker. Diagonal notch double-coverage is
# then L-split away (union preserved — no ortho gaps, no corner kisses).
PAD_X = 0.1
PAD_Y = -0.1
THICKEN = 0.1
GLOW_ATLAS = 16
CREDIT = "Classic silhouette; exact 1x1 pad + 0.1 exterior wrap"


def body_elements(opaque: set[tuple[int, int]], tex_key: str, w: int, h: int) -> list[dict]:
    """Body uses exact 1x1 pad (merged runs). Scale into 0..16 for 32x32 spears."""
    boxes = merge_runs(opaque)
    elements = []
    z0, z1 = 7.5, 8.5
    ux, uy = 16.0 / w, 16.0 / h
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        # texture y grows down; model y grows up
        my0 = h - y1
        my1 = h - y0
        uv = tex_uv(x0, y0, x1, y1, w, h)
        north_uv = [float(uv[2]), float(uv[1]), float(uv[0]), float(uv[3])]
        elements.append(
            {
                "name": f"{tex_key}_{i}",
                "from": [
                    round((float(x0) + PAD_X) * ux, 3),
                    round((float(my0) + PAD_Y) * uy, 3),
                    z0,
                ],
                "to": [
                    round((float(x1) + PAD_X) * ux, 3),
                    round((float(my1) + PAD_Y) * uy, 3),
                    z1,
                ],
                "faces": {
                    "north": {"uv": north_uv, "texture": f"#{tex_key}"},
                    "east": {
                        "uv": tex_uv(x1 - 1, y0, x1, y1, w, h),
                        "texture": f"#{tex_key}",
                    },
                    "south": {"uv": uv, "texture": f"#{tex_key}"},
                    "west": {
                        "uv": tex_uv(x0, y0, x0 + 1, y1, w, h),
                        "texture": f"#{tex_key}",
                    },
                    "up": {
                        "uv": tex_uv(x0, y0, x1, y0 + 1, w, h),
                        "texture": f"#{tex_key}",
                    },
                    "down": {
                        "uv": tex_uv(x0, y1 - 1, x1, y1, w, h),
                        "texture": f"#{tex_key}",
                    },
                },
            }
        )
    return elements


def glow_uv(tx: int, ty: int, w: int, h: int) -> list[float]:
    """Sample glow atlas in 0..16 even when the tool texture is 32x32."""
    gu = min(GLOW_ATLAS - 1, (tx * GLOW_ATLAS) // w)
    gv = min(GLOW_ATLAS - 1, (ty * GLOW_ATLAS) // h)
    return [float(gu), float(gv), float(gu + 1), float(gv + 1)]


def _norm_xy(element: dict) -> tuple[float, float, float, float]:
    fr, to = element["from"], element["to"]
    return (
        min(fr[0], to[0]),
        min(fr[1], to[1]),
        max(fr[0], to[0]),
        max(fr[1], to[1]),
    )


def _aabb_subtract(
    victim: tuple[float, float, float, float],
    hole: tuple[float, float, float, float],
    eps: float = 1e-9,
) -> list[tuple[float, float, float, float]]:
    """Axis-aligned rectangles covering victim \\ hole (union-preserving)."""
    vx0, vy0, vx1, vy1 = victim
    hx0 = max(hole[0], vx0)
    hy0 = max(hole[1], vy0)
    hx1 = min(hole[2], vx1)
    hy1 = min(hole[3], vy1)
    if hx1 - hx0 <= eps or hy1 - hy0 <= eps:
        return [victim]

    parts: list[tuple[float, float, float, float]] = []
    if hy0 - vy0 > eps:
        parts.append((vx0, vy0, vx1, hy0))
    if vy1 - hy1 > eps:
        parts.append((vx0, hy1, vx1, vy1))
    if hx0 - vx0 > eps:
        parts.append((vx0, hy0, hx0, hy1))
    if vx1 - hx1 > eps:
        parts.append((hx1, hy0, vx1, hy1))
    return parts or [victim]


def _with_xy(
    element: dict,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> dict:
    fr, to = element["from"], element["to"]
    return {
        "from": [round(x0, 3), round(y0, 3), fr[2]],
        "to": [round(x1, 3), round(y1, 3), to[2]],
        "light_emission": element["light_emission"],
        "rotation": element["rotation"],
        "faces": element["faces"],
    }


def resolve_diagonal_kisses(
    elements: list[dict],
    ux: float,
    uy: float,
) -> list[dict]:
    """Remove corner overlaps via L-split; keep silhouette union.

    Keeper cube stays intact (owns the corner). Victim becomes 1–2 AABBs that
    cover everything it covered except the intersection. Ortho flush planes are
    untouched — only the overlapping region is reassigned to one owner.

    Threshold is 2×THICKEN so cascading splits that leave 0.2×0.1 residuals
    still get cleaned (plain 0.1×0.1 kisses are the common case).
    """
    # Allow up to two thicken steps of residual after prior splits.
    max_kiss = 2.0 * THICKEN * min(ux, uy) + 1e-6
    current = list(elements)

    for _ in range(256):
        rects = [_norm_xy(e) for e in current]
        kisses: list[tuple[float, int, int, tuple[float, float, float, float]]] = []
        for i, a in enumerate(rects):
            for j in range(i + 1, len(rects)):
                b = rects[j]
                ox = min(a[2], b[2]) - max(a[0], b[0])
                oy = min(a[3], b[3]) - max(a[1], b[1])
                if ox <= 1e-9 or oy <= 1e-9:
                    continue
                if ox > max_kiss or oy > max_kiss:
                    continue
                hx0 = max(a[0], b[0])
                hy0 = max(a[1], b[1])
                hx1 = min(a[2], b[2])
                hy1 = min(a[3], b[3])
                area_i = (a[2] - a[0]) * (a[3] - a[1])
                area_j = (b[2] - b[0]) * (b[3] - b[1])
                # Prefer carving the smaller fragment so large rim cubes stay intact.
                if area_j < area_i - 1e-12:
                    victim_i, keeper_i = j, i
                else:
                    victim_i, keeper_i = i, j
                kisses.append((ox * oy, keeper_i, victim_i, (hx0, hy0, hx1, hy1)))

        if not kisses:
            break

        # Smallest overlap first (stable cleanup of thin residuals).
        kisses.sort(key=lambda t: t[0])
        _, _keeper, victim_i, hole = kisses[0]
        victim = current[victim_i]
        parts = _aabb_subtract(_norm_xy(victim), hole)
        new_els = [
            _with_xy(victim, x0, y0, x1, y1)
            for x0, y0, x1, y1 in parts
            if (x1 - x0) > 1e-9 and (y1 - y0) > 1e-9
        ]
        current = current[:victim_i] + new_els + current[victim_i + 1 :]
    else:
        raise RuntimeError("resolve_diagonal_kisses: did not converge")

    return current


def glow_elements(
    opaque: set[tuple[int, int]],
    w: int,
    h: int,
    glow: str = "glow",
) -> list[dict]:
    """One cube per opaque texel: exact 1x1 pad, then +0.1 on exterior sides.

    Base (latest commit): [tx+0.1, my-0.1] -> [tx+1.1, my+0.9]
    Wrap: expand each open side by THICKEN (0.1). Shared ortho edges stay flush.

    Diagonal staircase corners would otherwise share a THICKEN×THICKEN kiss.
    Those are L-split afterward so the union silhouette stays solid — same
    exterior size as full wrap, without darker double-coverage.

    Body keeps the unwrapped 1x1 pad (same center / PAD), so FP/GUI do not
    shift; the glow simply sticks out 0.1 past the body on open edges.
    """
    elements: list[dict] = []
    z_front, z_back = 8.6, 7.4
    ux, uy = 16.0 / w, 16.0 / h
    hidden = {"uv": [0, 0, 1, 1], "texture": f"#{glow}"}

    for tx, ty in sorted(opaque, key=lambda p: (p[1], p[0])):
        my = h - ty - 1
        open_w = (tx - 1, ty) not in opaque
        open_e = (tx + 1, ty) not in opaque
        open_u = (tx, ty - 1) not in opaque
        open_d = (tx, ty + 1) not in opaque

        fx0 = float(tx) + PAD_X - (THICKEN if open_w else 0.0)
        fx1 = float(tx) + 1.0 + PAD_X + (THICKEN if open_e else 0.0)
        fy0 = float(my) + PAD_Y - (THICKEN if open_d else 0.0)
        fy1 = float(my) + 1.0 + PAD_Y + (THICKEN if open_u else 0.0)

        uv = glow_uv(tx, ty, w, h)
        visible = {"uv": uv, "texture": f"#{glow}"}
        elements.append(
            {
                "from": [
                    round(fx0 * ux, 3),
                    round(fy0 * uy, 3),
                    z_front,
                ],
                "to": [
                    round(fx1 * ux, 3),
                    round(fy1 * uy, 3),
                    z_back,
                ],
                "light_emission": 15,
                "rotation": {
                    "angle": 0,
                    "axis": "y",
                    "origin": [round(float(tx) * ux, 3), round(float(my) * uy, 3), 5.7],
                },
                "faces": {
                    "north": visible,
                    "south": visible,
                    "east": hidden if not open_e else visible,
                    "west": hidden if not open_w else visible,
                    "up": hidden if not open_u else visible,
                    "down": hidden if not open_d else visible,
                },
            }
        )

    return resolve_diagonal_kisses(elements, ux, uy)


def write_json(path: Path, data: dict) -> None:
    """Write Blockbench-like compact JSON (arrays inline)."""
    path.parent.mkdir(parents=True, exist_ok=True)

    def fmt(obj, indent: int = 0) -> str:
        sp = "\t" * indent
        sp1 = "\t" * (indent + 1)
        if isinstance(obj, dict):
            if not obj:
                return "{}"
            lines = ["{"]
            items = list(obj.items())
            for i, (k, v) in enumerate(items):
                comma = "," if i < len(items) - 1 else ""
                lines.append(f'{sp1}"{k}": {fmt(v, indent + 1)}{comma}')
            lines.append(f"{sp}}}")
            return "\n".join(lines)
        if isinstance(obj, list):
            # Keep short numeric / mixed face-like arrays on one line
            if not obj:
                return "[]"
            if all(isinstance(x, (int, float, str)) and not isinstance(x, bool) for x in obj):
                inner = ", ".join(json.dumps(x) for x in obj)
                return f"[{inner}]"
            lines = ["["]
            for i, v in enumerate(obj):
                comma = "," if i < len(obj) - 1 else ""
                lines.append(f"{sp1}{fmt(v, indent + 1)}{comma}")
            lines.append(f"{sp}]")
            return "\n".join(lines)
        return json.dumps(obj)

    path.write_text(fmt(data) + "\n", encoding="utf-8")


def write_rpo(model_path: Path, no_gui_rel: str) -> None:
    rpo = model_path.with_suffix(".json.rpo")
    rpo.write_text(
        "{\n"
        '    condition: "enchantmentOutline.guiOutline.on",\n'
        "    fallbacks: [\n"
        f'      "{no_gui_rel}"\n'
        "    ]\n"
        "}\n",
        encoding="utf-8",
    )


def build_default_model(item: str, tool: str, opaque: set[tuple[int, int]], w: int, h: int) -> dict:
    key = TOOL_TEX_KEY[tool]
    return {
        "credit": "Generated from Classic Tools Fusion silhouette",
        "parent": TOOL_DISPLAY_PARENT[tool],
        "gui_light": "front",
        "textures": {
            key: f"item/{item}",
            "particle": f"item/{item}",
        },
        "elements": body_elements(opaque, key, w, h),
    }


def build_outline_model(
    opaque: set[tuple[int, int]],
    w: int,
    h: int,
    display: dict | None = None,
    glow_key: str = "glow",
    parent: str = "minecraft:item/handheld",
) -> dict:
    elements = glow_elements(opaque, w, h, glow_key)
    model: dict = {
        "parent": parent,
        "gui_light": "front",
        "credit": CREDIT,
        "textures": {
            glow_key: "item/enchanted_tool_overlays/enchantment_outline",
            "particle": "item/enchanted_tool_overlays/enchantment_outline",
        },
        "elements": elements,
        "groups": [
            {
                "name": "emissive_1",
                "origin": [12, 15, 0],
                "color": 0,
                "children": list(range(len(elements))),
            }
        ],
    }
    # Omit display to inherit parent transforms (critical for spear_in_hand).
    if display is not None:
        model["display"] = display
    return model


def build_flat_spear_model(item: str) -> dict:
    return {
        "parent": "minecraft:item/generated",
        "gui_light": "front",
        "credit": "Classic Tools Fusion texture",
        "textures": {"layer0": f"item/{item}"},
    }


def build_spear_in_hand_model(item: str) -> dict:
    # Vanilla spear pose lives on spear_in_hand — do not use handheld (sword) display.
    return {
        "parent": "minecraft:item/spear_in_hand",
        "gui_light": "front",
        "credit": "Classic Tools Fusion texture",
        "textures": {"layer0": f"item/{item}"},
    }


def generate_models() -> list[str]:
    written: list[str] = []
    DEFAULTS.mkdir(parents=True, exist_ok=True)
    NO_GUI.mkdir(parents=True, exist_ok=True)

    for mat in MATERIALS:
        for tool in TOOLS_3D:
            item = f"{mat}_{tool}"
            tex = TEX_DIR / f"{item}.png"
            if not tex.exists():
                raise FileNotFoundError(tex)
            w, h, opaque = load_opaque(tex)

            default_path = DEFAULTS / f"{item}.json"
            write_json(default_path, build_default_model(item, tool, opaque, w, h))
            written.append(str(default_path.relative_to(ROOT)))

            outline = build_outline_model(opaque, w, h, HANDHELD_DISPLAY)
            outline_path = MODELS / f"enchanted_{item}.json"
            write_json(outline_path, outline)
            written.append(str(outline_path.relative_to(ROOT)))

            no_gui = build_outline_model(opaque, w, h, NO_GUI_DISPLAY)
            no_gui_path = NO_GUI / f"enchanted_{item}.json"
            write_json(no_gui_path, no_gui)
            written.append(str(no_gui_path.relative_to(ROOT)))
            write_rpo(
                outline_path,
                f"assets/minecraft/models/item/no_gui_outline/enchanted_{item}.json",
            )

        # Spears: body models + GUI/in-hand outlines
        spear = f"{mat}_spear"
        spear_hand = f"{mat}_spear_in_hand"
        spear_tex = TEX_DIR / f"{spear}.png"
        hand_tex_path = TEX_DIR / f"{spear_hand}.png"
        hand_tex_name = spear_hand if hand_tex_path.exists() else spear

        write_json(MODELS / f"{spear}.json", build_flat_spear_model(spear))
        written.append(f"assets/minecraft/models/item/{spear}.json")
        write_json(MODELS / f"{spear_hand}.json", build_spear_in_hand_model(hand_tex_name))
        written.append(f"assets/minecraft/models/item/{spear_hand}.json")

        for item, tex_path, is_hand in [
            (spear, spear_tex, False),
            (spear_hand, TEX_DIR / f"{hand_tex_name}.png", True),
        ]:
            w, h, opaque = load_opaque(tex_path)
            if is_hand:
                # Inherit vanilla spear_in_hand first/third-person pose.
                outline = build_outline_model(
                    opaque,
                    w,
                    h,
                    display=None,
                    parent="minecraft:item/spear_in_hand",
                )
                no_gui = build_outline_model(
                    opaque,
                    w,
                    h,
                    display=None,
                    parent="minecraft:item/spear_in_hand",
                )
            else:
                # GUI/ground/fixed only — handheld display is fine here.
                outline = build_outline_model(opaque, w, h, HANDHELD_DISPLAY)
                no_gui = build_outline_model(opaque, w, h, NO_GUI_DISPLAY)
            outline_path = MODELS / f"enchanted_{item}.json"
            write_json(outline_path, outline)
            written.append(str(outline_path.relative_to(ROOT)))

            no_gui_path = NO_GUI / f"enchanted_{item}.json"
            write_json(no_gui_path, no_gui)
            written.append(str(no_gui_path.relative_to(ROOT)))
            write_rpo(
                outline_path,
                f"assets/minecraft/models/item/no_gui_outline/enchanted_{item}.json",
            )

    return written


def tool_type_from_item(item_id: str) -> str | None:
    for tool in ALL_TOOLS:
        if item_id.endswith(f"_{tool}"):
            return tool
    return None


def retarget_items() -> list[str]:
    """Replace shared enchanted_<tool> refs with enchanted_<material_tool> in vanilla items only."""
    changed: list[str] = []
    for mat in MATERIALS:
        for tool in ALL_TOOLS:
            item = f"{mat}_{tool}"
            path = ITEMS / f"{item}.json"
            if not path.exists():
                print(f"skip missing items file: {path.name}")
                continue
            text = path.read_text(encoding="utf-8")
            original = text

            if tool == "spear":
                text = text.replace(
                    '"model": "minecraft:item/enchanted_spear"',
                    f'"model": "minecraft:item/enchanted_{mat}_spear"',
                )
                text = text.replace(
                    '"model": "minecraft:item/enchanted_spear_in_hand"',
                    f'"model": "minecraft:item/enchanted_{mat}_spear_in_hand"',
                )
            else:
                # Only replace shared type outlines, not already-material-specific ones
                pattern = rf'("model"\s*:\s*")minecraft:item/enchanted_{tool}(")'
                text = re.sub(pattern, rf"\1minecraft:item/enchanted_{item}\2", text)

            if text != original:
                path.write_text(text, encoding="utf-8")
                changed.append(str(path.relative_to(ROOT)))
    return changed


def verify_customs_untouched() -> None:
    customs = [
        MODELS / "dragon_saber.json",
        MODELS / "ezio_pickaxe.json",
        MODELS / "ender_sword.json",
        MODELS / "enchanted_sword.json",  # shared outline kept for diminishing/custom
        MODELS / "enchanted_pickaxe.json",
        MODELS / "enchanted_axe.json",
        MODELS / "enchanted_shovel.json",
        MODELS / "enchanted_hoe.json",
        MODELS / "enchanted_spear.json",
    ]
    for p in customs:
        if not p.exists():
            raise FileNotFoundError(f"Expected custom/shared file missing: {p}")
    # netherite_sword should still have Dragon Saber case
    ns = (ITEMS / "netherite_sword.json").read_text(encoding="utf-8")
    assert "Dragon Saber" in ns and "dragon_saber" in ns
    assert "enchanted_netherite_sword" in ns
    assert '"minecraft:item/enchanted_sword"' not in ns.replace("enchanted_netherite_sword", "")
    # crude check: shared enchanted_sword should not remain in fallback
    if re.search(r'minecraft:item/enchanted_sword"', ns):
        raise AssertionError("netherite_sword still references shared enchanted_sword")


def main() -> None:
    written = generate_models()
    changed = retarget_items()
    verify_customs_untouched()
    print(f"Wrote {len(written)} model files")
    print(f"Retargeted {len(changed)} item definitions")
    print("Custom/shared assets preserved.")


if __name__ == "__main__":
    main()
