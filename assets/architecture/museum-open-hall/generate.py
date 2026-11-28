#!/usr/bin/env python3
"""
Reproducible Blender Python Architectural Generator for:
  Open Skylight Museum Hall (`assets/architecture/museum-open-hall/`)

Supports staged visual production and final deliverable export:
  - `--stage massing` : Stage A neutral clay architectural massing studies (5 views)
  - `--stage detail`  : Stage B neutral clay full architectural detailing studies (4 views)
  - `--stage final`   : Stages C, D, E, F — coherent PBR texture synthesis, Cycles lighting
                        scenarios (Soft Daylight, Direct Sunlight, Evening Exhibition),
                        12 required architectural & exhibition renders, catalog `preview.webp`,
                        editable `model.blend`, and self-contained `model.glb`.
  - `--export-only`   : Fast clean-checkout regeneration of textures, `model.blend`, and `model.glb`
                        without re-rendering diagnostic studies.

Coordinate convention (exported glTF 2.0 Y-up, meters):
  - X : Hall width  (-12.00 m Left Wall to +12.00 m Right Wall; 24.00 m clear)
  - Y : Height      (  0.00 m Finished Floor to +9.00 m Main Ceiling; +10.68 m Skylight Glass)
  - Z : Hall depth  ( -9.00 m Main Rear Exhibition Wall to +9.00 m Entrance Wall; 18.00 m clear)
  - Origin (0, 0, 0): Center of interior finished floor.
  - Blender internal conversion: (X_b, Y_b, Z_b) = (X_g, -Z_g, Y_g), a proper +90 deg X rotation
    that exports via `export_yup=True` back to exact (X_g, Y_g, Z_g) with zero manual correction.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------
# Paths & Architectural Specification Constants
# ---------------------------------------------------------------------------

ASSET_DIR = Path(__file__).resolve().parent
REPO_ROOT = ASSET_DIR.parent.parent.parent
TEX_DIR = ASSET_DIR / "textures"
WORK_DIR = REPO_ROOT / ".work" / "architecture" / "museum-open-hall"

# Core Interior Clear Dimensions (glTF meters)
HALL_WIDTH = 24.00          # X: -12.00 to +12.00
HALL_DEPTH = 18.00          # Z:  -9.00 to  +9.00
CEILING_HEIGHT = 9.00       # Y:   0.00 to  +9.00 floating canopy soffit

HALF_W = HALL_WIDTH * 0.5   # 12.00 m
HALF_D = HALL_DEPTH * 0.5   #  9.00 m

WALL_THICK = 0.40           # 400 mm structural perimeter walls
PORTAL_DEPTH = 1.60         # 1600 mm deep monumental architectural entrance portal (+9.00 to +10.60)
FLOOR_THICK = 0.32          # 320 mm structural concrete slab (-0.32 to 0.00)

ENTRANCE_WIDTH = 5.60       # X: -2.80 to +2.80 (within 5-6 m spec)
ENTRANCE_HEIGHT = 4.80      # Y:  0.00 to +4.80 (within 4-5 m spec)
ENTRANCE_FRAME_T = 0.055    # 55 mm anodized architectural bronze-pewter portal liner

# Subtle architectural wall-to-floor & floating-canopy perimeter cove details
BASE_REVEAL_H = 0.024       # 24 mm crisp museum wall-base shadow gap (subtle, non-cartoonish)
BASE_REVEAL_D = 0.024       # 24 mm recessed base shadow channel depth
TOP_WALL_REVEAL_H = 0.022   # 22 mm crisp ceiling shadow quirk on front & rear walls
TOP_WALL_REVEAL_D = 0.020

# Floating ceiling canopy & perimeter side daylight coves (inspired by contemporary museum daylight coves)
COVE_SIDE_W = 0.68          # 680 mm wide architectural daylight coves along Left & Right exhibition walls
COVE_TOP_Y = 9.76           # 760 mm tall sculptural canopy fascia & side daylight cove pocket; sealed above

# Monumental 5-bay Skylight Architecture (13.60 m x 11.80 m aperture, 1.68 m deep canted light well)
SKYLIGHT_W = 13.60          # X: -6.80 to +6.80 at Y = 9.00 m (within 13-14 m spec)
SKYLIGHT_D = 11.80          # Z: -5.90 to +5.90 at Y = 9.00 m (within 11-12 m spec)
SKY_HALF_W = SKYLIGHT_W * 0.5   # 6.80 m
SKY_HALF_D = SKYLIGHT_D * 0.5   # 5.90 m
SKY_CANT = 0.14             # 140 mm outward cant over 1.68 m deep plaster light well (~4.8 deg)
SKY_WELL_TOP_Y = 10.68      # Top of canted plaster skylight well
SKY_FRAME_TOP_Y = 10.82     # Top of powder-coated aluminum glazing mullions
SKY_CURB_TOP_Y = 10.90      # Exterior skylight flashing curb cap
SKY_GLASS_Y0 = 10.680       # Bottom of 20 mm laminated low-iron skylight glass
SKY_GLASS_Y1 = 10.700       # Top of 20 mm laminated low-iron skylight glass

# Recessed U-shaped architectural lighting track slots centered cleanly in the floating soffit wings
TRACK_X = 9.06              # Exact centerline of Left/Right floating soffits ((6.80 + 11.32)/2 = 9.06 m)
TRACK_BACK_Z = -7.35        # Exact centerline of Rear soffit ((-8.98 + -5.90)/2 = -7.44 -> -7.35 m)
TRACK_Z_END = 6.80          # Side tracks run Z = -7.35 to +6.80 m
TRACK_SLOT_W = 0.076        # 76 mm recessed ceiling slot width
TRACK_SLOT_D = 0.072        # 72 mm recessed ceiling slot depth

# Exhibition Artwork Mounting Anchors (9 primary positions)
# Centered mounting at Y = 1.55 m supports up to 2.60 m height with 0.25 m floor clearance.
# Taller works up to 5.60 m shift local +Y by (H - 2.60)/2.
ARTWORK_CENTER_Y = 1.55
ARTWORK_MIN_BOTTOM_Y = 0.25
ARTWORK_MAX_CENTERED_H = round((ARTWORK_CENTER_Y - ARTWORK_MIN_BOTTOM_Y) * 2.0, 4)  # 2.60 m
ARTWORK_MAX_SHIFTED_H = 5.60
WALL_EPS = 0.002            # 2 mm proud of plaster surface to prevent coplanar z-fighting

ARTWORK_SPECS = [
    # Back wall (Z = -9.00, inward normal +Z, local +X = world +X, local +Y = world +Y)
    {
        "name": "Anchor_Artwork_Back_01",
        "nav_name": "Anchor_Navigation_Artwork_01",
        "light_name": "Anchor_Light_Back_01",
        "wall": "Wall_Back",
        "pos": (-6.40, ARTWORK_CENTER_Y, -HALF_D + WALL_EPS),
        "axes": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "max_width": 4.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.80,
        "nav_dist": 3.60,
        "track_pos": (-6.40, 8.92, TRACK_BACK_Z),
    },
    {
        "name": "Anchor_Artwork_Back_02",
        "nav_name": "Anchor_Navigation_Artwork_02",
        "light_name": "Anchor_Light_Back_02",
        "wall": "Wall_Back",
        "pos": (0.00, ARTWORK_CENTER_Y, -HALF_D + WALL_EPS),
        "axes": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "max_width": 5.20,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.80,
        "nav_dist": 3.80,
        "track_pos": (0.00, 8.92, TRACK_BACK_Z),
    },
    {
        "name": "Anchor_Artwork_Back_03",
        "nav_name": "Anchor_Navigation_Artwork_03",
        "light_name": "Anchor_Light_Back_03",
        "wall": "Wall_Back",
        "pos": (6.40, ARTWORK_CENTER_Y, -HALF_D + WALL_EPS),
        "axes": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "max_width": 4.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.80,
        "nav_dist": 3.60,
        "track_pos": (6.40, 8.92, TRACK_BACK_Z),
    },
    # Left wall (X = -12.00, inward normal +X, local +X = world -Z, local +Y = world +Y)
    {
        "name": "Anchor_Artwork_Left_01",
        "nav_name": "Anchor_Navigation_Artwork_04",
        "light_name": "Anchor_Light_Left_01",
        "wall": "Wall_Left",
        "pos": (-HALF_W + WALL_EPS, ARTWORK_CENTER_Y, -5.20),
        "axes": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (-TRACK_X, 8.92, -5.20),
    },
    {
        "name": "Anchor_Artwork_Left_02",
        "nav_name": "Anchor_Navigation_Artwork_05",
        "light_name": "Anchor_Light_Left_02",
        "wall": "Wall_Left",
        "pos": (-HALF_W + WALL_EPS, ARTWORK_CENTER_Y, 0.00),
        "axes": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        "max_width": 4.00,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (-TRACK_X, 8.92, 0.00),
    },
    {
        "name": "Anchor_Artwork_Left_03",
        "nav_name": "Anchor_Navigation_Artwork_06",
        "light_name": "Anchor_Light_Left_03",
        "wall": "Wall_Left",
        "pos": (-HALF_W + WALL_EPS, ARTWORK_CENTER_Y, 5.20),
        "axes": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (-TRACK_X, 8.92, 5.20),
    },
    # Right wall (X = +12.00, inward normal -X, local +X = world +Z, local +Y = world +Y)
    {
        "name": "Anchor_Artwork_Right_01",
        "nav_name": "Anchor_Navigation_Artwork_07",
        "light_name": "Anchor_Light_Right_01",
        "wall": "Wall_Right",
        "pos": (HALF_W - WALL_EPS, ARTWORK_CENTER_Y, -5.20),
        "axes": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (TRACK_X, 8.92, -5.20),
    },
    {
        "name": "Anchor_Artwork_Right_02",
        "nav_name": "Anchor_Navigation_Artwork_08",
        "light_name": "Anchor_Light_Right_02",
        "wall": "Wall_Right",
        "pos": (HALF_W - WALL_EPS, ARTWORK_CENTER_Y, 0.00),
        "axes": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)),
        "max_width": 4.00,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (TRACK_X, 8.92, 0.00),
    },
    {
        "name": "Anchor_Artwork_Right_03",
        "nav_name": "Anchor_Navigation_Artwork_09",
        "light_name": "Anchor_Light_Right_03",
        "wall": "Wall_Right",
        "pos": (HALF_W - WALL_EPS, ARTWORK_CENTER_Y, 5.20),
        "axes": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (TRACK_X, 8.92, 5.20),
    },
]

PLACEMENT_SPECS = [
    ("Anchor_Place_Central_Installation", (0.00, 0.00, -0.60), (0.0, 0.0, 1.0)),
    ("Anchor_Place_Pedestal_01", (-3.80, 0.00, -2.20), (0.0, 0.0, 1.0)),
    ("Anchor_Place_Pedestal_02", (3.80, 0.00, -2.20), (0.0, 0.0, 1.0)),
    ("Anchor_Place_Bench_01", (-3.40, 0.00, 1.80), (0.0, 0.0, -1.0)),
    ("Anchor_Place_Bench_02", (3.40, 0.00, 1.80), (0.0, 0.0, -1.0)),
    ("Anchor_Place_Info_Stand", (-3.60, 0.00, 6.80), (0.0, 0.0, -1.0)),
    ("Anchor_Place_Invitation_Display", (3.60, 0.00, 6.80), (0.0, 0.0, -1.0)),
    ("Anchor_Place_Partition_01", (-4.80, 0.00, -0.60), (1.0, 0.0, 0.0)),
    ("Anchor_Place_Partition_02", (4.80, 0.00, -0.60), (-1.0, 0.0, 0.0)),
]

# ---------------------------------------------------------------------------
# Coordinate Conversion Helpers (glTF Y-up <-> Blender Z-up)
# ---------------------------------------------------------------------------

R_G2B = Matrix(((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))
R_B2G = R_G2B.transposed()


def g2b_pt(x: float, y: float, z: float) -> Vector:
    """Convert glTF (X, Y_up, Z_depth) point to Blender (X, Y_forward, Z_up)."""
    return Vector((x, -z, y))


def g2b_vec(v: Sequence[float]) -> Vector:
    return Vector((v[0], -v[2], v[1]))


def make_gltf_basis_matrix(
    pos_g: Tuple[float, float, float],
    x_axis_g: Tuple[float, float, float],
    y_axis_g: Tuple[float, float, float],
    z_axis_g: Tuple[float, float, float],
) -> Matrix:
    """Build Blender world matrix whose `export_yup=True` glTF export equals (X_g, Y_g, Z_g, pos_g)."""
    m_g = Matrix(
        (
            (x_axis_g[0], y_axis_g[0], z_axis_g[0], pos_g[0]),
            (x_axis_g[1], y_axis_g[1], z_axis_g[1], pos_g[1]),
            (x_axis_g[2], y_axis_g[2], z_axis_g[2], pos_g[2]),
            (0.0, 0.0, 0.0, 1.0),
        )
    )
    return R_G2B.to_4x4() @ m_g @ R_B2G.to_4x4()


def _build_look_matrix_gltf(
    eye_g: Tuple[float, float, float],
    target_g: Tuple[float, float, float],
    up_g: Tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> Matrix:
    eye = Vector(eye_g)
    target = Vector(target_g)
    up = Vector(up_g)
    forward = (target - eye).normalized()
    z_axis = -forward
    if abs(forward.dot(up)) > 0.995:
        up = Vector((0.0, 0.0, -1.0))
    x_axis = forward.cross(up).normalized()
    y_axis = z_axis.cross(x_axis).normalized()
    return Matrix(
        (
            (x_axis.x, y_axis.x, z_axis.x, eye.x),
            (x_axis.y, y_axis.y, z_axis.y, eye.y),
            (x_axis.z, y_axis.z, z_axis.z, eye.z),
            (0.0, 0.0, 0.0, 1.0),
        )
    )


def look_at_gltf_basis(
    eye_g: Tuple[float, float, float],
    target_g: Tuple[float, float, float],
    up_g: Tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> Matrix:
    """
    Build Blender world matrix for an exported glTF Empty anchor (`R_G2B @ M_g @ R_B2G`) so
    `export_yup=True` produces exact glTF local axes (-Z forward, +Y up, +X right).
    """
    m_g = _build_look_matrix_gltf(eye_g, target_g, up_g)
    return R_G2B.to_4x4() @ m_g @ R_B2G.to_4x4()


def look_at_blender_native(
    eye_g: Tuple[float, float, float],
    target_g: Tuple[float, float, float],
    up_g: Tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> Matrix:
    """
    Build Blender world matrix (`R_G2B @ M_g`) for native Blender Cameras & Lights, which
    emit/look along Blender local -Z with local +Y up and local +X right.
    """
    m_g = _build_look_matrix_gltf(eye_g, target_g, up_g)
    return R_G2B.to_4x4() @ m_g


# ---------------------------------------------------------------------------
# Architectural Mesh Builder (glTF Metric Coordinates -> Clean Manifold BMesh)
# ---------------------------------------------------------------------------


class ArchMesh:
    """Accumulates clean architectural geometry directly in glTF metric coordinates."""

    def __init__(self, name: str, uv_scale_meters: float = 4.0):
        self.name = name
        self.uv_scale = uv_scale_meters
        self.bm = bmesh.new()

    def add_quad_g(
        self,
        p0: Tuple[float, float, float],
        p1: Tuple[float, float, float],
        p2: Tuple[float, float, float],
        p3: Tuple[float, float, float],
    ) -> bmesh.types.BMFace:
        verts = [self.bm.verts.new(g2b_pt(*p)) for p in (p0, p1, p2, p3)]
        return self.bm.faces.new(verts)

    def add_box_g(
        self,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z0: float,
        z1: float,
        bevel: float = 0.0,
        skip_faces: Tuple[str, ...] = (),
    ) -> None:
        """
        Add an axis-aligned box in glTF coordinates [x0, x1] x [y0, y1] x [z0, z1]
        with outward-pointing normals and optional crisp 1-segment architectural edge bevel.
        """
        sub = bmesh.new()
        v000 = sub.verts.new(g2b_pt(x0, y0, z0))
        v100 = sub.verts.new(g2b_pt(x1, y0, z0))
        v101 = sub.verts.new(g2b_pt(x1, y0, z1))
        v001 = sub.verts.new(g2b_pt(x0, y0, z1))
        v010 = sub.verts.new(g2b_pt(x0, y1, z0))
        v110 = sub.verts.new(g2b_pt(x1, y1, z0))
        v111 = sub.verts.new(g2b_pt(x1, y1, z1))
        v011 = sub.verts.new(g2b_pt(x0, y1, z1))

        if "+y" not in skip_faces:
            sub.faces.new((v011, v111, v110, v010))
        if "-y" not in skip_faces:
            sub.faces.new((v000, v100, v101, v001))
        if "+z" not in skip_faces:
            sub.faces.new((v001, v101, v111, v011))
        if "-z" not in skip_faces:
            sub.faces.new((v100, v000, v010, v110))
        if "+x" not in skip_faces:
            sub.faces.new((v101, v100, v110, v111))
        if "-x" not in skip_faces:
            sub.faces.new((v000, v001, v011, v010))

        if bevel > 0.0 and not skip_faces:
            bmesh.ops.bevel(
                sub,
                geom=list(sub.edges),
                offset=bevel,
                offset_type="OFFSET",
                segments=1,
                profile=0.5,
                affect="EDGES",
            )
        self._append_bmesh(sub)
        sub.free()

    def add_hexahedron_g(
        self,
        b0: Tuple[float, float, float],
        b1: Tuple[float, float, float],
        b2: Tuple[float, float, float],
        b3: Tuple[float, float, float],
        t0: Tuple[float, float, float],
        t1: Tuple[float, float, float],
        t2: Tuple[float, float, float],
        t3: Tuple[float, float, float],
    ) -> None:
        """Closed 6-face manifold hexahedron with deterministically outward-recalculated normals."""
        sub = bmesh.new()
        vb = [sub.verts.new(g2b_pt(*p)) for p in (b0, b1, b2, b3)]
        vt = [sub.verts.new(g2b_pt(*p)) for p in (t0, t1, t2, t3)]
        sub.faces.new((vb[0], vb[3], vb[2], vb[1]))
        sub.faces.new((vt[0], vt[1], vt[2], vt[3]))
        sub.faces.new((vb[0], vb[1], vt[1], vt[0]))
        sub.faces.new((vb[1], vb[2], vt[2], vt[1]))
        sub.faces.new((vb[2], vb[3], vt[3], vt[2]))
        sub.faces.new((vb[3], vb[0], vt[0], vt[3]))
        bmesh.ops.recalc_face_normals(sub, faces=list(sub.faces))
        self._append_bmesh(sub)
        sub.free()

    def add_tapered_beam_x(
        self,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z_center: float,
        w_bottom: float,
        w_top: float,
        bevel: float = 0.0025,
    ) -> None:
        """Slender transverse skylight blade spanning X with subtle upward architectural taper."""
        sub = bmesh.new()
        hb = w_bottom * 0.5
        ht = w_top * 0.5
        v000 = sub.verts.new(g2b_pt(x0, y0, z_center - hb))
        v100 = sub.verts.new(g2b_pt(x1, y0, z_center - hb))
        v101 = sub.verts.new(g2b_pt(x1, y0, z_center + hb))
        v001 = sub.verts.new(g2b_pt(x0, y0, z_center + hb))
        v010 = sub.verts.new(g2b_pt(x0, y1, z_center - ht))
        v110 = sub.verts.new(g2b_pt(x1, y1, z_center - ht))
        v111 = sub.verts.new(g2b_pt(x1, y1, z_center + ht))
        v011 = sub.verts.new(g2b_pt(x0, y1, z_center + ht))
        sub.faces.new((v011, v111, v110, v010))
        sub.faces.new((v000, v100, v101, v001))
        sub.faces.new((v001, v101, v111, v011))
        sub.faces.new((v100, v000, v010, v110))
        sub.faces.new((v101, v100, v110, v111))
        sub.faces.new((v000, v001, v011, v010))
        if bevel > 0.0:
            bmesh.ops.bevel(
                sub,
                geom=list(sub.edges),
                offset=bevel,
                offset_type="OFFSET",
                segments=1,
                profile=0.5,
                affect="EDGES",
            )
        self._append_bmesh(sub)
        sub.free()

    def add_cylinder_segment_g(
        self,
        p0_g: Tuple[float, float, float],
        p1_g: Tuple[float, float, float],
        r0: float,
        r1: float,
        segments: int = 16,
        cap_start: bool = True,
        cap_end: bool = True,
    ) -> None:
        """Oriented cylinder/frustum from p0_g to p1_g in glTF space."""
        p0 = g2b_vec(p0_g)
        p1 = g2b_vec(p1_g)
        axis = p1 - p0
        length = axis.length
        if length < 1e-6:
            return
        z_dir = axis / length
        ref = Vector((1.0, 0.0, 0.0)) if abs(z_dir.x) < 0.9 else Vector((0.0, 1.0, 0.0))
        x_dir = z_dir.cross(ref).normalized()
        y_dir = z_dir.cross(x_dir).normalized()

        sub = bmesh.new()
        ring0 = []
        ring1 = []
        for i in range(segments):
            ang = (2.0 * math.pi * i) / segments
            ca, sa = math.cos(ang), math.sin(ang)
            ring0.append(sub.verts.new(p0 + (x_dir * ca + y_dir * sa) * r0))
            ring1.append(sub.verts.new(p1 + (x_dir * ca + y_dir * sa) * r1))

        for i in range(segments):
            j = (i + 1) % segments
            sub.faces.new((ring0[i], ring0[j], ring1[j], ring1[i]))

        if cap_start and r0 > 1e-5:
            c0 = sub.verts.new(p0)
            for i in range(segments):
                j = (i + 1) % segments
                sub.faces.new((c0, ring0[j], ring0[i]))
        if cap_end and r1 > 1e-5:
            c1 = sub.verts.new(p1)
            for i in range(segments):
                j = (i + 1) % segments
                sub.faces.new((c1, ring1[i], ring1[j]))

        self._append_bmesh(sub)
        sub.free()

    def _append_bmesh(self, sub: bmesh.types.BMesh) -> None:
        vert_map: Dict[int, bmesh.types.BMVert] = {}
        for i, v in enumerate(sub.verts):
            v.index = i
            vert_map[i] = self.bm.verts.new(v.co)
        for f in sub.faces:
            self.bm.faces.new([vert_map[v.index] for v in f.verts])

    def finalize(
        self,
        parent_obj: Optional[bpy.types.Object],
        collection: bpy.types.Collection,
        material: bpy.types.Material,
        smooth_angle_deg: float = 28.0,
    ) -> bpy.types.Object:
        bmesh.ops.remove_doubles(self.bm, verts=list(self.bm.verts), dist=1e-5)
        bmesh.ops.recalc_face_normals(self.bm, faces=list(self.bm.faces))

        # World-scale cubic box UV mapping in glTF metric space (1 UV unit = self.uv_scale meters)
        uv_layer = self.bm.loops.layers.uv.new("UVMap")
        inv_s = 1.0 / self.uv_scale
        for face in self.bm.faces:
            n_b = face.normal
            nx, ny, nz = n_b.x, n_b.z, -n_b.y
            ax, ay, az = abs(nx), abs(ny), abs(nz)
            for loop in face.loops:
                co_b = loop.vert.co
                gx, gy, gz = co_b.x, co_b.z, -co_b.y
                if ay >= ax and ay >= az:
                    u = (gx + HALF_W) * inv_s
                    v = (-gz + HALF_D) * inv_s
                elif az >= ax:
                    sign_x = 1.0 if nz >= 0.0 else -1.0
                    u = (sign_x * gx + HALF_W) * inv_s
                    v = gy * inv_s
                else:
                    sign_z = -1.0 if nx >= 0.0 else 1.0
                    u = (sign_z * gz + HALF_D) * inv_s
                    v = gy * inv_s
                loop[uv_layer].uv = (u, v)

        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()

        bm_sharp = bmesh.new()
        bm_sharp.from_mesh(mesh)
        cos_thresh = math.cos(math.radians(smooth_angle_deg))
        for f in bm_sharp.faces:
            f.smooth = True
        for e in bm_sharp.edges:
            if len(e.link_faces) == 2:
                if e.link_faces[0].normal.dot(e.link_faces[1].normal) < cos_thresh:
                    e.smooth = False
            else:
                e.smooth = False
        bm_sharp.to_mesh(mesh)
        bm_sharp.free()

        mesh.materials.append(material)
        obj = bpy.data.objects.new(self.name, mesh)
        if parent_obj is not None:
            obj.parent = parent_obj
        collection.objects.link(obj)
        return obj


# ---------------------------------------------------------------------------
# Architectural Geometry Construction (Stages A vs B/Final)
# ---------------------------------------------------------------------------


def build_floor(
    arch_parent: bpy.types.Object,
    col: bpy.types.Collection,
    mat_floor: bpy.types.Material,
    detailed: bool,
) -> bpy.types.Object:
    builder = ArchMesh("Floor", uv_scale_meters=4.8)
    if not detailed:
        builder.add_box_g(
            -HALF_W - WALL_THICK,
            HALF_W + WALL_THICK,
            -FLOOR_THICK,
            0.0,
            -HALF_D - WALL_THICK,
            HALF_D + PORTAL_DEPTH,
        )
        return builder.finalize(arch_parent, col, mat_floor)

    # Structural slab base (-0.32 m to -0.0026 m) spanning full building footprint + entrance portal
    joint_d = 0.0026  # 2.6 mm crisp saw-cut control joint bottom
    builder.add_box_g(
        -HALF_W - WALL_THICK,
        HALF_W + WALL_THICK,
        -FLOOR_THICK,
        -joint_d,
        -HALF_D - WALL_THICK,
        HALF_D + PORTAL_DEPTH,
    )

    # Poured, power-troweled museum concrete slabs (-0.0026 m to 0.000 m) with 2.8 mm micro-beveled control joints!
    # X cuts at [-12.03, -7.20, -2.80, +2.80, +7.20, +12.03] — note +-2.80 m aligns strictly with the 5.60 m entrance jambs!
    # Z cuts at [-9.03, -4.50, 0.00, +4.50, +9.03] plus continuous central portal threshold out to +10.60 m!
    gap = 0.0028
    hg = gap * 0.5
    ox = HALF_W + 0.03
    oz = HALF_D + 0.03
    x_cuts = [-ox, -7.20, -ENTRANCE_WIDTH * 0.5, ENTRANCE_WIDTH * 0.5, 7.20, ox]
    z_cuts = [-oz, -4.50, 0.00, 4.50, oz]

    # Subtle recessed flush floor access-box hatch detail in bay (-7.20..-2.80, 0.00..4.50) inspired by real galleries
    hatch_x0, hatch_x1 = -3.65, -3.39
    hatch_z0, hatch_z1 = 2.62, 2.88

    for ix in range(len(x_cuts) - 1):
        for iz in range(len(z_cuts) - 1):
            x0 = x_cuts[ix] + hg
            x1 = x_cuts[ix + 1] - hg
            z0 = z_cuts[iz] + hg
            z1 = z_cuts[iz + 1] - hg
            if ix == 1 and iz == 2:
                # Subdivide cleanly around the 260 x 260 mm flush concrete floor hatch inlay
                builder.add_box_g(x0, x1, -joint_d, 0.0, z0, hatch_z0 - hg, bevel=0.0008)
                builder.add_box_g(x0, x1, -joint_d, 0.0, hatch_z1 + hg, z1, bevel=0.0008)
                builder.add_box_g(x0, hatch_x0 - hg, -joint_d, 0.0, hatch_z0 + hg, hatch_z1 - hg, bevel=0.0008)
                builder.add_box_g(hatch_x1 + hg, x1, -joint_d, 0.0, hatch_z0 + hg, hatch_z1 - hg, bevel=0.0008)
                builder.add_box_g(hatch_x0 + hg, hatch_x1 - hg, -joint_d, 0.0, hatch_z0 + hg, hatch_z1 - hg, bevel=0.0008)
            else:
                builder.add_box_g(x0, x1, -joint_d, 0.0, z0, z1, bevel=0.0008)

    # Monumental entrance portal threshold slab (Z = +9.03 to +10.60, X = -2.80 to +2.80)
    builder.add_box_g(
        -ENTRANCE_WIDTH * 0.5 + hg,
        ENTRANCE_WIDTH * 0.5 - hg,
        -joint_d,
        0.0,
        oz + hg,
        HALF_D + PORTAL_DEPTH,
        bevel=0.0008,
    )

    return builder.finalize(arch_parent, col, mat_floor)


def build_walls_and_portal(
    arch_parent: bpy.types.Object,
    col: bpy.types.Collection,
    mat_wall: bpy.types.Material,
    mat_portal: bpy.types.Material,
    mat_trim: bpy.types.Material,
    detailed: bool,
) -> None:
    y_bot = BASE_REVEAL_H if detailed else 0.0
    # Left & Right exhibition walls rise seamlessly into the 9.76 m architectural side daylight coves,
    # while Rear & Entrance walls meet the floating ceiling canopy with a crisp 22 mm shadow reveal!
    y_cove_wall_top = COVE_TOP_Y if detailed else CEILING_HEIGHT
    y_end_wall_top = (CEILING_HEIGHT - TOP_WALL_REVEAL_H) if detailed else CEILING_HEIGHT
    bev = 0.0022 if detailed else 0.0
    corner_gap = 0.0018 if detailed else 0.0

    # 1. Wall_Back (Z = -9.40 to -9.00)
    wb = ArchMesh("Wall_Back", uv_scale_meters=4.8)
    wb.add_box_g(-HALF_W - WALL_THICK, HALF_W + WALL_THICK, 0.0, COVE_TOP_Y + 0.12, -HALF_D - WALL_THICK, -HALF_D - BASE_REVEAL_D)
    wb.add_box_g(-HALF_W + corner_gap, HALF_W - corner_gap, y_bot, y_end_wall_top, -HALF_D - BASE_REVEAL_D, -HALF_D, bevel=bev)
    # Upper rear cove closure inside left & right 680 mm side coves (Y = y_end_wall_top to COVE_TOP_Y)
    if detailed:
        wb.add_box_g(-HALF_W + corner_gap, -HALF_W + COVE_SIDE_W, y_end_wall_top, y_cove_wall_top, -HALF_D - BASE_REVEAL_D, -HALF_D)
        wb.add_box_g(HALF_W - COVE_SIDE_W, HALF_W - corner_gap, y_end_wall_top, y_cove_wall_top, -HALF_D - BASE_REVEAL_D, -HALF_D)
    wb.finalize(arch_parent, col, mat_wall)

    # 2. Wall_Left (X = -12.40 to -12.00)
    wl = ArchMesh("Wall_Left", uv_scale_meters=4.8)
    wl.add_box_g(-HALF_W - WALL_THICK, -HALF_W - BASE_REVEAL_D, 0.0, COVE_TOP_Y + 0.12, -HALF_D, HALF_D)
    wl.add_box_g(-HALF_W - BASE_REVEAL_D, -HALF_W, y_bot, y_cove_wall_top, -HALF_D + corner_gap, HALF_D - corner_gap, bevel=bev)
    wl.finalize(arch_parent, col, mat_wall)

    # 3. Wall_Right (X = +12.00 to +12.40)
    wr = ArchMesh("Wall_Right", uv_scale_meters=4.8)
    wr.add_box_g(HALF_W + BASE_REVEAL_D, HALF_W + WALL_THICK, 0.0, COVE_TOP_Y + 0.12, -HALF_D, HALF_D)
    wr.add_box_g(HALF_W, HALF_W + BASE_REVEAL_D, y_bot, y_cove_wall_top, -HALF_D + corner_gap, HALF_D - corner_gap, bevel=bev)
    wr.finalize(arch_parent, col, mat_wall)

    # 4. Wall_Entrance (Z = +9.00 to +10.60 with sculpted 1.60 m deep, 5.60 m x 4.80 m architectural portal)
    we = ArchMesh("Wall_Entrance", uv_scale_meters=4.8)
    ew = ENTRANCE_WIDTH * 0.5  # 2.80 m clear half-width
    eh = ENTRANCE_HEIGHT       # 4.80 m clear height
    ft = ENTRANCE_FRAME_T      # 0.055 m metal reveal liner
    ro_w = ew + (ft if detailed else 0.0)
    ro_h = eh + (ft if detailed else 0.0)

    # Left & Right structural piers (+9.024 to +10.60)
    we.add_box_g(-HALF_W - WALL_THICK, -ro_w, 0.0, COVE_TOP_Y + 0.12, HALF_D + BASE_REVEAL_D, HALF_D + PORTAL_DEPTH)
    we.add_box_g(ro_w, HALF_W + WALL_THICK, 0.0, COVE_TOP_Y + 0.12, HALF_D + BASE_REVEAL_D, HALF_D + PORTAL_DEPTH)
    # Interior exhibition plaster wings at Z = +9.000
    we.add_box_g(-HALF_W + corner_gap, -ew - (0.010 if detailed else 0.0), y_bot, y_end_wall_top, HALF_D, HALF_D + BASE_REVEAL_D, bevel=bev)
    we.add_box_g(ew + (0.010 if detailed else 0.0), HALF_W - corner_gap, y_bot, y_end_wall_top, HALF_D, HALF_D + BASE_REVEAL_D, bevel=bev)
    if detailed:
        # Upper front cove end-closures inside left & right 680 mm side coves
        we.add_box_g(-HALF_W + corner_gap, -HALF_W + COVE_SIDE_W, y_end_wall_top, y_cove_wall_top, HALF_D, HALF_D + BASE_REVEAL_D)
        we.add_box_g(HALF_W - COVE_SIDE_W, HALF_W - corner_gap, y_end_wall_top, y_cove_wall_top, HALF_D, HALF_D + BASE_REVEAL_D)
        # Inner plaster portal collar (Z = +9.024 to +9.54)
        we.add_box_g(-ro_w, -ew, y_bot, eh, HALF_D + BASE_REVEAL_D, HALF_D + 0.54, bevel=bev)
        we.add_box_g(ew, ro_w, y_bot, eh, HALF_D + BASE_REVEAL_D, HALF_D + 0.54, bevel=bev)
        we.add_box_g(-ro_w, ro_w, eh, ro_h, HALF_D + BASE_REVEAL_D, HALF_D + 0.54, bevel=bev)
        # Outer plaster portal collar (Z = +9.86 to +10.60)
        we.add_box_g(-ro_w, -ew, y_bot, eh, HALF_D + 0.86, HALF_D + PORTAL_DEPTH, bevel=bev)
        we.add_box_g(ew, ro_w, y_bot, eh, HALF_D + 0.86, HALF_D + PORTAL_DEPTH, bevel=bev)
        we.add_box_g(-ro_w, ro_w, eh, ro_h, HALF_D + 0.86, HALF_D + PORTAL_DEPTH, bevel=bev)
    # Lintel header above portal opening (Y = ro_h to ceiling)
    we.add_box_g(-ro_w, ro_w, ro_h, COVE_TOP_Y + 0.12, HALF_D + BASE_REVEAL_D, HALF_D + PORTAL_DEPTH)
    we.add_box_g(-ew - (0.010 if detailed else 0.0), ew + (0.010 if detailed else 0.0), eh + (0.010 if detailed else 0.0), y_end_wall_top, HALF_D, HALF_D + BASE_REVEAL_D, bevel=bev)
    we.finalize(arch_parent, col, mat_wall)

    # 5. Entrance_Frame (Refined anodized bronze-pewter portal threshold band & subtle shadow trim)
    ef = ArchMesh("Entrance_Frame", uv_scale_meters=1.5)
    f_bev = 0.0025 if detailed else 0.0
    if detailed:
        ef.add_box_g(-ro_w, -ew, 0.001, eh, HALF_D + 0.55, HALF_D + 0.85, bevel=f_bev)
        ef.add_box_g(ew, ro_w, 0.001, eh, HALF_D + 0.55, HALF_D + 0.85, bevel=f_bev)
        ef.add_box_g(-ro_w, ro_w, eh, ro_h, HALF_D + 0.55, HALF_D + 0.85, bevel=f_bev)
        ef.add_box_g(-ew - 0.010, -ew, 0.001, eh + 0.010, HALF_D + 0.002, HALF_D + BASE_REVEAL_D, bevel=0.001)
        ef.add_box_g(ew, ew + 0.010, 0.001, eh + 0.010, HALF_D + 0.002, HALF_D + BASE_REVEAL_D, bevel=0.001)
        ef.add_box_g(-ew - 0.010, ew + 0.010, eh, eh + 0.010, HALF_D + 0.002, HALF_D + BASE_REVEAL_D, bevel=0.001)
    else:
        ef.add_box_g(-ro_w, -ew, 0.001, eh, HALF_D, HALF_D + PORTAL_DEPTH)
        ef.add_box_g(ew, ro_w, 0.001, eh, HALF_D, HALF_D + PORTAL_DEPTH)
        ef.add_box_g(-ro_w, ro_w, eh, ro_h, HALF_D, HALF_D + PORTAL_DEPTH)
    ef.finalize(arch_parent, col, mat_portal)

    # 6. Wall_Floor_Transitions (Subtle 24 mm recessed base shadow-gap channel + front/rear ceiling shadow reveals)
    wt = ArchMesh("Wall_Floor_Transitions", uv_scale_meters=1.0)
    if detailed:
        t_th = 0.004
        wt.add_box_g(-HALF_W - BASE_REVEAL_D, HALF_W + BASE_REVEAL_D, 0.0005, BASE_REVEAL_H - 0.0005, -HALF_D - BASE_REVEAL_D, -HALF_D - BASE_REVEAL_D + t_th)
        wt.add_box_g(-HALF_W - BASE_REVEAL_D, -HALF_W - BASE_REVEAL_D + t_th, 0.0005, BASE_REVEAL_H - 0.0005, -HALF_D - BASE_REVEAL_D, HALF_D + BASE_REVEAL_D)
        wt.add_box_g(HALF_W + BASE_REVEAL_D - t_th, HALF_W + BASE_REVEAL_D, 0.0005, BASE_REVEAL_H - 0.0005, -HALF_D - BASE_REVEAL_D, HALF_D + BASE_REVEAL_D)
        wt.add_box_g(-HALF_W - BASE_REVEAL_D, -ew, 0.0005, BASE_REVEAL_H - 0.0005, HALF_D + BASE_REVEAL_D - t_th, HALF_D + BASE_REVEAL_D)
        wt.add_box_g(ew, HALF_W + BASE_REVEAL_D, 0.0005, BASE_REVEAL_H - 0.0005, HALF_D + BASE_REVEAL_D - t_th, HALF_D + BASE_REVEAL_D)
        # Rear & Entrance upper ceiling shadow-quirk liners (between -cx and +cx)
        cx = HALF_W - COVE_SIDE_W
        wt.add_box_g(-cx, cx, y_end_wall_top + 0.0005, CEILING_HEIGHT - 0.001, -HALF_D - TOP_WALL_REVEAL_D, -HALF_D - TOP_WALL_REVEAL_D + t_th)
        wt.add_box_g(-cx, cx, y_end_wall_top + 0.0005, CEILING_HEIGHT - 0.001, HALF_D + TOP_WALL_REVEAL_D - t_th, HALF_D + TOP_WALL_REVEAL_D)
    else:
        wt.add_box_g(-HALF_W, HALF_W, 0.0, 0.02, -HALF_D, -HALF_D + 0.015)
    wt.finalize(arch_parent, col, mat_trim)


def build_ceiling_and_skylight(
    arch_parent: bpy.types.Object,
    sky_parent: bpy.types.Object,
    col_arch: bpy.types.Collection,
    col_sky: bpy.types.Collection,
    mat_ceiling: bpy.types.Material,
    mat_beam: bpy.types.Material,
    mat_sky_frame: bpy.types.Material,
    mat_sky_glass: bpy.types.Material,
    detailed: bool,
) -> None:
    # 1. Ceiling: Floating architectural canopy (Y = 9.00 m) spanning cleanly from Wall_Back to Wall_Entrance,
    #    set back 680 mm from Wall_Left and Wall_Right to form two monumental full-length side daylight coves
    #    (Y = 9.00 m to 9.76 m), capped above by a light-tight structural roof slab (Y = 9.76 m to 10.68 m),
    #    and centered around a solid-manifold 1.68 m deep canted skylight well!
    cm = ArchMesh("Ceiling", uv_scale_meters=4.2)
    ox = HALF_W + WALL_THICK          # 12.40 m
    oz0 = -HALF_D - WALL_THICK        # -9.40 m
    oz1 = HALF_D + PORTAL_DEPTH       # +10.60 m
    y_soffit = CEILING_HEIGHT         #  9.000 m
    y_slot_top = CEILING_HEIGHT + TRACK_SLOT_D  # 9.072 m
    y_cove_top = COVE_TOP_Y           #  9.760 m
    y_roof_top = SKY_WELL_TOP_Y       # 10.680 m

    if not detailed:
        cm.add_box_g(-ox, ox, y_soffit, y_roof_top, oz0, -SKY_HALF_D)
        cm.add_box_g(-ox, ox, y_soffit, y_roof_top, SKY_HALF_D, oz1)
        cm.add_box_g(-ox, -SKY_HALF_W, y_soffit, y_roof_top, -SKY_HALF_D, SKY_HALF_D)
        cm.add_box_g(SKY_HALF_W, ox, y_soffit, y_roof_top, -SKY_HALF_D, SKY_HALF_D)
    else:
        ix, iz = SKY_HALF_W, SKY_HALF_D          # 6.80, 5.90 m at Y = 9.00 m
        wx = SKY_HALF_W + SKY_CANT               # 6.94 m at Y = 10.68 m
        wz = SKY_HALF_D + SKY_CANT               # 6.04 m at Y = 10.68 m
        bx = wx + 0.08                           # 7.02 m solid backing plane of canted skylight collar
        bz = wz + 0.08                           # 6.12 m solid backing plane of canted skylight collar

        cx = HALF_W - COVE_SIDE_W                # 11.32 m (680 mm clear of +-12.00 m side walls!)
        cz0 = -HALF_D - TOP_WALL_REVEAL_D        # -9.02 m (connects cleanly to Wall_Back!)
        cz1 = HALF_D + TOP_WALL_REVEAL_D         # +9.02 m (connects cleanly to Wall_Entrance!)

        # A. Light-tight structural upper roof slab (Y = 9.760 m to 10.680 m) outside [-bx, +bx] x [-bz, +bz]
        cm.add_box_g(-ox, ox, y_cove_top, y_roof_top, oz0, -bz)
        cm.add_box_g(-ox, ox, y_cove_top, y_roof_top, bz, oz1)
        cm.add_box_g(-ox, -bx, y_cove_top, y_roof_top, -bz, bz)
        cm.add_box_g(bx, ox, y_cove_top, y_roof_top, -bz, bz)

        # B. Middle floating canopy core (Y = 9.072 m to 9.760 m) spanning [-cx, +cx] x [cz0, cz1] around [-bx, +bx] x [-bz, +bz]
        cm.add_box_g(-cx, cx, y_slot_top, y_cove_top, cz0, -bz)
        cm.add_box_g(-cx, cx, y_slot_top, y_cove_top, bz, cz1)
        cm.add_box_g(-cx, -bx, y_slot_top, y_cove_top, -bz, bz)
        cm.add_box_g(bx, cx, y_slot_top, y_cove_top, -bz, bz)
        # Structural ceiling closure above rear wall & entrance portal
        cm.add_box_g(-ox, ox, y_soffit, y_cove_top, oz0, cz0)
        cm.add_box_g(-ox, ox, y_soffit, y_cove_top, cz1, oz1)

        # C. Lower ceiling soffit layer (Y = 9.000 m to 9.072 m) subdivided cleanly around the U-shaped recessed track slot!
        hs = TRACK_SLOT_W * 0.5                   # 0.038 m
        tx0, tx1 = TRACK_X - hs, TRACK_X + hs     # 9.022, 9.098
        tbz0, tbz1 = TRACK_BACK_Z - hs, TRACK_BACK_Z + hs  # -7.388, -7.312
        tz_end = TRACK_Z_END + hs                 # +6.838
        c_bev = 0.0025

        cm.add_box_g(-cx, cx, y_soffit, y_slot_top, cz0, tbz0, bevel=c_bev)
        cm.add_box_g(-cx, -tx1, y_soffit, y_slot_top, tbz0, cz1, bevel=c_bev)
        cm.add_box_g(tx1, cx, y_soffit, y_slot_top, tbz0, cz1, bevel=c_bev)
        cm.add_box_g(-tx1, tx1, y_soffit, y_slot_top, tz_end, cz1, bevel=c_bev)
        cm.add_box_g(-tx0, tx0, y_soffit, y_slot_top, tbz1, -bz)
        cm.add_box_g(-tx0, tx0, y_soffit, y_slot_top, bz, tz_end)
        cm.add_box_g(-tx0, -bx, y_soffit, y_slot_top, -bz, bz)
        cm.add_box_g(bx, tx0, y_soffit, y_slot_top, -bz, bz)

        # D. Four closed, solid-manifold mitered hexahedra forming the 1.68 m deep canted skylight daylight well!
        # North/Rear (-Z) canted wall solid
        cm.add_hexahedron_g(
            (-bx, y_soffit, -bz), (bx, y_soffit, -bz), (ix, y_soffit, -iz), (-ix, y_soffit, -iz),
            (-bx, y_roof_top, -bz), (bx, y_roof_top, -bz), (wx, y_roof_top, -wz), (-wx, y_roof_top, -wz),
        )
        # South/Entrance (+Z) canted wall solid
        cm.add_hexahedron_g(
            (-ix, y_soffit, iz), (ix, y_soffit, iz), (bx, y_soffit, bz), (-bx, y_soffit, bz),
            (-wx, y_roof_top, wz), (wx, y_roof_top, wz), (bx, y_roof_top, bz), (-bx, y_roof_top, bz),
        )
        # West/Left (-X) canted wall solid
        cm.add_hexahedron_g(
            (-bx, y_soffit, -bz), (-ix, y_soffit, -iz), (-ix, y_soffit, iz), (-bx, y_soffit, bz),
            (-bx, y_roof_top, -bz), (-wx, y_roof_top, -wz), (-wx, y_roof_top, wz), (-bx, y_roof_top, bz),
        )
        # East/Right (+X) canted wall solid
        cm.add_hexahedron_g(
            (ix, y_soffit, -iz), (bx, y_soffit, -bz), (bx, y_soffit, bz), (ix, y_soffit, iz),
            (wx, y_roof_top, -wz), (bx, y_roof_top, -bz), (bx, y_roof_top, bz), (wx, y_roof_top, wz),
        )

    cm.finalize(arch_parent, col_arch, mat_ceiling)

    # 2. Ceiling_Beams: 4 slender, rhythmic transverse architectural skylight blades dividing the 11.80 m well
    #    into 5 serene horizontal sky bays (Z = -3.54, -1.18, +1.18, +3.54 m), recessed mid-well (Y = 9.82 m to 10.60 m)!
    cb = ArchMesh("Ceiling_Beams", uv_scale_meters=2.5)
    beam_z_positions = (-3.54, -1.18, 1.18, 3.54)
    beam_y0 = 9.82
    beam_y1 = 10.60
    for bz in beam_z_positions:
        cb.add_tapered_beam_x(
            -SKY_HALF_W - 0.14,
            SKY_HALF_W + 0.14,
            beam_y0,
            beam_y1,
            bz,
            w_bottom=0.068,
            w_top=0.092,
            bevel=0.0025 if detailed else 0.0,
        )
    cb.finalize(arch_parent, col_arch, mat_beam)

    # 3. Skylight_Supports: Structural bearing ledger channels along the skylight curb sides (X = +-6.90 m)
    #    plus 2 ultra-slender 18 mm structural glass tension splines at X = -2.31, +2.31 m above the blades
    #    so the 5 transverse skylight bays read as pure, uninterrupted sky planes from below!
    ss = ArchMesh("Skylight_Supports", uv_scale_meters=2.0)
    wx = SKY_HALF_W + SKY_CANT   # 6.94 m
    wz = SKY_HALF_D + SKY_CANT   # 6.04 m
    # Perimeter longitudinal steel bearing channels at top of canted well
    ss.add_box_g(-wx - 0.02, -wx + 0.032, beam_y1, SKY_WELL_TOP_Y, -wz, wz, bevel=0.0015 if detailed else 0.0)
    ss.add_box_g(wx - 0.032, wx + 0.02, beam_y1, SKY_WELL_TOP_Y, -wz, wz, bevel=0.0015 if detailed else 0.0)
    sup_x_positions = (-2.31, 2.31)
    sup_hw = 0.009  # 18 mm low-profile structural glass spline
    for sx in sup_x_positions:
        ss.add_box_g(
            sx - sup_hw,
            sx + sup_hw,
            SKY_WELL_TOP_Y - 0.045,
            SKY_WELL_TOP_Y,
            -wz,
            wz,
        )
    ss.finalize(sky_parent, col_sky, mat_beam)

    # 4. Skylight_Frame: Powder-coated pale warm aluminum curb & 5-bay transverse glazing transoms + flush silicone joints
    sf = ArchMesh("Skylight_Frame", uv_scale_meters=1.5)
    curb_t = 0.22
    mull_hw = 0.028              # 56 mm transverse mullions aligned directly over the 4 Ceiling_Beams
    sil_hw = 0.008               # 16 mm flush structural-glazing silicone longitudinal joint
    f_bev = 0.002 if detailed else 0.0

    # Perimeter curb ring (Y = 10.68 to 10.90)
    sf.add_box_g(-wx - curb_t, wx + curb_t, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, -wz - curb_t, -wz + mull_hw, bevel=f_bev)
    sf.add_box_g(-wx - curb_t, wx + curb_t, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, wz - mull_hw, wz + curb_t, bevel=f_bev)
    sf.add_box_g(-wx - curb_t, -wx + mull_hw, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, -wz + mull_hw, wz - mull_hw, bevel=f_bev)
    sf.add_box_g(wx - mull_hw, wx + curb_t, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, -wz + mull_hw, wz - mull_hw, bevel=f_bev)

    # 4 continuous transverse aluminum glazing transoms directly above the 4 Ceiling_Beams
    for bz in beam_z_positions:
        sf.add_box_g(-wx + mull_hw, wx - mull_hw, SKY_WELL_TOP_Y, SKY_FRAME_TOP_Y, bz - mull_hw, bz + mull_hw, bevel=f_bev)

    # Subtle 16 mm structural silicone joint strips between the 3 glass panes per bay
    z_bay_edges = [
        -wz + mull_hw,
        -3.54 - mull_hw, -3.54 + mull_hw,
        -1.18 - mull_hw, -1.18 + mull_hw,
        1.18 - mull_hw, 1.18 + mull_hw,
        3.54 - mull_hw, 3.54 + mull_hw,
        wz - mull_hw,
    ]
    for sx in sup_x_positions:
        for iz_i in range(0, len(z_bay_edges), 2):
            sf.add_box_g(sx - sil_hw, sx + sil_hw, SKY_GLASS_Y0, SKY_GLASS_Y1 + 0.004, z_bay_edges[iz_i], z_bay_edges[iz_i + 1])
    sf.finalize(sky_parent, col_sky, mat_sky_frame)

    # 5. Skylight_Glass: 15 large laminated low-iron glazing panes combined into one semantic Skylight_Glass node
    sg = ArchMesh("Skylight_Glass", uv_scale_meters=2.5)
    gx_cuts = [-wx + mull_hw, -2.31 - sil_hw, -2.31 + sil_hw, 2.31 - sil_hw, 2.31 + sil_hw, wx - mull_hw]
    gz_cuts = z_bay_edges
    inset = 0.002
    for ix_i in range(0, len(gx_cuts), 2):
        for iz_i in range(0, len(gz_cuts), 2):
            sg.add_box_g(
                gx_cuts[ix_i] + inset,
                gx_cuts[ix_i + 1] - inset,
                SKY_GLASS_Y0,
                SKY_GLASS_Y1,
                gz_cuts[iz_i] + inset,
                gz_cuts[iz_i + 1] - inset,
            )
    sg.finalize(sky_parent, col_sky, mat_sky_glass)


def _add_semi_recessed_spotlight(
    mesh: ArchMesh,
    mount_x: float,
    mount_z: float,
    target_g: Tuple[float, float, float],
) -> None:
    """Compact semi-recessed architectural museum spotlight tucked cleanly inside the 72 mm ceiling slot."""
    # Track adapter stem recessed inside slot (Y = 9.055 down to 8.985)
    mesh.add_cylinder_segment_g((mount_x, 9.058, mount_z), (mount_x, 8.985, mount_z), 0.012, 0.012, segments=10)
    # Compact cylindrical snoot head pivoted at Y = 8.970 (projects only ~45 mm below Y = 9.00 m soffit!)
    pivot = Vector((mount_x, 8.970, mount_z))
    aim = (Vector(target_g) - pivot).normalized()
    rear = pivot - aim * 0.048
    front = pivot + aim * 0.068
    baffle_in = pivot + aim * 0.050
    mesh.add_cylinder_segment_g(
        (rear.x, rear.y, rear.z),
        (front.x, front.y, front.z),
        0.032,
        0.032,
        segments=14,
        cap_start=True,
        cap_end=False,
    )
    mesh.add_cylinder_segment_g(
        (front.x, front.y, front.z),
        (baffle_in.x, baffle_in.y, baffle_in.z),
        0.030,
        0.024,
        segments=14,
        cap_start=False,
        cap_end=True,
    )


def build_lighting_fixtures(
    fix_parent: bpy.types.Object,
    col_fix: bpy.types.Collection,
    mat_fixture: bpy.types.Material,
    detailed: bool,
) -> None:
    hs = TRACK_SLOT_W * 0.5  # 0.038 m
    # 1. Track_Back (Recessed track channel liner + 5 compact semi-recessed spotlights at Z = -7.20 m)
    tb = ArchMesh("Track_Back", uv_scale_meters=1.0)
    tb.add_box_g(-TRACK_X - hs, TRACK_X + hs, 9.040, 9.071, TRACK_BACK_Z - hs, TRACK_BACK_Z + hs)
    if detailed:
        for sx in (-6.40, -3.20, 0.00, 3.20, 6.40):
            _add_semi_recessed_spotlight(tb, sx, TRACK_BACK_Z, (sx, ARTWORK_CENTER_Y + 0.25, -HALF_D))
    tb.finalize(fix_parent, col_fix, mat_fixture)

    # 2. Track_Left (Recessed track channel liner + 5 compact semi-recessed spotlights at X = -9.10 m)
    tl = ArchMesh("Track_Left", uv_scale_meters=1.0)
    tl.add_box_g(-TRACK_X - hs, -TRACK_X + hs, 9.040, 9.071, TRACK_BACK_Z + hs + 0.001, TRACK_Z_END + hs)
    if detailed:
        for sz in (-5.20, -2.60, 0.00, 2.60, 5.20):
            _add_semi_recessed_spotlight(tl, -TRACK_X, sz, (-HALF_W, ARTWORK_CENTER_Y + 0.25, sz))
    tl.finalize(fix_parent, col_fix, mat_fixture)

    # 3. Track_Right (Recessed track channel liner + 5 compact semi-recessed spotlights at X = +9.10 m)
    tr = ArchMesh("Track_Right", uv_scale_meters=1.0)
    tr.add_box_g(TRACK_X - hs, TRACK_X + hs, 9.040, 9.071, TRACK_BACK_Z + hs + 0.001, TRACK_Z_END + hs)
    if detailed:
        for sz in (-5.20, -2.60, 0.00, 2.60, 5.20):
            _add_semi_recessed_spotlight(tr, TRACK_X, sz, (HALF_W, ARTWORK_CENTER_Y + 0.25, sz))
    tr.finalize(fix_parent, col_fix, mat_fixture)

    # 4. Recessed_Fixtures (10 discreet trimless pinhole downlight cones recessed flush at Y = 9.000 m)
    rf = ArchMesh("Recessed_Fixtures", uv_scale_meters=0.5)
    downlight_coords = [
        (-7.40, 7.80), (-3.70, 7.80), (3.70, 7.80), (7.40, 7.80),
        (-10.20, -7.80), (10.20, -7.80),
        (-10.20, -3.20), (-10.20, 3.20),
        (10.20, -3.20), (10.20, 3.20),
    ]
    for dx, dz in downlight_coords:
        rf.add_cylinder_segment_g((dx, 8.999, dz), (dx, 9.042, dz), 0.040, 0.028, segments=14, cap_start=False, cap_end=True)
    rf.finalize(fix_parent, col_fix, mat_fixture)


# ---------------------------------------------------------------------------
# Semantic Anchors Construction (Sections 13, 14, 15, 16)
# ---------------------------------------------------------------------------


def _new_empty(
    name: str,
    parent: Optional[bpy.types.Object],
    col: bpy.types.Collection,
    world_mat_b: Matrix,
    size: float = 0.25,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = size
    if parent is not None:
        obj.parent = parent
    obj.matrix_world = world_mat_b
    col.objects.link(obj)
    return obj


def build_all_anchors(
    root: bpy.types.Object,
    col_anchors: bpy.types.Collection,
) -> None:
    exh_grp = _new_empty("Exhibition_Anchors", root, col_anchors, Matrix.Identity(4), 0.4)
    lgt_grp = _new_empty("Lighting_Anchors", root, col_anchors, Matrix.Identity(4), 0.4)
    nav_grp = _new_empty("Navigation_Anchors", root, col_anchors, Matrix.Identity(4), 0.4)

    # 1. Nine Primary Wall-Mounted Artwork Anchors + Corresponding Spotlight & Navigation Anchors
    for spec in ARTWORK_SPECS:
        ax_x, ax_y, ax_z = spec["axes"]
        px, py, pz = spec["pos"]
        art_m = make_gltf_basis_matrix((px, py, pz), ax_x, ax_y, ax_z)
        art_obj = _new_empty(spec["name"], exh_grp, col_anchors, art_m, 0.35)
        art_obj["anchorRole"] = "artwork-mount"
        art_obj["targetWall"] = spec["wall"]
        art_obj["maxWidthMeters"] = spec["max_width"]
        art_obj["maxHeightMeters"] = spec["max_height"]
        art_obj["minBottomYMeters"] = ARTWORK_MIN_BOTTOM_Y
        art_obj["maxShiftedHeightMeters"] = ARTWORK_MAX_SHIFTED_H
        art_obj["recommendedClearanceMeters"] = spec["clearance"]

        tx, ty, tz = spec["track_pos"]
        lgt_m = look_at_gltf_basis((tx, ty, tz), (px, py, pz))
        lgt_obj = _new_empty(spec["light_name"], lgt_grp, col_anchors, lgt_m, 0.25)
        lgt_obj["anchorRole"] = "artwork-spotlight"
        lgt_obj["targetAnchor"] = spec["name"]

        nd = spec["nav_dist"]
        nx_pos = (px + ax_z[0] * nd, 1.60, pz + ax_z[2] * nd)
        nav_m = look_at_gltf_basis(nx_pos, (px, 1.55, pz))
        nav_obj = _new_empty(spec["nav_name"], nav_grp, col_anchors, nav_m, 0.30)
        nav_obj["anchorRole"] = "artwork-viewpoint"
        nav_obj["targetAnchor"] = spec["name"]

    # 2. Additional Optional Floor Placement Anchors (Section 14)
    for pname, ppos, pfront in PLACEMENT_SPECS:
        up = (0.0, 1.0, 0.0)
        zf = Vector(pfront).normalized()
        xf = Vector(up).cross(zf).normalized()
        pm = make_gltf_basis_matrix(ppos, (xf.x, xf.y, xf.z), up, (zf.x, zf.y, zf.z))
        p_obj = _new_empty(pname, exh_grp, col_anchors, pm, 0.30)
        p_obj["anchorRole"] = "floor-placement"

    # 3. Additional Lighting Anchors (Central installation accents + Perimeter evening ambient fill)
    extra_lights = [
        ("Anchor_Light_Center_01", (-3.40, 8.95, 0.00), (0.00, 1.00, -0.60)),
        ("Anchor_Light_Center_02", (3.40, 8.95, 0.00), (0.00, 1.00, -0.60)),
        ("Anchor_Light_Ambient_01", (-7.40, 8.95, 7.80), (-7.40, 0.00, 7.80)),
        ("Anchor_Light_Ambient_02", (7.40, 8.95, 7.80), (7.40, 0.00, 7.80)),
        ("Anchor_Light_Ambient_03", (-10.20, 8.95, -7.80), (-10.20, 0.00, -7.80)),
        ("Anchor_Light_Ambient_04", (10.20, 8.95, -7.80), (10.20, 0.00, -7.80)),
    ]
    for lname, lpos, ltgt in extra_lights:
        lm = look_at_gltf_basis(lpos, ltgt)
        lo = _new_empty(lname, lgt_grp, col_anchors, lm, 0.25)
        lo["anchorRole"] = "architectural-light"

    # 4. Primary Hall Navigation Anchors (Section 15 — Eye height Y = 1.60 m)
    primary_navs = [
        ("Anchor_Navigation_Entrance", (0.00, 1.60, 8.20), (0.00, 1.60, -9.00)),
        ("Anchor_Navigation_Center", (0.00, 1.60, 1.50), (0.00, 1.60, -9.00)),
        ("Anchor_Navigation_Back", (0.00, 1.60, -4.20), (0.00, 1.60, -9.00)),
        ("Anchor_Navigation_Left", (-6.20, 1.60, 0.00), (-12.00, 1.60, 0.00)),
        ("Anchor_Navigation_Right", (6.20, 1.60, 0.00), (12.00, 1.60, 0.00)),
    ]
    for nname, npos, ntgt in primary_navs:
        nm = look_at_gltf_basis(npos, ntgt)
        no = _new_empty(nname, nav_grp, col_anchors, nm, 0.35)
        no["anchorRole"] = "hall-navigation"


# ---------------------------------------------------------------------------
# Coherent Periodic PBR Texture Synthesis (Stage C)
# ---------------------------------------------------------------------------


def ensure_pbr_textures(force: bool = False) -> Dict[str, Path]:
    """
    Deterministically synthesize coherent, strictly tileable PBR texture maps in `TEX_DIR`.
    Derived from physical band-limited periodic height & trowel-burnish fields:
      - OpenGL (+Y) tangent-space normal maps
      - Spatially aligned roughness maps (including authentic power-troweled satin concrete sheen!)
      - Strictly neutral near-white mineral clouding basecolor maps so `material.color` recoloring works cleanly.
    """
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    expected = {
        "plaster_basecolor": TEX_DIR / "wall_plaster_basecolor.png",
        "plaster_normal": TEX_DIR / "wall_plaster_normal.png",
        "plaster_roughness": TEX_DIR / "wall_plaster_roughness.png",
        "concrete_basecolor": TEX_DIR / "floor_concrete_basecolor.png",
        "concrete_normal": TEX_DIR / "floor_concrete_normal.png",
        "concrete_roughness": TEX_DIR / "floor_concrete_roughness.png",
        "ceiling_normal": TEX_DIR / "ceiling_plaster_normal.png",
    }
    if not force and all(p.exists() for p in expected.values()):
        return expected

    import numpy as np
    import zlib
    import struct as pystruct

    def write_png_u8(path: Path, arr: "np.ndarray") -> None:
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        if arr.ndim == 2:
            h, w = arr.shape
            color_type = 0
        else:
            h, w, c = arr.shape
            color_type = 2 if c == 3 else 6
        raw_rows = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (
                pystruct.pack(">I", len(data))
                + tag
                + data
                + pystruct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
            )

        ihdr = pystruct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0)
        png_bytes = (
            b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw_rows, level=6))
            + chunk(b"IEND", b"")
        )
        path.write_bytes(png_bytes)

    def periodic_fbm(res: int, seed: int, freq_weights: Sequence[Tuple[int, float]]) -> "np.ndarray":
        rng = np.random.default_rng(seed)
        spec = np.zeros((res, res), dtype=np.complex128)
        ky = np.fft.fftfreq(res) * res
        kx = np.fft.fftfreq(res) * res
        KX, KY = np.meshgrid(kx, ky)
        KR = np.sqrt(KX * KX + KY * KY)

        for k_center, weight in freq_weights:
            bw = max(1.1, k_center * 0.45)
            env = np.exp(-0.5 * ((KR - k_center) / bw) ** 2)
            env[0, 0] = 0.0
            phase = rng.uniform(0.0, 2.0 * np.pi, size=(res, res))
            amp = rng.normal(1.0, 0.24, size=(res, res))
            spec += weight * env * amp * (np.cos(phase) + 1j * np.sin(phase))

        field = np.fft.ifft2(spec).real
        std = float(np.std(field))
        if std > 1e-9:
            field /= std
        return field

    def height_to_normal_rgb(height: "np.ndarray", strength: float) -> "np.ndarray":
        dh_dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * strength
        dh_dv = -(np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5 * strength
        nx = -dh_dx
        ny = -dh_dv
        nz = np.ones_like(height)
        inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
        return np.stack(
            [
                (nx * inv_len * 0.5 + 0.5) * 255.0,
                (ny * inv_len * 0.5 + 0.5) * 255.0,
                (nz * inv_len * 0.5 + 0.5) * 255.0,
            ],
            axis=-1,
        )

    def box2x2(a: "np.ndarray") -> "np.ndarray":
        return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])

    # 1. Museum Lime-Mineral Wall Plaster (4.80 m UV repeat: subtle organic tonal clouding + fine matte grain)
    res_p = 1024
    h_p_macro = periodic_fbm(res_p, seed=111, freq_weights=[(1, 0.70), (2, 0.55), (5, 0.35), (12, 0.25)])
    h_p_micro = periodic_fbm(res_p, seed=112, freq_weights=[(32, 0.45), (78, 0.55), (175, 0.50)])
    h_plaster = 0.45 * h_p_macro + 0.55 * h_p_micro
    n_plaster = height_to_normal_rgb(h_plaster, strength=0.11)

    hm512 = box2x2(h_p_macro)
    hi512 = box2x2(h_p_micro)
    # Neutral near-white mineral clouding [249..255] so walls have subtle lime-mineral depth without mottling
    p_lum = 0.987 + 0.008 * np.tanh(0.70 * hm512 + 0.30 * hi512)
    p_warm = 0.0015 * np.tanh(hm512)
    p_rgb = np.stack([(p_lum + p_warm) * 255.0, p_lum * 255.0, (p_lum - p_warm) * 255.0], axis=-1)
    r_plaster = (0.86 - 0.035 * np.tanh(0.65 * hm512 + 0.35 * hi512)) * 255.0

    write_png_u8(expected["plaster_basecolor"], p_rgb)
    write_png_u8(expected["plaster_normal"], n_plaster)
    write_png_u8(expected["plaster_roughness"], r_plaster)

    # 2. Power-Troweled Honed Architectural Concrete Floor (4.80 m UV repeat: silky satin Fresnel reflections!)
    res_c = 1024
    h_cloud = periodic_fbm(res_c, seed=212, freq_weights=[(1, 0.75), (2, 0.55), (4, 0.35), (8, 0.20)])
    h_trowel = periodic_fbm(res_c, seed=213, freq_weights=[(3, 0.55), (7, 0.45), (18, 0.30)])
    h_micro = periodic_fbm(res_c, seed=214, freq_weights=[(48, 0.35), (112, 0.42), (220, 0.38)])
    pores = np.minimum(0.0, h_micro + 1.85) * 0.22
    h_conc = 0.55 * h_cloud + 0.25 * h_trowel + 0.20 * h_micro + pores
    n_conc = height_to_normal_rgb(h_conc, strength=0.075)

    hc512 = box2x2(h_cloud)
    ht512 = box2x2(h_trowel)
    hm512_c = box2x2(h_micro)

    # Neutral near-white mineral clouding [235..253] multiplied by baseColorFactor (#B4B0A8)
    c_lum = 0.958 + 0.030 * np.tanh(0.65 * hc512 + 0.25 * ht512 + 0.15 * hm512_c)
    c_warm = 0.0045 * np.tanh(hc512 - 0.3 * ht512)
    c_rgb = np.stack([(c_lum + c_warm) * 255.0, c_lum * 255.0, (c_lum - c_warm * 1.1) * 255.0], axis=-1)

    # Authentic power-troweled museum concrete roughness (1024x1024): 0.245 on burnished trowel sweeps
    # to 0.375 in matte mineral clouds (mean ~0.305) -> soft, realistic skylight & artwork floor reflections!
    r_conc = (
        0.305
        - 0.052 * np.tanh(0.60 * h_trowel + 0.45 * h_cloud)
        + 0.018 * np.tanh(h_micro)
        - 0.045 * pores
    ) * 255.0

    write_png_u8(expected["concrete_basecolor"], c_rgb)
    write_png_u8(expected["concrete_normal"], n_conc)
    write_png_u8(expected["concrete_roughness"], r_conc)

    # 3. Warm Acoustic Mineral Ceiling Plaster (4.20 m UV repeat)
    res_ceil = 512
    h_ceil = periodic_fbm(res_ceil, seed=313, freq_weights=[(2, 0.40), (8, 0.35), (26, 0.45), (72, 0.55), (150, 0.50)])
    n_ceil = height_to_normal_rgb(h_ceil, strength=0.11)
    write_png_u8(expected["ceiling_normal"], n_ceil)

    return expected


# ---------------------------------------------------------------------------
# Semantic PBR Materials (Section 10 & Section 12)
# ---------------------------------------------------------------------------


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def hex_rgba(hex_str: str, alpha: float = 1.0) -> Tuple[float, float, float, float]:
    h = hex_str.lstrip("#")
    r = _srgb_to_linear(int(h[0:2], 16) / 255.0)
    g = _srgb_to_linear(int(h[2:4], 16) / 255.0)
    b = _srgb_to_linear(int(h[4:6], 16) / 255.0)
    return (r, g, b, alpha)


def _load_img(path: Path, non_color: bool) -> bpy.types.Image:
    img = bpy.data.images.load(str(path), check_existing=True)
    img.colorspace_settings.name = "Non-Color" if non_color else "sRGB"
    return img


def _ensure_nodes(id_block) -> bpy.types.NodeTree:
    if getattr(id_block, "node_tree", None) is None:
        id_block.use_nodes = True
    return id_block.node_tree


def create_materials(clay_mode: bool, force_textures: bool = False) -> Dict[str, bpy.types.Material]:
    """Create the 9 stable semantic material slots."""
    names = [
        "Mat_Wall_Plaster",
        "Mat_Floor_Concrete",
        "Mat_Ceiling",
        "Mat_Structural_Beam",
        "Mat_Skylight_Frame",
        "Mat_Skylight_Glass",
        "Mat_Entrance_Frame",
        "Mat_Lighting_Fixture",
        "Mat_Trim",
    ]
    mats: Dict[str, bpy.types.Material] = {}

    if clay_mode:
        for nm in names:
            m = bpy.data.materials.new(nm)
            nt = _ensure_nodes(m)
            bsdf = nt.nodes.get("Principled BSDF")
            if nm == "Mat_Skylight_Glass":
                if hasattr(m, "surface_render_method"):
                    m.surface_render_method = "BLENDED"
                bsdf.inputs["Base Color"].default_value = hex_rgba("#EAECEF", 0.06)
                bsdf.inputs["Alpha"].default_value = 0.05
                bsdf.inputs["Roughness"].default_value = 0.08
                lp = nt.nodes.new("ShaderNodeLightPath")
                tr = nt.nodes.new("ShaderNodeBsdfTransparent")
                mx = nt.nodes.new("ShaderNodeMixShader")
                out = nt.nodes.get("Material Output")
                nt.links.new(lp.outputs["Is Shadow Ray"], mx.inputs["Fac"])
                nt.links.new(bsdf.outputs["BSDF"], mx.inputs[1])
                nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
                nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
            else:
                tone = "#DFDAD0" if nm != "Mat_Floor_Concrete" else "#D0C9BD"
                bsdf.inputs["Base Color"].default_value = hex_rgba(tone)
                bsdf.inputs["Roughness"].default_value = 0.84
                bsdf.inputs["Metallic"].default_value = 0.0
            mats[nm] = m
        return mats

    tex = ensure_pbr_textures(force=force_textures)

    def make_textured_pbr(
        name: str,
        base_hex: str,
        metallic: float,
        roughness: float,
        base_map: Optional[Path] = None,
        rough_map: Optional[Path] = None,
        norm_map: Optional[Path] = None,
        norm_strength: float = 0.25,
        ior: float = 1.48,
    ) -> bpy.types.Material:
        m = bpy.data.materials.new(name)
        nt = _ensure_nodes(m)
        bsdf = nt.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = hex_rgba(base_hex)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = ior

        if base_map is not None:
            tex_c = nt.nodes.new("ShaderNodeTexImage")
            tex_c.image = _load_img(base_map, non_color=False)
            mix_n = nt.nodes.new("ShaderNodeMix")
            mix_n.data_type = "RGBA"
            mix_n.blend_type = "MULTIPLY"
            mix_n.inputs["Factor"].default_value = 1.0
            mix_n.inputs["B"].default_value = hex_rgba(base_hex)
            nt.links.new(tex_c.outputs["Color"], mix_n.inputs["A"])
            nt.links.new(mix_n.outputs["Result"], bsdf.inputs["Base Color"])

        if rough_map is not None:
            tex_r = nt.nodes.new("ShaderNodeTexImage")
            tex_r.image = _load_img(rough_map, non_color=True)
            nt.links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

        if norm_map is not None:
            tex_n = nt.nodes.new("ShaderNodeTexImage")
            tex_n.image = _load_img(norm_map, non_color=True)
            nmap = nt.nodes.new("ShaderNodeNormalMap")
            nmap.inputs["Strength"].default_value = norm_strength
            nt.links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
            nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

        return m

    # 1. Mat_Wall_Plaster — Warm museum lime-mineral plaster (#F3EFE7), matte with subtle clouding
    mats["Mat_Wall_Plaster"] = make_textured_pbr(
        "Mat_Wall_Plaster",
        base_hex="#F3EFE7",
        metallic=0.0,
        roughness=0.86,
        base_map=tex["plaster_basecolor"],
        rough_map=tex["plaster_roughness"],
        norm_map=tex["plaster_normal"],
        norm_strength=0.22,
        ior=1.46,
    )

    # 2. Mat_Floor_Concrete — Power-troweled honed architectural concrete (#B4B0A8) with calm satin reflections
    mats["Mat_Floor_Concrete"] = make_textured_pbr(
        "Mat_Floor_Concrete",
        base_hex="#B4B0A8",
        metallic=0.0,
        roughness=0.30,
        base_map=tex["concrete_basecolor"],
        rough_map=tex["concrete_roughness"],
        norm_map=tex["concrete_normal"],
        norm_strength=0.14,
        ior=1.52,
    )

    # 3. Mat_Ceiling — Serene warm limestone-mineral floating canopy soffit (#E9E4DA) for subtle tectonic contrast
    mats["Mat_Ceiling"] = make_textured_pbr(
        "Mat_Ceiling",
        base_hex="#E9E4DA",
        metallic=0.0,
        roughness=0.88,
        base_map=tex["plaster_basecolor"],
        norm_map=tex["ceiling_normal"],
        norm_strength=0.20,
        ior=1.46,
    )

    # 4. Mat_Structural_Beam — Crisp warm-white painted architectural skylight blades (#F5F2EB)
    mats["Mat_Structural_Beam"] = make_textured_pbr(
        "Mat_Structural_Beam",
        base_hex="#F5F2EB",
        metallic=0.08,
        roughness=0.56,
        norm_map=tex["ceiling_normal"],
        norm_strength=0.10,
    )

    # 5. Mat_Skylight_Frame — Powder-coated pale warm aluminum mullions (#DCD8D0)
    mats["Mat_Skylight_Frame"] = make_textured_pbr(
        "Mat_Skylight_Frame",
        base_hex="#DCD8D0",
        metallic=0.36,
        roughness=0.38,
    )

    # 6. Mat_Skylight_Glass — Clear low-iron architectural glazing with real-time glTF BLEND compatibility
    mg = bpy.data.materials.new("Mat_Skylight_Glass")
    nt = _ensure_nodes(mg)
    if hasattr(mg, "surface_render_method"):
        mg.surface_render_method = "BLENDED"
    elif hasattr(mg, "blend_method"):
        mg.blend_method = "BLEND"
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = hex_rgba("#EEF5FA", 1.0)
    bsdf.inputs["Metallic"].default_value = 0.04
    bsdf.inputs["Roughness"].default_value = 0.07
    bsdf.inputs["Alpha"].default_value = 0.14
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.52
    mats["Mat_Skylight_Glass"] = mg

    # 7. Mat_Entrance_Frame — Anodized warm pewter-bronze architectural portal liner (#524E49)
    mats["Mat_Entrance_Frame"] = make_textured_pbr(
        "Mat_Entrance_Frame",
        base_hex="#524E49",
        metallic=0.42,
        roughness=0.38,
    )

    # 8. Mat_Lighting_Fixture — Refined architectural dark graphite track & semi-recessed spotlight housing (#302E2C)
    mats["Mat_Lighting_Fixture"] = make_textured_pbr(
        "Mat_Lighting_Fixture",
        base_hex="#302E2C",
        metallic=0.38,
        roughness=0.42,
    )

    # 9. Mat_Trim — Subtle recessed shadow-gap reveal channel liner (#3C3935)
    mats["Mat_Trim"] = make_textured_pbr(
        "Mat_Trim",
        base_hex="#3C3935",
        metallic=0.25,
        roughness=0.52,
    )

    return mats


# ---------------------------------------------------------------------------
# Cycles Render Engine, Lighting Scenarios (A, B, C), & Temporary Exhibition (Stage E)
# ---------------------------------------------------------------------------


def configure_cycles(samples: int = 96, res_x: int = 1600, res_y: int = 1000) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 10
    scene.cycles.diffuse_bounces = 5
    scene.cycles.glossy_bounces = 4
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 8

    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"

    scene.render.resolution_x = res_x
    scene.render.resolution_y = res_y
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Base Contrast"
    scene.view_settings.exposure = 0.0


def setup_lighting_scenario(
    scenario: str,
    col_studio: bpy.types.Collection,
) -> None:
    """
    Configure Blender authoring lighting scenario in `Studio_Preview` collection (excluded from GLB).
    Scenarios:
      - 'soft_daylight' : Scenario A — luminous diffused skylight + perimeter cove daylight wash
      - 'direct_sun'    : Scenario B — sculpted angled sunlight through the 5-bay skylight coffer + sky fill
      - 'evening'       : Scenario C — twilight sky + warm perimeter cove grazing + 3000K gallery spotlights
    """
    for obj in list(col_studio.objects):
        if obj.type in ("LIGHT", "MESH") and obj.name.startswith("Studio_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    glass_obj = bpy.data.objects.get("Skylight_Glass")
    if glass_obj is not None and hasattr(glass_obj, "visible_shadow"):
        glass_obj.visible_shadow = False

    # Serene adjacent museum foyer / vestibule beyond the +Z entrance portal (authoring backdrop only)
    foyer_floor = ArchMesh("Studio_Foyer_Floor", uv_scale_meters=4.8)
    foyer_floor.add_box_g(-14.0, 14.0, -0.32, 0.0, HALF_D + PORTAL_DEPTH, 21.0)
    mat_floor_ref = bpy.data.materials.get("Mat_Floor_Concrete")
    foyer_floor.finalize(None, col_studio, mat_floor_ref)

    foyer_walls = ArchMesh("Studio_Foyer_Walls", uv_scale_meters=4.8)
    foyer_walls.add_box_g(-14.0, 14.0, 0.0, 9.6, 20.6, 21.0)
    foyer_walls.add_box_g(-14.0, -9.5, 0.0, 9.6, HALF_D + PORTAL_DEPTH, 20.6)
    foyer_walls.add_box_g(9.5, 14.0, 0.0, 9.6, HALF_D + PORTAL_DEPTH, 20.6)
    mat_wall_ref = bpy.data.materials.get("Mat_Wall_Plaster")
    foyer_walls.finalize(None, col_studio, mat_wall_ref)

    world = bpy.context.scene.world or bpy.data.worlds.new("Museum_World")
    bpy.context.scene.world = world
    wnt = _ensure_nodes(world)
    wnt.nodes.clear()
    bg = wnt.nodes.new("ShaderNodeBackground")
    wout = wnt.nodes.new("ShaderNodeOutputWorld")

    def add_area_light(
        name: str,
        pos_g: Tuple[float, float, float],
        target_g: Tuple[float, float, float],
        energy: float,
        size_x: float,
        size_y: float,
        color_hex: str,
        spread_deg: float = 135.0,
        camera_visible: bool = False,
        up_g: Tuple[float, float, float] = (0.0, 1.0, 0.0),
    ) -> None:
        ld = bpy.data.lights.new(name, type="AREA")
        ld.shape = "RECTANGLE"
        ld.size = size_x
        ld.size_y = size_y
        ld.energy = energy
        ld.color = hex_rgba(color_hex)[:3]
        if hasattr(ld, "spread"):
            ld.spread = math.radians(spread_deg)
        lo = bpy.data.objects.new(name, ld)
        lo.matrix_world = look_at_blender_native(pos_g, target_g, up_g=up_g)
        if hasattr(lo, "visible_camera"):
            lo.visible_camera = camera_visible
        col_studio.objects.link(lo)

    def add_spot_light(
        name: str,
        pos_g: Tuple[float, float, float],
        target_g: Tuple[float, float, float],
        energy: float,
        spot_deg: float,
        blend: float,
        color_hex: str,
        radius: float = 0.045,
    ) -> None:
        ld = bpy.data.lights.new(name, type="SPOT")
        ld.energy = energy
        ld.spot_size = math.radians(spot_deg)
        ld.spot_blend = blend
        ld.shadow_soft_size = radius
        ld.color = hex_rgba(color_hex)[:3]
        lo = bpy.data.objects.new(name, ld)
        lo.matrix_world = look_at_blender_native(pos_g, target_g)
        col_studio.objects.link(lo)

    def add_perimeter_cove_grazers(energy_side: float, color_hex: str) -> None:
        """Concealed natural daylight / evening grazing wash inside the Left & Right 680 mm architectural coves."""
        # Pass `up_g=(1.0, 0.0, 0.0)` so local +X (`size_x = 17.4 m`) aligns strictly with world Z along the side walls!
        add_area_light("Studio_Cove_Left", (-11.66, 9.68, 0.0), (-11.86, 2.0, 0.0), energy_side, 17.4, 0.48, color_hex, spread_deg=140.0, up_g=(1.0, 0.0, 0.0))
        add_area_light("Studio_Cove_Right", (11.66, 9.68, 0.0), (11.86, 2.0, 0.0), energy_side, 17.4, 0.48, color_hex, spread_deg=140.0, up_g=(-1.0, 0.0, 0.0))

    if scenario == "soft_daylight":
        # Luminous calm overcast-zenith sky visible overhead through the 5-bay skylight coffer!
        bg.inputs["Color"].default_value = hex_rgba("#EBF1F8")
        bg.inputs["Strength"].default_value = 2.40
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        # Primary diffused sky plane above skylight glazing (Y = 11.35 m)
        add_area_light(
            "Studio_Skylight_Soft_Dome",
            (0.0, 11.35, 0.0),
            (0.0, 0.0, -0.4),
            energy=3800.0,
            size_x=13.6,
            size_y=11.8,
            color_hex="#F7F9FC",
            spread_deg=134.0,
        )
        # Soft side-cove clerestory sky bounce washing gently down Wall_Left and Wall_Right!
        add_perimeter_cove_grazers(energy_side=680.0, color_hex="#F4F6FA")
        # Bright sunlit foyer beyond the +Z entrance portal
        add_area_light("Studio_Foyer_Daylight", (0.0, 8.8, 15.2), (0.0, 0.0, 11.5), energy=2200.0, size_x=12.0, size_y=6.0, color_hex="#F9F7F1", spread_deg=135.0)
        bpy.context.scene.view_settings.exposure = -0.22

    elif scenario == "direct_sun":
        bg.inputs["Color"].default_value = hex_rgba("#DCE8F6")
        bg.inputs["Strength"].default_value = 1.95
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        add_area_light(
            "Studio_Skylight_SkyFill",
            (0.0, 11.50, 0.0),
            (0.0, 0.0, 0.0),
            energy=1950.0,
            size_x=13.6,
            size_y=11.8,
            color_hex="#ECF3FC",
            spread_deg=140.0,
        )
        add_perimeter_cove_grazers(energy_side=480.0, color_hex="#F2F5FA")
        add_area_light("Studio_Foyer_SunFill", (0.0, 8.8, 15.2), (0.0, 0.0, 11.5), energy=1800.0, size_x=12.0, size_y=6.0, color_hex="#FFF9EE", spread_deg=135.0)

        # Controlled directional sunlight raking diagonally through the 5-bay transverse skylight blades
        sun_d = bpy.data.lights.new("Studio_Direct_Sun", type="SUN")
        sun_d.energy = 3.20
        sun_d.angle = math.radians(1.25)
        sun_d.color = hex_rgba("#FFF4E2")[:3]
        sun_o = bpy.data.objects.new("Studio_Direct_Sun", sun_d)
        sun_o.matrix_world = look_at_blender_native((6.6, 15.5, 4.2), (-2.6, 0.0, -2.4))
        col_studio.objects.link(sun_o)
        bpy.context.scene.view_settings.exposure = -0.32

    elif scenario == "evening":
        bg.inputs["Color"].default_value = hex_rgba("#162338")
        bg.inputs["Strength"].default_value = 0.55
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        add_area_light(
            "Studio_Twilight_Skylight",
            (0.0, 11.30, 0.0),
            (0.0, 0.0, 0.0),
            energy=240.0,
            size_x=13.4,
            size_y=11.6,
            color_hex="#92ACD0",
            spread_deg=145.0,
        )
        # Warm 2950K architectural cove grazing along Left & Right floating canopy side coves
        add_perimeter_cove_grazers(energy_side=320.0, color_hex="#FFEAD0")

        # Selective 3000K gallery track spotlights aimed at all 9 exhibition anchors
        for spec in ARTWORK_SPECS:
            tx, ty, tz = spec["track_pos"]
            px, py, pz = spec["pos"]
            add_spot_light(
                f"Studio_Spot_{spec['name']}",
                (tx, ty - 0.04, tz),
                (px, py + 0.04, pz),
                energy=780.0,
                spot_deg=38.0,
                blend=0.48,
                color_hex="#FFEDD6",
            )
        # Subtle warm central gallery circulation glow & foyer evening glow
        add_area_light("Studio_Evening_Ambient", (0.0, 8.85, 0.0), (0.0, 0.0, 0.0), energy=360.0, size_x=8.5, size_y=6.5, color_hex="#FFEED8", spread_deg=135.0)
        add_area_light("Studio_Foyer_Evening", (0.0, 8.5, 14.5), (0.0, 0.0, 11.5), energy=420.0, size_x=9.0, size_y=4.5, color_hex="#FFEBD2", spread_deg=130.0)
        bpy.context.scene.view_settings.exposure = 0.12


# ---------------------------------------------------------------------------
# Temporary 9-Artwork Exhibition Demonstration (Stage E — Never Exported to GLB)
# ---------------------------------------------------------------------------


def ensure_demo_artworks(demo_dir: Path) -> List[Path]:
    """Generate 9 museum-caliber contemporary abstract & luminous color-field paintings of varied aspect ratios."""
    demo_dir.mkdir(parents=True, exist_ok=True)
    paths = [demo_dir / f"demo_art_v2_{i:02d}.png" for i in range(1, 10)]
    if all(p.exists() for p in paths):
        return paths

    import numpy as np
    import zlib
    import struct as pystruct

    def save_rgb(path: Path, rgb: "np.ndarray") -> None:
        rgb = np.clip(rgb, 0, 255).astype(np.uint8)
        h, w, _ = rgb.shape
        raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

        def ch(t: bytes, d: bytes) -> bytes:
            return pystruct.pack(">I", len(d)) + t + d + pystruct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

        ihdr = pystruct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + ch(b"IHDR", ihdr) + ch(b"IDAT", zlib.compress(raw, 6)) + ch(b"IEND", b""))

    def hex_u8(hx: str) -> "np.ndarray":
        h = hx.lstrip("#")
        return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=np.float64)

    # Curated museum exhibition palette (inspired by luminous Rothko/Turrell/Sugimoto/contemporary color fields)
    specs = [
        ((540, 720), "#F2EEE6", "#1D4E6E", "#8FB8CC", "gradient_sky"),      # 01 Portrait cerulean sky field
        ((960, 600), "#1E282C", "#3A6351", "#D49B54", "triptych_horizon"),  # 02 Hero panoramic botanical/amber abstraction
        ((540, 720), "#EFEBE2", "#C97D3A", "#5C3A28", "luminous_orb"),      # 03 Portrait warm amber-ochre glow
        ((640, 640), "#ECE8DF", "#26384A", "#93A8B8", "diagonal_light"),    # 04 Square architectural cobalt study
        ((800, 540), "#F0ECE3", "#B87A3D", "#E6C88C", "luminous_orb"),      # 05 Landscape golden solstice field
        ((520, 720), "#EAE6DC", "#2F443B", "#8FA394", "gradient_sky"),      # 06 Portrait deep forest mist
        ((800, 540), "#EDE9E0", "#22313F", "#C48A5A", "triptych_horizon"),  # 07 Landscape twilight & sienna
        ((640, 640), "#F1EDE4", "#6E473B", "#D8C2A8", "diagonal_light"),    # 08 Square terracotta monolith
        ((540, 720), "#ECE7DD", "#354652", "#C8B698", "gradient_sky"),      # 09 Portrait warm stone & slate
    ]

    rng = np.random.default_rng(42)
    for idx, ((w, h), bg_h, c1_h, c2_h, mode) in enumerate(specs):
        yy, xx = np.meshgrid(np.linspace(0.0, 1.0, h), np.linspace(0.0, 1.0, w), indexing="ij")
        bg = hex_u8(bg_h)
        c1 = hex_u8(c1_h)
        c2 = hex_u8(c2_h)
        # Subtle fine linen canvas micro-grain
        grain = rng.normal(0.0, 2.2, size=(h, w, 1))

        margin = 0.045
        in_art = (xx > margin) & (xx < 1.0 - margin) & (yy > margin) & (yy < 1.0 - margin)
        ax = np.clip((xx - margin) / (1.0 - 2 * margin), 0.0, 1.0)
        ay = np.clip((yy - margin) / (1.0 - 2 * margin), 0.0, 1.0)

        if mode == "gradient_sky":
            t = np.clip(ay ** 1.15, 0.0, 1.0)[..., None]
            art = c1 * (1.0 - t) + c2 * t
            glow = np.exp(-((ax - 0.5) ** 2 + (ay - 0.68) ** 2) / 0.14)[..., None]
            art = art * (1.0 - 0.28 * glow) + bg * (0.28 * glow)
        elif mode == "luminous_orb":
            r2 = ((ax - 0.5) ** 2) / 0.11 + ((ay - 0.5) ** 2) / 0.15
            glow = np.exp(-r2)[..., None]
            art = c1 * (1.0 - glow) + c2 * glow
        elif mode == "triptych_horizon":
            wave = 0.52 + 0.06 * np.sin(ax * 6.28) + 0.03 * np.cos(ax * 15.0)
            band = 1.0 / (1.0 + np.exp(-(ay - wave) * 24.0))[..., None]
            tex_mod = (0.5 + 0.5 * np.sin(ax * 22.0) * np.cos(ay * 16.0))[..., None]
            top = c1 * (0.72 + 0.28 * tex_mod) + c2 * 0.18 * (1.0 - ay[..., None])
            bot = c2 * (0.55 + 0.45 * (1.0 - ay[..., None])) * 0.65 + bg * 0.20
            art = top * (1.0 - band) + bot * band
        else:
            diag = np.clip(0.65 * ax + 0.45 * (1.0 - ay), 0.0, 1.0)[..., None]
            art = c1 * (1.0 - diag) + c2 * diag

        img = np.where(in_art[..., None], art + grain, bg)
        save_rgb(paths[idx], img)

    return paths


def populate_exhibition_demo(col_demo: bpy.types.Collection) -> None:
    """Temporarily mount 9 varied-aspect-ratio artworks + 2 minimalist oak gallery benches in `col_demo`."""
    demo_dir = WORK_DIR / "demo_artwork"
    art_paths = ensure_demo_artworks(demo_dir)

    dims = [
        (1.65, 2.20),  # Back_01 portrait
        (3.40, 2.12),  # Back_02 hero panoramic canvas
        (1.65, 2.20),  # Back_03 portrait
        (1.90, 1.90),  # Left_01 square
        (2.55, 1.72),  # Left_02 landscape
        (1.58, 2.18),  # Left_03 portrait
        (2.55, 1.72),  # Right_01 landscape
        (1.90, 1.90),  # Right_02 square
        (1.65, 2.20),  # Right_03 portrait
    ]

    mat_frame = bpy.data.materials.new("Demo_Mat_Frame")
    _ensure_nodes(mat_frame)
    mat_frame.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_rgba("#38312B")
    mat_frame.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.46

    for idx, (spec, (fw, fh), img_p) in enumerate(zip(ARTWORK_SPECS, dims, art_paths)):
        hw, hh = fw * 0.5, fh * 0.5
        fd = 0.044
        ft = 0.022
        ax_x, ax_y, ax_z = [Vector(a) for a in spec["axes"]]
        origin_g = Vector(spec["pos"])

        def local_to_gltf(lx: float, ly: float, lz: float) -> Tuple[float, float, float]:
            p = origin_g + ax_x * lx + ax_y * ly + ax_z * lz
            return (p.x, p.y, p.z)

        fm = ArchMesh(f"Demo_Frame_{idx+1:02d}", uv_scale_meters=1.0)
        bars = [
            (-hw - ft, hw + ft, hh, hh + ft, 0.0, fd),
            (-hw - ft, hw + ft, -hh - ft, -hh, 0.0, fd),
            (-hw - ft, -hw, -hh, hh, 0.0, fd),
            (hw, hw + ft, -hh, hh, 0.0, fd),
        ]
        for x0, x1, y0, y1, z0, z1 in bars:
            p000 = local_to_gltf(x0, y0, z0)
            p100 = local_to_gltf(x1, y0, z0)
            p101 = local_to_gltf(x1, y0, z1)
            p001 = local_to_gltf(x0, y0, z1)
            p010 = local_to_gltf(x0, y1, z0)
            p110 = local_to_gltf(x1, y1, z0)
            p111 = local_to_gltf(x1, y1, z1)
            p011 = local_to_gltf(x0, y1, z1)
            fm.add_quad_g(p011, p111, p110, p010)
            fm.add_quad_g(p000, p100, p101, p001)
            fm.add_quad_g(p001, p101, p111, p011)
            fm.add_quad_g(p100, p000, p010, p110)
            fm.add_quad_g(p101, p100, v110 := p110, p111)
            fm.add_quad_g(p000, p001, p011, p010)
        fm.finalize(None, col_demo, mat_frame)

        bm_a = bmesh.new()
        z_art = 0.032
        v0 = bm_a.verts.new(g2b_pt(*local_to_gltf(-hw, -hh, z_art)))
        v1 = bm_a.verts.new(g2b_pt(*local_to_gltf(hw, -hh, z_art)))
        v2 = bm_a.verts.new(g2b_pt(*local_to_gltf(hw, hh, z_art)))
        v3 = bm_a.verts.new(g2b_pt(*local_to_gltf(-hw, hh, z_art)))
        face = bm_a.faces.new((v0, v1, v2, v3))
        uv_l = bm_a.loops.layers.uv.new("UVMap")
        for lp, uv in zip(face.loops, ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))):
            lp[uv_l].uv = uv
        m_art = bpy.data.meshes.new(f"Demo_Art_{idx+1:02d}")
        bm_a.to_mesh(m_art)
        bm_a.free()

        mat_a = bpy.data.materials.new(f"Demo_Mat_Art_{idx+1:02d}")
        nt = _ensure_nodes(mat_a)
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.56
        tex_n = nt.nodes.new("ShaderNodeTexImage")
        tex_n.image = _load_img(img_p, non_color=False)
        nt.links.new(tex_n.outputs["Color"], bsdf.inputs["Base Color"])
        m_art.materials.append(mat_a)
        o_art = bpy.data.objects.new(f"Demo_Art_{idx+1:02d}", m_art)
        col_demo.objects.link(o_art)

    # Minimalist architectural white-oak gallery benches at Anchor_Place_Bench_01 & 02 (scale reference only)
    mat_oak = bpy.data.materials.new("Demo_Mat_Bench_Oak")
    _ensure_nodes(mat_oak)
    mat_oak.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_rgba("#C7B293")
    mat_oak.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.62

    for bx in (-3.40, 3.40):
        bench = ArchMesh(f"Demo_Bench_{'L' if bx < 0 else 'R'}", uv_scale_meters=1.0)
        bench.add_box_g(bx - 1.40, bx + 1.40, 0.37, 0.44, 1.54, 2.06, bevel=0.004)
        bench.add_box_g(bx - 1.16, bx - 1.02, 0.0, 0.37, 1.58, 2.02, bevel=0.003)
        bench.add_box_g(bx + 1.02, bx + 1.16, 0.0, 0.37, 1.58, 2.02, bevel=0.003)
        bench.finalize(None, col_demo, mat_oak)


# ---------------------------------------------------------------------------
# Camera Render Helper
# ---------------------------------------------------------------------------


def render_camera_view(
    out_path: Path,
    eye_g: Tuple[float, float, float],
    target_g: Tuple[float, float, float],
    lens_mm: float = 24.0,
    shift_y: float = 0.0,
    col_studio: Optional[bpy.types.Collection] = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cam_data = bpy.data.cameras.new("Render_Cam")
    cam_data.lens = lens_mm
    cam_data.sensor_width = 36.0
    cam_data.shift_y = shift_y
    cam_data.clip_start = 0.1
    cam_data.clip_end = 120.0

    cam_obj = bpy.data.objects.new("Render_Cam", cam_data)
    cam_obj.matrix_world = look_at_blender_native(eye_g, target_g)
    target_col = col_studio or bpy.context.scene.collection
    target_col.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data)


# ---------------------------------------------------------------------------
# Build Full Museum Scene & Export
# ---------------------------------------------------------------------------


def build_museum_scene(
    clay_mode: bool,
    detailed: bool,
    force_textures: bool = False,
) -> Tuple[bpy.types.Collection, bpy.types.Collection]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    col_export = bpy.data.collections.new("Museum_Export")
    col_arch = bpy.data.collections.new("Architecture")
    col_sky = bpy.data.collections.new("Skylight")
    col_fix = bpy.data.collections.new("Lighting_Fixtures")
    col_anc = bpy.data.collections.new("Anchors")
    col_studio = bpy.data.collections.new("Studio_Preview")

    scene.collection.children.link(col_export)
    scene.collection.children.link(col_studio)
    col_export.children.link(col_arch)
    col_export.children.link(col_sky)
    col_export.children.link(col_fix)
    col_export.children.link(col_anc)

    root = _new_empty("Museum_Open_Hall", None, col_export, Matrix.Identity(4), 1.0)
    root["assetId"] = "architecture/museum-open-hall"
    root["coordinateSystem"] = "glTF-Y-up-meters"
    root["walkableBoundsMeters"] = {
        "interiorMin": [-11.65, 0.0, -8.65],
        "interiorMax": [11.65, 2.60, 8.65],
        "entrancePortalMin": [-2.50, 0.0, 8.65],
        "entrancePortalMax": [2.50, 2.60, 10.60],
    }

    arch_grp = _new_empty("Architecture", root, col_arch, Matrix.Identity(4), 0.6)
    sky_grp = _new_empty("Skylight", root, col_sky, Matrix.Identity(4), 0.6)
    fix_grp = _new_empty("Lighting_Fixtures", root, col_fix, Matrix.Identity(4), 0.6)

    mats = create_materials(clay_mode=clay_mode, force_textures=force_textures)

    build_floor(arch_grp, col_arch, mats["Mat_Floor_Concrete"], detailed=detailed)
    build_walls_and_portal(
        arch_grp,
        col_arch,
        mats["Mat_Wall_Plaster"],
        mats["Mat_Entrance_Frame"],
        mats["Mat_Trim"],
        detailed=detailed,
    )
    build_ceiling_and_skylight(
        arch_grp,
        sky_grp,
        col_arch,
        col_sky,
        mats["Mat_Ceiling"],
        mats["Mat_Structural_Beam"],
        mats["Mat_Skylight_Frame"],
        mats["Mat_Skylight_Glass"],
        detailed=detailed,
    )
    if detailed:
        build_lighting_fixtures(fix_grp, col_fix, mats["Mat_Lighting_Fixture"], detailed=True)
    build_all_anchors(root, col_anc)

    return col_export, col_studio


def export_canonical_glb(
    glb_path: Path,
    col_studio: bpy.types.Collection,
    col_demo: Optional[bpy.types.Collection] = None,
) -> None:
    """Export only the canonical `Museum_Export` hierarchy to a self-contained GLB."""
    vl = bpy.context.view_layer
    studio_lc = vl.layer_collection.children.get(col_studio.name)
    demo_lc = vl.layer_collection.children.get(col_demo.name) if col_demo else None
    if studio_lc:
        studio_lc.exclude = True
    if demo_lc:
        demo_lc.exclude = True

    mg = bpy.data.materials.get("Mat_Skylight_Glass")
    if mg and mg.node_tree is not None:
        nt = mg.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        out = nt.nodes.get("Material Output")
        if bsdf and out:
            nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    bpy.ops.object.select_all(action="DESELECT")
    col_exp = bpy.data.collections["Museum_Export"]

    def select_col_recursive(c: bpy.types.Collection) -> None:
        for o in c.objects:
            o.select_set(True)
        for ch in c.children:
            select_col_recursive(ch)

    select_col_recursive(col_exp)

    glb_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=False,
        export_texcoords=True,
        export_normals=True,
        export_tangents=False,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_image_format="AUTO",
    )

    if studio_lc:
        studio_lc.exclude = False


def make_glass_cycles_friendly() -> None:
    """Route shadow rays transparently through `Mat_Skylight_Glass` in Cycles while keeping camera reflections."""
    mg = bpy.data.materials.get("Mat_Skylight_Glass")
    if not mg or mg.node_tree is None:
        return
    nt = mg.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    if not bsdf or not out:
        return
    lp = nt.nodes.new("ShaderNodeLightPath")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mx = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Shadow Ray"], mx.inputs["Fac"])
    nt.links.new(bsdf.outputs["BSDF"], mx.inputs[1])
    nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1 :]
    else:
        argv = []
    parser = argparse.ArgumentParser(description="Generate Open Skylight Museum Hall")
    parser.add_argument("--stage", choices=["massing", "detail", "final"], default="final")
    parser.add_argument("--export-only", action="store_true", help="Build textures, blend, and GLB without full render suite")
    parser.add_argument("--force-textures", action="store_true", help="Regenerate coherent PBR textures in textures/")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    if args.stage == "massing":
        out_dir = WORK_DIR / "stage-a-massing"
        _, col_studio = build_museum_scene(clay_mode=True, detailed=False)
        configure_cycles(samples=48, res_x=1280, res_y=800)
        setup_lighting_scenario("soft_daylight", col_studio)
        render_camera_view(out_dir / "01_massing_entrance.png", (0.0, 1.65, 8.5), (0.0, 1.65, -9.0), lens_mm=21.0, shift_y=0.095, col_studio=col_studio)
        render_camera_view(out_dir / "02_massing_center.png", (0.0, 1.65, 2.2), (0.0, 1.65, -9.0), lens_mm=23.0, shift_y=0.090, col_studio=col_studio)
        render_camera_view(out_dir / "03_massing_rear_to_entrance.png", (0.0, 1.65, -7.8), (0.0, 1.65, 9.0), lens_mm=21.0, shift_y=0.085, col_studio=col_studio)
        render_camera_view(out_dir / "04_massing_side.png", (8.2, 1.65, 1.5), (-12.0, 1.65, -2.0), lens_mm=23.0, shift_y=0.085, col_studio=col_studio)
        render_camera_view(out_dir / "05_massing_topdown.png", (0.0, 25.0, 2.8), (0.0, 0.0, 0.0), lens_mm=24.0, col_studio=col_studio)
        print("Stage A massing studies rendered to:", out_dir)
        return

    if args.stage == "detail":
        out_dir = WORK_DIR / "stage-b-detail"
        _, col_studio = build_museum_scene(clay_mode=True, detailed=True)
        configure_cycles(samples=64, res_x=1440, res_y=900)
        setup_lighting_scenario("direct_sun", col_studio)
        render_camera_view(out_dir / "01_detail_entrance.png", (0.0, 1.65, 8.4), (0.0, 1.65, -9.0), lens_mm=21.0, shift_y=0.105, col_studio=col_studio)
        render_camera_view(out_dir / "02_detail_skylight_and_coves.png", (0.0, 1.65, 5.2), (0.0, 9.8, -1.8), lens_mm=20.0, col_studio=col_studio)
        render_camera_view(out_dir / "03_detail_portal_and_reveal.png", (-4.8, 1.65, 2.2), (1.6, 1.65, 9.6), lens_mm=25.0, shift_y=0.055, col_studio=col_studio)
        render_camera_view(out_dir / "04_detail_wall_floor_junction.png", (-8.5, 0.90, 3.2), (-12.0, 0.30, -3.5), lens_mm=36.0, col_studio=col_studio)
        print("Stage B clay detailing studies rendered to:", out_dir)
        return

    # Stage `final`: Full PBR Materials, GLB Export, Blend Save, and 12 Visualization Renders
    ensure_pbr_textures(force=args.force_textures)
    _, col_studio = build_museum_scene(clay_mode=False, detailed=True, force_textures=False)

    # Export clean canonical `model.glb` before attaching Cycles-only shadow shader nodes or demo exhibits
    glb_path = ASSET_DIR / "model.glb"
    export_canonical_glb(glb_path, col_studio)

    # Make glass shadow-transparent for crisp Cycles visualization & save editable `model.blend`
    make_glass_cycles_friendly()
    setup_lighting_scenario("soft_daylight", col_studio)

    hero_cam_d = bpy.data.cameras.new("Preview_Camera")
    hero_cam_d.lens = 21.0
    hero_cam_d.sensor_width = 36.0
    hero_cam_d.shift_y = 0.115
    hero_cam_o = bpy.data.objects.new("Preview_Camera", hero_cam_d)
    hero_cam_o.matrix_world = look_at_blender_native((0.0, 1.65, 8.4), (0.0, 1.65, -9.0))
    col_studio.objects.link(hero_cam_o)
    bpy.context.scene.camera = hero_cam_o

    blend_path = ASSET_DIR / "model.blend"
    for img in bpy.data.images:
        if img.filepath:
            try:
                rel = Path(bpy.path.abspath(img.filepath)).resolve().relative_to(ASSET_DIR)
                img.filepath = "//" + rel.as_posix()
            except ValueError:
                pass
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path), compress=True, relative_remap=False)
    print(f"Saved {blend_path} and {glb_path} ({glb_path.stat().st_size} bytes)")

    if args.export_only:
        return

    # Render all 12 required Blender visualizations (Section 18) + catalog `preview.webp`
    # Uses level optical axes (`target_y == eye_y`) + vertical lens shift (`shift_y`) so architectural
    # verticals remain 100% plumb while framing the monumental 9 m floating canopy & 5-bay skylight coffer!
    renders_dir = WORK_DIR / "renders"
    configure_cycles(samples=72, res_x=1600, res_y=1000)

    # Scenario A — Soft Daylight (Views 1..8, 12)
    setup_lighting_scenario("soft_daylight", col_studio)
    render_camera_view(renders_dir / "01_empty_entrance.png", (0.0, 1.65, 8.4), (0.0, 1.65, -9.0), lens_mm=20.0, shift_y=0.125, col_studio=col_studio)
    render_camera_view(renders_dir / "02_empty_center.png", (0.0, 1.65, 3.6), (0.0, 1.65, -9.0), lens_mm=20.5, shift_y=0.135, col_studio=col_studio)
    render_camera_view(renders_dir / "03_left_exhibition_wall.png", (5.6, 1.65, 1.2), (-12.0, 1.65, -1.2), lens_mm=22.0, shift_y=0.098, col_studio=col_studio)
    render_camera_view(renders_dir / "04_right_exhibition_wall.png", (-5.6, 1.65, 1.2), (12.0, 1.65, -1.2), lens_mm=22.0, shift_y=0.098, col_studio=col_studio)
    render_camera_view(renders_dir / "05_rear_exhibition_wall.png", (0.0, 1.65, 1.4), (0.0, 1.65, -9.0), lens_mm=21.5, shift_y=0.115, col_studio=col_studio)
    render_camera_view(renders_dir / "06_skylight_and_ceiling.png", (0.0, 1.65, 5.2), (0.0, 9.8, -1.4), lens_mm=20.0, col_studio=col_studio)
    render_camera_view(renders_dir / "07_floor_and_wall_material_detail.png", (-8.6, 0.82, 2.8), (-12.0, 0.42, -3.2), lens_mm=38.0, col_studio=col_studio)
    render_camera_view(renders_dir / "08_soft_daylight_environment.png", (-4.8, 1.65, 7.6), (1.6, 1.65, -9.0), lens_mm=20.5, shift_y=0.118, col_studio=col_studio)
    render_camera_view(renders_dir / "12_human_eye_navigation.png", (2.8, 1.60, 5.4), (-3.8, 1.60, -9.0), lens_mm=27.0, shift_y=0.075, col_studio=col_studio)

    # Scenario B — Direct Sunlight (View 9)
    setup_lighting_scenario("direct_sun", col_studio)
    render_camera_view(renders_dir / "09_direct_sunlight_environment.png", (-4.4, 1.65, 7.8), (1.4, 1.65, -9.0), lens_mm=21.0, shift_y=0.112, col_studio=col_studio)
    # Also render symmetrical axial direct-sunlight overview to compare for catalog hero preview!
    render_camera_view(renders_dir / "09b_direct_sunlight_axial.png", (0.0, 1.65, 8.4), (0.0, 1.65, -9.0), lens_mm=21.0, shift_y=0.115, col_studio=col_studio)

    # Scenario C — Evening Exhibition (View 10 — empty architectural evening)
    setup_lighting_scenario("evening", col_studio)
    render_camera_view(renders_dir / "10_evening_exhibition_environment.png", (-4.2, 1.65, 7.2), (1.4, 1.65, -9.0), lens_mm=21.0, shift_y=0.105, col_studio=col_studio)

    # Stage E — Temporary 9-Artwork Exhibition Demonstration (View 11 — Daylight & Evening)
    col_demo = bpy.data.collections.new("Demo_Exhibition")
    bpy.context.scene.collection.children.link(col_demo)
    populate_exhibition_demo(col_demo)

    setup_lighting_scenario("soft_daylight", col_studio)
    for spec in ARTWORK_SPECS:
        tx, ty, tz = spec["track_pos"]
        px, py, pz = spec["pos"]
        ld = bpy.data.lights.new(f"Demo_DaySpot_{spec['name']}", type="SPOT")
        ld.energy = 340.0
        ld.spot_size = math.radians(38.0)
        ld.spot_blend = 0.48
        ld.color = hex_rgba("#FFF5E6")[:3]
        lo = bpy.data.objects.new(ld.name, ld)
        lo.matrix_world = look_at_blender_native((tx, ty - 0.04, tz), (px, py, pz))
        col_demo.objects.link(lo)

    render_camera_view(renders_dir / "11_nine_artwork_exhibition.png", (0.0, 1.65, 8.2), (0.0, 1.65, -9.0), lens_mm=21.0, shift_y=0.110, col_studio=col_studio)
    setup_lighting_scenario("evening", col_studio)
    render_camera_view(renders_dir / "11b_nine_artwork_evening.png", (-4.2, 1.65, 7.2), (1.4, 1.65, -9.0), lens_mm=21.0, shift_y=0.105, col_studio=col_studio)

    # Convert the flagship architectural view (`09b_direct_sunlight_axial.png`) to catalog `preview.webp`
    preview_webp = ASSET_DIR / "preview.webp"
    cwebp = shutil.which("cwebp")
    if cwebp:
        subprocess.run(
            [cwebp, "-q", "90", str(renders_dir / "09b_direct_sunlight_axial.png"), "-o", str(preview_webp)],
            check=True,
        )
    print("Completed all 12 architectural renders and catalog preview.webp")


if __name__ == "__main__":
    main()
