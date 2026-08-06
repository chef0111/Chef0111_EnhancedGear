from pathlib import Path

p = Path(__file__).with_name("retouch_outlines_from_originals.py")
text = p.read_text(encoding="utf-8")
start = text.index("def find_center_diagonal_axis(")
end = text.index("def glow_elements(")
new = r'''def find_center_diagonal_axis(
    opaque: set[tuple[int, int]],
    h: int,
) -> set[tuple[int, int]]:
    """Continuous center-diagonal spine (tip→pommel), 1 cell wide.

    Every spine cell stays unshifted. Sizing/push happens in compute_cell_boxes
    and only grows into empty / off-spine sides so the ridge never tears.
    """
    if not opaque:
        return set()

    centers: list[tuple[int, int, float, float]] = []
    for tx, ty in opaque:
        mx = tx + 0.5
        my = (h - ty - 1) + 0.5
        centers.append((tx, ty, mx, my))

    # Tip → pommel defines the tool diagonal (avoids guard/head bias).
    tip = max(centers, key=lambda c: (c[2] + c[3], c[2]))
    pom = min(centers, key=lambda c: (c[2] + c[3], c[2]))
    dx, dy = tip[2] - pom[2], tip[3] - pom[3]
    if abs(dx) < 1e-6 and abs(dy) < 1e-6:
        dx, dy = 1.0, 1.0
    if dx * dy >= 0:
        dx, dy = 1.0, 1.0
    else:
        dx, dy = 1.0, -1.0

    cx = (tip[2] + pom[2]) * 0.5
    cy = (tip[3] + pom[3]) * 0.5
    nrm = math.hypot(dx, dy)

    buckets: dict[int, tuple[float, int, int]] = {}
    for tx, ty, x, y in centers:
        dist = abs(((x - cx) * dy - (y - cy) * dx) / nrm)
        if dist > 0.85:
            continue
        proj = round(((x - cx) * dx + (y - cy) * dy) / nrm)
        prev = buckets.get(proj)
        if prev is None or dist < prev[0]:
            buckets[proj] = (dist, tx, ty)

    return {(tx, ty) for _d, tx, ty in buckets.values()}


def compute_cell_boxes(
    opaque: set[tuple[int, int]],
    w: int,
    h: int,
) -> dict[tuple[int, int], list[float]]:
    """Spine cubes grow to 1.2 on free sides; off-spine surrounds push 0.2."""
    ux, uy = 16.0 / w, 16.0 / h
    ridge = find_center_diagonal_axis(opaque, h)

    x_shift = {p: 0.0 for p in opaque}
    y_shift = {p: 0.0 for p in opaque}
    grow_x: dict[tuple[int, int], bool] = {}
    grow_y: dict[tuple[int, int], bool] = {}

    for tx, ty in ridge:
        # Grow only into empty or off-spine cells — never into the ridge.
        gx = (tx - 1, ty) not in ridge
        gy = (tx, ty - 1) not in ridge
        grow_x[(tx, ty)] = gx
        grow_y[(tx, ty)] = gy
        if gx:
            x = tx - 1
            while (x, ty) in opaque and (x, ty) not in ridge:
                x_shift[(x, ty)] = -PUSH
                x -= 1
        if gy:
            y = ty - 1
            while (tx, y) in opaque and (tx, y) not in ridge:
                y_shift[(tx, y)] = PUSH
                y -= 1

    boxes: dict[tuple[int, int], list[float]] = {}
    for tx, ty in opaque:
        my = h - ty - 1
        if (tx, ty) in ridge:
            x0 = tx - PAD if grow_x[(tx, ty)] else tx + PAD
            y0 = my - PAD
            x1 = tx + 1 + PAD
            y1 = my + 1 + PAD if grow_y[(tx, ty)] else my + 1 - PAD
        else:
            x0 = tx + PAD + x_shift[(tx, ty)]
            y0 = my - PAD + y_shift[(tx, ty)]
            x1, y1 = x0 + 1.0, y0 + 1.0
        boxes[(tx, ty)] = [
            round(x0 * ux, 3),
            round(y0 * uy, 3),
            round(x1 * ux, 3),
            round(y1 * uy, 3),
        ]
    return boxes


'''
p.write_text(text[:start] + new + text[end:], encoding="utf-8")
print("patched ok")
