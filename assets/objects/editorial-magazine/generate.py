#!/usr/bin/env python3
"""Procedural Blender generator for FrilAssets: objects/editorial-magazine.

Authors a photorealistic A4 (210 x 297 mm) perfect-bound softcover editorial magazine:
  - Physical construction: 280 gsm satin-coated flexible covers (0.32 mm), 56 printed
    interior pages (28 sheets of 135 gsm silk-matte coated stock, ~5.15 mm closed spine),
    continuous unrolling PUR perfect-bound spine with 4-score hinge channels, and
    micro-terraced layered paper blocks.
  - Deformation: Exact arc-length-preserving tangent-angle integration (Elastica model)
    sampled onto a multi-chain skeletal rig (32 bones per sheet/block + 9-bone unrolling
    spine) with 40-step bisection height solvers so sheets maintain <0.1% length error,
    constant thickness, synchronized front/back surfaces, and zero mesh intersections.
  - Customization: 8 independent right-reading [0, 1] artwork material slots on UVMap
    (TEXCOORD_0) + coherent tileable micro-paper PBR maps on UVMap_Detail (TEXCOORD_1).
  - Animations: Magazine_Open, Magazine_PageTurn, Magazine_Close (consistent resting poses).

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python assets/objects/editorial-magazine/generate.py
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector


ASSET_DIR = Path(__file__).resolve().parent
REPO_ROOT = ASSET_DIR.parents[2]
WORK_DIR = REPO_ROOT / ".work" / "objects" / "editorial-magazine"
TEX_DIR = ASSET_DIR / "textures"
BLEND_PATH = ASSET_DIR / "model.blend"
GLB_PATH = ASSET_DIR / "model.glb"
PREVIEW_WEBP_PATH = ASSET_DIR / "preview.webp"

# ---------------------------------------------------------------------------
# Physical A4 Perfect-Bound Editorial Magazine Specification (Meters)
# ---------------------------------------------------------------------------
PAGE_W = 0.21000         # 210.0 mm single-page trim width (420.0 mm nominal spread)
PAGE_H = 0.29700         # 297.0 mm trim height
CORNER_R = 0.00045       # Subtle crisp guillotine corner rounding in profile

# Calipers (56 printed pages = 28 physical sheets of 135 gsm silk-matte coated stock)
T_COVER = 0.000320       # 0.320 mm (280 gsm C2S satin-laminated cover board)
T_PAGE = 0.000145        # 0.145 mm single interior coated sheet
T_BLOCK_R = 0.001820     # 13 stacked sheets (~1.82 mm)
T_BLOCK_L = 0.001680     # 12 stacked sheets (~1.68 mm)
REST_GAP = 0.000110      # 0.110 mm micro air cushion guaranteeing zero BVH contact across curved poses

# Closed spine centerline stations u_j measured from Cover_Back centerline (z = 0.160 mm)
Z0_CB = 0.5 * T_COVER                                            # 0.000160 m
U_CB = 0.000000
U_BR = (0.5 * T_COVER + REST_GAP + 0.5 * T_BLOCK_R)              # 0.001225 m
U_PR = (U_BR + 0.5 * T_BLOCK_R + REST_GAP + 0.5 * T_PAGE)        # 0.0023625 m
U_PT = (U_PR + T_PAGE + REST_GAP)                                # 0.0025825 m
U_PL = (U_PT + T_PAGE + REST_GAP)                                # 0.0028025 m
U_BL = (U_PL + 0.5 * T_PAGE + REST_GAP + 0.5 * T_BLOCK_L)        # 0.003875 m
U_CF = (U_BL + 0.5 * T_BLOCK_L + REST_GAP + 0.5 * T_COVER)       # 0.005035 m
SPINE_SPAN = U_CF                                                # 0.005035 m
TOTAL_CLOSED_SPINE_H = Z0_CB + U_CF + 0.5 * T_COVER              # 0.005355 m (5.355 mm, inside 4-6 mm!)

# Discretization for arc-length chains (finer near the binding gutter!)
# 12 fine intervals of 3.0 mm over [0, 36 mm] + 20 intervals of 8.7 mm over [36, 210 mm] = 32 bones
BONE_S_NODES: list[float] = (
    [0.0030 * i for i in range(12)]
    + [0.0360 + (PAGE_W - 0.0360) * (j / 20.0) for j in range(21)]
)
N_SHEET_BONES = len(BONE_S_NODES) - 1  # 32 serial bones per flexible sheet/stack
BONE_S_MIDS = np.array([0.5 * (BONE_S_NODES[k] + BONE_S_NODES[k + 1]) for k in range(N_SHEET_BONES)], dtype=np.float64)
BONE_DS = np.array([BONE_S_NODES[k + 1] - BONE_S_NODES[k] for k in range(N_SHEET_BONES)], dtype=np.float64)
N_SPINE_BONES = 8

# High-resolution quadrature grid for exact numerical arc-length integration
N_QUAD = 512
S_QUAD = np.linspace(0.0, PAGE_W, N_QUAD + 1)
DS_QUAD = PAGE_W / N_QUAD

# Physical detail UV repeat scale on UVMap_Detail (TEXCOORD_1)
DETAIL_REPEAT_M = 0.0525  # 52.5 mm physical tile (4x across width, ~5.66x across height)


# ---------------------------------------------------------------------------
# Color & Math Utilities
# ---------------------------------------------------------------------------
def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def hex_to_linear_rgba(hex_str: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    h = hex_str.lstrip("#")
    return (
        srgb_to_linear(int(h[0:2], 16) / 255.0),
        srgb_to_linear(int(h[2:4], 16) / 255.0),
        srgb_to_linear(int(h[4:6], 16) / 255.0),
        alpha,
    )


def smoothstep(e0: float, e1: float, x: float) -> float:
    if e1 == e0:
        return 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


def smootherstep(e0: float, e1: float, x: float) -> float:
    if e1 == e0:
        return 0.0
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def smoothstep_np(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# Coherent Procedural PBR Texture Synthesis (Tileable Spectral Heightfields)
# ---------------------------------------------------------------------------
def save_rgba_png(path: Path, rgba_uint8: np.ndarray, colorspace: str = "Non-Color") -> bpy.types.Image:
    """Save a (H, W, 4) uint8 array losslessly to PNG via Blender Image API and return image."""
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w, _ = rgba_uint8.shape
    img = bpy.data.images.new(name=path.stem, width=w, height=h, alpha=False, float_buffer=False)
    # Blender image.pixels is bottom-to-top float [0..1]
    flipped = np.flipud(rgba_uint8).astype(np.float32) / 255.0
    img.pixels.foreach_set(flipped.ravel())
    img.filepath_raw = str(path)
    img.file_format = "PNG"
    img.save()
    img.colorspace_settings.name = colorspace
    return img


def periodic_spectral_heightfield(size: int, seed: int, freq_weights: list[tuple[float, float, float, float]]) -> np.ndarray:
    """Synthesize a strictly tileable 2D heightfield in [-1, 1] using FFT band-limited noise.
    freq_weights: list of (f_low, f_high, amp, anisotropy_xy)
    """
    rng = np.random.default_rng(seed)
    ky = np.fft.fftfreq(size) * size
    kx = np.fft.fftfreq(size) * size
    KX, KY = np.meshgrid(kx, ky)

    spec = np.zeros((size, size), dtype=np.complex128)
    for f_lo, f_hi, amp, aniso in freq_weights:
        phase = rng.uniform(0.0, 2.0 * np.pi, (size, size))
        mag = rng.standard_normal((size, size))
        R = np.sqrt((KX * aniso) ** 2 + (KY / aniso) ** 2)
        sigma = 0.5 * (f_hi - f_lo) + 1e-6
        mid = 0.5 * (f_hi + f_lo)
        band = np.exp(-0.5 * ((R - mid) / sigma) ** 2)
        band[0, 0] = 0.0
        spec += amp * band * mag * (np.cos(phase) + 1j * np.sin(phase))

    field = np.fft.ifft2(spec).real
    std = np.std(field) + 1e-9
    field = field / (3.0 * std)
    return np.clip(field, -1.0, 1.0)


def height_to_opengl_normal_uint8(height: np.ndarray, strength: float) -> np.ndarray:
    """Derive a spatially aligned OpenGL (+Y) tangent-space normal map from a periodic heightfield."""
    dh_dx = 0.5 * (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1))
    dh_dy = 0.5 * (np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0))
    nx = -strength * dh_dx
    # Row 0 is top of image; OpenGL +Y points UP (toward smaller row index)
    ny = +strength * dh_dy
    nz = np.ones_like(height)
    norm = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx /= norm
    ny /= norm
    nz /= norm

    out = np.zeros((*height.shape, 4), dtype=np.uint8)
    out[..., 0] = np.clip(np.round((0.5 * nx + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 1] = np.clip(np.round((0.5 * ny + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 2] = np.clip(np.round((0.5 * nz + 0.5) * 255.0), 0, 255).astype(np.uint8)
    out[..., 3] = 255
    return out


def scalar_to_gray_uint8(val01: np.ndarray) -> np.ndarray:
    g = np.clip(np.round(val01 * 255.0), 0, 255).astype(np.uint8)
    out = np.empty((*val01.shape, 4), dtype=np.uint8)
    out[..., 0] = g
    out[..., 1] = g
    out[..., 2] = g
    out[..., 3] = 255
    return out


def generate_pbr_textures() -> dict[str, bpy.types.Image]:
    """Generate coherent, rights-cleared PBR maps for interior silk paper, satin cover, and layered paper edges.
    Stage 13 optimization: 256x256 lossless periodic maps for the 52.5 mm tiled micro-grain (~125 DPI physical
    surface resolution) and full 512x512 lossless maps for the 13-sheet layered paper-edge macro detail."""
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    sz_micro = 256
    sz = 512

    # 1. Interior 135 gsm silk-matte coated paper (calendered fine clay + subtle long-grain cellulose)
    h_int = periodic_spectral_heightfield(
        sz_micro,
        seed=104135,
        freq_weights=[
            (4.0, 12.0, 0.30, 1.18),    # Subtle machine-direction paper formation
            (14.0, 42.0, 0.55, 1.08),   # Fine calendered fiber weave
            (48.0, 108.0, 0.45, 1.00),  # Micro clay-coating texture
        ],
    )
    n_int = height_to_opengl_normal_uint8(h_int, strength=1.15)
    r_int_val = 0.63 - 0.038 * h_int
    r_int = scalar_to_gray_uint8(r_int_val)

    # 2. Cover 280 gsm satin-laminated art stock (smoother polymer/satin film over dense art board)
    h_cov = periodic_spectral_heightfield(
        sz_micro,
        seed=204280,
        freq_weights=[
            (3.0, 10.0, 0.35, 1.12),    # Gentle board formation wave
            (16.0, 46.0, 0.35, 1.04),   # Smooth coated base
            (55.0, 115.0, 0.25, 1.00),  # Satin cell-glaze micro-finish
        ],
    )
    n_cov = height_to_opengl_normal_uint8(h_cov, strength=0.72)
    r_cov_val = 0.37 - 0.028 * h_cov
    r_cov = scalar_to_gray_uint8(r_cov_val)

    # 3. Layered guillotine-trimmed paper block edges (13 sheets per U=0..1 across stack thickness!)
    # Mapped so V (rows) runs across stack thickness (13 subtle sheet layers) and U (cols) runs along page edge
    rng_e = np.random.default_rng(304056)
    y_norm = np.linspace(0.0, 1.0, sz, endpoint=False)[:, None]
    x_norm = np.linspace(0.0, 1.0, sz, endpoint=False)[None, :]

    n_layers = 13
    # Slight per-sheet thickness/phase jitter that remains strictly periodic over 0..1
    sheet_phase = n_layers * y_norm + 0.06 * np.sin(2.0 * np.pi * x_norm * 2.0) + 0.04 * np.cos(2.0 * np.pi * x_norm * 5.0)
    # Rounded sheet edge crown (cos^0.6 profile, soft micro-shadow crease between sheets, NO harsh black stripes!)
    frac = sheet_phase - np.floor(sheet_phase)
    sheet_arch = 1.0 - (2.0 * np.abs(frac - 0.5)) ** 1.85
    fiber_micro = periodic_spectral_heightfield(
        sz,
        seed=304999,
        freq_weights=[(18.0, 60.0, 0.35, 0.45), (75.0, 200.0, 0.50, 0.75)],
    )
    h_edge = np.clip(0.68 * (sheet_arch * 2.0 - 1.0) + 0.32 * fiber_micro, -1.0, 1.0)
    n_edge = height_to_opengl_normal_uint8(h_edge, strength=2.10)

    # Tonal variation: warm ivory paper with delicate 3.5% inter-sheet shadow modulation (0.935..0.985 sRGB)
    per_sheet_tone = 0.008 * np.sin(2.0 * np.pi * np.floor(n_layers * y_norm) * 0.37)
    luma_srgb = np.clip(0.956 + 0.022 * sheet_arch + per_sheet_tone + 0.008 * fiber_micro, 0.915, 0.992)
    edge_rgb = np.empty((sz, sz, 4), dtype=np.uint8)
    edge_rgb[..., 0] = np.clip(np.round(luma_srgb * 250.0), 0, 255).astype(np.uint8)
    edge_rgb[..., 1] = np.clip(np.round(luma_srgb * 246.0), 0, 255).astype(np.uint8)
    edge_rgb[..., 2] = np.clip(np.round(luma_srgb * 238.0), 0, 255).astype(np.uint8)
    edge_rgb[..., 3] = 255

    r_edge_val = np.clip(0.81 - 0.045 * sheet_arch + 0.03 * fiber_micro, 0.70, 0.90)
    r_edge = scalar_to_gray_uint8(r_edge_val)

    return {
        "interior_normal": save_rgba_png(TEX_DIR / "paper_interior_normal.png", n_int, "Non-Color"),
        "interior_roughness": save_rgba_png(TEX_DIR / "paper_interior_roughness.png", r_int, "Non-Color"),
        "cover_normal": save_rgba_png(TEX_DIR / "paper_cover_normal.png", n_cov, "Non-Color"),
        "cover_roughness": save_rgba_png(TEX_DIR / "paper_cover_roughness.png", r_cov, "Non-Color"),
        "edge_basecolor": save_rgba_png(TEX_DIR / "paper_edge_basecolor.png", edge_rgb, "sRGB"),
        "edge_normal": save_rgba_png(TEX_DIR / "paper_edge_normal.png", n_edge, "Non-Color"),
        "edge_roughness": save_rgba_png(TEX_DIR / "paper_edge_roughness.png", r_edge, "Non-Color"),
    }


# ---------------------------------------------------------------------------
# Exact Elastica / Tangent-Angle Integration Engine (Stage 3)
# ---------------------------------------------------------------------------
def integrate_curve_from_theta(
    x0: float, z0: float, theta_q: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Integrate x(s) = x0 + int_0^s cos(theta) du, z(s) = z0 + int_0^s sin(theta) du
    using composite trapezoidal rule on S_QUAD (513 points, sub-micron precision)."""
    cos_t = np.cos(theta_q)
    sin_t = np.sin(theta_q)
    dx = 0.5 * DS_QUAD * (cos_t[:-1] + cos_t[1:])
    dz = 0.5 * DS_QUAD * (sin_t[:-1] + sin_t[1:])
    x = np.empty_like(S_QUAD)
    z = np.empty_like(S_QUAD)
    x[0] = x0
    z[0] = z0
    x[1:] = x0 + np.cumsum(dx)
    z[1:] = z0 + np.cumsum(dz)
    return x, z


