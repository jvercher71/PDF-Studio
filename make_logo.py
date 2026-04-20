"""
Zeus PDF Logo Generator
Creates the lightning bolt "Z" logo in all required sizes.
Run once: python3 make_logo.py
Outputs: assets/zeuspdf.png, assets/zeuspdf.icns, assets/zeuspdf.ico
"""
import os
import struct
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]
ASSETS = Path("assets")
ASSETS.mkdir(exist_ok=True)


def draw_logo(size: int) -> Image.Image:
    """
    Zeus PDF logo: deep navy background, gold lightning bolt,
    subtle glow, 'Z' letterform worked into the bolt shape.
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size

    # ── Background: rounded square ─────────────────────────────────
    pad = int(s * 0.04)
    bg_rect = [pad, pad, s - pad, s - pad]
    radius = int(s * 0.18)

    # Dark gradient feel via two layered rounded rects
    draw.rounded_rectangle(bg_rect, radius=radius,
                           fill=(15, 20, 45, 255))          # deep navy
    # Inner highlight strip (top)
    hi_rect = [pad, pad, s - pad, pad + int(s * 0.35)]
    draw.rounded_rectangle(hi_rect, radius=radius,
                           fill=(25, 35, 75, 180))

    # ── Lightning bolt — classic Z-bolt shape ──────────────────────
    # Defined as fraction of size so it scales cleanly
    cx = s * 0.5
    # Bolt points (top-right to bottom-left, wide Z shape)
    bolt = [
        (s * 0.62, s * 0.10),   # top-right tip
        (s * 0.28, s * 0.46),   # mid-left
        (s * 0.52, s * 0.46),   # mid-right indent
        (s * 0.18, s * 0.90),   # bottom-left tip
        (s * 0.52, s * 0.52),   # mid-left lower
        (s * 0.30, s * 0.52),   # mid-right lower indent
    ]
    bolt = [(int(x), int(y)) for x, y in bolt]

    # Glow layer (soft gold blur approximated by larger polygon)
    glow_expand = max(2, int(s * 0.025))
    glow_pts = _expand_polygon(bolt, glow_expand)
    draw.polygon(glow_pts, fill=(255, 215, 0, 60))   # gold glow

    # Main bolt — gold gradient simulation (two polygons)
    draw.polygon(bolt, fill=(255, 200, 30, 255))     # bright gold
    # Inner highlight (lighter stripe down the bolt)
    inner = _expand_polygon(bolt, -max(1, int(s * 0.015)))
    if inner:
        draw.polygon(inner, fill=(255, 240, 120, 180))

    # ── White outline on bolt ──────────────────────────────────────
    # Draw outline by stroking slightly larger polygon in white, then bolt on top
    # (PIL doesn't have stroke, so layer it)
    outline = _expand_polygon(bolt, max(1, int(s * 0.012)))
    draw.polygon(outline, fill=(255, 255, 255, 80))
    draw.polygon(bolt, fill=(255, 200, 30, 255))
    draw.polygon(inner, fill=(255, 240, 120, 180))

    # ── Small "PDF" text tag at bottom ────────────────────────────
    if size >= 128:
        tag_h = max(12, int(s * 0.12))
        tag_rect = [int(s*0.15), int(s*0.82), int(s*0.85), int(s*0.93)]
        draw.rounded_rectangle(tag_rect, radius=int(s*0.03),
                               fill=(255, 200, 30, 220))
        # "PDF" in navy text — use default font for reliability
        try:
            font_size = max(8, int(s * 0.09))
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except Exception:
            font = ImageFont.load_default()

        text = "PDF"
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (tag_rect[0] + tag_rect[2]) // 2 - tw // 2
        ty = (tag_rect[1] + tag_rect[3]) // 2 - th // 2
        draw.text((tx, ty), text, fill=(15, 20, 45, 255), font=font)

    return img


def _expand_polygon(pts: list, amount: int) -> list:
    """Expand/contract polygon by moving each point outward from centroid."""
    if not pts or amount == 0:
        return pts
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    result = []
    for x, y in pts:
        dx = x - cx
        dy = y - cy
        dist = (dx**2 + dy**2) ** 0.5
        if dist == 0:
            result.append((x, y))
        else:
            factor = (dist + amount) / dist
            result.append((int(cx + dx * factor), int(cy + dy * factor)))
    return result


def make_all():
    print("Generating Zeus PDF logo...")

    # ── Master PNG (1024px) ────────────────────────────────────────
    master = draw_logo(1024)
    master_path = ASSETS / "zeuspdf_1024.png"
    master.save(master_path, "PNG")
    print(f"  ✅ Master: {master_path}")

    # ── Scaled PNGs ────────────────────────────────────────────────
    imgs: dict[int, Image.Image] = {}
    for sz in SIZES:
        img = master.resize((sz, sz), Image.LANCZOS)
        path = ASSETS / f"zeuspdf_{sz}.png"
        img.save(path, "PNG")
        imgs[sz] = img
    print(f"  ✅ Scaled PNGs: {', '.join(str(s) for s in SIZES)}")

    # ── .ico (Windows) — 16,32,48,64,128,256 ─────────────────────
    # sizes= must be passed to the master (1024px) so Pillow can
    # LANCZOS-downscale each layer from full resolution.  Passing a
    # pre-shrunk source produces only that one tiny layer (806 bytes).
    ico_sizes = [16, 32, 48, 64, 128, 256]
    ico_path = ASSETS / "zeuspdf.ico"
    master.convert("RGBA").save(ico_path, format="ICO",
                                sizes=[(s, s) for s in ico_sizes])
    print(f"  ✅ ICO: {ico_path}")

    # ── .icns (macOS) via iconutil ─────────────────────────────────
    iconset = ASSETS / "zeuspdf.iconset"
    iconset.mkdir(exist_ok=True)

    icns_map = {
        16:  "icon_16x16.png",
        32:  "icon_16x16@2x.png",
        32:  "icon_32x32.png",
        64:  "icon_32x32@2x.png",
        128: "icon_128x128.png",
        256: "icon_128x128@2x.png",
        256: "icon_256x256.png",
        512: "icon_256x256@2x.png",
        512: "icon_512x512.png",
        1024:"icon_512x512@2x.png",
    }
    # Write all required sizes
    for sz, fname in [
        (16,   "icon_16x16.png"),
        (32,   "icon_16x16@2x.png"),
        (32,   "icon_32x32.png"),
        (64,   "icon_32x32@2x.png"),
        (128,  "icon_128x128.png"),
        (256,  "icon_128x128@2x.png"),
        (256,  "icon_256x256.png"),
        (512,  "icon_256x256@2x.png"),
        (512,  "icon_512x512.png"),
        (1024, "icon_512x512@2x.png"),
    ]:
        img = master.resize((sz, sz), Image.LANCZOS)
        img.save(iconset / fname, "PNG")

    result = subprocess.run(
        ["iconutil", "-c", "icns", str(iconset), "-o", str(ASSETS / "zeuspdf.icns")],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"  ✅ ICNS: {ASSETS / 'zeuspdf.icns'}")
    else:
        print(f"  ⚠️  iconutil failed: {result.stderr.strip()}")

    # Clean up iconset folder
    import shutil
    shutil.rmtree(iconset, ignore_errors=True)

    # ── Symlinks / copies for build scripts ───────────────────────
    for name in ("zeuspdf.icns", "zeuspdf.ico"):
        src = ASSETS / name
        if src.exists():
            dst = ASSETS / name.replace("zeuspdf", "pdfstudio")
            if not dst.exists():
                import shutil
                shutil.copy2(src, dst)

    print("\n  Logo generation complete!")
    print(f"  Assets in: {ASSETS.resolve()}")


if __name__ == "__main__":
    make_all()
