#!/usr/bin/env python3
"""Procedural Blender generator for FrilAssets: stationery/fril-signature-seal.

Builds the Fril Signature Wax Seal directly from the canonical vector emblem
(`source/emblem.svg`) and `material-presets.json`, synthesizes and packs a subtle
coherent microscopic wax normal map, authors the `Wax_Seal -> {Wax_Body, Wax_Emblem}`
hierarchy with customizable `Sealing_Wax` and `Seal_Emblem` PBR materials within the
<5,000 triangle web budget, and writes `model.glb`, `model.blend`, and `preview.webp`.

Optional diagnostic multi-angle previews are written to `.work/fril-signature-seal/previews/`
only when `-- --diagnostics` is passed on the command line.

Coordinate convention:
  - Blender authoring space:
      X: horizontal (+X right)
      Z: vertical (+Z up, toward 4-point star)
      -Y: front face & relief direction (rear attachment plane lies at Y = 0)
  - Exported glTF 2.0 (`export_yup=True`):
      X_glTF = +X_Blender (horizontal)
      Y_glTF = +Z_Blender (vertical)
      Z_glTF = -Y_Blender (positive Z = front face & relief; rear attachment on XY plane Z = 0)

Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 \
      --python assets/stationery/fril-signature-seal/generate.py
"""

from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.geometry import tessellate_polygon


ASSET_DIR = Path(__file__).resolve().parent
REPO_ROOT = ASSET_DIR.parents[2]
SOURCE_DIR = ASSET_DIR / "source"
WORK_SEAL_DIR = REPO_ROOT / ".work" / "fril-signature-seal"
DIAG_PREVIEWS_DIR = WORK_SEAL_DIR / "previews"

SVG_PATH = SOURCE_DIR / "emblem.svg"
PRESETS_PATH = ASSET_DIR / "material-presets.json"
BLEND_PATH = ASSET_DIR / "model.blend"
GLB_PATH = ASSET_DIR / "model.glb"
HERO_PREVIEW_PATH = ASSET_DIR / "preview.webp"

# Physical target dimensions in meters
NOMINAL_DIAMETER = 0.0280
NOMINAL_RADIUS = 0.5 * NOMINAL_DIAMETER  # 0.0140 m (14.0 mm)
MAX_RIM_HEIGHT = 0.00248                 # ~2.5 mm maximum pressed rim thickness
FIELD_BASE_HEIGHT = 0.00138              # 1.38 mm central recessed stamping field
RELIEF_MAX_HEIGHT = 0.00031              # 0.31 mm (within 0.20-0.35 mm target range)

# Emblem physical span on the 28 mm seal (measured from source/reference.png: 0.673 * R_nom)
EMBLEM_RADIUS_METERS = 0.00942           # 18.84 mm emblem span across laurel wreath
MASK_CANVAS_SPAN_METERS = (2.0 * EMBLEM_RADIUS_METERS) / 0.840  # 0.0224286 m full canvas

# Organic 6-scallop melted-wax perimeter harmonics calibrated to the reference seal silhouette
# (crown lobe at +Y_glTF = pi/2, subtle natural hand-poured asymmetry, zero mechanical symmetry)
OUTER_LOBE_HARMONICS: list[tuple[int, float, float]] = [
    (1, -0.0045, +0.0085),
    (2, -0.0060, +0.0155),
    (3, -0.0110, -0.0125),
    (4, +0.0065, -0.0050),
    (5, -0.0085, +0.0145),
    (6, -0.0435, +0.0095),  # Primary 6-lobe melted-wax scallop (-cos(6*pi/2) = +1 at 12 o'clock!)
    (7, +0.0035, -0.0055),
]


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear_rgba(hex_str: str) -> tuple[float, float, float, float]:
    h = hex_str.lstrip("#")
    return (
        srgb_to_linear(int(h[0:2], 16) / 255.0),
        srgb_to_linear(int(h[2:4], 16) / 255.0),
        srgb_to_linear(int(h[4:6], 16) / 255.0),
        1.0,
    )


def smoothstep(e0: float, e1: float, x: float) -> float:
    if e1 == e0:
        return 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


def outer_wax_radius(theta: float) -> float:
    """Organic melted-wax outer radius at polar angle theta (+X=0, +Y_glTF/+Z_Blender=pi/2)."""
    mod = 1.0
    for k, ak, bk in OUTER_LOBE_HARMONICS:
        mod += ak * math.cos(k * theta) + bk * math.sin(k * theta)
    return NOMINAL_RADIUS * mod


def wax_surface_height(x: float, y_up: float) -> float:
    """Front wax surface height (glTF +Z, meters above rear attachment plane Z=0)
    for any (x, y_up) point on Wax_Body."""
    r = math.hypot(x, y_up)
    theta = math.atan2(y_up, x)
    r_out = outer_wax_radius(theta)

    # Subtle natural thickness variation across the hand-pressed wax pool (+-0.05 mm)
    organic_tilt = 0.000040 * math.sin(theta + 0.65) + 0.000025 * math.cos(2.0 * theta - 0.35)

    # 1. Central recessed stamping field & restrained circular brass-die impression
    r_bead = 0.01028   # Delicate raised concentric stamp bead (10.28 mm radius)
    r_moat = 0.01105   # Recessed outer stamp-die edge moat (11.05 mm radius)

    dish = -0.000038 * min(1.0, (r / 0.0098) ** 2)
    h_field = FIELD_BASE_HEIGHT + dish + 0.45 * organic_tilt

    if r <= r_moat:
        bead = 0.000155 * math.exp(-(((r - r_bead) / 0.00027) ** 2))
        moat = -0.000150 * math.exp(-(((r - r_moat) / 0.00040) ** 2))
        return h_field + bead + moat

    # 2. Plump outer melted-wax cushion rim (from r_moat out to r_out)
    h_at_moat = (
        h_field
        + 0.000155 * math.exp(-(((r_moat - r_bead) / 0.00027) ** 2))
        - 0.000150
    )
    rim_span = max(0.0014, r_out - r_moat)
    u = max(0.0, min(1.0, (r - r_moat) / rim_span))

    # Lobe mass variation: wider lobes pooled slightly thicker wax (~2.34 mm to ~2.53 mm)
    lobe_boost = 0.48 * (r_out - NOMINAL_RADIUS)
    h_crest = MAX_RIM_HEIGHT + lobe_boost + organic_tilt
    h_crest = max(0.00232, min(0.00254, h_crest))

    u_crest = 0.43
    if u <= u_crest:
        s = smoothstep(0.0, u_crest, u)
        return h_at_moat + (h_crest - h_at_moat) * s

    s = max(0.0, min(1.0, (u - u_crest) / (1.0 - u_crest)))
    arc = math.sqrt(max(0.0, 1.0 - s * s))
    h_edge_contact = 0.00024
    return h_edge_contact + (h_crest - h_edge_contact) * (arc ** 0.86)


