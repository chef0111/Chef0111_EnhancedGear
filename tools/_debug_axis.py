from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location(
    "r", Path(__file__).with_name("retouch_outlines_from_originals.py")
)
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

for name in ("diamond_sword", "diamond_pickaxe"):
    w, h, op = r.load_opaque(
        Path(__file__).resolve().parents[1] / f"assets/minecraft/textures/item/{name}.png"
    )
    axis = r.find_center_diagonal_axis(op, h)
    print(f"\n=== {name} axis={len(axis)} ===")
    print(sorted(axis))
    for ty in range(h):
        row = ""
        for tx in range(w):
            if (tx, ty) in axis:
                row += "A"
            elif (tx, ty) in op:
                row += "#"
            else:
                row += "."
        print(f"{ty:2d} {row}")
    boxes = r.compute_cell_boxes(op, w, h)
    print("gaps", r.count_ortho_gaps(op, boxes))
    # size breakdown for axis cells
    for tx, ty in sorted(axis):
        b = boxes[(tx, ty)]
        print(f"  axis {tx,ty} size=({b[2]-b[0]:.1f},{b[3]-b[1]:.1f}) box={b}")
