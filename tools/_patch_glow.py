from pathlib import Path

path = Path(__file__).with_name("generate_classic_outlines.py")
text = path.read_text(encoding="utf-8")
start = text.index("def resolve_thicken_overlaps(")
end = text.index("def write_json(")
new = '''def glow_elements(
    opaque: set[tuple[int, int]],
    w: int,
    h: int,
    glow: str = "glow",
) -> list[dict]:
    """One cube per opaque texel: exact 1x1 pad, then +0.1 on exterior sides.

    Base (latest commit): [tx+0.1, my-0.1] -> [tx+1.1, my+0.9]
    Wrap: expand each open side by THICKEN (0.1). Shared ortho edges stay flush.

    Diagonal staircase corners can share a THICKEN x THICKEN kiss where both
    neighbors expand into the same empty notch. That tiny double-coverage is
    kept on purpose — peeling it back opened visible gaps in the silhouette.

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
    return elements


'''
path.write_text(text[:start] + new + text[end:], encoding="utf-8")
print("ok")