def create_packed_micro_wax_normal_image(size: int = 256) -> bpy.types.Image:
    """Author a restrained, coherent multi-scale cooled-wax height field and pack a lossless
    linear OpenGL (+Y) tangent-space normal map directly into Blender memory (zero external
    file path dependencies)."""
    rng = np.random.default_rng(42026)

    fy = np.fft.fftfreq(size)[:, None] * size
    fx = np.fft.fftfreq(size)[None, :] * size
    freq = np.hypot(fx, fy)

    phase1 = rng.uniform(0.0, 2.0 * math.pi, (size, size))
    phase2 = rng.uniform(0.0, 2.0 * math.pi, (size, size))
    amp1 = np.exp(-(((freq - 3.5) / 2.8) ** 2)) * (freq > 0)
    amp2 = 0.14 * np.exp(-(((freq - 18.0) / 11.0) ** 2)) * (freq > 0)
    amp3 = 0.08 * np.exp(-(((freq - 58.0) / 26.0) ** 2)) * (freq > 0)

    spec = (amp1 + amp2) * (np.cos(phase1) + 1j * np.sin(phase1)) + amp3 * (
        np.cos(phase2) + 1j * np.sin(phase2)
    )
    height = np.real(np.fft.ifft2(spec))
    height = (height - np.mean(height)) / (np.std(height) + 1e-12)

    dh_dx = 0.5 * (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1))
    dh_drow = 0.5 * (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0))
    dh_dy_uv = -dh_drow

    strength = 0.26
    nx = -strength * dh_dx
    ny = -strength * dh_dy_uv
    nz = np.ones_like(height)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= norm
    ny /= norm
    nz /= norm

    rgb = np.stack([0.5 * nx + 0.5, 0.5 * ny + 0.5, 0.5 * nz + 0.5], axis=-1)
    rgb_q = np.clip(np.round(rgb * 255.0), 0, 255) / 255.0
    # Blender Image.pixels starts at bottom-left row (row[::-1] of top-down array)
    rgba_bottom_up = np.ones((size, size, 4), dtype=np.float32)
    rgba_bottom_up[:, :, :3] = rgb_q[::-1].astype(np.float32)

    img = bpy.data.images.new(
        name="wax-micro-normal", width=size, height=size, alpha=False, float_buffer=False
    )
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set(rgba_bottom_up.ravel())
    img.pack()
    return img


