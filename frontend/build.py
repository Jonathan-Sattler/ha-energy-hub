"""Assemble the house card: embeds the material textures and writes the served file.

Run: uv run --with pillow python frontend/build.py
"""
import base64, io, json
from pathlib import Path
from PIL import Image, ImageEnhance

ROOT = Path(__file__).resolve().parent.parent
TEX = ROOT / "design" / "textures"
SPEC = {"plaster": ("white_plaster.png", 128, 70), "brown": ("brown_plaster.png", 64, 70), "clinker": ("plinth_clinker.png", 240, 78),
        "roof": ("roof_tiles_brown.png", 288, 80), "door": ("garage_door.png", 96, 78), "wood": ("dark_wood.png", 96, 72),
        "pavers": ("driveway_pavers.png", 200, 78), "terrace": ("terrace_slabs.png", 240, 80)}
tex = {}
for key, (name, width, quality) in SPEC.items():
    im = Image.open(TEX / name).convert("RGB")
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    if key == "roof":
        im = ImageEnhance.Contrast(im).enhance(1.15)
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=quality, optimize=True)
    tex[key] = {"uri": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}
src = (Path(__file__).parent / "card.src.js").read_text()
out = ROOT / "custom_components" / "energy_hub" / "frontend" / "energy-hub-house-card.js"
out.write_text(src.replace("__TEX__", json.dumps(tex)))
print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")
