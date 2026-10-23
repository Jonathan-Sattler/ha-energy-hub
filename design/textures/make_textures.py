"""Generate seamless PNG material textures for the house model (SketchUp etc.).

Run:  uv run --with pillow --with numpy python design/textures/make_textures.py
Outputs 1024 px PNGs into design/textures/. Real-world sizes are printed for the
SketchUp material dialog.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).parent
SIZE = 1024
rng = np.random.default_rng(42)


def periodic_noise(size: int, beta: float, seed: int) -> np.ndarray:
    """Fractal noise that tiles seamlessly, built in the frequency domain."""
    r = np.random.default_rng(seed)
    white = r.standard_normal((size, size))
    f = np.fft.fft2(white)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    radius = np.sqrt(fx**2 + fy**2)
    radius[0, 0] = 1.0
    f *= 1.0 / radius**beta
    f[0, 0] = 0
    out = np.real(np.fft.ifft2(f))
    out -= out.min()
    out /= out.max()
    return out


def band(size: int, lo: float, hi: float, seed: int) -> np.ndarray:
    """Noise limited to one frequency band (0..1 normalised), seamless."""
    r = np.random.default_rng(seed)
    white = r.standard_normal((size, size))
    f = np.fft.fft2(white)
    fy = np.fft.fftfreq(size)[:, None]
    fx = np.fft.fftfreq(size)[None, :]
    radius = np.sqrt(fx**2 + fy**2) * 2  # 0..1
    mask = ((radius >= lo) & (radius < hi)).astype(float)
    out = np.real(np.fft.ifft2(f * mask))
    out = (out - out.mean()) / (out.std() + 1e-9)
    return out


def to_img(rgb: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")


def hex_rgb(h: str) -> np.ndarray:
    return np.array([int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)], dtype=float)


def plaster(base_hex: str, name: str, grain: float = 9.0, mottle: float = 5.0) -> None:
    """Rough rendered plaster: fine speckle grain plus low-frequency mottling."""
    base = hex_rgb(base_hex)
    fine = band(SIZE, 0.25, 1.0, seed=1 if name == "white" else 7)
    mid = band(SIZE, 0.05, 0.25, seed=2 if name == "white" else 8)
    low = periodic_noise(SIZE, 2.2, seed=3 if name == "white" else 9) - 0.5
    lum = fine * grain + mid * (grain * 0.5) + low * mottle * 2
    # sparse darker pits like a sprayed render
    pits = band(SIZE, 0.6, 1.0, seed=5) > 2.4
    lum = lum - pits * 14
    rgb = base[None, None, :] + lum[..., None]
    img = to_img(rgb)
    img.save(OUT / f"{name}_plaster.png")


def band_rect(h: int, w: int, lo: float, hi: float, seed: int) -> np.ndarray:
    """Seamless band-limited noise for a non-square image."""
    r = np.random.default_rng(seed)
    white = r.standard_normal((h, w))
    f = np.fft.fft2(white)
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    radius = np.sqrt(fx**2 + fy**2) * 2
    mask = ((radius >= lo) & (radius < hi)).astype(float)
    out = np.real(np.fft.ifft2(f * mask))
    return (out - out.mean()) / (out.std() + 1e-9)


def roof_tiles() -> None:
    """Weathered concrete pan tiles as on the house: half-round barrel beside a flat
    trough, barrels in continuous columns (no stagger), rows overlapping with a lip.
    Image 1200 x 1000 px = 1.2 x 1.0 m: 4 tiles of 30 cm across, 3 rows of 33.3 cm."""
    W, H = 1200, 1000
    cols, rows = 4, 3
    tw, th = W / cols, H / rows
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    u = (xx % tw) / tw
    v = (yy % th) / th
    row = np.floor(yy / th)
    col = np.floor(xx / tw)

    # --- surface height across one tile: flat trough 0..0.52, barrel 0.52..1.0 (half round)
    bc, br = 0.76, 0.24
    inside = np.abs(u - bc) < br
    barrel = np.where(inside, np.sqrt(np.clip(1 - ((u - bc) / br) ** 2, 0, 1)), 0.0)
    trough = -0.05 * np.sin(np.pi * np.clip(u / 0.52, 0, 1))  # very slight dish
    height = barrel * 1.0 + trough
    # --- lighting from the true surface normal (light from the upper left, slightly in front)
    nx = np.where(inside, (u - bc) / br, 0.0)          # half-round barrel: normal = (x, z) / r
    nz = np.sqrt(np.clip(1 - nx**2, 0, 1))
    lx, lz = -0.62, 0.78
    diffuse = np.clip(nx * lx + nz * lz, 0, 1)
    lighting = 0.38 + 0.72 * diffuse                     # ambient + diffuse, 0.38 .. 1.1
    # specular sheen on the barrel crest facing the light
    lighting += 0.18 * np.exp(-((u - (bc - 0.09)) / 0.05) ** 2) * inside
    # cast shadow of each barrel onto the trough to its right (start of the next tile)
    lighting -= 0.30 * np.exp(-((u) / 0.07) ** 2) + 0.12 * np.exp(-((u - 0.12) / 0.06) ** 2)
    # --- row overlap: lip at the bottom of each tile, hard shadow on the top of the tile below
    lip = np.exp(-((1 - v) / 0.02) ** 2)
    lighting += 0.16 * lip - 0.42 * np.exp(-((v) / 0.05) ** 2) - 0.14 * np.exp(-((v - 0.08) / 0.05) ** 2)
    lighting -= 0.10 * np.exp(-((1 - v) / 0.006) ** 2)  # dark edge line right at the lip

    # --- colour: weathered grey-brown; troughs greyer, barrels browner
    base_trough = hex_rgb("#7a685c")
    base_barrel = hex_rgb("#8a6c5c")
    px = base_trough[None, None, :] * (1 - barrel[..., None]) + base_barrel[None, None, :] * barrel[..., None]
    # per-tile tint and large-scale mottling, as additive offsets before lighting
    tile_id = (col + 97 * row).astype(int)
    r = np.random.default_rng(11)
    tints = r.normal(0, 8, size=(tile_id.max() + 2,))
    px += (tints[tile_id] + band_rect(H, W, 0.25, 1.0, 12) * 5 + band_rect(H, W, 0.03, 0.2, 13) * 7)[..., None]
    px = px * np.clip(lighting, 0.15, 1.3)[..., None]

    # --- lichen specks: small pale dots, more on the flat parts
    speck = band_rect(H, W, 0.5, 1.0, 15)
    lichen = (speck > 2.3) & (barrel < 0.7)
    lichen_soft = np.array(Image.fromarray((lichen * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.1))) / 255.0
    px = px * (1 - lichen_soft[..., None] * 0.8) + hex_rgb("#c4bdb0")[None, None, :] * lichen_soft[..., None] * 0.8
    # --- moss clumps: dark olive, in the troughs just above the row overlap
    clump = band_rect(H, W, 0.08, 0.35, 16)
    moss = (clump > 1.6) & (barrel < 0.35) & (v > 0.5)
    moss_soft = np.array(Image.fromarray((moss * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))) / 255.0
    px = px * (1 - moss_soft[..., None] * 0.9) + hex_rgb("#4a4733")[None, None, :] * moss_soft[..., None] * 0.9
    # fine concrete grain last
    px += band_rect(H, W, 0.6, 1.0, 17)[..., None] * 3.5
    to_img(px).save(OUT / "roof_tiles_brown.png")


def dark_wood() -> None:
    """Dark stained spruce boards, vertical, 10 cm wide, seamless."""
    base = hex_rgb("#4b3020")
    boards = 10
    bw = SIZE / boards
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    u = (xx % bw) / bw
    board_id = np.floor(xx / bw).astype(int)
    r = np.random.default_rng(21)
    tint = r.normal(0, 6, size=boards)[board_id]
    # grain: stretched noise along y, warped a little per board
    warp = band(SIZE, 0.02, 0.1, seed=22) * 6
    grain_src = band(SIZE, 0.08, 0.6, seed=23)
    grain = np.zeros_like(grain_src)
    for b in range(boards):
        sel = board_id == b
        shift = int(r.integers(0, SIZE))
        grain[sel] = np.roll(grain_src, shift, axis=0)[sel]
    # growth rings seen edge-on: dense dark lines that wander along the board
    rings = np.sin(xx * 0.9 + warp * 1.8 + grain * 4.0)
    grain = np.clip(rings, 0.2, 1) * -9 + grain * 4 + band(SIZE, 0.3, 1.0, seed=24) * 2
    shade = tint + grain
    # board edges: dark gap and bevel highlight
    shade += -34 * np.exp(-(np.minimum(u, 1 - u) * 60) ** 2) + 8 * np.exp(-((u - 0.06) * 30) ** 2)
    px = base[None, None, :] + shade[..., None]
    px[..., 0] += grain * 0.3  # warm highlights
    to_img(px).save(OUT / "dark_wood.png")


def plinth() -> None:
    """Clinker brick slips along the base of the walls: 24 x 7.1 cm bricks, 1 cm
    light grey joints, running bond with half-brick offset, flamed tan-to-dark-brown
    colour per brick with mottling. Image 1000 x 972 px = 1.0 x 0.972 m
    (4 bricks across, 12 courses)."""
    W, H = 1000, 972
    bw, bh, joint = 250.0, 81.0, 10.0  # brick pitch incl. joint, in px (1 px = 1 mm)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    course = np.floor(yy / bh)
    offset = np.where(course % 2 == 1, bw / 2, 0.0)
    u = (xx + offset) % bw
    v = yy % bh
    in_brick = (u >= joint) & (v >= joint)
    # soften brick corners and give the face a slight pillow edge
    ub = (u - joint) / (bw - joint)
    vb = (v - joint) / (bh - joint)
    edge = np.minimum(np.minimum(ub, 1 - ub) * (bw - joint), np.minimum(vb, 1 - vb) * (bh - joint))
    bevel = np.clip(edge / 6.0, 0, 1)

    # per-brick colour from a flamed palette
    brick_id = (np.floor((xx + offset) / bw) + 131 * course).astype(int)
    r = np.random.default_rng(31)
    n = brick_id.max() + 2
    palette = np.array([hex_rgb(c) for c in ["#b3804e", "#a86f44", "#8f5a38", "#7a4a30", "#64392a", "#4f2e22", "#c08e5c"]])
    pick = r.integers(0, len(palette), size=n)
    blend = r.random(size=n)
    pick2 = r.integers(0, len(palette), size=n)
    # flamed look: each brick fades from one palette colour to another along a random direction
    ang = r.random(size=n) * 2 * np.pi
    gx, gy = np.cos(ang)[brick_id], np.sin(ang)[brick_id]
    t = np.clip(0.5 + 0.9 * ((ub - 0.5) * gx + (vb - 0.5) * gy * 0.35), 0, 1)
    px = palette[pick][brick_id] * (1 - t[..., None]) + palette[pick2][brick_id] * t[..., None]
    px = px * (0.9 + 0.2 * blend[brick_id][..., None])  # overall lightness varies per brick
    # subtle mottling and fine speckle
    px += (band_rect(H, W, 0.15, 0.6, 33) * 5)[..., None]
    speck = band_rect(H, W, 0.6, 1.0, 34)
    px += (speck * 6)[..., None]
    px += ((speck > 2.2) * 28)[..., None] * np.array([1.1, .9, .7])[None, None, :]   # light sand grains
    px -= ((speck < -2.3) * 30)[..., None]                                           # dark pits
    px *= (0.82 + 0.18 * bevel)[..., None]
    # mortar
    mortar = hex_rgb("#c9c3b6")[None, None, :] + (band_rect(H, W, 0.3, 1.0, 35) * 6)[..., None]
    mortar -= (band_rect(H, W, 0.05, 0.3, 36) * 5)[..., None]
    out = np.where(in_brick[..., None], px, mortar)
    # recessed joints: shadow on the mortar just below and right of each brick
    shadow = (~in_brick) * (np.exp(-((u) / 5.0) ** 2) * (u < joint) + np.exp(-((v) / 5.0) ** 2) * (v < joint))
    out *= (1 - 0.22 * np.clip(shadow, 0, 1))[..., None]
    to_img(out).save(OUT / "plinth_clinker.png")
    old = OUT / "plinth_plaster.png"
    if old.exists():
        old.unlink()


def garage_door() -> None:
    """Sectional garage door as on both garages (Ansicht 5): four equal, flat, smooth
    sections stacked, matte sepia brown, with a fine joint line between sections.
    Image 1000 x 2000 px covers the WHOLE door height: set the image height to the
    door height in Fusion (then each section is a quarter), width 1.0 m, tiles
    seamlessly sideways."""
    W, H = 1000, 2000
    base = hex_rgb("#64483a")  # sepia brown; Fusion's viewport renders it noticeably darker
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    sec = H / 4
    v = yy % sec
    # joint between sections: 8 mm shadow line with a 3 mm light edge below it
    # (bolder than the real joint so it still reads at model viewing distance)
    d = np.minimum(v, sec - v)
    groove = -60 * np.exp(-(d / 4.0) ** 2)
    lip = 14 * np.exp(-((v - 9.0) / 2.0) ** 2)
    # gaps at the top (frame) and bottom (floor seal): plain dark edge
    edge = -20 * np.exp(-(np.minimum(yy, H - 1 - yy) / 2.5) ** 2)
    # each section is very slightly lighter at the top (powder-coated steel, soft sheen)
    sheen = 2 * np.cos(v / sec * np.pi)
    # barely visible coating texture
    fine = band_rect(H, W, 0.5, 1.0, 43) * 1.2 + band_rect(H, W, 0.05, 0.3, 44) * 1.5
    lum = groove + lip + edge + sheen + fine
    px = base[None, None, :] + lum[..., None]
    to_img(px).save(OUT / "garage_door.png")


if __name__ == "__main__":
    plaster("#efece4", "white")
    plaster("#7a5540", "brown")
    plinth()
    roof_tiles()
    dark_wood()
    garage_door()
    print("written:", sorted(p.name for p in OUT.glob("*.png")))
    print("SketchUp sizes: white/brown plaster 1.0 x 1.0 m; plinth_clinker 1.0 x 0.972 m; roof_tiles_brown 1.2 x 1.0 m; dark_wood 1.0 x 1.0 m; garage_door 1.0 m wide x full door height (4 sections)")