def compute_emblem_sdf_meters_from_svg(svg_path: Path, grid_size: int = 768) -> np.ndarray:
    """Rasterize canonical source/emblem.svg in a temporary directory and compute a smooth
    2D Euclidean Signed Distance Field in meters via sub-pixel Jump Flooding."""
    with tempfile.TemporaryDirectory() as tmp:
        mask_png = Path(tmp) / "emblem-mask.png"
        raw_g = Path(tmp) / "mask.gray"
        subprocess.run(
            [
                "magick",
                "-background",
                "none",
                "-density",
                "300",
                str(svg_path),
                "-resize",
                "1024x1024!",
                "-alpha",
                "extract",
                "-colorspace",
                "Gray",
                "-depth",
                "8",
                str(mask_png),
            ],
            check=True,
        )
        subprocess.run(
            [
                "magick",
                str(mask_png),
                "-resize",
                f"{grid_size}x{grid_size}!",
                "-colorspace",
                "Gray",
                "-depth",
                "16",
                f"gray:{raw_g}",
            ],
            check=True,
        )
        alpha = (
            np.fromfile(raw_g, dtype="<u2").reshape((grid_size, grid_size)).astype(np.float64)
            / 65535.0
        )

    inside = alpha >= 0.5
    gy = 0.5 * (np.roll(alpha, -1, axis=0) - np.roll(alpha, 1, axis=0))
    gx = 0.5 * (np.roll(alpha, -1, axis=1) - np.roll(alpha, 1, axis=1))
    gmag = np.hypot(gx, gy)

    nbr_diff = np.zeros_like(inside)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nbr_diff |= inside != np.roll(np.roll(inside, dy, axis=0), dx, axis=1)
    boundary = nbr_diff | ((alpha > 0.05) & (alpha < 0.95))
    boundary[0, :] = boundary[-1, :] = boundary[:, 0] = boundary[:, -1] = False

    yy, xx = np.meshgrid(
        np.arange(grid_size, dtype=np.float64),
        np.arange(grid_size, dtype=np.float64),
        indexing="ij",
    )
    inf_coord = 1e9
    seed_x = np.full((grid_size, grid_size), inf_coord, dtype=np.float64)
    seed_y = np.full((grid_size, grid_size), inf_coord, dtype=np.float64)

    valid_g = boundary & (gmag > 1e-4)
    shift = np.clip((0.5 - alpha[valid_g]) / gmag[valid_g], -0.75, 0.75)
    seed_x[valid_g] = xx[valid_g] + shift * (gx[valid_g] / gmag[valid_g])
    seed_y[valid_g] = yy[valid_g] + shift * (gy[valid_g] / gmag[valid_g])

    fallback_b = boundary & (~valid_g)
    seed_x[fallback_b] = xx[fallback_b]
    seed_y[fallback_b] = yy[fallback_b]

    best_d2 = (seed_x - xx) ** 2 + (seed_y - yy) ** 2

    steps = [1, 256, 128, 64, 32, 16, 8, 4, 2, 1]
    offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    for step in steps:
        for dy, dx in offsets:
            sy = dy * step
            sx = dx * step
            r_src0, r_src1 = max(0, -sy), min(grid_size, grid_size - sy)
            c_src0, c_src1 = max(0, -sx), min(grid_size, grid_size - sx)
            r_dst0, r_dst1 = max(0, sy), min(grid_size, grid_size + sy)
            c_dst0, c_dst1 = max(0, sx), min(grid_size, grid_size + sx)

            cand_x = seed_x[r_src0:r_src1, c_src0:c_src1]
            cand_y = seed_y[r_src0:r_src1, c_src0:c_src1]
            cand_d2 = (cand_x - xx[r_dst0:r_dst1, c_dst0:c_dst1]) ** 2 + (
                cand_y - yy[r_dst0:r_dst1, c_dst0:c_dst1]
            ) ** 2
            cur_d2 = best_d2[r_dst0:r_dst1, c_dst0:c_dst1]
            improve = cand_d2 < cur_d2
            if np.any(improve):
                best_d2[r_dst0:r_dst1, c_dst0:c_dst1] = np.where(improve, cand_d2, cur_d2)
                seed_x[r_dst0:r_dst1, c_dst0:c_dst1] = np.where(
                    improve, cand_x, seed_x[r_dst0:r_dst1, c_dst0:c_dst1]
                )
                seed_y[r_dst0:r_dst1, c_dst0:c_dst1] = np.where(
                    improve, cand_y, seed_y[r_dst0:r_dst1, c_dst0:c_dst1]
                )

    dist_px = np.sqrt(best_d2)
    signed_px = np.where(inside, dist_px, -dist_px)

    kernel = np.array([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0
    pad_s = np.pad(signed_px, 2, mode="edge")
    sm_h = sum(kernel[k] * pad_s[:, k : k + grid_size] for k in range(5))
    sm_hv = sum(kernel[k] * sm_h[k : k + grid_size, :] for k in range(5))

    meters_per_px = MASK_CANVAS_SPAN_METERS / grid_size
    return sm_hv * meters_per_px


def marching_squares_contours_meters(sdf: np.ndarray, iso_m: float) -> list[np.ndarray]:
    """Extract closed 2D contours in seal coordinates (x_m, y_up_m) at SDF = iso_m."""
    n = sdf.shape[0]
    f = np.pad(sdf, 1, mode="constant", constant_values=-1.0)
    hp, wp = f.shape
    meters_per_px = MASK_CANVAS_SPAN_METERS / n

    def px_to_seal_xy(col_px: float, row_px: float) -> tuple[float, float]:
        x_m = (col_px - 0.5 * (n - 1)) * meters_per_px
        y_up_m = (0.5 * (n - 1) - row_px) * meters_per_px
        return (x_m, y_up_m)

    def interp_h(r: int, c: int) -> tuple[float, float]:
        v0, v1 = f[r, c], f[r, c + 1]
        t = 0.5 if abs(v1 - v0) < 1e-15 else max(0.0, min(1.0, (iso_m - v0) / (v1 - v0)))
        return px_to_seal_xy(c + t - 1.0, r - 1.0)

    def interp_v(r: int, c: int) -> tuple[float, float]:
        v0, v1 = f[r, c], f[r + 1, c]
        t = 0.5 if abs(v1 - v0) < 1e-15 else max(0.0, min(1.0, (iso_m - v0) / (v1 - v0)))
        return px_to_seal_xy(c - 1.0, r + t - 1.0)

    next_edge: dict[tuple, tuple] = {}
    edge_pt: dict[tuple, tuple[float, float]] = {}

    for r in range(hp - 1):
        for c in range(wp - 1):
            tl = 1 if f[r, c] >= iso_m else 0
            tr = 1 if f[r, c + 1] >= iso_m else 0
            br = 1 if f[r + 1, c + 1] >= iso_m else 0
            bl = 1 if f[r + 1, c] >= iso_m else 0
            code = (tl << 3) | (tr << 2) | (br << 1) | bl
            if code == 0 or code == 15:
                continue

            e_top = ("H", r, c)
            e_right = ("V", r, c + 1)
            e_bot = ("H", r + 1, c)
            e_left = ("V", r, c)

            segs = []
            if code == 1:
                segs.append((e_left, e_bot))
            elif code == 2:
                segs.append((e_bot, e_right))
            elif code == 3:
                segs.append((e_left, e_right))
            elif code == 4:
                segs.append((e_right, e_top))
            elif code == 5:
                center = 0.25 * (f[r, c] + f[r, c + 1] + f[r + 1, c + 1] + f[r + 1, c])
                if center >= iso_m:
                    segs.append((e_left, e_top))
                    segs.append((e_right, e_bot))
                else:
                    segs.append((e_left, e_bot))
                    segs.append((e_right, e_top))
            elif code == 6:
                segs.append((e_bot, e_top))
            elif code == 7:
                segs.append((e_left, e_top))
            elif code == 8:
                segs.append((e_top, e_left))
            elif code == 9:
                segs.append((e_top, e_bot))
            elif code == 10:
                center = 0.25 * (f[r, c] + f[r, c + 1] + f[r + 1, c + 1] + f[r + 1, c])
                if center >= iso_m:
                    segs.append((e_top, e_right))
                    segs.append((e_bot, e_left))
                else:
                    segs.append((e_top, e_left))
                    segs.append((e_bot, e_right))
            elif code == 11:
                segs.append((e_top, e_right))
            elif code == 12:
                segs.append((e_right, e_left))
            elif code == 13:
                segs.append((e_right, e_bot))
            elif code == 14:
                segs.append((e_bot, e_left))

            for ea, eb in segs:
                next_edge[ea] = eb
                for ek in (ea, eb):
                    if ek not in edge_pt:
                        edge_pt[ek] = interp_h(ek[1], ek[2]) if ek[0] == "H" else interp_v(ek[1], ek[2])

    visited = set()
    loops: list[np.ndarray] = []
    for start in next_edge:
        if start in visited:
            continue
        pts = []
        cur = start
        while cur not in visited and cur in next_edge:
            visited.add(cur)
            pts.append(edge_pt[cur])
            cur = next_edge[cur]
        if len(pts) >= 6:
            loops.append(np.array(pts, dtype=np.float64))
    return loops


def poly_signed_area_2d(pts: np.ndarray) -> float:
    x, y = pts[:, 0], pts[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def rdp_open(pts: np.ndarray, eps: float, max_seg_len: float) -> np.ndarray:
    if len(pts) <= 2:
        return pts
    p0, p1 = pts[0], pts[-1]
    chord = p1 - p0
    clen = float(np.linalg.norm(chord))
    if clen < 1e-12:
        dists = np.linalg.norm(pts - p0[None, :], axis=1)
    else:
        u = chord / clen
        rel = pts - p0[None, :]
        proj = rel @ u
        perp = rel - proj[:, None] * u[None, :]
        dists = np.linalg.norm(perp, axis=1)
    idx = int(np.argmax(dists))
    if float(dists[idx]) > eps or (clen > max_seg_len and len(pts) > 3):
        if idx == 0 or idx == len(pts) - 1:
            idx = len(pts) // 2
        left = rdp_open(pts[: idx + 1], eps, max_seg_len)
        right = rdp_open(pts[idx:], eps, max_seg_len)
        return np.vstack([left[:-1], right])
    return np.array([p0, p1])


def simplify_closed_loop(pts: np.ndarray, eps: float, max_seg_len: float) -> np.ndarray:
    sm = pts.copy()
    for _ in range(2):
        sm = 0.6 * sm + 0.2 * (np.roll(sm, 1, axis=0) + np.roll(sm, -1, axis=0))
    i0 = int(np.argmin(sm[:, 0]))
    sm = np.roll(sm, -i0, axis=0)
    i1 = int(np.argmax(sm[:, 0]))
    if i1 <= 1 or i1 >= len(sm) - 1:
        i1 = len(sm) // 2
    s1 = rdp_open(sm[: i1 + 1], eps, max_seg_len)
    s2 = rdp_open(np.vstack([sm[i1:], sm[0:1]]), eps, max_seg_len)
    return np.vstack([s1[:-1], s2[:-1]])


def point_in_poly_2d(pt: tuple[float, float], poly: np.ndarray) -> bool:
    px, py = pt
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i, 0], poly[i, 1]
        xj, yj = poly[j, 0], poly[j, 1]
        if (yi > py) != (yj > py):
            x_int = (xj - xi) * (py - yi) / (yj - yi + 1e-30) + xi
            if px < x_int:
                inside = not inside
        j = i
    return inside


def assign_seal_uvs(bm: bmesh.types.BMesh, relax_rear: bool = False) -> None:
    """Assign planar XY UVs across 32mm x 32mm. On the flat rear attachment surface,
    scale UVs down slightly so the release-backed bottom looks smoothly cooled."""
    uv_layer = bm.loops.layers.uv.new("UVMap")
    uv_span = 0.0320
    for face in bm.faces:
        scale = 0.22 if (relax_rear and face.normal.y > 0.9) else 1.0
        for loop in face.loops:
            u = (loop.vert.co.x / uv_span) * scale + 0.5
            v = (loop.vert.co.z / uv_span) * scale + 0.5
            loop[uv_layer].uv = (u, v)


def build_wax_body(parent_obj: bpy.types.Object, mat: bpy.types.Material) -> bpy.types.Object:
    """Build Wax_Body (~2,050 tris) with flat rear attachment surface on Blender Y=0
    (glTF XY plane Z=0) and organic 6-scallop pressed wax rim along Blender -Y (glTF +Z)."""
    bm = bmesh.new()

    n_theta = 76  # Smooth 4.7 deg angular resolution within the 5,000-triangle budget
    thetas = [2.0 * math.pi * i / n_theta for i in range(n_theta)]

    r_inner_fixed = [
        0.0048,
        0.0094,
        0.00998,
        0.01028,  # circular raised stamp bead crest
        0.01060,
        0.01105,  # circular recessed stamp-edge moat
    ]
    outer_fracs = [0.16, 0.34, 0.50, 0.68, 0.84, 0.94, 1.00]

    front_rings: list[list[bmesh.types.BMVert]] = []
    h_center = wax_surface_height(0.0, 0.0)
    v_front_center = bm.verts.new((0.0, -h_center, 0.0))

    for r_fix in r_inner_fixed:
        ring = []
        for th in thetas:
            x = r_fix * math.cos(th)
            y_up = r_fix * math.sin(th)
            h = wax_surface_height(x, y_up)
            ring.append(bm.verts.new((x, -h, y_up)))
        front_rings.append(ring)

    r_moat = 0.01105
    for uf in outer_fracs:
        ring = []
        for th in thetas:
            r_out = outer_wax_radius(th)
            r = r_moat + uf * (r_out - r_moat)
            x = r * math.cos(th)
            y_up = r * math.sin(th)
            h = wax_surface_height(x, y_up)
            ring.append(bm.verts.new((x, -h, y_up)))
        front_rings.append(ring)

    back_edge_ring = []
    for th in thetas:
        r_back = outer_wax_radius(th) - 0.00026
        x = r_back * math.cos(th)
        y_up = r_back * math.sin(th)
        back_edge_ring.append(bm.verts.new((x, 0.0, y_up)))

    v_back_center = bm.verts.new((0.0, 0.0, 0.0))

    r0 = front_rings[0]
    for i in range(n_theta):
        inext = (i + 1) % n_theta
        bm.faces.new((v_front_center, r0[i], r0[inext]))

    for k in range(len(front_rings) - 1):
        ra = front_rings[k]
        rb = front_rings[k + 1]
        for i in range(n_theta):
            inext = (i + 1) % n_theta
            bm.faces.new((ra[i], rb[i], rb[inext], ra[inext]))

    r_last = front_rings[-1]
    for i in range(n_theta):
        inext = (i + 1) % n_theta
        bm.faces.new((r_last[i], back_edge_ring[i], back_edge_ring[inext], r_last[inext]))

    for i in range(n_theta):
        inext = (i + 1) % n_theta
        bm.faces.new((v_back_center, back_edge_ring[inext], back_edge_ring[i]))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assign_seal_uvs(bm, relax_rear=True)

    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    if non_man != 0:
        raise RuntimeError(f"Wax_Body has {non_man} non-manifold edges!")

    mesh = bpy.data.meshes.new("Wax_Body")
    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = poly.normal.y < 0.95

    mesh.materials.append(mat)
    obj = bpy.data.objects.new("Wax_Body", mesh)
    obj.parent = parent_obj
    bpy.context.collection.objects.link(obj)
    return obj


def build_wax_emblem(
    parent_obj: bpy.types.Object, mat: bpy.types.Material, sdf_m: np.ndarray
) -> bpy.types.Object:
    """Build Wax_Emblem (~2,700 tris) as cushioned 3D pressed-wax relief integrated into
    Wax_Body so total asset triangle count stays cleanly below the 5,000-triangle budget."""
    bm = bmesh.new()

    # 3-tier cushioned dome profile tuned so total seal (Wax_Body + Wax_Emblem) <= 4,900 tris
    # while keeping every leaf tip, stem, star point, and calligraphic F crisp at 28 mm scale.
    tiers = [
        (-0.000032, -0.000022, 0.000086, 0.00072),  # L0: Embedded meniscus base (never floats!)
        (+0.000052, +0.000165, 0.000095, 0.00078),  # L1: Sloped draft shoulder & slender stem crown
        (+0.000148, +0.000305, 0.000105, 0.00086),  # L2: Pillowed dome summit (F, star, leaf bellies)
    ]

    tier_contours: list[list[dict]] = []
    for iso_m, rel_h, eps, max_seg in tiers:
        raw_loops = marching_squares_contours_meters(sdf_m, iso_m=iso_m)
        level_items = []
        for lp in raw_loops:
            if abs(poly_signed_area_2d(lp)) < 8e-9:
                continue
            simp = simplify_closed_loop(lp, eps=eps, max_seg_len=max_seg)
            if len(simp) < 3:
                continue
            if poly_signed_area_2d(simp) < 0:
                simp = simp[::-1].copy()

            verts = []
            for x_m, y_up_m in simp:
                z_front = wax_surface_height(float(x_m), float(y_up_m)) + rel_h
                verts.append(bm.verts.new((float(x_m), -z_front, float(y_up_m))))
            level_items.append({"pts2d": simp, "verts": verts})
        tier_contours.append(level_items)

    def add_tessellated_region(outer_item: dict, hole_items: list[dict]) -> None:
        loops_vec: list[list[Vector]] = [
            [Vector((float(p[0]), float(p[1]), 0.0)) for p in outer_item["pts2d"]]
        ]
        flat_verts: list[bmesh.types.BMVert] = list(outer_item["verts"])

        for h_item in hole_items:
            rev_pts = h_item["pts2d"][::-1]
            rev_verts = list(reversed(h_item["verts"]))
            loops_vec.append([Vector((float(p[0]), float(p[1]), 0.0)) for p in rev_pts])
            flat_verts.extend(rev_verts)

        tris = tessellate_polygon(loops_vec)
        for i0, i1, i2 in tris:
            v0, v1, v2 = flat_verts[i0], flat_verts[i1], flat_verts[i2]
            if v0 != v1 and v1 != v2 and v2 != v0:
                try:
                    bm.faces.new((v0, v1, v2))
                except ValueError:
                    pass

    for k in range(len(tier_contours) - 1):
        outers = tier_contours[k]
        inners = tier_contours[k + 1]
        for out_it in outers:
            child_holes = [
                in_it
                for in_it in inners
                if point_in_poly_2d(
                    (float(in_it["pts2d"][0, 0]), float(in_it["pts2d"][0, 1])),
                    out_it["pts2d"],
                )
            ]
            add_tessellated_region(out_it, child_holes)

    for top_it in tier_contours[-1]:
        add_tessellated_region(top_it, [])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        if f.normal.y > 0.0:
            f.normal_flip()

    assign_seal_uvs(bm, relax_rear=False)

    mesh = bpy.data.meshes.new("Wax_Emblem")
    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = True

    mesh.materials.append(mat)
    obj = bpy.data.objects.new("Wax_Emblem", mesh)
    obj.parent = parent_obj
    bpy.context.collection.objects.link(obj)
    return obj


def create_wax_material(
    name: str,
    normal_img: bpy.types.Image,
    base_rgba: tuple[float, float, float, float],
    metallic: float,
    roughness: float,
    normal_scale: float,
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new(type="ShaderNodeOutputMaterial")
    out_node.location = (360, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (60, 0)
    bsdf.inputs["Base Color"].default_value = base_rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.52
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.42
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.0

    tex_node = nodes.new(type="ShaderNodeTexImage")
    tex_node.location = (-520, -140)
    tex_node.image = normal_img

    norm_node = nodes.new(type="ShaderNodeNormalMap")
    norm_node.location = (-220, -140)
    norm_node.inputs["Strength"].default_value = normal_scale

    links.new(tex_node.outputs["Color"], norm_node.inputs["Color"])
    links.new(norm_node.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])
    return mat


def apply_preset_to_material(mat: bpy.types.Material, spec: dict) -> None:
    nodes = mat.node_tree.nodes
    bsdf = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    norm = next(n for n in nodes if n.type == "NORMAL_MAP")
    bsdf.inputs["Base Color"].default_value = tuple(spec["baseColorFactor"])
    bsdf.inputs["Metallic"].default_value = float(spec["metallicFactor"])
    bsdf.inputs["Roughness"].default_value = float(spec["roughnessFactor"])
    norm.inputs["Strength"].default_value = float(spec["normalScale"])


def create_simple_dielectric_mat(
    name: str, hex_color: str, roughness: float = 0.88
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out_n = nodes.new(type="ShaderNodeOutputMaterial")
    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = hex_to_linear_rgba(hex_color)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    links.new(bsdf.outputs["BSDF"], out_n.inputs["Surface"])
    return mat


def setup_eevee_render(width: int, height: int, exposure: float = -0.32) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"

    eevee = scene.eevee
    if hasattr(eevee, "taa_render_samples"):
        eevee.taa_render_samples = 128
    if hasattr(eevee, "use_raytracing"):
        eevee.use_raytracing = True
    if hasattr(eevee, "use_shadows"):
        eevee.use_shadows = True

    if hasattr(scene, "view_settings"):
        avail = [
            it.identifier
            for it in scene.view_settings.bl_rna.properties["view_transform"].enum_items
        ]
        if "AgX" in avail:
            scene.view_settings.view_transform = "AgX"
            looks = [
                it.identifier
                for it in scene.view_settings.bl_rna.properties["look"].enum_items
            ]
            if "AgX - Medium High Contrast" in looks:
                scene.view_settings.look = "AgX - Medium High Contrast"
        scene.view_settings.exposure = exposure


def render_to_webp(out_webp: Path, width: int, height: int, exposure: float = -0.32) -> None:
    out_webp.parent.mkdir(parents=True, exist_ok=True)
    setup_eevee_render(width, height, exposure=exposure)
    scene = bpy.context.scene
    cwebp = shutil.which("cwebp")
    with tempfile.TemporaryDirectory() as tmp:
        png_p = Path(tmp) / "frame.png"
        scene.render.filepath = str(png_p)
        bpy.ops.render.render(write_still=True)
        if cwebp:
            subprocess.run([cwebp, "-q", "93", str(png_p), "-o", str(out_webp)], check=True)
        else:
            scene.render.image_settings.file_format = "WEBP"
            scene.render.image_settings.quality = 93
            scene.render.filepath = str(out_webp)
            bpy.ops.render.render(write_still=True)


def create_studio_collection() -> tuple[bpy.types.Collection, bpy.types.Object, bpy.types.Object]:
    col = bpy.data.collections.new("Studio_Preview")
    bpy.context.scene.collection.children.link(col)

    # Large seamless editorial stone/parchment studio board so side & wide views never show edges
    bm = bmesh.new()
    s = 4.50
    verts = [
        bm.verts.new((-s, 0.00001, -s)),
        bm.verts.new((+s, 0.00001, -s)),
        bm.verts.new((+s, 0.00001, +s)),
        bm.verts.new((-s, 0.00001, +s)),
    ]
    bm.faces.new((verts[0], verts[3], verts[2], verts[1]))
    bg_mesh = bpy.data.meshes.new("Studio_Board")
    bm.to_mesh(bg_mesh)
    bm.free()
    bg_mat = create_simple_dielectric_mat("Mat_Studio_Board", "#DDD5CA", roughness=0.94)
    bg_mesh.materials.append(bg_mat)
    bg_obj = bpy.data.objects.new("Studio_Board", bg_mesh)
    col.objects.link(bg_obj)

    cam_data = bpy.data.cameras.new("Preview_Camera")
    cam_data.lens = 85.0
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.002
    cam_data.clip_end = 5.0
    cam_obj = bpy.data.objects.new("Preview_Camera", cam_data)
    col.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    def add_light(
        name: str,
        pos: tuple[float, float, float],
        aim: tuple[float, float, float],
        energy: float,
        sx: float,
        sy: float,
        color=(1.0, 1.0, 1.0),
    ):
        ld = bpy.data.lights.new(name=name, type="AREA")
        ld.energy = energy
        ld.shape = "RECTANGLE"
        ld.size = sx
        ld.size_y = sy
        ld.color = color
        lo = bpy.data.objects.new(name, ld)
        lo.location = Vector(pos)
        lo.rotation_euler = (Vector(aim) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(lo)
        return lo

    # Calibrated studio lighting: preserves deep velvety burgundy & crisp highlights without blowout
    add_light(
        "Seal_Light_Key",
        (-0.072, -0.056, 0.076),
        (0.0, -0.0014, 0.0),
        energy=0.28,
        sx=0.044,
        sy=0.036,
        color=(1.0, 0.985, 0.962),
    )
    add_light(
        "Seal_Light_Fill",
        (0.082, -0.072, -0.028),
        (0.0, -0.0010, 0.0),
        energy=0.085,
        sx=0.075,
        sy=0.065,
        color=(0.98, 0.99, 1.0),
    )
    add_light(
        "Seal_Light_Rim",
        (0.030, -0.032, 0.086),
        (0.0, -0.0018, 0.002),
        energy=0.14,
        sx=0.028,
        sy=0.020,
        color=(1.0, 0.975, 0.94),
    )

    world = bpy.data.worlds.new("Seal_Studio_World")
    if world.node_tree is None:
        world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = hex_to_linear_rgba("#D6CEC3")
        bg_node.inputs["Strength"].default_value = 0.12
    bpy.context.scene.world = world

    return col, cam_obj, bg_obj


def aim_camera(
    cam_obj: bpy.types.Object,
    pos: tuple[float, float, float],
    target: tuple[float, float, float],
    ortho_scale: float | None = None,
    lens: float = 85.0,
    up_axis: str = "Y",
) -> None:
    cam_data = cam_obj.data
    if ortho_scale is not None:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho_scale
    else:
        cam_data.type = "PERSP"
        cam_data.lens = lens
    cam_obj.location = Vector(pos)
    cam_obj.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", up_axis).to_euler()


def build_sample_envelope_flap_props(col: bpy.types.Collection) -> list[bpy.types.Object]:
    """Build a realistic dimensional sample ivory wedding envelope (pocket + closed beveled
    Euro-flap casting a crisp paper shadow) so Wax_Seal at (0,0,0) demonstrates zero-offset
    attachment right over the closed flap tip."""
    props: list[bpy.types.Object] = []

    mat_desk = create_simple_dielectric_mat("Tmp_Env_Desk", "#CFC7BC", roughness=0.95)
    mat_pocket = create_simple_dielectric_mat("Tmp_Env_Pocket", "#EFE5D4", roughness=0.86)
    mat_flap = create_simple_dielectric_mat("Tmp_Env_Flap", "#F5ECE0", roughness=0.82)

    # 1. Studio table behind the envelope (at Y = +0.0042 m)
    bm_d = bmesh.new()
    sd = 0.40
    vd = [
        bm_d.verts.new((-sd, 0.0042, -sd)),
        bm_d.verts.new((+sd, 0.0042, -sd)),
        bm_d.verts.new((+sd, 0.0042, +sd)),
        bm_d.verts.new((-sd, 0.0042, +sd)),
    ]
    bm_d.faces.new((vd[0], vd[3], vd[2], vd[1]))
    md = bpy.data.meshes.new("Tmp_Sample_Desk")
    bm_d.to_mesh(md)
    bm_d.free()
    md.materials.append(mat_desk)
    ob_d = bpy.data.objects.new("Tmp_Sample_Desk", md)
    col.objects.link(ob_d)
    props.append(ob_d)

    # 2. Envelope body pocket (220mm x 110mm, centered horizontally, top crease at Z = +0.056 m,
    # bottom at Z = -0.054 m, front face at Y = +0.0012 m so the closed flap overhangs by 1.2 mm
    # and casts an unmistakable crisp paper shadow!)
    bm_b = bmesh.new()
    hw = 0.110
    z_top, z_bot = +0.056, -0.054
    y_pf, y_pb = +0.00125, +0.00400
    vb_f = [
        bm_b.verts.new((-hw, y_pf, z_bot)),
        bm_b.verts.new((+hw, y_pf, z_bot)),
        bm_b.verts.new((+hw, y_pf, z_top)),
        bm_b.verts.new((-hw, y_pf, z_top)),
    ]
    vb_b = [
        bm_b.verts.new((-hw, y_pb, z_bot)),
        bm_b.verts.new((+hw, y_pb, z_bot)),
        bm_b.verts.new((+hw, y_pb, z_top)),
        bm_b.verts.new((-hw, y_pb, z_top)),
    ]
    bm_b.faces.new((vb_f[0], vb_f[3], vb_f[2], vb_f[1]))
    for i in range(4):
        inext = (i + 1) % 4
        bm_b.faces.new((vb_f[i], vb_f[inext], vb_b[inext], vb_b[i]))
    bmesh.ops.recalc_face_normals(bm_b, faces=bm_b.faces)
    mb = bpy.data.meshes.new("Tmp_Sample_Envelope_Body")
    bm_b.to_mesh(mb)
    bm_b.free()
    mb.materials.append(mat_pocket)
    ob_b = bpy.data.objects.new("Tmp_Sample_Envelope_Body", mb)
    col.objects.link(ob_b)
    props.append(ob_b)

    # 3. Closed pointed Euro-flap with exact C1 tangent lines from (+-w_top, z_top_f) to rounded tip
    bm_f = bmesh.new()
    r_tip = 0.0180
    w_top = 0.1095
    z_top_f = +0.0580
    z_virt_apex = -0.0175  # Virtual sharp apex below seal; tangent circle rounds tip at Z ~= -0.0135
    dz_v = z_top_f - z_virt_apex
    l_diag = math.hypot(w_top, dz_v)
    z_c = z_virt_apex + r_tip * l_diag / w_top
    nx = dz_v / l_diag
    nz = w_top / l_diag  # outward downward normal (-nz along Z)
    ang_tan = math.atan2(nx, nz)  # angle from -Z axis to tangent point

    pts_2d: list[tuple[float, float]] = [(-w_top, z_top_f)]
    n_arc = 18
    for j in range(n_arc + 1):
        a = -ang_tan + (2.0 * ang_tan) * (j / n_arc)
        pts_2d.append((r_tip * math.sin(a), z_c - r_tip * math.cos(a)))
    pts_2d.append((+w_top, z_top_f))

    front_v = [bm_f.verts.new((x, 0.00001, z)) for (x, z) in pts_2d]
    back_v = [bm_f.verts.new((x, 0.00075, z)) for (x, z) in pts_2d]
    bm_f.faces.new(list(reversed(front_v)))
    bm_f.faces.new(back_v)
    for i in range(len(pts_2d)):
        inext = (i + 1) % len(pts_2d)
        bm_f.faces.new((front_v[i], front_v[inext], back_v[inext], back_v[i]))
    bmesh.ops.recalc_face_normals(bm_f, faces=bm_f.faces)

    mf = bpy.data.meshes.new("Tmp_Sample_Envelope_Flap")
    bm_f.to_mesh(mf)
    bm_f.free()
    for p in mf.polygons:
        p.use_smooth = abs(p.normal.y) < 0.9
    mf.materials.append(mat_flap)
    ob_f = bpy.data.objects.new("Tmp_Sample_Envelope_Flap", mf)
    col.objects.link(ob_f)
    props.append(ob_f)

    return props


def render_previews(
    seal_root: bpy.types.Object,
    wax_body: bpy.types.Object,
    wax_emblem: bpy.types.Object,
    mat_wax: bpy.types.Material,
    mat_emblem: bpy.types.Material,
    normal_img: bpy.types.Image,
    presets_data: dict,
    studio_col: bpy.types.Collection,
    cam_obj: bpy.types.Object,
    bg_obj: bpy.types.Object,
    render_diagnostics: bool = False,
) -> None:
    presets = {p["id"]: p for p in presets_data["presets"]}
    default_p = presets["burgundy"]
    apply_preset_to_material(mat_wax, default_p["Sealing_Wax"])
    apply_preset_to_material(mat_emblem, default_p["Seal_Emblem"])

    # Canonical catalog preview (always rendered to preview.webp)
    bg_obj.hide_render = False
    aim_camera(cam_obj, pos=(0.032, -0.092, 0.026), target=(0.0, -0.0012, 0.0002), lens=85.0)
    render_to_webp(HERO_PREVIEW_PATH, width=1400, height=1050, exposure=-0.30)

    if not render_diagnostics:
        setup_eevee_render(1400, 1050, exposure=-0.30)
        return

    # Optional diagnostic previews written strictly to .work/fril-signature-seal/previews/
    aim_camera(cam_obj, pos=(-0.034, -0.090, 0.028), target=(0.0, -0.0012, 0.0002), lens=85.0)
    render_to_webp(DIAG_PREVIEWS_DIR / "perspective.webp", width=1400, height=1050, exposure=-0.30)

    aim_camera(cam_obj, pos=(0.0, -0.090, 0.0), target=(0.0, 0.0, 0.0), ortho_scale=0.0355)
    render_to_webp(DIAG_PREVIEWS_DIR / "front.webp", width=1200, height=1200, exposure=-0.30)

    aim_camera(cam_obj, pos=(0.011, -0.044, -0.007), target=(0.0002, -0.0015, 0.0008), lens=92.0)
    render_to_webp(DIAG_PREVIEWS_DIR / "emblem-detail.webp", width=1400, height=1050, exposure=-0.28)

    aim_camera(cam_obj, pos=(0.082, -0.014, 0.002), target=(0.0, -0.0012, 0.0), ortho_scale=0.034)
    render_to_webp(DIAG_PREVIEWS_DIR / "side.webp", width=1400, height=900, exposure=-0.25)

    # 5. previews/back.webp — Clean 3/4 view of the flat rear XY attachment surface
    orig_bg_y = bg_obj.location.y
    # Shift backdrop behind the camera-target line at Y = -0.045 m facing +Y so rear view has studio paper bg!
    bg_obj.location.y = -0.045
    bg_obj.rotation_euler = (math.pi, 0.0, 0.0)

    rear_light_data = bpy.data.lights.new(name="Tmp_Rear_Key", type="AREA")
    rear_light_data.energy = 0.28
    rear_light_data.shape = "RECTANGLE"
    rear_light_data.size = 0.055
    rear_light_data.size_y = 0.045
    rear_light_obj = bpy.data.objects.new("Tmp_Rear_Key", rear_light_data)
    rear_light_obj.location = Vector((-0.052, 0.068, 0.052))
    rear_light_obj.rotation_euler = (Vector((0.0, 0.0, 0.0)) - rear_light_obj.location).to_track_quat("-Z", "Y").to_euler()
    studio_col.objects.link(rear_light_obj)

    rear_fill_data = bpy.data.lights.new(name="Tmp_Rear_Fill", type="AREA")
    rear_fill_data.energy = 0.10
    rear_fill_data.size = 0.070
    rear_fill_obj = bpy.data.objects.new("Tmp_Rear_Fill", rear_fill_data)
    rear_fill_obj.location = Vector((0.060, 0.070, -0.025))
    rear_fill_obj.rotation_euler = (Vector((0.0, 0.0, 0.0)) - rear_fill_obj.location).to_track_quat("-Z", "Y").to_euler()
    studio_col.objects.link(rear_fill_obj)

    aim_camera(cam_obj, pos=(0.028, 0.088, 0.022), target=(0.0, 0.0, 0.0), lens=85.0)
    render_to_webp(DIAG_PREVIEWS_DIR / "back.webp", width=1200, height=1200, exposure=-0.26)

    for ro, rd in [(rear_light_obj, rear_light_data), (rear_fill_obj, rear_fill_data)]:
        bpy.data.objects.remove(ro, do_unlink=True)
        bpy.data.lights.remove(rd, do_unlink=True)
    bg_obj.location.y = orig_bg_y
    bg_obj.rotation_euler = (0.0, 0.0, 0.0)

    # 6. previews/envelope.webp — Burgundy seal attached at (0,0,0) onto a closed sample ivory envelope
    bg_obj.hide_render = True
    key_l = bpy.data.objects["Seal_Light_Key"]
    fill_l = bpy.data.objects["Seal_Light_Fill"]
    rim_l = bpy.data.objects["Seal_Light_Rim"]
    orig_key_e, orig_key_loc = key_l.data.energy, key_l.location.copy()
    orig_fill_e, orig_rim_e = fill_l.data.energy, rim_l.data.energy

    # Scale light distance for wider envelope composition (~14cm field of view)
    key_l.location = Vector((-0.14, -0.13, 0.16))
    key_l.rotation_euler = (Vector((0.0, 0.0, 0.0)) - key_l.location).to_track_quat("-Z", "Y").to_euler()
    key_l.data.energy = 1.35
    key_l.data.size = 0.11
    key_l.data.size_y = 0.09
    fill_l.data.energy = 0.25
    rim_l.data.energy = 0.30

    env_props = build_sample_envelope_flap_props(studio_col)
    aim_camera(cam_obj, pos=(0.036, -0.195, 0.032), target=(0.0, 0.0, 0.002), lens=80.0)
    render_to_webp(DIAG_PREVIEWS_DIR / "envelope.webp", width=1400, height=1050, exposure=-0.32)

    for p_obj in env_props:
        m = p_obj.data
        mats = list(m.materials)
        bpy.data.objects.remove(p_obj, do_unlink=True)
        bpy.data.meshes.remove(m, do_unlink=True)
        for mt in mats:
            if mt and mt.users == 0:
                bpy.data.materials.remove(mt, do_unlink=True)

    # 7. previews/material-variants.webp — All 7 presets on identical shared geometry
    bg_obj.hide_render = False
    seal_root.hide_render = True
    wax_body.hide_render = True
    wax_emblem.hide_render = True

    variant_objs = []
    variant_mats = []
    preset_list = presets_data["presets"]
    row_positions = [
        (-0.0540, +0.0190),
        (-0.0180, +0.0190),
        (+0.0180, +0.0190),
        (+0.0540, +0.0190),
        (-0.0360, -0.0190),
        (0.0000, -0.0190),
        (+0.0360, -0.0190),
    ]

    key_l.location = Vector((-0.16, -0.19, 0.18))
    key_l.rotation_euler = (Vector((0.0, 0.0, 0.0)) - key_l.location).to_track_quat("-Z", "Y").to_euler()
    key_l.data.energy = 1.65
    key_l.data.size = 0.18
    key_l.data.size_y = 0.14
    fill_l.data.energy = 0.42
    rim_l.data.energy = 0.32

    for p_spec, (px, pz) in zip(preset_list, row_positions):
        mw = create_wax_material(
            f"Tmp_Wax_{p_spec['id']}",
            normal_img,
            tuple(p_spec["Sealing_Wax"]["baseColorFactor"]),
            p_spec["Sealing_Wax"]["metallicFactor"],
            p_spec["Sealing_Wax"]["roughnessFactor"],
            p_spec["Sealing_Wax"]["normalScale"],
        )
        me = create_wax_material(
            f"Tmp_Emb_{p_spec['id']}",
            normal_img,
            tuple(p_spec["Seal_Emblem"]["baseColorFactor"]),
            p_spec["Seal_Emblem"]["metallicFactor"],
            p_spec["Seal_Emblem"]["roughnessFactor"],
            p_spec["Seal_Emblem"]["normalScale"],
        )
        variant_mats.extend([mw, me])

        ob_w = bpy.data.objects.new(f"Tmp_Body_{p_spec['id']}", wax_body.data)
        ob_w.location = (px, 0.0, pz)
        ob_w.material_slots[0].link = "OBJECT"
        ob_w.material_slots[0].material = mw
        studio_col.objects.link(ob_w)

        ob_e = bpy.data.objects.new(f"Tmp_Emblem_{p_spec['id']}", wax_emblem.data)
        ob_e.location = (px, 0.0, pz)
        ob_e.material_slots[0].link = "OBJECT"
        ob_e.material_slots[0].material = me
        studio_col.objects.link(ob_e)
        variant_objs.extend([ob_w, ob_e])

    aim_camera(cam_obj, pos=(0.0, -0.24, -0.010), target=(0.0, 0.0, 0.0), ortho_scale=0.150)
    render_to_webp(DIAG_PREVIEWS_DIR / "material-variants.webp", width=1600, height=1000, exposure=-0.50)

    # Restore clean single-seal studio scene
    for vo in variant_objs:
        bpy.data.objects.remove(vo, do_unlink=True)
    for vm in variant_mats:
        bpy.data.materials.remove(vm, do_unlink=True)

    wax_body.material_slots[0].link = "DATA"
    wax_body.material_slots[0].material = mat_wax
    wax_emblem.material_slots[0].link = "DATA"
    wax_emblem.material_slots[0].material = mat_emblem

    seal_root.hide_render = False
    wax_body.hide_render = False
    wax_emblem.hide_render = False

    key_l.location = orig_key_loc
    key_l.rotation_euler = (Vector((0.0, -0.0014, 0.0)) - orig_key_loc).to_track_quat("-Z", "Y").to_euler()
    key_l.data.energy = orig_key_e
    key_l.data.size = 0.044
    key_l.data.size_y = 0.036
    fill_l.data.energy = orig_fill_e
    rim_l.data.energy = orig_rim_e
    aim_camera(cam_obj, pos=(0.032, -0.092, 0.026), target=(0.0, -0.0012, 0.0002), lens=85.0)
    setup_eevee_render(1400, 1050, exposure=-0.30)


def export_standalone_glb(export_objs: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in export_objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = export_objs[0]

    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_normals=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_cameras=False,
        export_lights=False,
    )


def main() -> None:
    if not SVG_PATH.exists():
        raise FileNotFoundError(f"Missing required canonical vector source: {SVG_PATH}")
    if not PRESETS_PATH.exists():
        raise FileNotFoundError(f"Missing required material presets file: {PRESETS_PATH}")

    argv_after_dd = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    render_diagnostics = "--diagnostics" in argv_after_dd

    presets_data = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    default_preset = next(p for p in presets_data["presets"] if p["isDefault"])

    sdf_m = compute_emblem_sdf_meters_from_svg(SVG_PATH, grid_size=768)

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    normal_img = create_packed_micro_wax_normal_image(size=256)

    mat_sealing_wax = create_wax_material(
        "Sealing_Wax",
        normal_img,
        tuple(default_preset["Sealing_Wax"]["baseColorFactor"]),
        default_preset["Sealing_Wax"]["metallicFactor"],
        default_preset["Sealing_Wax"]["roughnessFactor"],
        default_preset["Sealing_Wax"]["normalScale"],
    )
    mat_seal_emblem = create_wax_material(
        "Seal_Emblem",
        normal_img,
        tuple(default_preset["Seal_Emblem"]["baseColorFactor"]),
        default_preset["Seal_Emblem"]["metallicFactor"],
        default_preset["Seal_Emblem"]["roughnessFactor"],
        default_preset["Seal_Emblem"]["normalScale"],
    )

    wax_seal_root = bpy.data.objects.new("Wax_Seal", None)
    wax_seal_root.empty_display_type = "PLAIN_AXES"
    wax_seal_root.empty_display_size = 0.015
    wax_seal_root.location = (0.0, 0.0, 0.0)
    bpy.context.collection.objects.link(wax_seal_root)

    wax_body = build_wax_body(wax_seal_root, mat_sealing_wax)
    wax_emblem = build_wax_emblem(wax_seal_root, mat_seal_emblem, sdf_m)

    export_standalone_glb([wax_seal_root, wax_body, wax_emblem])

    studio_col, cam_obj, bg_obj = create_studio_collection()
    render_previews(
        wax_seal_root,
        wax_body,
        wax_emblem,
        mat_sealing_wax,
        mat_seal_emblem,
        normal_img,
        presets_data,
        studio_col,
        cam_obj,
        bg_obj,
        render_diagnostics=render_diagnostics,
    )

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)

    body_tris = sum(len(p.vertices) - 2 for p in wax_body.data.polygons)
    emb_tris = sum(len(p.vertices) - 2 for p in wax_emblem.data.polygons)
    print(
        f"SUMMARY: Wax_Body tris={body_tris}, Wax_Emblem tris={emb_tris}, "
        f"Total tris={body_tris + emb_tris}, GLB bytes={GLB_PATH.stat().st_size}"
    )


if __name__ == "__main__":
    main()
