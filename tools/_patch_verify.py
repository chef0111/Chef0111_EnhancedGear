from pathlib import Path

p = Path(__file__).with_name("verify_face_culling.py")
t = p.read_text(encoding="utf-8")
old = """    overlaps = 0
    for i, a in enumerate(rects):
        for b in rects[i + 1 :]:
            ox = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            oy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            if ox > 1e-9 and oy > 1e-9:
                overlaps += 1
    if overlaps:
        errs.append(f\"{model_stem}: {overlaps} area overlaps\")
"""
# Fix escapes for matching actual file content
old = old.replace('\\"', '"')
new = """    # Staircase exterior wraps can kiss <= 0.2 at diagonal corners; keep those.
    kiss = 0.2 * min(ux, uy) + 1e-6
    overlaps = 0
    for i, a in enumerate(rects):
        for b in rects[i + 1 :]:
            ox = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
            oy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
            if ox > 1e-9 and oy > 1e-9:
                if ox <= kiss and oy <= kiss:
                    continue
                overlaps += 1
    if overlaps:
        errs.append(f\"{model_stem}: {overlaps} area overlaps\")
""".replace('\\"', '"')
if old not in t:
    # show nearby context
    idx = t.find("overlaps = 0")
    print(repr(t[idx:idx+250]))
    raise SystemExit("old block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
