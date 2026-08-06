#!/usr/bin/env python3
from pathlib import Path
import json
import re

root = Path(r"D:\.legacy\Minecraft\game\home\Fabric-26.2\resourcepacks\Chef0111_EnhancedGear")
mats = ["wooden", "stone", "iron", "golden", "copper", "diamond", "netherite"]
tools = ["sword", "pickaxe", "axe", "shovel", "hoe", "spear"]
errors = []

for m in mats:
    for t in tools:
        item = f"{m}_{t}"
        checks = [
            root / f"assets/minecraft/models/item/enchanted_{item}.json",
            root / f"assets/minecraft/models/item/no_gui_outline/enchanted_{item}.json",
            root / f"assets/minecraft/textures/item/{item}.png",
            root / f"assets/minecraft/items/{item}.json",
        ]
        if t != "spear":
            checks.append(root / f"assets/minecraft/models/item/defaults/{item}.json")
        else:
            checks += [
                root / f"assets/minecraft/models/item/{item}.json",
                root / f"assets/minecraft/models/item/{item}_in_hand.json",
                root / f"assets/minecraft/models/item/enchanted_{item}_in_hand.json",
            ]
        for c in checks:
            if not c.exists():
                errors.append(f"MISSING {c.relative_to(root)}")

        text = (root / f"assets/minecraft/items/{item}.json").read_text(encoding="utf-8")
        if t == "spear":
            if f"enchanted_{m}_spear" not in text:
                errors.append(f"{item}.json missing enchanted_{m}_spear")
            cleaned = text.replace(f"minecraft:item/enchanted_{m}_spear_in_hand", "")
            cleaned = cleaned.replace(f"minecraft:item/enchanted_{m}_spear", "")
            if "minecraft:item/enchanted_spear" in cleaned:
                errors.append(f"{item}.json still has shared enchanted_spear")
        else:
            if f"enchanted_{item}" not in text:
                errors.append(f"{item}.json missing enchanted_{item}")
            if re.search(rf'minecraft:item/enchanted_{t}"', text):
                errors.append(f"{item}.json still references shared enchanted_{t}")

for rel in [
    "assets/minecraft/models/item/dragon_saber.json",
    "assets/minecraft/models/item/ezio_pickaxe.json",
    "assets/minecraft/models/item/ender_sword.json",
    "assets/minecraft/models/item/enchanted_sword.json",
    "assets/minecraft/models/item/enchanted_pickaxe.json",
]:
    if not (root / rel).exists():
        errors.append(f"CUSTOM MISSING {rel}")

ns = (root / "assets/minecraft/items/netherite_sword.json").read_text(encoding="utf-8")
for s in ["Dragon Saber", "dragon_saber", "The Creation Ender", "ender_sword", "enchanted_netherite_sword"]:
    if s not in ns:
        errors.append(f"netherite_sword missing {s}")

np = (root / "assets/minecraft/items/netherite_pickaxe.json").read_text(encoding="utf-8")
for s in ["Ezio's Pick", "ezio_pickaxe", "enchanted_netherite_pickaxe"]:
    if s not in np:
        errors.append(f"netherite_pickaxe missing {s}")

dim = (root / "assets/minecraft/items/diminishing_items/diminishing_copper_sword.json").read_text(encoding="utf-8")
if "minecraft:item/enchanted_sword" not in dim:
    errors.append("diminishing copper sword lost shared enchanted_sword")

for sample in ["defaults/diamond_sword.json", "enchanted_iron_pickaxe.json", "enchanted_netherite_axe.json"]:
    data = json.loads((root / "assets/minecraft/models/item" / sample).read_text(encoding="utf-8"))
    if not data.get("elements"):
        errors.append(f"{sample} has no elements")
    if "enchanted" in sample and data["elements"][0].get("light_emission") != 15:
        errors.append(f"{sample} missing light_emission")

# silhouette match sanity: outline cells should roughly equal dilated ring
from PIL import Image

def opaque(path):
    im = Image.open(path).convert("RGBA")
    px = im.load()
    w, h = im.size
    return {(x, y) for y in range(h) for x in range(w) if px[x, y][3] > 0}, w, h

def ring(op, w, h):
    out = set()
    for x, y in op:
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            n = (x+dx, y+dy)
            if n not in op and -1 <= n[0] <= w and -1 <= n[1] <= h:
                out.add(n)
    return out

for item in ["diamond_sword", "netherite_axe", "iron_pickaxe"]:
    op, w, h = opaque(root / f"assets/minecraft/textures/item/{item}.png")
    expected = len(ring(op, w, h))
    data = json.loads((root / f"assets/minecraft/models/item/enchanted_{item}.json").read_text(encoding="utf-8"))
    # each element covers a run; count covered cells via from/to
    covered = 0
    for e in data["elements"]:
        x0, y0, _ = e["from"]
        x1, y1, _ = e["to"]
        # undo 0.1 pad
        covered += max(1, int(round((x1 - 0.1) - (x0 + 0.1)))) * max(1, int(round((y1 - 0.1) - (y0 + 0.1))))
    if covered < expected * 0.5:
        errors.append(f"{item} outline coverage low: {covered} vs expected~{expected}")

print(f"ERRORS: {len(errors)}")
for e in errors:
    print(" -", e)
if not errors:
    print("ALL CHECKS PASSED")