def spine_state_at_open_progress(q_spine: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Compute the unrolling perfect-bound spine centerline across u in [0, SPINE_SPAN].
    q_spine = 0.0 -> vertical closed spine at X = 0, Z in [Z0_CB, Z0_CB + SPINE_SPAN] (Front Cover Closed on +X)
    q_spine = 1.0 -> horizontal open spine centered at X = 0, resting on Z >= Z0_CB (Open Spread)
    q_spine = 2.0 -> vertical closed spine at X = 0, u=0 (Cover_Back) at TOP Z0_CB + SPINE_SPAN down to
                     u=SPINE_SPAN (Cover_Front) at BOTTOM Z0_CB (Back Cover Closed on -X)
    Returns (u_grid, x_sp, z_sp, theta_sp) of length 65.
    """
    n_u = 64
    u_grid = np.linspace(0.0, SPINE_SPAN, n_u + 1)
    du = SPINE_SPAN / n_u
    w = u_grid / SPINE_SPAN

    if q_spine <= 1.0:
        # Base angle transitions smoothly from +pi/2 (vertical) to pi (horizontal toward -X)
        # Subtle 0.10 rad sin(2*pi*w) arch when open gives realistic 0.08 mm central spine flex
        theta_sp = (0.5 * math.pi) * (1.0 + q_spine) - (0.10 * q_spine) * np.sin(2.0 * math.pi * w)
        x_start = q_spine * (0.5 * SPINE_SPAN)
        z_start = Z0_CB

        cos_t = np.cos(theta_sp)
        sin_t = np.sin(theta_sp)
        x_sp = np.empty_like(u_grid)
        z_sp = np.empty_like(u_grid)
        x_sp[0] = x_start
        z_sp[0] = z_start
        x_sp[1:] = x_start + np.cumsum(0.5 * du * (cos_t[:-1] + cos_t[1:]))
        z_sp[1:] = z_start + np.cumsum(0.5 * du * (sin_t[:-1] + sin_t[1:]))
        return u_grid, x_sp, z_sp, theta_sp

    # Back-cover closing regime: q_spine in (1.0, 2.0], qb = q_spine - 1.0 in (0.0, 1.0].
    # Cover_Front (u = SPINE_SPAN) remains anchored flat on tabletop Z = Z0_CB while sliding from x_end(q=1) to X = 0!
    qb = max(0.0, min(1.0, q_spine - 1.0))
    theta_open1 = math.pi - 0.10 * np.sin(2.0 * math.pi * w)
    cos_o1 = np.cos(theta_open1)
    x_end_open1 = 0.5 * SPINE_SPAN + float(np.sum(0.5 * du * (cos_o1[:-1] + cos_o1[1:])))

    theta_sp = math.pi + (0.5 * math.pi) * qb - 0.10 * (1.0 - qb) * np.sin(2.0 * math.pi * w)
    cos_t = np.cos(theta_sp)
    sin_t = np.sin(theta_sp)
    dx_cum = np.zeros_like(u_grid)
    dz_cum = np.zeros_like(u_grid)
    dx_cum[1:] = np.cumsum(0.5 * du * (cos_t[:-1] + cos_t[1:]))
    dz_cum[1:] = np.cumsum(0.5 * du * (sin_t[:-1] + sin_t[1:]))

    x_end = (1.0 - qb) * x_end_open1
    z_end = Z0_CB
    x_sp = x_end - (dx_cum[-1] - dx_cum)
    z_sp = z_end - (dz_cum[-1] - dz_cum)
    return u_grid, x_sp, z_sp, theta_sp


def eval_spine_station(
    u_val: float, q_spine: float, glue_inward_offset: float = 0.0
) -> tuple[float, float, float]:
    """Return (x0, z0, theta_sp) for a sheet glued at station u_val along the spine."""
    u_grid, x_sp, z_sp, theta_sp = spine_state_at_open_progress(q_spine)
    x0 = float(np.interp(u_val, u_grid, x_sp))
    z0 = float(np.interp(u_val, u_grid, z_sp))
    th = float(np.interp(u_val, u_grid, theta_sp))
    if glue_inward_offset != 0.0:
        # Inward normal n_in = (+sin(th), -cos(th)): (+1, 0) when vertical, (0, +1) when horizontal
        x0 += glue_inward_offset * math.sin(th)
        z0 += -glue_inward_offset * math.cos(th)
    return x0, z0, th


def integrate_bones_end_z(z0: float, theta_q: np.ndarray) -> float:
    """Exact discrete Z endpoint produced by the 32 serial bones (eliminates all quadrature mismatch!)."""
    th_mids = np.interp(BONE_S_MIDS, S_QUAD, theta_q)
    return z0 + float(np.sum(BONE_DS * np.sin(th_mids)))


def integrate_bones_curve(x0: float, z0: float, theta_q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact 33 bone joint coordinates (x, z) produced by the 32 serial bones."""
    th_mids = np.interp(BONE_S_MIDS, S_QUAD, theta_q)
    xs = np.empty(N_SHEET_BONES + 1, dtype=np.float64)
    zs = np.empty(N_SHEET_BONES + 1, dtype=np.float64)
    xs[0], zs[0] = x0, z0
    xs[1:] = x0 + np.cumsum(BONE_DS * np.cos(th_mids))
    zs[1:] = z0 + np.cumsum(BONE_DS * np.sin(th_mids))
    return xs, zs


def solve_resting_arch_theta(
    z0: float,
    z_rest_target: float,
    side: str,
    arch_deg: float,
    flat_start_u: float = 0.76,
) -> np.ndarray:
    """Construct a smooth, low-curvature C2 Elastica angle profile theta(s) on S_QUAD that:
      1. Emerges smoothly from the PUR binding gutter with bounded curvature (max bone delta < 2.2 deg,
         eliminating LBS root pinch and keeping local edge/thickness strain < 0.25%!),
      2. Rises in a realistic editorial gutter arch (`arch_deg`) over u in [0, 0.34],
      3. Levels off cleanly to flat resting contact (0 deg on right, 180 deg on left) for u >= flat_start_u,
      4. Solves 48-step bisection DIRECTLY on the 32-bone discrete sum `integrate_bones_end_z`
         so the 32-bone tail lands on `z_rest_target` with < 1e-15 m error!
    """
    u = S_QUAD / PAGE_W
    sgn = +1.0 if side == "right" else -1.0
    theta_end = 0.0 if side == "right" else math.pi

    # Natural perfect-bound gutter emergence: max angle right near the spine, decaying smoothly into inflection
    arch_rad = math.radians(arch_deg)
    # Cosine half-bell starting smoothly at full emergence angle at s=0 and reaching 0 at u=0.34
    u_arch = np.clip(u / 0.34, 0.0, 1.0)
    arch_env = 0.5 * (1.0 + np.cos(math.pi * u_arch))
    theta_no_dip = theta_end + sgn * arch_rad * arch_env

    # Smooth inflection/dip kernel supported strictly on u in [0.16, flat_start_u]
    dip_u = np.clip((u - 0.16) / (flat_start_u - 0.16), 0.0, 1.0)
    dip_kernel = (np.sin(math.pi * dip_u) ** 2.0) * (1.0 - smoothstep_np(flat_start_u - 0.04, flat_start_u, u))

    def end_z(dip_amp: float) -> float:
        th = theta_no_dip - sgn * dip_amp * dip_kernel
        return integrate_bones_end_z(z0, th)

    lo, hi = -1.35, +1.35
    f_lo = end_z(lo) - z_rest_target
    for _ in range(48):
        mid = 0.5 * (lo + hi)
        f_mid = end_z(mid) - z_rest_target
        if (f_lo <= 0.0 and f_mid <= 0.0) or (f_lo > 0.0 and f_mid > 0.0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    dip_best = 0.5 * (lo + hi)
    return theta_no_dip - sgn * dip_best * dip_kernel


def closed_pose_profiles() -> dict[str, tuple[float, float, np.ndarray]]:
    """Exact physical Closed State (p_open = 0.0, all layers stacked on +X resting on Z = 0)."""
    q_sp = 0.0
    glue_in = 0.00028
    profiles: dict[str, tuple[float, float, np.ndarray]] = {}

    x0, z0, _ = eval_spine_station(U_CB, q_sp, 0.0)
    profiles["Cover_Back"] = (x0, z0, np.zeros_like(S_QUAD))

    # Parallel stacked layers when closed, each maintaining exact REST_GAP clearance from spine to fore-edge!
    specs = [
        ("Pages_Block_Right", U_BR, Z0_CB + U_BR, 0.45),
        ("Page_Right", U_PR, Z0_CB + U_PR, 0.48),
        ("Page_Turning", U_PT, Z0_CB + U_PT, 0.50),
        ("Page_Left", U_PL, Z0_CB + U_PL, 0.52),
        ("Pages_Block_Left", U_BL, Z0_CB + U_BL, 0.55),
    ]
    for name, u_st, z_rest, crown_deg in specs:
        xr, zr, _ = eval_spine_station(u_st, q_sp, glue_in)
        th = solve_resting_arch_theta(zr, z_rest, side="right", arch_deg=crown_deg, flat_start_u=0.62)
        profiles[name] = (xr, zr, th)

    xcf, zcf, _ = eval_spine_station(U_CF, q_sp, 0.0)
    th_cf = solve_resting_arch_theta(zcf, Z0_CB + U_CF, side="right", arch_deg=0.95, flat_start_u=0.68)
    profiles["Cover_Front"] = (xcf, zcf, th_cf)
    return profiles


def open_pose_profiles(turned: bool = False) -> dict[str, tuple[float, float, np.ndarray]]:
    """Exact physical Open Spread State (q_spine = 1.0) with nested normal-offset root placement
    so stacked curved layers maintain positive clearance everywhere from s = 0 to s = 210 mm!"""
    q_sp = 1.0
    profiles: dict[str, tuple[float, float, np.ndarray]] = {}

    # 1. Covers lie flat on Z = 0 beneath their respective stacks
    xcb, zcb, _ = eval_spine_station(U_CB, q_sp, 0.0)
    profiles["Cover_Back"] = (xcb, zcb, np.zeros_like(S_QUAD))

    xcf, zcf, _ = eval_spine_station(U_CF, q_sp, 0.0)
    profiles["Cover_Front"] = (xcf, zcf, np.full_like(S_QUAD, math.pi))

    r_relax = 0.0
    l_settle = 0.0

    # 2. Right Stack: pure vertical parallel-curve offsets (dx=0, dz >= half_sum / cos(theta_max) + margin)
    # guarantees Delta_perp(s) = dz * cos(theta(s)) > half_sum at EVERY s in [0, 210 mm] (both positive & negative theta!)
    cos_min = math.cos(math.radians(23.0))
    x_br = +0.00140
    dz_cb_br = (0.5 * T_BLOCK_R) / cos_min + REST_GAP
    z_br = T_COVER + dz_cb_br + 0.00004
    z_rest_br = T_COVER + dz_cb_br
    arch_br = 22.0 + r_relax
    th_br = solve_resting_arch_theta(z_br, z_rest_br, side="right", arch_deg=arch_br)
    profiles["Pages_Block_Right"] = (x_br, z_br, th_br)

    dz_br_pr = (0.5 * T_BLOCK_R + 0.5 * T_PAGE) / cos_min + REST_GAP
    x_pr = x_br
    z_pr = z_br + dz_br_pr
    z_rest_pr = z_rest_br + dz_br_pr
    th_pr = solve_resting_arch_theta(z_pr, z_rest_pr, side="right", arch_deg=arch_br)
    profiles["Page_Right"] = (x_pr, z_pr, th_pr)

    # 3. Left Stack: mirror-symmetric pure vertical parallel-curve offsets
    x_bl = -0.00140
    dz_cf_bl = (0.5 * T_BLOCK_L) / cos_min + REST_GAP
    z_bl = T_COVER + dz_cf_bl + 0.00004
    z_rest_bl = T_COVER + dz_cf_bl
    arch_bl = 22.0 + l_settle
    th_bl = solve_resting_arch_theta(z_bl, z_rest_bl, side="left", arch_deg=arch_bl)
    profiles["Pages_Block_Left"] = (x_bl, z_bl, th_bl)

    dz_bl_pl = (0.5 * T_BLOCK_L + 0.5 * T_PAGE) / cos_min + REST_GAP
    x_pl = x_bl
    z_pl = z_bl + dz_bl_pl
    z_rest_pl = z_rest_bl + dz_bl_pl
    th_pl = solve_resting_arch_theta(z_pl, z_rest_pl, side="left", arch_deg=arch_bl)
    profiles["Page_Left"] = (x_pl, z_pl, th_pl)

    # 4. Page_Turning
    dz_page = T_PAGE / cos_min + REST_GAP
    if not turned:
        x_pt = x_pr
        z_pt = z_pr + dz_page
        z_rest_pt = z_rest_pr + dz_page
        th_pt = solve_resting_arch_theta(z_pt, z_rest_pt, side="right", arch_deg=arch_br)
    else:
        x_pt = x_pl
        z_pt = z_pl + dz_page
        z_rest_pt = z_rest_pl + dz_page
        th_pt = solve_resting_arch_theta(z_pt, z_rest_pt, side="left", arch_deg=arch_bl)
    profiles["Page_Turning"] = (x_pt, z_pt, th_pt)
    return profiles


def evaluate_page_turn_pose(t: float) -> tuple[float, dict[str, tuple[float, float, np.ndarray]], float]:
    """Evaluate exact Elastica pose for Magazine_PageTurn at progress t in [0.0, 1.0]."""
    t = max(0.0, min(1.0, t))
    p0 = open_pose_profiles(turned=False)
    p1 = open_pose_profiles(turned=True)
    if t <= 0.0:
        return 1.0, p0, 0.0
    if t >= 1.0:
        return 1.0, p1, 0.0

    s_blend = smootherstep(0.10, 0.90, t)
    out: dict[str, tuple[float, float, np.ndarray]] = {}
    for k in ("Cover_Back", "Cover_Front", "Pages_Block_Right", "Page_Right", "Pages_Block_Left", "Page_Left"):
        x0 = (1.0 - s_blend) * p0[k][0] + s_blend * p1[k][0]
        z0 = (1.0 - s_blend) * p0[k][1] + s_blend * p1[k][1]
        th = (1.0 - s_blend) * p0[k][2] + s_blend * p1[k][2]
        out[k] = (x0, z0, th)

    x_pt0, z_pt0, th0_rest = p0["Page_Turning"]
    x_pt1, z_pt1, th1_rest = p1["Page_Turning"]
    u = S_QUAD / PAGE_W

    # Smooth root arc in central gutter (lifts slightly by +0.35 mm over central glue ridge at t=0.5)
    r_prog = smootherstep(0.05, 0.95, t)
    x_pt = (1.0 - r_prog) * x_pt0 + r_prog * x_pt1
    z_pt = (1.0 - r_prog) * z_pt0 + r_prog * z_pt1 + 0.00035 * math.sin(math.pi * t)

    # Note: During initial peel (t in 0..0.25), outer page lifts FIRST while base stays >= th0_rest
    # so Page_Turning lifts strictly UPWARD off Page_Right everywhere!
    # During final settle (t in 0.75..1.0), base reaches left arch while outer page stays <= th1_rest
    # (elevated above Page_Left) and cushions gently down onto Page_Left!
    base_prog = smootherstep(0.08, 0.92, t)
    th_base = (1.0 - base_prog) * th0_rest + base_prog * th1_rest

    lift_env = math.sin(math.pi * min(1.0, t / 0.56)) ** 1.25 if t < 0.56 else 0.0
    land_env = math.sin(math.pi * ((t - 0.44) / 0.56)) ** 1.25 if t > 0.44 else 0.0
    crest_env = math.exp(-((t - 0.50) / 0.19) ** 2)

    u_flex = smoothstep_np(0.015, 0.92, u) ** 1.15
    th_wave = (
        +math.radians(48.0) * lift_env * (u_flex ** 1.20)
        + math.radians(16.0) * crest_env * (u_flex ** 1.05)
        - math.radians(42.0) * land_env * (u_flex ** 1.20)
    )
    th_pt = th_base + th_wave
    out["Page_Turning"] = (x_pt, z_pt, th_pt)

    torsion = math.radians(0.55) * math.sin(math.pi * t) ** 2
    return 1.0, out, torsion


def evaluate_open_close_pose(p: float) -> tuple[float, dict[str, tuple[float, float, np.ndarray]], float]:
    """Evaluate exact collision-free pose for Magazine_Open (p: 0 -> 1) and Magazine_Close (p: 1 -> 0).
    Two-stage physical choreography matching real hand opening:
      - Stage A (p in [0.00, 0.46]): Flexible Cover_Front lifts from closed stack (half-open at p = 0.24!)
        and arcs across onto the left studio tabletop (Z = 0) while interior pages remain stacked on +X.
      - Stage B (p in [0.40, 1.00]): Spine unrolls smoothly onto tabletop; Pages_Block_Left + Page_Left
        turn together as a parallel locked sheaf (maintaining exact normal separation so they never touch!)
        onto Cover_Front, while Pages_Block_Right + Page_Right + Page_Turning arch smoothly into the right spread!
    """
    p = max(0.0, min(1.0, p))
    p_closed = closed_pose_profiles()
    p_open = open_pose_profiles(turned=False)
    if p <= 0.0:
        return 0.0, p_closed, 0.0
    if p >= 1.0:
        return 1.0, p_open, 0.0

    q_spine = smootherstep(0.38, 0.92, p)
    u = S_QUAD / PAGE_W
    u_flex = smoothstep_np(0.015, 0.92, u) ** 1.15
    out: dict[str, tuple[float, float, np.ndarray]] = {}

    # 1. Cover_Back remains flat on Z = 0
    xcb, zcb, _ = eval_spine_station(U_CB, q_spine, 0.0)
    out["Cover_Back"] = (xcb, zcb, np.zeros_like(S_QUAD))

    # 2. Cover_Front opens smoothly over p in [0.00, 0.52]
    xcf_sp, zcf_sp, _ = eval_spine_station(U_CF, q_spine, 0.0)
    if p >= 0.54:
        out["Cover_Front"] = (xcf_sp, zcf_sp, np.full_like(S_QUAD, math.pi))
    else:
        t_cf = smootherstep(0.00, 0.54, p)
        th_cf_0 = p_closed["Cover_Front"][2]
        th_cf_1 = np.full_like(S_QUAD, math.pi)
        cf_lift = math.sin(math.pi * min(1.0, t_cf / 0.56)) ** 1.25 if t_cf < 0.56 else 0.0
        cf_land = math.sin(math.pi * ((t_cf - 0.44) / 0.56)) ** 1.35 if t_cf > 0.44 else 0.0
        th_cf = (1.0 - t_cf) * th_cf_0 + t_cf * th_cf_1
        th_cf += math.radians(36.0) * cf_lift * (u_flex ** 1.15) - math.radians(34.0) * cf_land * (u_flex ** 1.20)
        # Keep Cover_Front strictly >= Z0_CB above tabletop during landing
        _, z_chk = integrate_bones_curve(xcf_sp, zcf_sp, th_cf)
        if float(np.min(z_chk)) < Z0_CB:
            for _ in range(30):
                th_cf -= 0.012 * u_flex
                _, z_chk = integrate_bones_curve(xcf_sp, zcf_sp, th_cf)
                if float(np.min(z_chk)) >= Z0_CB:
                    break
        out["Cover_Front"] = (xcf_sp, zcf_sp, th_cf)

    # 3. Right Stack (Pages_Block_Right -> Page_Right -> Page_Turning) blends smoothly using pure vertical parallel curves!
    cos_min = math.cos(math.radians(23.0))
    r_prog = smootherstep(0.40, 0.96, p)
    x_br = (1.0 - r_prog) * p_closed["Pages_Block_Right"][0] + r_prog * p_open["Pages_Block_Right"][0]
    z_br = (1.0 - r_prog) * p_closed["Pages_Block_Right"][1] + r_prog * p_open["Pages_Block_Right"][1]
    z_rest_br = (1.0 - r_prog) * (Z0_CB + U_BR) + r_prog * (T_COVER + (0.5 * T_BLOCK_R) / cos_min + REST_GAP)
    arch_br = (1.0 - r_prog) * 0.45 + r_prog * 22.0
    flat_br = (1.0 - r_prog) * 0.62 + r_prog * 0.76
    th_br = solve_resting_arch_theta(z_br, z_rest_br, side="right", arch_deg=arch_br, flat_start_u=flat_br)
    out["Pages_Block_Right"] = (x_br, z_br, th_br)

    dz_br_pr = (1.0 - r_prog) * (U_PR - U_BR) + r_prog * ((0.5 * T_BLOCK_R + 0.5 * T_PAGE) / cos_min + REST_GAP)
    x_pr = x_br
    z_pr = z_br + dz_br_pr
    z_rest_pr = z_rest_br + dz_br_pr
    th_pr = solve_resting_arch_theta(z_pr, z_rest_pr, side="right", arch_deg=arch_br, flat_start_u=flat_br)
    out["Page_Right"] = (x_pr, z_pr, th_pr)

    dz_page = (1.0 - r_prog) * (U_PT - U_PR) + r_prog * (T_PAGE / cos_min + REST_GAP)
    x_pt = x_pr
    z_pt = z_pr + dz_page
    z_rest_pt = z_rest_pr + dz_page
    th_pt = solve_resting_arch_theta(z_pt, z_rest_pt, side="right", arch_deg=arch_br, flat_start_u=flat_br)
    out["Page_Turning"] = (x_pt, z_pt, th_pt)

    # 4. Left Sheaf (Pages_Block_Left + Page_Left):
    if p <= 0.42:
        x_pl = x_pt
        z_pl = z_pt + dz_page
        z_rest_pl_w = z_rest_pt + dz_page
        th_pl = solve_resting_arch_theta(z_pl, z_rest_pl_w, side="right", arch_deg=arch_br, flat_start_u=flat_br)
        out["Page_Left"] = (x_pl, z_pl, th_pl)

        dz_pl_bl = (1.0 - r_prog) * (U_BL - U_PL) + r_prog * ((0.5 * T_BLOCK_L + 0.5 * T_PAGE) / cos_min + REST_GAP)
        x_bl = x_pl
        z_bl = z_pl + dz_pl_bl
        z_rest_bl_w = z_rest_pl_w + dz_pl_bl
        th_bl = solve_resting_arch_theta(z_bl, z_rest_bl_w, side="right", arch_deg=arch_br, flat_start_u=flat_br)
        out["Pages_Block_Left"] = (x_bl, z_bl, th_bl)
    else:
        tl = smootherstep(0.42, 1.00, p)
        x_bl0, z_bl0, th_bl0 = p_closed["Pages_Block_Left"]
        x_bl1, z_bl1, th_bl1 = p_open["Pages_Block_Left"]

        x_bl = (1.0 - tl) * x_bl0 + tl * x_bl1
        z_bl = (1.0 - tl) * z_bl0 + tl * z_bl1 + 0.00165 * (math.sin(math.pi * tl) ** 0.75)

        lift_l = math.sin(math.pi * min(1.0, tl / 0.56)) ** 1.25 if tl < 0.56 else 0.0
        land_l = math.sin(math.pi * ((tl - 0.44) / 0.56)) ** 1.30 if tl > 0.44 else 0.0
        th_bl = (1.0 - tl) * th_bl0 + tl * th_bl1
        th_bl += math.radians(38.0) * lift_l * (u_flex ** 1.18) - math.radians(36.0) * land_l * (u_flex ** 1.22)
        out["Pages_Block_Left"] = (x_bl, z_bl, th_bl)

        # Exact parallel-curve normal offset at EVERY bone station k along Pages_Block_Left!
        # Since Page_Left has identical tangent angle th_bl (with a slight convex-side clearance boost during bending)
        # and root offset along -n(th_bl[0]) (which equals (0, -sep) at theta=0 and (0, +sep) at theta=pi!),
        # let's compute exact bone-by-bone parallel offset or root normal step with extra margin!
        sep_sheaf = ((0.5 * T_BLOCK_L + 0.5 * T_PAGE) / cos_min + REST_GAP)
        # At tl=0 (theta~0): offset is (0, -(U_BL - U_PL)); at tl=1 (theta~158 deg): offset is (0, +dz_bl_pl)!
        # Along -n(th_bl_mean), (-n) = (+sin(th), -cos(th)) rotates smoothly from (0, -1) through (+1, 0) to (0, +1)!
        th_mean = float(np.mean(th_bl[12:28]))
        off_sheaf = (1.0 - tl) * (U_BL - U_PL) + tl * (sep_sheaf + 0.00046 * (1.0 - smootherstep(0.97, 1.00, tl))) + 0.00068 * math.sin(math.pi * tl)
        x_pl_s = x_bl + off_sheaf * math.sin(th_mean)
        z_pl_s = z_bl - off_sheaf * math.cos(th_mean)
        w_end = smootherstep(0.975, 1.00, tl)
        x_pl = (1.0 - w_end) * x_pl_s + w_end * p_open["Page_Left"][0]
        z_pl = (1.0 - w_end) * z_pl_s + w_end * p_open["Page_Left"][1]
        out["Page_Left"] = (x_pl, z_pl, th_bl.copy())

    return q_spine, out, 0.0


def back_closed_pose_profiles() -> dict[str, tuple[float, float, np.ndarray]]:
    """Exact physical Back-Cover-Closed State (q_spine = 2.0, all layers stacked on -X resting on Cover_Front
    at Z = Z0_CB, with Cover_Back on TOP at Z = Z0_CB + SPINE_SPAN so Mat_Cover_Back_Outer faces +Z upward)."""
    q_sp = 2.0
    glue_in = 0.00028
    profiles: dict[str, tuple[float, float, np.ndarray]] = {}

    xcf, zcf, _ = eval_spine_station(U_CF, q_sp, 0.0)
    profiles["Cover_Front"] = (xcf, zcf, np.full_like(S_QUAD, math.pi))

    # Bottom-to-top physical spine order when folded onto -X: V = SPINE_SPAN - U
    specs = [
        ("Pages_Block_Left", U_BL, Z0_CB + (SPINE_SPAN - U_BL), 0.45),
        ("Page_Left", U_PL, Z0_CB + (SPINE_SPAN - U_PL), 0.48),
        ("Page_Turning", U_PT, Z0_CB + (SPINE_SPAN - U_PT), 0.50),
        ("Page_Right", U_PR, Z0_CB + (SPINE_SPAN - U_PR), 0.52),
        ("Pages_Block_Right", U_BR, Z0_CB + (SPINE_SPAN - U_BR), 0.55),
    ]
    for name, u_st, z_rest, crown_deg in specs:
        xl, zl, _ = eval_spine_station(u_st, q_sp, glue_in)
        th = solve_resting_arch_theta(zl, z_rest, side="left", arch_deg=crown_deg, flat_start_u=0.62)
        profiles[name] = (xl, zl, th)

    xcb, zcb, _ = eval_spine_station(U_CB, q_sp, 0.0)
    th_cb = solve_resting_arch_theta(zcb, Z0_CB + SPINE_SPAN, side="left", arch_deg=0.95, flat_start_u=0.68)
    profiles["Cover_Back"] = (xcb, zcb, th_cb)
    return profiles


def evaluate_back_close_open_pose(p_close: float) -> tuple[float, dict[str, tuple[float, float, np.ndarray]], float]:
    """Evaluate exact collision-free pose for Magazine_Close_Back (p_close: 0 -> 1) and
    Magazine_Open_Back (p_close: 1 -> 0).
    Exact mirror dual of evaluate_open_close_pose parameterized by s_open = 1.0 - p_close:
      - At p_close = 0.0 (s_open = 1.0): matches open_pose_profiles(turned=True) to 0.000 mm!
      - Stage 1 (p_close in [0.00, 0.58]): Right sheaf (Pages_Block_Right + Page_Right) folds across
        the gutter onto the left stack while Spine rolls smoothly toward vertical on X = 0.
      - Stage 2 (p_close in [0.46, 1.00]): Flexible Cover_Back lifts from +X tabletop, arcs over the
        spine, and settles cleanly onto the top of the left stack with Mat_Cover_Back_Outer facing UP!
      - At p_close = 1.0 (s_open = 0.0): matches back_closed_pose_profiles() to 0.000 mm!
    """
    p_close = max(0.0, min(1.0, p_close))
    s = 1.0 - p_close  # s = 0.0 is Back-Cover-Closed, s = 1.0 is Final Open Spread (turned=True)
    p_bclosed = back_closed_pose_profiles()
    p_open = open_pose_profiles(turned=True)
    if s <= 0.0:
        return 2.0, p_bclosed, 0.0
    if s >= 1.0:
        return 1.0, p_open, 0.0

    qb_open = smootherstep(0.38, 0.92, s)
    q_spine = 2.0 - qb_open  # Smoothly transitions from 2.0 (at s=0) to 1.0 (at s=1)
    u = S_QUAD / PAGE_W
    u_flex = smoothstep_np(0.015, 0.92, u) ** 1.15
    out: dict[str, tuple[float, float, np.ndarray]] = {}

    # 1. Cover_Front remains anchored flat on tabletop Z = Z0_CB along -X (theta = pi)
    xcf, zcf, _ = eval_spine_station(U_CF, q_spine, 0.0)
    out["Cover_Front"] = (xcf, zcf, np.full_like(S_QUAD, math.pi))

    # 2. Cover_Back opens smoothly over s in [0.00, 0.54] (closes over p_close in [0.46, 1.00])
    xcb_sp, zcb_sp, _ = eval_spine_station(U_CB, q_spine, 0.0)
    if s >= 0.54:
        out["Cover_Back"] = (xcb_sp, zcb_sp, np.zeros_like(S_QUAD))
    else:
        t_cb = smootherstep(0.00, 0.54, s)
        th_cb_0 = p_bclosed["Cover_Back"][2]  # ~pi on -X
        th_cb_1 = np.zeros_like(S_QUAD)       # 0 on +X
        cb_lift = math.sin(math.pi * min(1.0, t_cb / 0.56)) ** 1.25 if t_cb < 0.56 else 0.0
        cb_land = math.sin(math.pi * ((t_cb - 0.44) / 0.56)) ** 1.35 if t_cb > 0.44 else 0.0
        th_cb = (1.0 - t_cb) * th_cb_0 + t_cb * th_cb_1
        # Mirror reflection theta -> pi - theta reverses wave sign!
        th_cb += -math.radians(36.0) * cb_lift * (u_flex ** 1.15) + math.radians(34.0) * cb_land * (u_flex ** 1.20)
        _, z_chk = integrate_bones_curve(xcb_sp, zcb_sp, th_cb)
        if float(np.min(z_chk)) < Z0_CB:
            for _ in range(30):
                th_cb += 0.012 * u_flex
                _, z_chk = integrate_bones_curve(xcb_sp, zcb_sp, th_cb)
                if float(np.min(z_chk)) >= Z0_CB:
                    break
        out["Cover_Back"] = (xcb_sp, zcb_sp, th_cb)

    # 3. Left Stack (Pages_Block_Left -> Page_Left -> Page_Turning) blends smoothly on -X
    cos_min = math.cos(math.radians(23.0))
    l_prog = smootherstep(0.40, 0.96, s)
    v_bl = SPINE_SPAN - U_BL
    v_pl = SPINE_SPAN - U_PL
    v_pt = SPINE_SPAN - U_PT
    v_pr = SPINE_SPAN - U_PR
    v_br = SPINE_SPAN - U_BR

    x_bl = (1.0 - l_prog) * p_bclosed["Pages_Block_Left"][0] + l_prog * p_open["Pages_Block_Left"][0]
    z_bl = (1.0 - l_prog) * p_bclosed["Pages_Block_Left"][1] + l_prog * p_open["Pages_Block_Left"][1]
    z_rest_bl = (1.0 - l_prog) * (Z0_CB + v_bl) + l_prog * (T_COVER + (0.5 * T_BLOCK_L) / cos_min + REST_GAP)
    arch_bl = (1.0 - l_prog) * 0.45 + l_prog * 22.0
    flat_bl = (1.0 - l_prog) * 0.62 + l_prog * 0.76
    th_bl = solve_resting_arch_theta(z_bl, z_rest_bl, side="left", arch_deg=arch_bl, flat_start_u=flat_bl)
    out["Pages_Block_Left"] = (x_bl, z_bl, th_bl)

    dz_bl_pl = (1.0 - l_prog) * (v_pl - v_bl) + l_prog * ((0.5 * T_BLOCK_L + 0.5 * T_PAGE) / cos_min + REST_GAP)
    x_pl = x_bl
    z_pl = z_bl + dz_bl_pl
    z_rest_pl = z_rest_bl + dz_bl_pl
    th_pl = solve_resting_arch_theta(z_pl, z_rest_pl, side="left", arch_deg=arch_bl, flat_start_u=flat_bl)
    out["Page_Left"] = (x_pl, z_pl, th_pl)

    dz_page = (1.0 - l_prog) * (v_pt - v_pl) + l_prog * (T_PAGE / cos_min + REST_GAP)
    x_pt = x_pl
    z_pt = z_pl + dz_page
    z_rest_pt = z_rest_pl + dz_page
    th_pt = solve_resting_arch_theta(z_pt, z_rest_pt, side="left", arch_deg=arch_bl, flat_start_u=flat_bl)
    out["Page_Turning"] = (x_pt, z_pt, th_pt)

    # 4. Right Sheaf (Pages_Block_Right + Page_Right):
    if s <= 0.42:
        x_pr = x_pt
        z_pr = z_pt + dz_page
        z_rest_pr_w = z_rest_pt + dz_page
        th_pr = solve_resting_arch_theta(z_pr, z_rest_pr_w, side="left", arch_deg=arch_bl, flat_start_u=flat_bl)
        out["Page_Right"] = (x_pr, z_pr, th_pr)

        dz_pr_br = (1.0 - l_prog) * (v_br - v_pr) + l_prog * ((0.5 * T_BLOCK_R + 0.5 * T_PAGE) / cos_min + REST_GAP)
        x_br = x_pr
        z_br = z_pr + dz_pr_br
        z_rest_br_w = z_rest_pr_w + dz_pr_br
        th_br = solve_resting_arch_theta(z_br, z_rest_br_w, side="left", arch_deg=arch_bl, flat_start_u=flat_bl)
        out["Pages_Block_Right"] = (x_br, z_br, th_br)
    else:
        tr = smootherstep(0.42, 1.00, s)
        x_br0, z_br0, th_br0 = p_bclosed["Pages_Block_Right"]
        x_br1, z_br1, th_br1 = p_open["Pages_Block_Right"]

        x_br = (1.0 - tr) * x_br0 + tr * x_br1
        z_br = (1.0 - tr) * z_br0 + tr * z_br1 + 0.00165 * (math.sin(math.pi * tr) ** 0.75)

        lift_r = math.sin(math.pi * min(1.0, tr / 0.56)) ** 1.25 if tr < 0.56 else 0.0
        land_r = math.sin(math.pi * ((tr - 0.44) / 0.56)) ** 1.30 if tr > 0.44 else 0.0
        th_br = (1.0 - tr) * th_br0 + tr * th_br1
        th_br += -math.radians(38.0) * lift_r * (u_flex ** 1.18) + math.radians(36.0) * land_r * (u_flex ** 1.22)
        out["Pages_Block_Right"] = (x_br, z_br, th_br)

        # Mirror normal n_plus(th) = (-sin(th), +cos(th)): (0, -1) at th=pi (Page_Right below Block_Right on -X)
        # rotating smoothly through (-1, 0) at th=pi/2 to (0, +1) at th=0 (Page_Right above Block_Right on +X)!
        sep_sheaf = ((0.5 * T_BLOCK_R + 0.5 * T_PAGE) / cos_min + REST_GAP)
        th_mean = float(np.mean(th_br[12:28]))
        off_sheaf = (1.0 - tr) * (v_br - v_pr) + tr * (sep_sheaf + 0.00046 * (1.0 - smootherstep(0.97, 1.00, tr))) + 0.00068 * math.sin(math.pi * tr)
        x_pr_s = x_br - off_sheaf * math.sin(th_mean)
        z_pr_s = z_br + off_sheaf * math.cos(th_mean)
        w_end = smootherstep(0.975, 1.00, tr)
        x_pr = (1.0 - w_end) * x_pr_s + w_end * p_open["Page_Right"][0]
        z_pr = (1.0 - w_end) * z_pr_s + w_end * p_open["Page_Right"][1]
        out["Page_Right"] = (x_pr, z_pr, th_br.copy())

    return q_spine, out, 0.0


# ---------------------------------------------------------------------------
# Material Creation (Dual-UV Setup: UVMap for Artwork, UVMap_Detail for Micro-Paper)
# ---------------------------------------------------------------------------
def build_paper_material(
    name: str,
    base_hex: str,
    normal_img: bpy.types.Image,
    rough_img: bpy.types.Image,
    normal_strength: float,
    spec_ior_level: float = 0.34,
    ior: float = 1.49,
    base_img: bpy.types.Image | None = None,
    detail_uv_name: str = "UVMap_Detail",
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    if mat.node_tree is None:
        mat.use_nodes = True
    mat.use_backface_culling = False
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_n = nodes.new("ShaderNodeOutputMaterial")
    out_n.location = (420, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (120, 0)
    bsdf.inputs["Base Color"].default_value = hex_to_linear_rgba(base_hex)
    bsdf.inputs["Metallic"].default_value = 0.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = ior
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = spec_ior_level
    if "Coat Weight" in bsdf.inputs and "Cover" in name:
        bsdf.inputs["Coat Weight"].default_value = 0.08
        bsdf.inputs["Coat Roughness"].default_value = 0.32

    if base_img is not None:
        uv0 = nodes.new("ShaderNodeUVMap")
        uv0.location = (-560, 260)
        uv0.uv_map = "UVMap"
        tex_b = nodes.new("ShaderNodeTexImage")
        tex_b.location = (-280, 260)
        tex_b.image = base_img
        links.new(uv0.outputs["UV"], tex_b.inputs["Vector"])
        links.new(tex_b.outputs["Color"], bsdf.inputs["Base Color"])

    uv_det = nodes.new("ShaderNodeUVMap")
    uv_det.location = (-560, -120)
    uv_det.uv_map = detail_uv_name

    tex_r = nodes.new("ShaderNodeTexImage")
    tex_r.location = (-280, -20)
    tex_r.image = rough_img
    links.new(uv_det.outputs["UV"], tex_r.inputs["Vector"])
    links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

    tex_n = nodes.new("ShaderNodeTexImage")
    tex_n.location = (-280, -280)
    tex_n.image = normal_img
    links.new(uv_det.outputs["UV"], tex_n.inputs["Vector"])

    norm_n = nodes.new("ShaderNodeNormalMap")
    norm_n.location = (-40, -260)
    norm_n.uv_map = detail_uv_name
    norm_n.inputs["Strength"].default_value = normal_strength
    links.new(tex_n.outputs["Color"], norm_n.inputs["Color"])
    links.new(norm_n.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out_n.inputs["Surface"])
    return mat


def create_all_materials(tex: dict[str, bpy.types.Image]) -> dict[str, bpy.types.Material]:
    mats: dict[str, bpy.types.Material] = {}
    # 4 Cover artwork slots + 1 Spine exterior slot (280 gsm satin-coated stock)
    for slot in (
        "Mat_Cover_Front_Outer",
        "Mat_Cover_Front_Inner",
        "Mat_Cover_Back_Outer",
        "Mat_Cover_Back_Inner",
        "Mat_Spine_Exterior",
    ):
        mats[slot] = build_paper_material(
            slot,
            base_hex="#FAF7F2",
            normal_img=tex["cover_normal"],
            rough_img=tex["cover_roughness"],
            normal_strength=0.055,
            spec_ior_level=0.40,
            ior=1.50,
        )

    # 4 Interior replaceable page artwork slots + 1 structural interior paper slot (135 gsm silk-matte)
    for slot in (
        "Mat_Page_Left",
        "Mat_Page_Right",
        "Mat_Page_Turning_Front",
        "Mat_Page_Turning_Back",
        "Mat_Paper_Interior",
    ):
        mats[slot] = build_paper_material(
            slot,
            base_hex="#F7F4EE",
            normal_img=tex["interior_normal"],
            rough_img=tex["interior_roughness"],
            normal_strength=0.085,
            spec_ior_level=0.30,
            ior=1.48,
        )

    # Cut & layered paper-stack edge material (uses UVMap so V=0..1 spans exact stack thickness!)
    mats["Mat_Paper_Edges"] = build_paper_material(
        "Mat_Paper_Edges",
        base_hex="#FFFFFF",
        normal_img=tex["edge_normal"],
        rough_img=tex["edge_roughness"],
        normal_strength=0.22,
        spec_ior_level=0.22,
        ior=1.47,
        base_img=tex["edge_basecolor"],
        detail_uv_name="UVMap",
    )
    return mats


# ---------------------------------------------------------------------------
# Armature & High-Subdivision Thin-Shell / Layered-Block Mesh Builders
# ---------------------------------------------------------------------------
CHAIN_ORDER = [
    ("Cover_Back", U_CB, 0.0),
    ("Pages_Block_Right", U_BR, 0.00028),
    ("Page_Right", U_PR, 0.00028),
    ("Page_Turning", U_PT, 0.00028),
    ("Page_Left", U_PL, 0.00028),
    ("Pages_Block_Left", U_BL, 0.00028),
    ("Cover_Front", U_CF, 0.0),
]


def create_magazine_armature(col: bpy.types.Collection) -> bpy.types.Object:
    """Create Magazine_Root as the canonical Armature at (0, 0, 0) on the resting surface."""
    arm_data = bpy.data.armatures.new("Magazine_Rig_Data")
    arm_obj = bpy.data.objects.new("Magazine_Root", arm_data)
    arm_obj.location = (0.0, 0.0, 0.0)
    col.objects.link(arm_obj)

    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones

    root_b = eb.new("Rig_Origin")
    root_b.head = Vector((0.0, 0.0, 0.0))
    root_b.tail = Vector((0.0, 0.040, 0.0))
    root_b.use_deform = False

    # 8-bone unrolling spine chain along closed vertical spine X=0, Z in [Z0_CB, Z0_CB + SPINE_SPAN]
    du_sp = SPINE_SPAN / N_SPINE_BONES
    prev_sp = root_b
    for i in range(N_SPINE_BONES):
        b = eb.new(f"Spine_{i:02d}")
        z_a = Z0_CB + i * du_sp
        z_b = Z0_CB + (i + 1) * du_sp
        b.head = Vector((0.0, 0.0, z_a))
        b.tail = Vector((0.0, 0.0, z_b))
        b.roll = 0.0
        b.parent = prev_sp
        b.use_connect = (i > 0)
        prev_sp = b

    # 7 serial 32-bone arc-length chains lying along +X in rest pose
    for cname, u_st, glue_in in CHAIN_ORDER:
        x_r = glue_in
        z_r = Z0_CB + u_st
        prev_b = root_b
        for k in range(N_SHEET_BONES):
            s0 = BONE_S_NODES[k]
            s1 = BONE_S_NODES[k + 1]
            b = eb.new(f"{cname}_{k:02d}")
            b.head = Vector((x_r + s0, 0.0, z_r))
            b.tail = Vector((x_r + s1, 0.0, z_r))
            b.roll = 0.0
            b.parent = prev_b
            b.use_connect = (k > 0)
            prev_b = b

    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_obj


def compute_smooth_chain_weights(s_val: float) -> list[tuple[int, float]]:
    """Smooth piecewise-linear tent weights over adjacent bone midpoints so curved sheets
    have C1-smooth vertex positions without rigid segment faceting."""
    mids = [0.5 * (BONE_S_NODES[k] + BONE_S_NODES[k + 1]) for k in range(N_SHEET_BONES)]
    if s_val <= mids[0]:
        return [(0, 1.0)]
    if s_val >= mids[-1]:
        return [(N_SHEET_BONES - 1, 1.0)]
    for k in range(N_SHEET_BONES - 1):
        if mids[k] <= s_val <= mids[k + 1]:
            alpha = (s_val - mids[k]) / (mids[k + 1] - mids[k])
            w0 = 1.0 - alpha
            w1 = alpha
            res = []
            if w0 > 1e-5:
                res.append((k, w0))
            if w1 > 1e-5:
                res.append((k + 1, w1))
            return res
    return [(N_SHEET_BONES - 1, 1.0)]


def s_grid_stations() -> list[float]:
    """56 subdivisions along width s in [0, PAGE_W], preserving full hinge, score, gutter-arch, and fore-edge fidelity."""
    pts: list[float] = []
    # Spine glue & 4.8 mm hinge score region [0..12 mm]: 14 fine steps (~0.85 mm)
    for i in range(14):
        pts.append(0.0120 * (i / 14.0))
    # Gutter arch region [12..72 mm]: 22 steps (~2.7 mm)
    for i in range(22):
        pts.append(0.0120 + 0.0600 * (i / 22.0))
    # Mid & fore-edge region [72..209.4 mm]: 18 steps
    for i in range(18):
        pts.append(0.0720 + (PAGE_W - 0.0006 - 0.0720) * (i / 18.0))
    # Fore-edge micro-bevel support loop + outer edge
    pts.append(PAGE_W - 0.00018)
    pts.append(PAGE_W)
    return pts


def y_grid_stations() -> list[float]:
    """11 subdivisions along straight spine-parallel height Y in [-PAGE_H/2, +PAGE_H/2] with crisp bevel loops."""
    hh = 0.5 * PAGE_H
    pts = [-hh, -hh + 0.00020]
    n_mid = 8
    for j in range(1, n_mid):
        pts.append(-hh + 0.00020 + (PAGE_H - 0.00040) * (j / n_mid))
    pts.extend([+hh - 0.00020, +hh])
    return pts


def add_thickness_shape_key(obj: bpy.types.Object, z_center: float) -> None:
    """Add bind-space `Thickness_Scale` morph target along undeformed sheet/stack thickness axis.
    Because glTF/Three.js applies morph targets in bind space BEFORE skeletal skinning, setting
    `morphTargetInfluences[0] = (targetThickness / defaultThickness) - 1.0` scales sheet or
    page-block thickness cleanly along the curved Elastica surface normal without world-Y shear!"""
    sk_basis = obj.shape_key_add(name="Basis", from_mix=False)
    sk_basis.interpolation = "KEY_LINEAR"
    sk_thick = obj.shape_key_add(name="Thickness_Scale", from_mix=False)
    sk_thick.interpolation = "KEY_LINEAR"
    sk_thick.slider_min = -0.98
    sk_thick.slider_max = 12.0
    sk_thick.value = 0.0
    mesh = obj.data
    for idx, v in enumerate(mesh.vertices):
        dz = v.co.z - z_center
        sk_thick.data[idx].co = Vector((v.co.x, v.co.y, v.co.z + dz))


def build_flexible_sheet_mesh(
    name: str,
    chain_prefix: str,
    arm_obj: bpy.types.Object,
    col: bpy.types.Collection,
    u_station: float,
    glue_in: float,
    thickness: float,
    mat_top: bpy.types.Material,
    mat_bot: bpy.types.Material,
    mat_edge: bpy.types.Material,
    top_uv_mirror_u: bool,
    bot_uv_mirror_u: bool,
    has_hinge_score: bool = False,
    edge_micro_seed: int = 0,
) -> bpy.types.Object:
    """Build a unified, watertight manifold thin-shell sheet (Cover or Single Page) with:
      - Separate material assignments for Top face (slot 0), Bottom face (slot 1), and Perimeter edges (slot 2)
      - Predictable full-page [0, 1] x [0, 1] UVs on UVMap (unmirrored right-reading!)
      - Physical-scale micro-paper UVs on UVMap_Detail
      - Optional 4.8 mm outer hinge score groove on softcovers
      - Subtle sub-0.08 mm organic guillotine trim variation on interior pages
    """
    s_vals = s_grid_stations()
    y_vals = y_grid_stations()
    ns = len(s_vals)
    ny = len(y_vals)

    x_root = glue_in
    z_root = Z0_CB + u_station
    half_t = 0.5 * thickness

    bm = bmesh.new()
    top_grid: list[list[bmesh.types.BMVert]] = []
    bot_grid: list[list[bmesh.types.BMVert]] = []
    vert_s_param: dict[int, float] = {}

    for j, y in enumerate(y_vals):
        y_norm = (y + 0.5 * PAGE_H) / PAGE_H
        # Subtle <= 0.07 mm organic trim variation along fore-edge for interior sheets
        trim_dx = 0.0
        if edge_micro_seed != 0:
            trim_dx = 0.000055 * math.sin(2.0 * math.pi * y_norm * 1.7 + edge_micro_seed)

        row_top: list[bmesh.types.BMVert] = []
        row_bot: list[bmesh.types.BMVert] = []
        for i, s in enumerate(s_vals):
            # Optional 4-score softcover hinge channel at s = 4.8 mm (0.075 mm subtle score indent)
            score_dz_top = 0.0
            score_dz_bot = 0.0
            if has_hinge_score:
                g = math.exp(-((s - 0.0048) / 0.00075) ** 2)
                if name == "Cover_Front":
                    score_dz_top = -0.000075 * g
                    score_dz_bot = +0.000025 * g
                else:
                    score_dz_bot = +0.000075 * g
                    score_dz_top = -0.000025 * g

            # Subtle edge bevel at outermost perimeter
            is_perim = (i == ns - 1) or (j == 0) or (j == ny - 1)
            bev = 0.22 * half_t if is_perim else 0.0

            sx = s + (trim_dx * (s / PAGE_W) if i > ns - 6 else 0.0)
            vt = bm.verts.new((x_root + sx, y, z_root + half_t - bev + score_dz_top))
            vb = bm.verts.new((x_root + sx, y, z_root - half_t + bev + score_dz_bot))
            row_top.append(vt)
            row_bot.append(vb)
        top_grid.append(row_top)
        bot_grid.append(row_bot)

    bm.verts.index_update()
    for j in range(ny):
        for i, s in enumerate(s_vals):
            vert_s_param[top_grid[j][i].index] = s
            vert_s_param[bot_grid[j][i].index] = s

    uv0 = bm.loops.layers.uv.new("UVMap")
    uv1 = bm.loops.layers.uv.new("UVMap_Detail")

    def set_face_uvs(face: bmesh.types.BMFace, mat_idx: int, mirror_u: bool, is_edge: bool = False) -> None:
        face.material_index = mat_idx
        face.smooth = not is_edge
        for loop in face.loops:
            v_idx = loop.vert.index
            co = loop.vert.co
            s_v = vert_s_param[v_idx]
            u_raw = max(0.0, min(1.0, s_v / PAGE_W))
            v_raw = max(0.0, min(1.0, (co.y + 0.5 * PAGE_H) / PAGE_H))
            if is_edge:
                # Edge strip UV: U along edge length, V across sheet thickness (single sheet = 1/13th of block)
                e_u = (s_v + (co.y + 0.5 * PAGE_H)) / DETAIL_REPEAT_M
                e_v = 0.5 + ((co.z - z_root) / max(thickness, 1e-5)) * (1.0 / 13.0)
                loop[uv0].uv = (e_u, e_v)
                loop[uv1].uv = (e_u, e_v)
            else:
                u_art = (1.0 - u_raw) if mirror_u else u_raw
                loop[uv0].uv = (u_art, v_raw)
                loop[uv1].uv = (s_v / DETAIL_REPEAT_M, (co.y + 0.5 * PAGE_H) / DETAIL_REPEAT_M)

    # Top faces (+Z normal in rest pose -> material slot 0)
    for j in range(ny - 1):
        for i in range(ns - 1):
            f = bm.faces.new((top_grid[j][i], top_grid[j][i + 1], top_grid[j + 1][i + 1], top_grid[j + 1][i]))
            set_face_uvs(f, mat_idx=0, mirror_u=top_uv_mirror_u)

    # Bottom faces (-Z normal in rest pose -> material slot 1)
    for j in range(ny - 1):
        for i in range(ns - 1):
            f = bm.faces.new((bot_grid[j][i], bot_grid[j + 1][i], bot_grid[j + 1][i + 1], bot_grid[j][i + 1]))
            set_face_uvs(f, mat_idx=1, mirror_u=bot_uv_mirror_u)

    # 4 Continuous perimeter edge strips (material slot 2 = Mat_Paper_Edges)
    # Right fore-edge (i = ns - 1)
    for j in range(ny - 1):
        f = bm.faces.new((bot_grid[j][-1], bot_grid[j + 1][-1], top_grid[j + 1][-1], top_grid[j][-1]))
        set_face_uvs(f, mat_idx=2, mirror_u=False, is_edge=True)
    # Left spine-root cap (i = 0)
    for j in range(ny - 1):
        f = bm.faces.new((top_grid[j][0], top_grid[j + 1][0], bot_grid[j + 1][0], bot_grid[j][0]))
        set_face_uvs(f, mat_idx=2, mirror_u=False, is_edge=True)
    # Bottom foot edge (j = 0)
    for i in range(ns - 1):
        f = bm.faces.new((bot_grid[0][i], top_grid[0][i], top_grid[0][i + 1], bot_grid[0][i + 1]))
        set_face_uvs(f, mat_idx=2, mirror_u=False, is_edge=True)
    # Top head edge (j = ny - 1)
    for i in range(ns - 1):
        f = bm.faces.new((top_grid[-1][i], bot_grid[-1][i], bot_grid[-1][i + 1], top_grid[-1][i + 1]))
        set_face_uvs(f, mat_idx=2, mirror_u=False, is_edge=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    if non_man != 0:
        raise RuntimeError(f"{name} has {non_man} non-manifold edges!")

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    mesh.materials.append(mat_top)
    mesh.materials.append(mat_bot)
    mesh.materials.append(mat_edge)

    obj = bpy.data.objects.new(name, mesh)
    obj.parent = arm_obj
    col.objects.link(obj)

    add_thickness_shape_key(obj, z_root)

    # Create vertex groups for the 32 bones of this chain
    vgs = [obj.vertex_groups.new(name=f"{chain_prefix}_{k:02d}") for k in range(N_SHEET_BONES)]
    for v_idx, s_v in vert_s_param.items():
        for b_idx, w in compute_smooth_chain_weights(s_v):
            vgs[b_idx].add([v_idx], w, "REPLACE")

    mod = obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj
    return obj


def build_layered_page_block_mesh(
    name: str,
    chain_prefix: str,
    arm_obj: bpy.types.Object,
    col: bpy.types.Collection,
    u_station: float,
    glue_in: float,
    thickness: float,
    n_sub_layers: int,
    mat_paper: bpy.types.Material,
    mat_edge: bpy.types.Material,
    seed: int,
) -> bpy.types.Object:
    """Build a deformable paper-stack block (Pages_Block_Left / Pages_Block_Right) with
    true multi-layer terraced perimeter geometry along the fore-edge, head edge, and foot edge
    so macro close-ups show genuine stacked sheets rather than a flat box wall!"""
    s_vals = s_grid_stations()
    y_vals = y_grid_stations()
    ns = len(s_vals)
    ny = len(y_vals)

    x_root = glue_in
    z_root = Z0_CB + u_station
    half_t = 0.5 * thickness

    bm = bmesh.new()
    vert_s_param: dict[int, float] = {}

    # Top and bottom surfaces of the stack
    top_grid: list[list[bmesh.types.BMVert]] = []
    bot_grid: list[list[bmesh.types.BMVert]] = []
    for j, y in enumerate(y_vals):
        rt: list[bmesh.types.BMVert] = []
        rb: list[bmesh.types.BMVert] = []
        for i, s in enumerate(s_vals):
            vt = bm.verts.new((x_root + s, y, z_root + half_t))
            vb = bm.verts.new((x_root + s, y, z_root - half_t))
            rt.append(vt)
            rb.append(vb)
        top_grid.append(rt)
        bot_grid.append(rb)

    # Intermediate sheet-terrace rings around the perimeter!
    # Closed perimeter walk of (i, j) indices (CCW in XY):
    # Bottom edge (j=0, i=0..ns-1) -> Right fore-edge (i=ns-1, j=1..ny-1)
    # -> Top head edge (j=ny-1, i=ns-2..0) -> Left spine edge (i=0, j=ny-2..1)
    perim_ij: list[tuple[int, int]] = []
    for i in range(ns):
        perim_ij.append((i, 0))
    for j in range(1, ny):
        perim_ij.append((ns - 1, j))
    for i in range(ns - 2, -1, -1):
        perim_ij.append((i, ny - 1))
    for j in range(ny - 2, 0, -1):
        perim_ij.append((0, j))
    n_perim = len(perim_ij)

    # Build rings from bottom (k=0 -> bot_grid) through k=1..n_sub_layers-1 to top (k=n_sub_layers -> top_grid)
    rng = np.random.default_rng(seed)
    layer_jitters = rng.uniform(-0.000085, +0.000085, n_sub_layers + 1)
    layer_jitters[0] = 0.0
    layer_jitters[-1] = 0.0

    rings: list[list[bmesh.types.BMVert]] = []
    rings.append([bot_grid[j][i] for (i, j) in perim_ij])

    for k in range(1, n_sub_layers):
        frac = k / n_sub_layers
        z_l = z_root - half_t + frac * thickness
        jit = float(layer_jitters[k])
        ring_k: list[bmesh.types.BMVert] = []
        for i, j in perim_ij:
            s = s_vals[i]
            y = y_vals[j]
            # Natural paper shingling + micro-stepped sheet edges on fore-edge & head/foot edges
            # (zero offset at spine i=0 so binding junction stays 100% flush!)
            w_free = smoothstep(0.005, 0.045, s)
            dx = 0.0
            dy = 0.0
            if i == ns - 1:
                # Subtle organic sheet-by-sheet step + natural curved-stack fore-edge bevel
                shingle = -0.00045 * (frac - 0.5) if "Right" in name else +0.00045 * (frac - 0.5)
                dx = jit + shingle + 0.00004 * math.sin(2.0 * math.pi * (y / PAGE_H) * 2.3 + k)
            if j == 0:
                dy = -abs(jit) * 0.6 * w_free
            elif j == ny - 1:
                dy = +abs(jit) * 0.6 * w_free
            v = bm.verts.new((x_root + s + dx, y + dy, z_l))
            ring_k.append(v)
        rings.append(ring_k)

    rings.append([top_grid[j][i] for (i, j) in perim_ij])

    bm.verts.index_update()
    for j in range(ny):
        for i, s in enumerate(s_vals):
            vert_s_param[top_grid[j][i].index] = s
            vert_s_param[bot_grid[j][i].index] = s
    for k in range(1, n_sub_layers):
        for p_idx, (i, _j) in enumerate(perim_ij):
            vert_s_param[rings[k][p_idx].index] = s_vals[i]

    uv0 = bm.loops.layers.uv.new("UVMap")
    uv1 = bm.loops.layers.uv.new("UVMap_Detail")

    def assign_uv(face: bmesh.types.BMFace, is_edge: bool) -> None:
        face.material_index = 1 if is_edge else 0
        face.smooth = True
        for loop in face.loops:
            co = loop.vert.co
            s_v = vert_s_param[loop.vert.index]
            if is_edge:
                eu = (s_v + (co.y + 0.5 * PAGE_H)) / DETAIL_REPEAT_M
                ev = max(0.0, min(1.0, (co.z - (z_root - half_t)) / thickness))
                loop[uv0].uv = (eu, ev)
                loop[uv1].uv = (eu, ev)
            else:
                u0 = max(0.0, min(1.0, s_v / PAGE_W))
                v0 = max(0.0, min(1.0, (co.y + 0.5 * PAGE_H) / PAGE_H))
                loop[uv0].uv = (u0, v0)
                loop[uv1].uv = (s_v / DETAIL_REPEAT_M, (co.y + 0.5 * PAGE_H) / DETAIL_REPEAT_M)

    # Top & bottom faces
    for j in range(ny - 1):
        for i in range(ns - 1):
            ft = bm.faces.new((top_grid[j][i], top_grid[j][i + 1], top_grid[j + 1][i + 1], top_grid[j + 1][i]))
            assign_uv(ft, is_edge=False)
            fb = bm.faces.new((bot_grid[j][i], bot_grid[j + 1][i], bot_grid[j + 1][i + 1], bot_grid[j][i + 1]))
            assign_uv(fb, is_edge=False)

    # Multi-layered terraced perimeter faces
    for k in range(n_sub_layers):
        ra = rings[k]
        rb = rings[k + 1]
        for p_idx in range(n_perim):
            p_next = (p_idx + 1) % n_perim
            fe = bm.faces.new((ra[p_idx], ra[p_next], rb[p_next], rb[p_idx]))
            assign_uv(fe, is_edge=True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    if non_man != 0:
        raise RuntimeError(f"{name} has {non_man} non-manifold edges!")

    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()

    mesh.materials.append(mat_paper)
    mesh.materials.append(mat_edge)

    obj = bpy.data.objects.new(name, mesh)
    obj.parent = arm_obj
    col.objects.link(obj)

    add_thickness_shape_key(obj, z_root)

    vgs = [obj.vertex_groups.new(name=f"{chain_prefix}_{k:02d}") for k in range(N_SHEET_BONES)]
    for v_idx, s_v in vert_s_param.items():
        for b_idx, w in compute_smooth_chain_weights(s_v):
            vgs[b_idx].add([v_idx], w, "REPLACE")

    mod = obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj
    return obj


def build_binding_mesh(
    arm_obj: bpy.types.Object,
    col: bpy.types.Collection,
    mat_spine_ext: bpy.types.Material,
    mat_paper_int: bpy.types.Material,
) -> bpy.types.Object:
    """Build continuous deformable Perfect-Bound Spine (`Binding`) skinned to Spine_00..07.
    Wraps seamlessly from Cover_Back's spine edge around the exterior rounded corners to
    Cover_Front's spine edge, with an inner PUR adhesive cradle holding the interior page roots."""
    y_vals = y_grid_stations()
    ny = len(y_vals)
    nu = 24  # Smooth stations along spine arc u in [0, SPINE_SPAN]

    # Cross-section profile around spine centerline at station u:
    # Exterior skin at x = -0.5 * T_COVER (-0.160 mm, flush with Z=0 when unrolled!),
    # inner PUR adhesive bed at x = +0.42 mm (overlapping page roots cleanly so zero gap ever appears!)
    x_ext = -0.5 * T_COVER
    x_int = +0.00142

    bm = bmesh.new()
    ext_grid: list[list[bmesh.types.BMVert]] = []
    int_grid: list[list[bmesh.types.BMVert]] = []
    vert_u_param: dict[int, float] = {}

    for j, y in enumerate(y_vals):
        re: list[bmesh.types.BMVert] = []
        ri: list[bmesh.types.BMVert] = []
        for i in range(nu + 1):
            u_frac = i / nu
            u_v = u_frac * SPINE_SPAN
            z_v = Z0_CB + u_v
            # Rounded square-back perfect-binding shoulder near u=0 and u=SPINE_SPAN
            shoulder = math.sin(math.pi * u_frac) ** 0.45
            xe = x_ext - 0.00005 * shoulder
            # Overlap cover spine-root by 0.25 mm at ends so zero hairline corner gap ever appears!
            xi = +0.00025 + (x_int - 0.00025) * (math.sin(math.pi * u_frac) ** 0.65)
            ve = bm.verts.new((xe, y, z_v))
            vi = bm.verts.new((xi, y, z_v))
            re.append(ve)
            ri.append(vi)
        ext_grid.append(re)
        int_grid.append(ri)

    bm.verts.index_update()
    for j in range(ny):
        for i in range(nu + 1):
            u_v = (i / nu) * SPINE_SPAN
            vert_u_param[ext_grid[j][i].index] = u_v
            vert_u_param[int_grid[j][i].index] = u_v

    uv0 = bm.loops.layers.uv.new("UVMap")
    uv1 = bm.loops.layers.uv.new("UVMap_Detail")

    def set_spine_uv(face: bmesh.types.BMFace, mat_idx: int) -> None:
        face.material_index = mat_idx
        face.smooth = True
        for loop in face.loops:
            co = loop.vert.co
            u_v = vert_u_param[loop.vert.index]
            u0 = u_v / SPINE_SPAN
            v0 = (co.y + 0.5 * PAGE_H) / PAGE_H
            loop[uv0].uv = (u0, v0)
            loop[uv1].uv = (u_v / DETAIL_REPEAT_M, (co.y + 0.5 * PAGE_H) / DETAIL_REPEAT_M)

    # Exterior spine faces (-X normal in rest pose -> slot 0 = Mat_Spine_Exterior)
    for j in range(ny - 1):
        for i in range(nu):
            f = bm.faces.new((ext_grid[j][i], ext_grid[j + 1][i], ext_grid[j + 1][i + 1], ext_grid[j][i + 1]))
            set_spine_uv(f, 0)

    # Interior PUR glue bed (+X normal -> slot 1 = Mat_Paper_Interior)
    for j in range(ny - 1):
        for i in range(nu):
            f = bm.faces.new((int_grid[j][i], int_grid[j][i + 1], int_grid[j + 1][i + 1], int_grid[j + 1][i]))
            set_spine_uv(f, 1)

    # End caps (u=0, u=SPINE_SPAN, j=0, j=ny-1)
    for j in range(ny - 1):
        f0 = bm.faces.new((ext_grid[j][0], int_grid[j][0], int_grid[j + 1][0], ext_grid[j + 1][0]))
        set_spine_uv(f0, 0)
        f1 = bm.faces.new((int_grid[j][-1], ext_grid[j][-1], ext_grid[j + 1][-1], int_grid[j + 1][-1]))
        set_spine_uv(f1, 0)
    for i in range(nu):
        fb = bm.faces.new((ext_grid[0][i], ext_grid[0][i + 1], int_grid[0][i + 1], int_grid[0][i]))
        set_spine_uv(fb, 0)
        ft = bm.faces.new((int_grid[-1][i], int_grid[-1][i + 1], ext_grid[-1][i + 1], ext_grid[-1][i]))
        set_spine_uv(ft, 0)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    non_man = sum(1 for e in bm.edges if not e.is_manifold)
    if non_man != 0:
        raise RuntimeError(f"Binding has {non_man} non-manifold edges!")

    mesh = bpy.data.meshes.new("Binding")
    bm.to_mesh(mesh)
    bm.free()

    mesh.materials.append(mat_spine_ext)
    mesh.materials.append(mat_paper_int)

    obj = bpy.data.objects.new("Binding", mesh)
    obj.parent = arm_obj
    col.objects.link(obj)

    du_sp = SPINE_SPAN / N_SPINE_BONES
    mids = [(k + 0.5) * du_sp for k in range(N_SPINE_BONES)]
    vgs = [obj.vertex_groups.new(name=f"Spine_{k:02d}") for k in range(N_SPINE_BONES)]

    for v_idx, u_v in vert_u_param.items():
        if u_v <= mids[0]:
            vgs[0].add([v_idx], 1.0, "REPLACE")
        elif u_v >= mids[-1]:
            vgs[-1].add([v_idx], 1.0, "REPLACE")
        else:
            for k in range(N_SPINE_BONES - 1):
                if mids[k] <= u_v <= mids[k + 1]:
                    a = (u_v - mids[k]) / (mids[k + 1] - mids[k])
                    if 1.0 - a > 1e-5:
                        vgs[k].add([v_idx], 1.0 - a, "REPLACE")
                    if a > 1e-5:
                        vgs[k + 1].add([v_idx], a, "REPLACE")
                    break

    mod = obj.modifiers.new(name="Armature", type="ARMATURE")
    mod.object = arm_obj
    return obj


# ---------------------------------------------------------------------------
# Applying Exact Elastica Poses to Armature PoseBones & Baking glTF Actions
# ---------------------------------------------------------------------------
def build_world_bone_matrix(head_pos: Vector, theta_xz: float, rest_angle_xz: float, twist_x: float = 0.0) -> Matrix:
    """Compute target armature-space Matrix for a bone whose rest pose has angle `rest_angle_xz` in XZ.
    In Blender:
      - A bone along +X (head->tail = (+ds, 0, 0), roll = 0) has local +Y along +X, local +Z along +Z, local +X along +Y!
        Wait: instead of guessing bone roll axes, we transform the bone's exact rest `bone.matrix_local`
        by a pure rotation around world -Y (since rotation by +theta from +X toward +Z in right-handed XYZ
        is rotation by -theta around +Y: R_y(-d_theta) * (1, 0, 0) = (cos(d_theta), 0, sin(d_theta))!)!
    """
    raise NotImplementedError  # Replaced by exact rest-matrix conjugation in apply_pose_to_armature!


def apply_pose_to_armature(
    arm_obj: bpy.types.Object,
    q_spine: float,
    profiles: dict[str, tuple[float, float, np.ndarray]],
    turning_torsion_rad: float = 0.0,
    prev_quats: dict[str, Quaternion] | None = None,
) -> None:
    """Set exact pose bone local basis transforms on `arm_obj` from continuous Elastica profiles.
    Uses exact analytical parent-to-child conjugation:
      M_basis_child = inv(M_rest_child) @ M_rest_parent @ inv(M_pose_parent) @ M_pose_child
    so zero intermediate depsgraph updates are needed, bone lengths stay 100.000000% invariant,
    and quaternion signs remain hemisphere-continuous across animation frames!"""
    pbones = arm_obj.pose.bones
    bones_rest = arm_obj.data.bones

    def set_bone_basis(pb: bpy.types.PoseBone, rb: bpy.types.Bone, m_pose_parent: Matrix, m_rest_parent: Matrix, m_pose_cur: Matrix, is_chain_root: bool) -> None:
        m_basis = rb.matrix_local.inverted() @ m_rest_parent @ m_pose_parent.inverted() @ m_pose_cur
        loc, quat, _sca = m_basis.decompose()
        quat.normalize()
        if prev_quats is not None:
            q_old = prev_quats.get(pb.name)
            if q_old is not None and quat.dot(q_old) < 0.0:
                quat = Quaternion((-quat.w, -quat.x, -quat.y, -quat.z))
            prev_quats[pb.name] = quat.copy()
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = quat
        pb.location = loc if is_chain_root else Vector((0.0, 0.0, 0.0))

    rb_origin = bones_rest["Rig_Origin"]
    m_origin_rest = rb_origin.matrix_local
    m_origin_pose = rb_origin.matrix_local

    # 1. Spine chain (rest direction = +Z, i.e., theta_rest = +pi/2)
    u_grid, x_sp, z_sp, _th_sp = spine_state_at_open_progress(q_spine)
    du_sp = SPINE_SPAN / N_SPINE_BONES

    sp_head_cur = Vector((float(x_sp[0]), 0.0, float(z_sp[0])))
    m_parent_pose = m_origin_pose
    m_parent_rest = m_origin_rest
    for i in range(N_SPINE_BONES):
        bname = f"Spine_{i:02d}"
        pb = pbones[bname]
        rb = bones_rest[bname]
        x_next = float(np.interp((i + 1) * du_sp, u_grid, x_sp))
        z_next = float(np.interp((i + 1) * du_sp, u_grid, z_sp))
        th_seg = math.atan2(z_next - sp_head_cur.z, x_next - sp_head_cur.x)
        d_th = th_seg - (0.5 * math.pi)
        rot_w = Matrix.Rotation(-d_th, 4, "Y")
        m_world = Matrix.Translation(sp_head_cur) @ rot_w @ Matrix.Translation(-rb.head_local) @ rb.matrix_local

        set_bone_basis(pb, rb, m_parent_pose, m_parent_rest, m_world, is_chain_root=(i == 0))
        m_parent_pose = m_world
        m_parent_rest = rb.matrix_local
        sp_head_cur = sp_head_cur + Vector((du_sp * math.cos(th_seg), 0.0, du_sp * math.sin(th_seg)))

    # 2. All 7 sheet/block chains (rest direction = +X, theta_rest = 0.0)
    for cname, _u_st, _glue_in in CHAIN_ORDER:
        x0, z0, th_q = profiles[cname]
        head_cur = Vector((x0, 0.0, z0))
        m_parent_pose = m_origin_pose
        m_parent_rest = m_origin_rest
        for k in range(N_SHEET_BONES):
            bname = f"{cname}_{k:02d}"
            pb = pbones[bname]
            rb = bones_rest[bname]
            s_mid = 0.5 * (BONE_S_NODES[k] + BONE_S_NODES[k + 1])
            ds = BONE_S_NODES[k + 1] - BONE_S_NODES[k]
            th_seg = float(np.interp(s_mid, S_QUAD, th_q))

            rot_w = Matrix.Rotation(-th_seg, 4, "Y")
            if cname == "Page_Turning" and abs(turning_torsion_rad) > 1e-7:
                twist_amt = turning_torsion_rad * (s_mid / PAGE_W)
                tangent_axis = Vector((math.cos(th_seg), 0.0, math.sin(th_seg)))
                rot_w = Matrix.Rotation(twist_amt, 4, tangent_axis) @ rot_w

            m_world = Matrix.Translation(head_cur) @ rot_w @ Matrix.Translation(-rb.head_local) @ rb.matrix_local
            set_bone_basis(pb, rb, m_parent_pose, m_parent_rest, m_world, is_chain_root=(k == 0))
            m_parent_pose = m_world
            m_parent_rest = rb.matrix_local
            head_cur = head_cur + Vector((ds * math.cos(th_seg), 0.0, ds * math.sin(th_seg)))

    bpy.context.view_layer.update()


def keyframe_all_deform_bones(arm_obj: bpy.types.Object, frame: int) -> None:
    pbones = arm_obj.pose.bones
    # Only root bones of each chain need location keys; connected child bones need only rotation_quaternion!
    root_bones = {"Spine_00"} | {f"{cname}_00" for cname, _, _ in CHAIN_ORDER}
    for pb in pbones:
        if pb.name == "Rig_Origin":
            continue
        pb.rotation_mode = "QUATERNION"
        if pb.name in root_bones:
            pb.keyframe_insert(data_path="location", frame=frame)
        pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)


def bake_demonstration_animations(arm_obj: bpy.types.Object, n_keys: int = 61) -> dict[str, bpy.types.Action]:
    """Bake the 3 required demonstration clips onto NLA tracks with exact resting-state consistency:
      - Magazine_Open     (frames 1..61, closed -> open)
      - Magazine_PageTurn (frames 1..61, open right -> open left)
      - Magazine_Close    (frames 1..61, open -> closed)
    """
    scene = bpy.context.scene
    scene.render.fps = 30
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()

    specs = [
        ("Magazine_Open", lambda u: evaluate_open_close_pose(u)),
        ("Magazine_PageTurn", lambda u: evaluate_page_turn_pose(u)),
        ("Magazine_PageTurn_Back", lambda u: evaluate_page_turn_pose(1.0 - u)),
        ("Magazine_Close", lambda u: evaluate_open_close_pose(1.0 - u)),
        ("Magazine_Close_Back", lambda u: evaluate_back_close_open_pose(u)),
        ("Magazine_Open_Back", lambda u: evaluate_back_close_open_pose(1.0 - u)),
    ]

    actions: dict[str, bpy.types.Action] = {}
    for clip_name, eval_fn in specs:
        act = bpy.data.actions.new(name=clip_name)
        act.use_fake_user = True
        arm_obj.animation_data.action = act
        if hasattr(act, "slots") and len(act.slots) == 0:
            slot = act.slots.new(id_type="OBJECT", name=arm_obj.name)
            arm_obj.animation_data.action_slot = slot

        prev_quats: dict[str, Quaternion] = {}
        for idx in range(n_keys):
            u = idx / (n_keys - 1)
            frame = idx + 1
            scene.frame_set(frame)
            q_sp, profs, tors = eval_fn(u)
            apply_pose_to_armature(arm_obj, q_sp, profs, tors, prev_quats=prev_quats)
            keyframe_all_deform_bones(arm_obj, frame)

        # Ensure linear interpolation between dense baked keys so SLERP never overshoots clearances
        if hasattr(act, "layers") and len(act.layers) > 0:
            # Blender 5.x slotted/layered actions
            for layer in act.layers:
                for strip in layer.strips:
                    if hasattr(strip, "channelbags"):
                        for bag in strip.channelbags:
                            for fc in bag.fcurves:
                                for kp in fc.keyframe_points:
                                    kp.interpolation = "LINEAR"
        elif hasattr(act, "fcurves"):
            for fc in act.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"

        actions[clip_name] = act

    # Keep all 3 Actions directly on bpy.data.actions (with fake_user=True) and use_nla=False
    # so Blender 5.2 Slotted Actions evaluate deterministically and glTF ACTIONS mode exports all 3 clips!
    arm_obj.animation_data.use_nla = False
    arm_obj.animation_data.action = None
    for track in list(arm_obj.animation_data.nla_tracks):
        arm_obj.animation_data.nla_tracks.remove(track)

    q_sp, profs, tors = evaluate_open_close_pose(1.0)
    apply_pose_to_armature(arm_obj, q_sp, profs, tors)
    scene.frame_start = 1
    scene.frame_end = n_keys
    scene.frame_set(1)
    return actions


# ---------------------------------------------------------------------------
# Studio Product Photography Rig (Cycles Metal GPU) & GLB Export
# ---------------------------------------------------------------------------
def create_studio_photography_collection() -> tuple[bpy.types.Collection, bpy.types.Object]:
    """Professional studio cyclorama + 3-point softbox lighting in an isolated collection
    excluded from production GLB export."""
    col = bpy.data.collections.new("Studio_Preview")
    bpy.context.scene.collection.children.link(col)

    # Large seamless 360-degree studio cyclorama bowl at Z = -0.00002 m so every side/grazing angle has a clean backdrop
    bm = bmesh.new()
    n_ang = 48
    radii_z = [(0.0, -0.00002), (0.55, -0.00002), (0.95, -0.00002)]
    r_c = 0.65
    for k in range(1, 12):
        a = 0.5 * math.pi * (k / 11.0)
        radii_z.append((0.95 + r_c * math.sin(a), -0.00002 + r_c * (1.0 - math.cos(a))))
    radii_z.append((0.95 + r_c, 1.80))

    center_v = bm.verts.new((0.0, 0.0, -0.00002))
    rings_bg = []
    for rad, zv in radii_z[1:]:
        ring = [bm.verts.new((rad * math.cos(2.0 * math.pi * i / n_ang), rad * math.sin(2.0 * math.pi * i / n_ang), zv)) for i in range(n_ang)]
        rings_bg.append(ring)
    for i in range(n_ang):
        inext = (i + 1) % n_ang
        bm.faces.new((center_v, rings_bg[0][i], rings_bg[0][inext]))
    for r_i in range(len(rings_bg) - 1):
        for i in range(n_ang):
            inext = (i + 1) % n_ang
            bm.faces.new((rings_bg[r_i][i], rings_bg[r_i + 1][i], rings_bg[r_i + 1][inext], rings_bg[r_i][inext]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bg_mesh = bpy.data.meshes.new("Studio_Cyclorama")
    bm.to_mesh(bg_mesh)
    bm.free()
    for p in bg_mesh.polygons:
        p.use_smooth = True

    mat_bg = bpy.data.materials.new("Mat_Studio_Cyclorama")
    if mat_bg.node_tree is None:
        mat_bg.use_nodes = True
    bsdf = mat_bg.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = hex_to_linear_rgba("#B6AEA2")
        bsdf.inputs["Roughness"].default_value = 0.90
        if "Specular IOR Level" in bsdf.inputs:
            bsdf.inputs["Specular IOR Level"].default_value = 0.22
    bg_mesh.materials.append(mat_bg)
    bg_obj = bpy.data.objects.new("Studio_Cyclorama", bg_mesh)
    col.objects.link(bg_obj)

    cam_data = bpy.data.cameras.new("Studio_Camera")
    cam_data.lens = 65.0
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.005
    cam_data.clip_end = 10.0
    cam_obj = bpy.data.objects.new("Studio_Camera", cam_data)
    col.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    def add_softbox(name: str, pos: tuple[float, float, float], aim: tuple[float, float, float], energy: float, sx: float, sy: float, temp_rgb=(1.0, 1.0, 1.0)):
        ld = bpy.data.lights.new(name=name, type="AREA")
        ld.shape = "RECTANGLE"
        ld.size = sx
        ld.size_y = sy
        ld.energy = energy
        ld.color = temp_rgb
        lo = bpy.data.objects.new(name, ld)
        lo.location = Vector(pos)
        lo.rotation_euler = (Vector(aim) - Vector(pos)).to_track_quat("-Z", "Z").to_euler()
        col.objects.link(lo)

    # Sculpted directional key softbox (raking studio light that carves out the gutter, page arch & layered edges!)
    add_softbox("Studio_Key_Softbox", (-0.68, -0.42, 0.52), (0.0, 0.0, 0.01), energy=28.0, sx=0.46, sy=0.36, temp_rgb=(1.0, 0.985, 0.96))
    # Restrained cool fill from right so shadows remain rich and dimensional
    add_softbox("Studio_Fill_Softbox", (0.78, -0.58, 0.44), (0.0, 0.0, 0.01), energy=4.8, sx=0.72, sy=0.55, temp_rgb=(0.95, 0.97, 1.0))
    # Rear-top rim softbox for authentic satin sheen across coated cover & curved page crest
    add_softbox("Studio_Rim_Softbox", (0.10, 0.72, 0.48), (0.0, -0.02, 0.02), energy=14.0, sx=0.62, sy=0.28, temp_rgb=(1.0, 0.99, 0.97))

    world = bpy.data.worlds.new("Studio_World")
    if world.node_tree is None:
        world.use_nodes = True
    bg_n = world.node_tree.nodes.get("Background")
    if bg_n:
        bg_n.inputs["Color"].default_value = hex_to_linear_rgba("#B0A89C")
        bg_n.inputs["Strength"].default_value = 0.10
    bpy.context.scene.world = world
    return col, cam_obj


def configure_cycles_metal(width: int = 1600, height: int = 1200, samples: int = 44, exposure: float = -0.34) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.refresh_devices()
    metal_devs = [d for d in prefs.devices if d.type == "METAL"]
    if metal_devs:
        prefs.compute_device_type = "METAL"
        for d in prefs.devices:
            d.use = (d.type == "METAL")
        scene.cycles.device = "GPU"
    else:
        scene.cycles.device = "CPU"

    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.transmission_bounces = 2
    scene.cycles.transparent_max_bounces = 2
    scene.cycles.use_denoising = True
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"

    avail = [it.identifier for it in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
    if "AgX" in avail:
        scene.view_settings.view_transform = "AgX"
        looks = [it.identifier for it in scene.view_settings.bl_rna.properties["look"].enum_items]
        if "AgX - Medium High Contrast" in looks:
            scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = exposure


def aim_camera(cam_obj: bpy.types.Object, pos: tuple[float, float, float], target: tuple[float, float, float], lens: float = 65.0, up_axis: str = "Z") -> None:
    cam_obj.data.type = "PERSP"
    cam_obj.data.lens = lens
    cam_obj.location = Vector(pos)
    cam_obj.rotation_euler = (Vector(target) - Vector(pos)).to_track_quat("-Z", up_axis).to_euler()


def render_webp(out_webp: Path, width: int = 1600, height: int = 1200, samples: int = 44, exposure: float = -0.34) -> None:
    out_webp.parent.mkdir(parents=True, exist_ok=True)
    configure_cycles_metal(width=width, height=height, samples=samples, exposure=exposure)
    cwebp = shutil.which("cwebp")
    with tempfile.TemporaryDirectory() as tmp:
        png_p = Path(tmp) / "render.png"
        bpy.context.scene.render.filepath = str(png_p)
        bpy.ops.render.render(write_still=True)
        if cwebp:
            subprocess.run([cwebp, "-q", "92", str(png_p), "-o", str(out_webp)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            shutil.copy2(png_p, out_webp.with_suffix(".png"))


def isolate_and_compact_glb(glb_path: Path) -> None:
    """Surgically isolate animation channels in `model.glb` and compact unreferenced animation buffers:
      - `Magazine_PageTurn`: strictly isolated to `Page_Turning_00..31` (33 channels: 1 root translation +
        32 rotations). Playing or seeking `Magazine_PageTurn` NEVER resets covers, spine, resting pages, or stacks!
      - `Magazine_Open` / `Magazine_Close`: retain only active chain-root translations (8) + deforming bone
        rotations (232) = 240 channels, stripping all 459 redundant constant scale=(1,1,1) / child-translation /
        Rig_Origin tracks and garbage-collecting orphaned accessors & bufferViews.
    """
    raw = glb_path.read_bytes()
    magic, version, _total_len = struct.unpack_from("<III", raw, 0)
    if magic != 0x46546C67:
        raise RuntimeError("Invalid GLB magic header")
    j_len, j_type = struct.unpack_from("<II", raw, 12)
    gltf = json.loads(raw[20 : 20 + j_len].decode("utf-8"))
    b_off = 20 + j_len
    b_len, b_type = struct.unpack_from("<II", raw, b_off)
    bin_blob = raw[b_off + 8 : b_off + 8 + b_len]

    nodes = gltf["nodes"]
    chain_roots = {"Spine_00"} | {f"{cname}_00" for cname, _, _ in CHAIN_ORDER}

    for anim in gltf.get("animations", []):
        aname = anim["name"]
        old_samplers = anim["samplers"]
        new_channels = []
        new_samplers = []
        sampler_remap: dict[int, int] = {}

        for ch in anim["channels"]:
            tgt = ch["target"]
            nname = nodes[tgt["node"]]["name"]
            path = tgt["path"]
            if nname == "Rig_Origin" or path == "scale":
                continue
            if path == "translation" and nname not in chain_roots:
                continue
            if aname in ("Magazine_PageTurn", "Magazine_PageTurn_Back") and not nname.startswith("Page_Turning_"):
                continue

            old_s_idx = ch["sampler"]
            if old_s_idx not in sampler_remap:
                sampler_remap[old_s_idx] = len(new_samplers)
                new_samplers.append(old_samplers[old_s_idx])
            ch["sampler"] = sampler_remap[old_s_idx]
            new_channels.append(ch)

        anim["channels"] = new_channels
        anim["samplers"] = new_samplers

    # Collect all referenced accessor indices across meshes, skins, animations
    used_acc: set[int] = set()
    for m in gltf.get("meshes", []):
        for prim in m.get("primitives", []):
            for a_idx in prim.get("attributes", {}).values():
                used_acc.add(a_idx)
            if "indices" in prim:
                used_acc.add(prim["indices"])
            for tgt in prim.get("targets", []):
                for a_idx in tgt.values():
                    used_acc.add(a_idx)
    for sk in gltf.get("skins", []):
        if "inverseBindMatrices" in sk:
            used_acc.add(sk["inverseBindMatrices"])
    for anim in gltf.get("animations", []):
        for s in anim.get("samplers", []):
            used_acc.add(s["input"])
            used_acc.add(s["output"])

    old_accs = gltf.get("accessors", [])
    acc_remap: dict[int, int] = {}
    new_accs = []
    for old_i, acc in enumerate(old_accs):
        if old_i in used_acc:
            acc_remap[old_i] = len(new_accs)
            new_accs.append(acc)
    gltf["accessors"] = new_accs

    for m in gltf.get("meshes", []):
        for prim in m.get("primitives", []):
            prim["attributes"] = {k: acc_remap[v] for k, v in prim.get("attributes", {}).items()}
            if "indices" in prim:
                prim["indices"] = acc_remap[prim["indices"]]
            for tgt in prim.get("targets", []):
                for k in list(tgt.keys()):
                    tgt[k] = acc_remap[tgt[k]]
    for sk in gltf.get("skins", []):
        if "inverseBindMatrices" in sk:
            sk["inverseBindMatrices"] = acc_remap[sk["inverseBindMatrices"]]
    for anim in gltf.get("animations", []):
        for s in anim.get("samplers", []):
            s["input"] = acc_remap[s["input"]]
            s["output"] = acc_remap[s["output"]]

    # Collect all referenced bufferView indices across accessors and images
    used_bv: set[int] = set()
    for acc in gltf["accessors"]:
        if "bufferView" in acc:
            used_bv.add(acc["bufferView"])
        if "sparse" in acc:
            used_bv.add(acc["sparse"]["indices"]["bufferView"])
            used_bv.add(acc["sparse"]["values"]["bufferView"])
    for img in gltf.get("images", []):
        if "bufferView" in img:
            used_bv.add(img["bufferView"])

    old_bvs = gltf.get("bufferViews", [])
    bv_remap: dict[int, int] = {}
    new_bvs = []
    new_bin = bytearray()
    for old_i, bv in enumerate(old_bvs):
        if old_i not in used_bv:
            continue
        start = bv.get("byteOffset", 0)
        length = bv["byteLength"]
        chunk = bin_blob[start : start + length]
        # Pad start to 4-byte alignment
        while len(new_bin) % 4 != 0:
            new_bin.append(0)
        bv_copy = dict(bv)
        bv_copy["byteOffset"] = len(new_bin)
        new_bin.extend(chunk)
        bv_remap[old_i] = len(new_bvs)
        new_bvs.append(bv_copy)

    while len(new_bin) % 4 != 0:
        new_bin.append(0)

    gltf["bufferViews"] = new_bvs
    gltf["buffers"][0]["byteLength"] = len(new_bin)

    for acc in gltf["accessors"]:
        if "bufferView" in acc:
            acc["bufferView"] = bv_remap[acc["bufferView"]]
        if "sparse" in acc:
            acc["sparse"]["indices"]["bufferView"] = bv_remap[acc["sparse"]["indices"]["bufferView"]]
            acc["sparse"]["values"]["bufferView"] = bv_remap[acc["sparse"]["values"]["bufferView"]]
    for img in gltf.get("images", []):
        if "bufferView" in img:
            img["bufferView"] = bv_remap[img["bufferView"]]

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(new_bin)
    out = bytearray()
    out.extend(struct.pack("<III", 0x46546C67, version, total_len))
    out.extend(struct.pack("<II", len(json_bytes), j_type))
    out.extend(json_bytes)
    out.extend(struct.pack("<II", len(new_bin), b_type))
    out.extend(new_bin)
    glb_path.write_bytes(bytes(out))


def export_production_glb(asset_col: bpy.types.Collection, studio_col: bpy.types.Collection, arm_obj: bpy.types.Object) -> None:
    """Export self-contained production model.glb in meters (+Y up), excluding studio props/cameras/lights."""
    arm_obj.animation_data.use_nla = False
    arm_obj.animation_data.action = None
    q_sp, profs, tors = evaluate_open_close_pose(1.0)
    apply_pose_to_armature(arm_obj, q_sp, profs, tors)

    bpy.ops.object.select_all(action="DESELECT")
    for obj in asset_col.all_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=False,
        export_texcoords=True,
        export_normals=True,
        export_tangents=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_skins=True,
        export_all_influences=False,
        export_morph=True,
        export_morph_normal=False,
        export_morph_tangent=False,
        export_morph_animation=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_anim_slide_to_zero=True,
        export_bake_animation=True,
        export_anim_single_armature=True,
        export_optimize_animation_size=False,
    )
    isolate_and_compact_glb(GLB_PATH)
    arm_obj.animation_data.action = None
    q_sp, profs, tors = evaluate_open_close_pose(1.0)
    apply_pose_to_armature(arm_obj, q_sp, profs, tors)


def build_asset(skip_preview: bool = False) -> dict[str, bpy.types.Object]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    asset_col = bpy.data.collections.new("Editorial_Magazine")
    scene.collection.children.link(asset_col)

    tex = generate_pbr_textures()
    mats = create_all_materials(tex)
    arm_obj = create_magazine_armature(asset_col)

    objs: dict[str, bpy.types.Object] = {"Magazine_Root": arm_obj}
    objs["Binding"] = build_binding_mesh(arm_obj, asset_col, mats["Mat_Spine_Exterior"], mats["Mat_Paper_Interior"])

    # Covers:
    # Cover_Back (flat on +X): Top (+Z) = Inner (u = s/L), Bot (-Z) = Outer (u = 1 - s/L when flipped horizontally!)
    objs["Cover_Back"] = build_flexible_sheet_mesh(
        "Cover_Back", "Cover_Back", arm_obj, asset_col,
        u_station=U_CB, glue_in=0.0, thickness=T_COVER,
        mat_top=mats["Mat_Cover_Back_Inner"], mat_bot=mats["Mat_Cover_Back_Outer"], mat_edge=mats["Mat_Paper_Edges"],
        top_uv_mirror_u=False, bot_uv_mirror_u=True, has_hinge_score=True,
    )
    # Cover_Front (closed on +X): Top (+Z) = Outer (u = s/L), Bot (-Z) = Inner (when opened 180 deg to -X, faces UP -> u = 1 - s/L!)
    objs["Cover_Front"] = build_flexible_sheet_mesh(
        "Cover_Front", "Cover_Front", arm_obj, asset_col,
        u_station=U_CF, glue_in=0.0, thickness=T_COVER,
        mat_top=mats["Mat_Cover_Front_Outer"], mat_bot=mats["Mat_Cover_Front_Inner"], mat_edge=mats["Mat_Paper_Edges"],
        top_uv_mirror_u=False, bot_uv_mirror_u=True, has_hinge_score=True,
    )

    # Layered Deformable Page Blocks (8-layer terraced edges — identical macro fidelity, 30% leaner!)
    objs["Pages_Block_Right"] = build_layered_page_block_mesh(
        "Pages_Block_Right", "Pages_Block_Right", arm_obj, asset_col,
        u_station=U_BR, glue_in=0.00028, thickness=T_BLOCK_R, n_sub_layers=8,
        mat_paper=mats["Mat_Paper_Interior"], mat_edge=mats["Mat_Paper_Edges"], seed=401,
    )
    objs["Pages_Block_Left"] = build_layered_page_block_mesh(
        "Pages_Block_Left", "Pages_Block_Left", arm_obj, asset_col,
        u_station=U_BL, glue_in=0.00028, thickness=T_BLOCK_L, n_sub_layers=8,
        mat_paper=mats["Mat_Paper_Interior"], mat_edge=mats["Mat_Paper_Edges"], seed=402,
    )

    # Individual Replaceable Interior Pages:
    # Page_Right (stays on +X): Top (+Z) = Mat_Page_Right (u = s/L), Bot (-Z) = Mat_Paper_Interior
    objs["Page_Right"] = build_flexible_sheet_mesh(
        "Page_Right", "Page_Right", arm_obj, asset_col,
        u_station=U_PR, glue_in=0.00028, thickness=T_PAGE,
        mat_top=mats["Mat_Page_Right"], mat_bot=mats["Mat_Paper_Interior"], mat_edge=mats["Mat_Paper_Edges"],
        top_uv_mirror_u=False, bot_uv_mirror_u=True, edge_micro_seed=11,
    )
    # Page_Turning (starts on +X, turns 180 deg to -X): Top (+Z) = Front (u = s/L), Bot (-Z) = Back (u = 1 - s/L)
    objs["Page_Turning"] = build_flexible_sheet_mesh(
        "Page_Turning", "Page_Turning", arm_obj, asset_col,
        u_station=U_PT, glue_in=0.00028, thickness=T_PAGE,
        mat_top=mats["Mat_Page_Turning_Front"], mat_bot=mats["Mat_Page_Turning_Back"], mat_edge=mats["Mat_Paper_Edges"],
        top_uv_mirror_u=False, bot_uv_mirror_u=True, edge_micro_seed=23,
    )
    # Page_Left (closed on +X, opens 180 deg onto -X): Top (+Z when closed) = Mat_Paper_Interior, Bot (-Z when closed -> +Z when open!) = Mat_Page_Left (u = 1 - s/L!)
    objs["Page_Left"] = build_flexible_sheet_mesh(
        "Page_Left", "Page_Left", arm_obj, asset_col,
        u_station=U_PL, glue_in=0.00028, thickness=T_PAGE,
        mat_top=mats["Mat_Paper_Interior"], mat_bot=mats["Mat_Page_Left"], mat_edge=mats["Mat_Paper_Edges"],
        top_uv_mirror_u=False, bot_uv_mirror_u=True, edge_micro_seed=37,
    )

    bake_demonstration_animations(arm_obj, n_keys=61)
    studio_col, cam_obj = create_studio_photography_collection()

    export_production_glb(asset_col, studio_col, arm_obj)

    # Render canonical catalog preview (full-frame 3/4 studio view of neutral blank magazine with 28% turning page!)
    if not skip_preview:
        q_sp, profs, tors = evaluate_page_turn_pose(0.28)
        apply_pose_to_armature(arm_obj, q_sp, profs, tors)
        aim_camera(cam_obj, pos=(0.25, -0.82, 0.53), target=(0.0, 0.015, 0.042), lens=60.0)
        render_webp(PREVIEW_WEBP_PATH, width=1600, height=1200, samples=48, exposure=-0.34)

    # Leave model.blend in clean Open Spread pose with strictly relative texture paths
    q_sp, profs, tors = evaluate_open_close_pose(1.0)
    apply_pose_to_armature(arm_obj, q_sp, profs, tors)
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_mainfile(compress=True)
    blend1 = BLEND_PATH.with_suffix(".blend1")
    if blend1.exists():
        blend1.unlink()
    return objs


def main() -> None:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-preview", action="store_true")
    args = parser.parse_args(argv)
    build_asset(skip_preview=args.skip_preview)
    print(f"Built {BLEND_PATH} and {GLB_PATH}")


if __name__ == "__main__":
    main()
