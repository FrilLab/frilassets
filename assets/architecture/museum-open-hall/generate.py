#!/usr/bin/env python3
"""
Reproducible Blender Python Architectural Generator for:
  Open Skylight Museum Hall (`assets/architecture/museum-open-hall/`)

Supports staged visual production and final deliverable export:
  - `--stage massing` : Stage A neutral clay architectural massing studies (5 views)
  - `--stage detail`  : Stage B neutral clay full architectural detailing studies (6 views)
  - `--stage final`   : Stages C, D, E, F — coherent PBR texture generation, Cycles lighting
                        scenarios (Soft Daylight, Direct Sunlight, Evening Exhibition),
                        12 required architectural & exhibition renders, catalog `preview.webp`,
                        editable `model.blend`, and self-contained `model.glb`.
  - `--export-only`   : Fast clean-checkout regeneration of textures, `model.blend`, and `model.glb`
                        without re-rendering diagnostic studies.

Coordinate convention (exported glTF 2.0 Y-up, meters):
  - X : Hall width  (-12.00 m Left Wall to +12.00 m Right Wall; 24.00 m clear)
  - Y : Height      (  0.00 m Finished Floor to +9.00 m Main Ceiling; +10.36 m Skylight Glass)
  - Z : Hall depth  ( -9.00 m Main Rear Exhibition Wall to +9.00 m Entrance Wall; 18.00 m clear)
  - Origin (0, 0, 0): Center of interior finished floor.
  - Blender internal conversion: (X_b, Y_b, Z_b) = (X_g, -Z_g, Y_g), a proper +90 deg X rotation
    that exports via `export_yup=True` back to exact (X_g, Y_g, Z_g) with zero manual correction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import bpy
import bmesh
from mathutils import Matrix, Vector

# ---------------------------------------------------------------------------
# Paths & Constants
# ---------------------------------------------------------------------------

ASSET_DIR = Path(__file__).resolve().parent
REPO_ROOT = ASSET_DIR.parent.parent.parent
TEX_DIR = ASSET_DIR / "textures"
WORK_DIR = REPO_ROOT / ".work" / "architecture" / "museum-open-hall"

# Core Interior Clear Dimensions (glTF meters)
HALL_WIDTH = 24.00       # X: -12.00 to +12.00
HALL_DEPTH = 18.00       # Z:  -9.00 to  +9.00
CEILING_HEIGHT = 9.00    # Y:   0.00 to  +9.00

HALF_W = HALL_WIDTH * 0.5   # 12.00
HALF_D = HALL_DEPTH * 0.5   #  9.00

WALL_THICK = 0.40           # 400 mm structural exterior walls
PORTAL_DEPTH = 1.20         # 1200 mm deep monumental entrance portal (+9.00 to +10.20)
FLOOR_THICK = 0.32          # 320 mm structural floor slab (-0.32 to 0.00)

ENTRANCE_WIDTH = 5.60       # X: -2.80 to +2.80
ENTRANCE_HEIGHT = 4.60      # Y:  0.00 to +4.60
ENTRANCE_FRAME_T = 0.060    # 60 mm architectural metal portal liner

# Wall-to-floor & wall-to-ceiling recessed shadow reveals
BASE_REVEAL_H = 0.065       # 65 mm high floating wall base shadow reveal
BASE_REVEAL_D = 0.028       # 28 mm deep recessed shadow channel
TOP_REVEAL_H = 0.025        # 25 mm high ceiling perimeter shadow reveal
TOP_REVEAL_D = 0.022        # 22 mm deep ceiling shadow channel

# Skylight Architecture (4 x 4 monumental coffer bays)
SKYLIGHT_W = 13.60          # X: -6.80 to +6.80 (within 13-14 m spec)
SKYLIGHT_D = 11.40          # Z: -5.70 to +5.70 (within 11-12 m spec)
SKY_HALF_W = SKYLIGHT_W * 0.5   # 6.80
SKY_HALF_D = SKYLIGHT_D * 0.5   # 5.70
SKY_CANT = 0.08             # 80 mm outward cant over 1.28 m daylight well height (~3.6 deg)
SKY_WELL_TOP_Y = 10.28      # Top of canted plaster skylight reveal well
SKY_FRAME_TOP_Y = 10.44     # Top of aluminum mullion frame
SKY_CURB_TOP_Y = 10.52      # Exterior curb flashing cap
SKY_GLASS_Y0 = 10.350       # Bottom of 18 mm laminated skylight glass
SKY_GLASS_Y1 = 10.368       # Top of 18 mm laminated skylight glass

# Recessed U-shaped exhibition lighting track geometry
TRACK_X = 8.80              # Left/Right tracks at X = +-8.80 m (3.20 m from side walls)
TRACK_BACK_Z = -6.50        # Rear track at Z = -6.50 m (2.50 m from rear wall)
TRACK_Z_END = 6.50          # Side tracks run Z = -6.50 to +6.50 m
TRACK_SLOT_W = 0.068        # 68 mm recessed ceiling slot width
TRACK_SLOT_D = 0.052        # 52 mm recessed slot depth into ceiling

# Exhibition Artwork Mounting Anchors (9 primary positions)
# Centered mounting at Y = 1.55 m supports up to 2.60 m height with 0.25 m floor clearance
# (0.185 m above the 0.065 m base shadow reveal). Taller works up to 5.60 m shift local +Y by (H - 2.60)/2.
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
        "track_pos": (-6.40, 8.84, TRACK_BACK_Z),
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
        "track_pos": (0.00, 8.84, TRACK_BACK_Z),
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
        "track_pos": (6.40, 8.84, TRACK_BACK_Z),
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
        "track_pos": (-TRACK_X, 8.84, -5.20),
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
        "track_pos": (-TRACK_X, 8.84, 0.00),
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
        "track_pos": (-TRACK_X, 8.84, 5.20),
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
        "track_pos": (TRACK_X, 8.84, -5.20),
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
        "track_pos": (TRACK_X, 8.84, 0.00),
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
        "track_pos": (TRACK_X, 8.84, 5.20),
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

    def __init__(self, name: str, uv_scale_meters: float = 2.5):
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

    def add_poly_g(self, pts: Sequence[Tuple[float, float, float]]) -> bmesh.types.BMFace:
        verts = [self.bm.verts.new(g2b_pt(*p)) for p in pts]
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
        `skip_faces` may include: '-x', '+x', '-y', '+y', '-z', '+z'.
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

    def add_tapered_beam_x(
        self,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z_center: float,
        w_bottom: float,
        w_top: float,
        bevel: float = 0.003,
    ) -> None:
        """Transverse structural beam spanning X with subtle upward architectural taper."""
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
        segments: int = 20,
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
        parent_obj: bpy.types.Object,
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
            # Convert normal back to glTF: (nx, nz, -ny)
            nx, ny, nz = n_b.x, n_b.z, -n_b.y
            ax, ay, az = abs(nx), abs(ny), abs(nz)
            for loop in face.loops:
                co_b = loop.vert.co
                gx, gy, gz = co_b.x, co_b.z, -co_b.y
                if ay >= ax and ay >= az:
                    # Horizontal floor/ceiling face: U = X, V = -Z
                    u = (gx + HALF_W) * inv_s
                    v = (-gz + HALF_D) * inv_s
                elif az >= ax:
                    # Front/Rear wall face: U = +-X, V = Y
                    sign_x = 1.0 if nz >= 0.0 else -1.0
                    u = (sign_x * gx + HALF_W) * inv_s
                    v = gy * inv_s
                else:
                    # Left/Right wall face: U = -+Z, V = Y
                    sign_z = -1.0 if nx >= 0.0 else 1.0
                    u = (sign_z * gz + HALF_D) * inv_s
                    v = gy * inv_s
                loop[uv_layer].uv = (u, v)

        mesh = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(mesh)
        self.bm.free()

        # Mark sharp edges beyond `smooth_angle_deg` and use flat/sharp normals cleanly
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
    builder = ArchMesh("Floor", uv_scale_meters=3.0)
    if not detailed:
        builder.add_box_g(-HALF_W - WALL_THICK, HALF_W + WALL_THICK, -FLOOR_THICK, 0.0, -HALF_D - WALL_THICK, HALF_D + PORTAL_DEPTH)
        return builder.finalize(arch_parent, col, mat_floor)

    # Structural slab base (-0.32 m to -0.003 m) spanning full building footprint including entrance threshold
    joint_d = 0.0028  # 2.8 mm deep micro-beveled expansion joint bottom
    builder.add_box_g(
        -HALF_W - WALL_THICK,
        HALF_W + WALL_THICK,
        -FLOOR_THICK,
        -joint_d,
        -HALF_D - WALL_THICK,
        HALF_D + PORTAL_DEPTH,
    )

    # Finished floor top panels (-0.0028 m to 0.000 m) with subtle 3.2 mm expansion joints
    # Perimeter honed stone/concrete border band (0.60 m wide) + 4 x 3 poured concrete gallery bays
    # aligned cleanly with the 4 x 4 skylight structural axes!
    gap = 0.0032
    hg = gap * 0.5
    bx = HALF_W - 0.60  # 11.40 m
    bz = HALF_D - 0.60  #  8.40 m

    # Outer ring extending slightly under the recessed wall channel (-12.04 to +12.04, -9.04 to +9.04)
    ox = HALF_W + 0.04
    oz = HALF_D + 0.04
    # 4 perimeter border strips around [-bx, +bx] x [-bz, +bz]
    builder.add_box_g(-ox, ox, -joint_d, 0.0, -oz, -bz - hg, bevel=0.001)
    # Front border split around entrance portal [-2.80, +2.80] so threshold slab runs cleanly out to +10.20 m
    builder.add_box_g(-ox, -ENTRANCE_WIDTH * 0.5 - hg, -joint_d, 0.0, bz + hg, oz, bevel=0.001)
    builder.add_box_g(ENTRANCE_WIDTH * 0.5 + hg, ox, -joint_d, 0.0, bz + hg, oz, bevel=0.001)
    # Entrance portal threshold slab (flush, continuous through the 1.20 m portal)
    builder.add_box_g(
        -ENTRANCE_WIDTH * 0.5 + hg,
        ENTRANCE_WIDTH * 0.5 - hg,
        -joint_d,
        0.0,
        bz + hg,
        HALF_D + PORTAL_DEPTH,
        bevel=0.001,
    )
    # Left & Right perimeter border strips
    builder.add_box_g(-ox, -bx - hg, -joint_d, 0.0, -bz + hg, bz - hg, bevel=0.001)
    builder.add_box_g(bx + hg, ox, -joint_d, 0.0, -bz + hg, bz - hg, bevel=0.001)

    # Central 4 x 4 architectural concrete bays aligned with skylight structural axes (-5.70, 0.00, +5.70 in X; -4.20, 0.00, +4.20 in Z)
    x_cuts = [-bx, -5.70, 0.00, 5.70, bx]
    z_cuts = [-bz, -2.85, 2.85, bz]
    for ix in range(len(x_cuts) - 1):
        for iz in range(len(z_cuts) - 1):
            x0 = x_cuts[ix] + hg
            x1 = x_cuts[ix + 1] - hg
            z0 = z_cuts[iz] + hg
            z1 = z_cuts[iz + 1] - hg
            builder.add_box_g(x0, x1, -joint_d, 0.0, z0, z1, bevel=0.001)

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
    y_top = (CEILING_HEIGHT - TOP_REVEAL_H) if detailed else CEILING_HEIGHT
    bev = 0.0025 if detailed else 0.0
    corner_gap = 0.002 if detailed else 0.0  # crisp 2 mm vertical shadow hairline at wall corners

    # 1. Wall_Back (Z = -9.40 to -9.00)
    wb = ArchMesh("Wall_Back", uv_scale_meters=3.2)
    # Full-height exterior light-tight structural backing [-9.40, -9.028]
    wb.add_box_g(-HALF_W - WALL_THICK, HALF_W + WALL_THICK, 0.0, CEILING_HEIGHT + 0.45, -HALF_D - WALL_THICK, -HALF_D - BASE_REVEAL_D)
    # Interior exhibition plaster leaf [-9.028, -9.000] floating cleanly between base & ceiling shadow reveals
    wb.add_box_g(-HALF_W + corner_gap, HALF_W - corner_gap, y_bot, y_top, -HALF_D - BASE_REVEAL_D, -HALF_D, bevel=bev)
    wb.finalize(arch_parent, col, mat_wall)

    # 2. Wall_Left (X = -12.40 to -12.00)
    wl = ArchMesh("Wall_Left", uv_scale_meters=3.2)
    wl.add_box_g(-HALF_W - WALL_THICK, -HALF_W - BASE_REVEAL_D, 0.0, CEILING_HEIGHT + 0.45, -HALF_D, HALF_D)
    wl.add_box_g(-HALF_W - BASE_REVEAL_D, -HALF_W, y_bot, y_top, -HALF_D + corner_gap, HALF_D - corner_gap, bevel=bev)
    wl.finalize(arch_parent, col, mat_wall)

    # 3. Wall_Right (X = +12.00 to +12.40)
    wr = ArchMesh("Wall_Right", uv_scale_meters=3.2)
    wr.add_box_g(HALF_W + BASE_REVEAL_D, HALF_W + WALL_THICK, 0.0, CEILING_HEIGHT + 0.45, -HALF_D, HALF_D)
    wr.add_box_g(HALF_W, HALF_W + BASE_REVEAL_D, y_bot, y_top, -HALF_D + corner_gap, HALF_D - corner_gap, bevel=bev)
    wr.finalize(arch_parent, col, mat_wall)

    # 4. Wall_Entrance (Z = +9.00 to +10.20 with 5.60 m x 4.60 m portal opening)
    we = ArchMesh("Wall_Entrance", uv_scale_meters=3.2)
    ro_half_w = ENTRANCE_WIDTH * 0.5 + (ENTRANCE_FRAME_T if detailed else 0.0)  # 2.86 m rough opening half-width
    ro_h = ENTRANCE_HEIGHT + (ENTRANCE_FRAME_T if detailed else 0.0)            # 4.66 m rough opening height
    quirk = 0.012 if detailed else 0.0                                          # 12 mm shadow quirk around metal portal frame

    # Left structural pier + plaster face
    we.add_box_g(-HALF_W - WALL_THICK, -ro_half_w, 0.0, CEILING_HEIGHT + 0.45, HALF_D + BASE_REVEAL_D, HALF_D + PORTAL_DEPTH)
    we.add_box_g(-HALF_W + corner_gap, -ro_half_w - quirk, y_bot, y_top, HALF_D, HALF_D + BASE_REVEAL_D, bevel=bev)
    # Right structural pier + plaster face
    we.add_box_g(ro_half_w, HALF_W + WALL_THICK, 0.0, CEILING_HEIGHT + 0.45, HALF_D + BASE_REVEAL_D, HALF_D + PORTAL_DEPTH)
    we.add_box_g(ro_half_w + quirk, HALF_W - corner_gap, y_bot, y_top, HALF_D, HALF_D + BASE_REVEAL_D, bevel=bev)
    # Lintel header above portal opening (Y = ro_h to ceiling)
    we.add_box_g(-ro_half_w, ro_half_w, ro_h, CEILING_HEIGHT + 0.45, HALF_D + BASE_REVEAL_D, HALF_D + PORTAL_DEPTH)
    we.add_box_g(-ro_half_w - quirk, ro_half_w + quirk, ro_h + quirk, y_top, HALF_D, HALF_D + BASE_REVEAL_D, bevel=bev)
    we.finalize(arch_parent, col, mat_wall)

    # 5. Entrance_Frame (60 mm powder-coated architectural portal liner spanning Z = +8.995 to +10.205)
    ef = ArchMesh("Entrance_Frame", uv_scale_meters=1.5)
    ew = ENTRANCE_WIDTH * 0.5  # 2.80 m clear half-width
    eh = ENTRANCE_HEIGHT       # 4.60 m clear height
    ft = ENTRANCE_FRAME_T      # 0.06 m liner thickness
    z_f0 = HALF_D - (0.006 if detailed else 0.0)
    z_f1 = HALF_D + PORTAL_DEPTH + (0.006 if detailed else 0.0)
    f_bev = 0.003 if detailed else 0.0
    # Left jamb
    ef.add_box_g(-ew - ft, -ew, 0.001, eh, z_f0, z_f1, bevel=f_bev)
    # Right jamb
    ef.add_box_g(ew, ew + ft, 0.001, eh, z_f0, z_f1, bevel=f_bev)
    # Header lintel liner
    ef.add_box_g(-ew - ft, ew + ft, eh, eh + ft, z_f0, z_f1, bevel=f_bev)
    ef.finalize(arch_parent, col, mat_portal)

    # 6. Wall_Floor_Transitions (Recessed shadow-gap channels at wall base and ceiling perimeter)
    wt = ArchMesh("Wall_Floor_Transitions", uv_scale_meters=1.0)
    if detailed:
        # Base shadow-gap liners (L-profile recessed 28 mm behind plaster face, Y = 0.001 to 0.0645)
        t_th = 0.004
        # Back wall base liner
        wt.add_box_g(-HALF_W - BASE_REVEAL_D, HALF_W + BASE_REVEAL_D, 0.001, BASE_REVEAL_H - 0.0005, -HALF_D - BASE_REVEAL_D, -HALF_D - BASE_REVEAL_D + t_th)
        # Left wall base liner
        wt.add_box_g(-HALF_W - BASE_REVEAL_D, -HALF_W - BASE_REVEAL_D + t_th, 0.001, BASE_REVEAL_H - 0.0005, -HALF_D - BASE_REVEAL_D, HALF_D + BASE_REVEAL_D)
        # Right wall base liner
        wt.add_box_g(HALF_W + BASE_REVEAL_D - t_th, HALF_W + BASE_REVEAL_D, 0.001, BASE_REVEAL_H - 0.0005, -HALF_D - BASE_REVEAL_D, HALF_D + BASE_REVEAL_D)
        # Entrance wings base liners
        wt.add_box_g(-HALF_W - BASE_REVEAL_D, -ro_half_w, 0.001, BASE_REVEAL_H - 0.0005, HALF_D + BASE_REVEAL_D - t_th, HALF_D + BASE_REVEAL_D)
        wt.add_box_g(ro_half_w, HALF_W + BASE_REVEAL_D, 0.001, BASE_REVEAL_H - 0.0005, HALF_D + BASE_REVEAL_D - t_th, HALF_D + BASE_REVEAL_D)
        # Upper ceiling perimeter shadow-reveal liners (Y = 8.9755 to 8.999)
        wt.add_box_g(-HALF_W - TOP_REVEAL_D, HALF_W + TOP_REVEAL_D, y_top + 0.0005, CEILING_HEIGHT - 0.001, -HALF_D - TOP_REVEAL_D, -HALF_D - TOP_REVEAL_D + t_th)
        wt.add_box_g(-HALF_W - TOP_REVEAL_D, -HALF_W - TOP_REVEAL_D + t_th, y_top + 0.0005, CEILING_HEIGHT - 0.001, -HALF_D - TOP_REVEAL_D, HALF_D + TOP_REVEAL_D)
        wt.add_box_g(HALF_W + TOP_REVEAL_D - t_th, HALF_W + TOP_REVEAL_D, y_top + 0.0005, CEILING_HEIGHT - 0.001, -HALF_D - TOP_REVEAL_D, HALF_D + TOP_REVEAL_D)
        wt.add_box_g(-HALF_W - TOP_REVEAL_D, HALF_W + TOP_REVEAL_D, y_top + 0.0005, CEILING_HEIGHT - 0.001, HALF_D + TOP_REVEAL_D - t_th, HALF_D + TOP_REVEAL_D)
    else:
        wt.add_box_g(-HALF_W, HALF_W, 0.0, 0.04, -HALF_D, -HALF_D + 0.015)
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
    # 1. Ceiling (Perimeter ceiling soffits with pocketed U-track slot + canted skylight daylight well)
    cm = ArchMesh("Ceiling", uv_scale_meters=3.0)
    ox = HALF_W + WALL_THICK
    oz0 = -HALF_D - WALL_THICK
    oz1 = HALF_D + PORTAL_DEPTH
    y_soffit = CEILING_HEIGHT
    y_slot_top = CEILING_HEIGHT + TRACK_SLOT_D  # 9.052 m
    y_roof_top = SKY_WELL_TOP_Y                 # 10.28 m

    if not detailed:
        # Simple perimeter ceiling slabs around [-6.80, +6.80] x [-5.70, +5.70]
        cm.add_box_g(-ox, ox, y_soffit, y_roof_top, oz0, -SKY_HALF_D)
        cm.add_box_g(-ox, ox, y_soffit, y_roof_top, SKY_HALF_D, oz1)
        cm.add_box_g(-ox, -SKY_HALF_W, y_soffit, y_roof_top, -SKY_HALF_D, SKY_HALF_D)
        cm.add_box_g(SKY_HALF_W, ox, y_soffit, y_roof_top, -SKY_HALF_D, SKY_HALF_D)
    else:
        # Upper roof mass above track slot (Y = 9.052 to 10.28) with canted inner skylight daylight well!
        # Let's build the outer roof slab outside [-6.88, +6.88] x [-5.78, +5.78] first:
        wx = SKY_HALF_W + SKY_CANT  # 6.88 m at top of canted skylight reveal
        wz = SKY_HALF_D + SKY_CANT  # 5.78 m at top of canted skylight reveal
        cm.add_box_g(-ox, ox, y_slot_top, y_roof_top, oz0, -wz)
        cm.add_box_g(-ox, ox, y_slot_top, y_roof_top, wz, oz1)
        cm.add_box_g(-ox, -wx, y_slot_top, y_roof_top, -wz, wz)
        cm.add_box_g(wx, ox, y_slot_top, y_roof_top, -wz, wz)

        # Lower ceiling soffit layer (Y = 9.000 to 9.052) subdivided cleanly around the U-shaped recessed lighting track slot!
        # U-track slot occupies:
        #   Back slot: X in [-8.834, +8.834], Z in [-6.534, -6.466]
        #   Left slot: X in [-8.834, -8.766], Z in [-6.466, +6.534]
        #   Right slot: X in [+8.766, +8.834], Z in [-6.466, +6.534]
        hs = TRACK_SLOT_W * 0.5  # 0.034 m
        tx0, tx1 = TRACK_X - hs, TRACK_X + hs     # 8.766, 8.834
        tbz0, tbz1 = TRACK_BACK_Z - hs, TRACK_BACK_Z + hs  # -6.534, -6.466
        tz_end = TRACK_Z_END + hs                 # +6.534

        # Zone 1: Far rear strip (Z from oz0 to tbz0 = -6.534)
        cm.add_box_g(-ox, ox, y_soffit, y_slot_top, oz0, tbz0)
        # Zone 2: Outer left strip (X from -ox to -tx1 = -8.834, Z from tbz0 to oz1)
        cm.add_box_g(-ox, -tx1, y_soffit, y_slot_top, tbz0, oz1)
        # Zone 3: Outer right strip (X from +tx1 = +8.834 to +ox, Z from tbz0 to oz1)
        cm.add_box_g(tx1, ox, y_soffit, y_slot_top, tbz0, oz1)
        # Zone 4: Front strip forward of side tracks (X from -tx1 to +tx1, Z from tz_end = +6.534 to oz1)
        cm.add_box_g(-tx1, tx1, y_soffit, y_slot_top, tz_end, oz1)
        # Zone 5: Inner soffit collar between U-track [-8.766, +8.766] x [-6.466, +6.534] and skylight well [-6.88, +6.88] x [-5.78, +5.78]
        cm.add_box_g(-tx0, tx0, y_soffit, y_slot_top, tbz1, -wz)
        cm.add_box_g(-tx0, tx0, y_soffit, y_slot_top, wz, tz_end)
        cm.add_box_g(-tx0, -wx, y_soffit, y_slot_top, -wz, wz)
        cm.add_box_g(wx, tx0, y_soffit, y_slot_top, -wz, wz)

        # Canted Skylight Daylight Well Collar (connects aperture [-6.80, +6.80] x [-5.70, +5.70] at Y=9.00
        # smoothly up to [-6.88, +6.88] x [-5.78, +5.78] at Y=10.28, backed out to +-wx / +-wz!)
        # 4 trapezoidal cross-section canted wedges around the skylight perimeter:
        ix, iz = SKY_HALF_W, SKY_HALF_D  # 6.80, 5.70 at bottom
        # North/Rear reveal (-Z side):
        # Bottom soffit ring from -wz to -iz at Y=9.00, canted inner face from (-ix, 9.00, -iz) to (-wx, 10.28, -wz)
        cm.add_quad_g((-wx, y_soffit, -wz), (wx, y_soffit, -wz), (ix, y_soffit, -iz), (-ix, y_soffit, -iz))
        cm.add_quad_g((-ix, y_soffit, -iz), (ix, y_soffit, -iz), (wx, y_roof_top, -wz), (-wx, y_roof_top, -wz))
        # South/Entrance reveal (+Z side):
        cm.add_quad_g((-ix, y_soffit, iz), (ix, y_soffit, iz), (wx, y_soffit, wz), (-wx, y_soffit, wz))
        cm.add_quad_g((ix, y_soffit, iz), (-ix, y_soffit, iz), (-wx, y_roof_top, wz), (wx, y_roof_top, wz))
        # West/Left reveal (-X side):
        cm.add_quad_g((-wx, y_soffit, wz), (-ix, y_soffit, iz), (-ix, y_soffit, -iz), (-wx, y_soffit, -wz))
        cm.add_quad_g((-ix, y_soffit, iz), (-wx, y_roof_top, wz), (-wx, y_roof_top, -wz), (-ix, y_soffit, -iz))
        # East/Right reveal (+X side):
        cm.add_quad_g((ix, y_soffit, iz), (wx, y_soffit, wz), (wx, y_soffit, -wz), (ix, y_soffit, -iz))
        cm.add_quad_g((ix, y_soffit, -iz), (wx, y_roof_top, -wz), (wx, y_roof_top, wz), (ix, y_soffit, iz))

    cm.finalize(arch_parent, col_arch, mat_ceiling)

    # 2. Ceiling_Beams (3 slender transverse daylight-baffle structural beams at Z = -2.85, 0.00, +2.85 m)
    cb = ArchMesh("Ceiling_Beams", uv_scale_meters=2.0)
    beam_z_positions = (-2.85, 0.00, 2.85)
    beam_y0 = 9.14
    beam_y1 = 9.86
    for bz in beam_z_positions:
        cb.add_tapered_beam_x(
            -SKY_HALF_W - 0.05,
            SKY_HALF_W + 0.05,
            beam_y0,
            beam_y1,
            bz,
            w_bottom=0.130,
            w_top=0.164,
            bevel=0.003 if detailed else 0.0,
        )
    cb.finalize(arch_parent, col_arch, mat_beam)

    # 3. Skylight_Supports (3 longitudinal daylight-baffle fins at X = -3.40, 0.00, +3.40 m, cleanly segmented between primary beams)
    ss = ArchMesh("Skylight_Supports", uv_scale_meters=2.0)
    sup_x_positions = (-3.40, 0.00, 3.40)
    sup_hw = 0.046  # 92 mm wide refined architectural baffle fins
    z_spans = [
        (-SKY_HALF_D - 0.06, -2.85 - 0.082),
        (-2.85 + 0.082, -0.082),
        (0.082, 2.85 - 0.082),
        (2.85 + 0.082, SKY_HALF_D + 0.06),
    ]
    for sx in sup_x_positions:
        # Continuous upper purlin chord above primary beams (Y = 9.862 to 10.28)
        ss.add_box_g(
            sx - sup_hw,
            sx + sup_hw,
            beam_y1 + 0.002,
            SKY_WELL_TOP_Y,
            -SKY_HALF_D - 0.06,
            SKY_HALF_D + 0.06,
            bevel=0.002 if detailed else 0.0,
        )
        # Lower notched baffle web segments between primary beams (Y = 9.52 to 9.860)
        for z0, z1 in z_spans:
            ss.add_box_g(
                sx - sup_hw,
                sx + sup_hw,
                9.52,
                beam_y1,
                z0,
                z1,
                bevel=0.002 if detailed else 0.0,
            )
    ss.finalize(sky_parent, col_sky, mat_beam)

    # 4. Skylight_Frame (Powder-coated architectural aluminum curb & 4x4 glazing mullion grid)
    sf = ArchMesh("Skylight_Frame", uv_scale_meters=1.5)
    wx = SKY_HALF_W + SKY_CANT  # 6.88
    wz = SKY_HALF_D + SKY_CANT  # 5.78
    curb_t = 0.22
    mull_hw = 0.038  # 76 mm mullions
    f_bev = 0.0025 if detailed else 0.0

    # Perimeter curb ring (Y = 10.28 to 10.52)
    sf.add_box_g(-wx - curb_t, wx + curb_t, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, -wz - curb_t, -wz + mull_hw, bevel=f_bev)
    sf.add_box_g(-wx - curb_t, wx + curb_t, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, wz - mull_hw, wz + curb_t, bevel=f_bev)
    sf.add_box_g(-wx - curb_t, -wx + mull_hw, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, -wz + mull_hw, wz - mull_hw, bevel=f_bev)
    sf.add_box_g(wx - mull_hw, wx + curb_t, SKY_WELL_TOP_Y, SKY_CURB_TOP_Y, -wz + mull_hw, wz - mull_hw, bevel=f_bev)

    # 3 longitudinal mullions at X = -3.40, 0.00, +3.40 (Y = 10.28 to 10.44)
    for sx in sup_x_positions:
        sf.add_box_g(sx - mull_hw, sx + mull_hw, SKY_WELL_TOP_Y, SKY_FRAME_TOP_Y, -wz + mull_hw, wz - mull_hw, bevel=f_bev)

    # 3 transverse transoms at Z = -2.85, 0.00, +2.85 segmented cleanly between longitudinal mullions
    x_bay_edges = [-wx + mull_hw, -3.40 - mull_hw, -3.40 + mull_hw, -mull_hw, mull_hw, 3.40 - mull_hw, 3.40 + mull_hw, wx - mull_hw]
    for bz in beam_z_positions:
        for i in range(0, len(x_bay_edges), 2):
            sf.add_box_g(x_bay_edges[i], x_bay_edges[i + 1], SKY_WELL_TOP_Y, SKY_FRAME_TOP_Y, bz - mull_hw, bz + mull_hw, bevel=f_bev)
    sf.finalize(sky_parent, col_sky, mat_sky_frame)

    # 5. Skylight_Glass (16 independent glazing panes combined into one semantic Skylight_Glass node)
    sg = ArchMesh("Skylight_Glass", uv_scale_meters=2.0)
    gx_cuts = [-wx + mull_hw, -3.40 - mull_hw, -3.40 + mull_hw, -mull_hw, mull_hw, 3.40 - mull_hw, 3.40 + mull_hw, wx - mull_hw]
    gz_cuts = [-wz + mull_hw, -2.85 - mull_hw, -2.85 + mull_hw, -mull_hw, mull_hw, 2.85 - mull_hw, 2.85 + mull_hw, wz - mull_hw]
    inset = 0.002
    for ix in range(0, len(gx_cuts), 2):
        for iz in range(0, len(gz_cuts), 2):
            sg.add_box_g(
                gx_cuts[ix] + inset,
                gx_cuts[ix + 1] - inset,
                SKY_GLASS_Y0,
                SKY_GLASS_Y1,
                gz_cuts[iz] + inset,
                gz_cuts[iz + 1] - inset,
            )
    sg.finalize(sky_parent, col_sky, mat_sky_glass)


def _add_spotlight_head(
    mesh: ArchMesh,
    mount_x: float,
    mount_z: float,
    target_g: Tuple[float, float, float],
) -> None:
    """Minimal cylindrical architectural museum spotlight (ERCO Parscan style) hanging from recessed ceiling track."""
    # Vertical stem adapter from recessed track (Y = 9.015) down to yoke pivot (Y = 8.87)
    mesh.add_cylinder_segment_g((mount_x, 9.018, mount_z), (mount_x, 8.885, mount_z), 0.014, 0.014, segments=12)
    # Yoke collar
    mesh.add_box_g(mount_x - 0.028, mount_x + 0.028, 8.865, 8.890, mount_z - 0.016, mount_z + 0.016)
    # Oriented cylindrical spotlight body aimed toward `target_g` (14 smooth-shaded segments at Y=8.85m)
    pivot = Vector((mount_x, 8.855, mount_z))
    aim = (Vector(target_g) - pivot).normalized()
    rear = pivot - aim * 0.075
    front = pivot + aim * 0.105
    baffle_in = pivot + aim * 0.082
    mesh.add_cylinder_segment_g(
        (rear.x, rear.y, rear.z),
        (front.x, front.y, front.z),
        0.046,
        0.046,
        segments=14,
        cap_start=True,
        cap_end=False,
    )
    # Recessed anti-glare snoot baffle cap inside front aperture
    mesh.add_cylinder_segment_g(
        (front.x, front.y, front.z),
        (baffle_in.x, baffle_in.y, baffle_in.z),
        0.044,
        0.036,
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
    # 1. Track_Back (Recessed track housing at Z = -6.50 m + 5 aimed spotlights)
    tb = ArchMesh("Track_Back", uv_scale_meters=1.0)
    tb.add_box_g(-TRACK_X - 0.030, TRACK_X + 0.030, 9.015, 9.051, TRACK_BACK_Z - 0.030, TRACK_BACK_Z + 0.030)
    if detailed:
        for sx in (-6.40, -3.20, 0.00, 3.20, 6.40):
            _add_spotlight_head(tb, sx, TRACK_BACK_Z, (sx, ARTWORK_CENTER_Y + 0.25, -HALF_D))
    tb.finalize(fix_parent, col_fix, mat_fixture)

    # 2. Track_Left (Recessed track housing at X = -8.80 m + 5 aimed spotlights)
    tl = ArchMesh("Track_Left", uv_scale_meters=1.0)
    tl.add_box_g(-TRACK_X - 0.030, -TRACK_X + 0.030, 9.015, 9.051, TRACK_BACK_Z + 0.031, TRACK_Z_END + 0.030)
    if detailed:
        for sz in (-5.20, -2.60, 0.00, 2.60, 5.20):
            _add_spotlight_head(tl, -TRACK_X, sz, (-HALF_W, ARTWORK_CENTER_Y + 0.25, sz))
    tl.finalize(fix_parent, col_fix, mat_fixture)

    # 3. Track_Right (Recessed track housing at X = +8.80 m + 5 aimed spotlights)
    tr = ArchMesh("Track_Right", uv_scale_meters=1.0)
    tr.add_box_g(TRACK_X - 0.030, TRACK_X + 0.030, 9.015, 9.051, TRACK_BACK_Z + 0.031, TRACK_Z_END + 0.030)
    if detailed:
        for sz in (-5.20, -2.60, 0.00, 2.60, 5.20):
            _add_spotlight_head(tr, TRACK_X, sz, (HALF_W, ARTWORK_CENTER_Y + 0.25, sz))
    tr.finalize(fix_parent, col_fix, mat_fixture)

    # 4. Recessed_Fixtures (10 discreet architectural downlight bezels along perimeter ceiling soffits)
    rf = ArchMesh("Recessed_Fixtures", uv_scale_meters=0.5)
    downlight_coords = [
        (-7.60, 7.60), (-3.80, 7.60), (3.80, 7.60), (7.60, 7.60),
        (-10.40, -7.60), (10.40, -7.60),
        (-10.40, -3.20), (-10.40, 3.20),
        (10.40, -3.20), (10.40, 3.20),
    ]
    for dx, dz in downlight_coords:
        rf.add_cylinder_segment_g((dx, 8.997, dz), (dx, 9.035, dz), 0.058, 0.042, segments=16, cap_start=False, cap_end=True)
    rf.finalize(fix_parent, col_fix, mat_fixture)


# ---------------------------------------------------------------------------
# Semantic Anchors Construction (Sections 13, 14, 15, 16)
# ---------------------------------------------------------------------------


def _new_empty(
    name: str,
    parent: bpy.types.Object,
    col: bpy.types.Collection,
    world_mat_b: Matrix,
    size: float = 0.25,
) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = size
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

        # Corresponding spotlight anchor at ceiling track aperture aimed at artwork center (local -Z = beam)
        tx, ty, tz = spec["track_pos"]
        lgt_m = look_at_gltf_basis((tx, ty, tz), (px, py, pz))
        lgt_obj = _new_empty(spec["light_name"], lgt_grp, col_anchors, lgt_m, 0.25)
        lgt_obj["anchorRole"] = "artwork-spotlight"
        lgt_obj["targetAnchor"] = spec["name"]

        # Corresponding human-eye-level inspection anchor (Y = 1.60 m, `nav_dist` out along inward normal)
        nd = spec["nav_dist"]
        nx_pos = (px + ax_z[0] * nd, 1.60, pz + ax_z[2] * nd)
        nav_m = look_at_gltf_basis(nx_pos, (px, 1.55, pz))
        nav_obj = _new_empty(spec["nav_name"], nav_grp, col_anchors, nav_m, 0.30)
        nav_obj["anchorRole"] = "artwork-viewpoint"
        nav_obj["targetAnchor"] = spec["name"]

    # 2. Additional Optional Floor Placement Anchors (Section 14)
    for pname, ppos, pfront in PLACEMENT_SPECS:
        up = (0.0, 1.0, 0.0)
        # Local XY vertical/upright or floor anchor with +Y up and +Z facing `pfront`
        zf = Vector(pfront).normalized()
        xf = Vector(up).cross(zf).normalized()
        pm = make_gltf_basis_matrix(ppos, (xf.x, xf.y, xf.z), up, (zf.x, zf.y, zf.z))
        p_obj = _new_empty(pname, exh_grp, col_anchors, pm, 0.30)
        p_obj["anchorRole"] = "floor-placement"

    # 3. Additional Lighting Anchors (Central installation accents + Perimeter evening ambient fill)
    extra_lights = [
        ("Anchor_Light_Center_01", (-3.40, 8.95, 0.00), (0.00, 1.00, -0.60)),
        ("Anchor_Light_Center_02", (3.40, 8.95, 0.00), (0.00, 1.00, -0.60)),
        ("Anchor_Light_Ambient_01", (-7.60, 8.95, 7.60), (-7.60, 0.00, 7.60)),
        ("Anchor_Light_Ambient_02", (7.60, 8.95, 7.60), (7.60, 0.00, 7.60)),
        ("Anchor_Light_Ambient_03", (-10.40, 8.95, -7.60), (-10.40, 0.00, -7.60)),
        ("Anchor_Light_Ambient_04", (10.40, 8.95, -7.60), (10.40, 0.00, -7.60)),
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
    Every surface uses a periodic multi-octave Fourier / value-noise height field in millimeters,
    deriving OpenGL (+Y) tangent-space normal maps and spatially aligned roughness + neutral
    near-white variation maps so runtime `material.color` tinting works cleanly.
    """
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    expected = {
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
        """Lossless 8-bit grayscale or RGB PNG writer using stdlib zlib."""
        arr = np.clip(arr, 0, 255).astype(np.uint8)
        if arr.ndim == 2:
            h, w = arr.shape
            color_type = 0
            raw_rows = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))
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
        """Exact seamless 2D periodic fractal field via band-limited spectral synthesis."""
        rng = np.random.default_rng(seed)
        spec = np.zeros((res, res), dtype=np.complex128)
        ky = np.fft.fftfreq(res) * res
        kx = np.fft.fftfreq(res) * res
        KX, KY = np.meshgrid(kx, ky)
        KR = np.sqrt(KX * KX + KY * KY)

        for k_center, weight in freq_weights:
            bw = max(1.2, k_center * 0.45)
            env = np.exp(-0.5 * ((KR - k_center) / bw) ** 2)
            env[0, 0] = 0.0
            phase = rng.uniform(0.0, 2.0 * np.pi, size=(res, res))
            amp = rng.normal(1.0, 0.25, size=(res, res))
            spec += weight * env * amp * (np.cos(phase) + 1j * np.sin(phase))

        field = np.fft.ifft2(spec).real
        std = float(np.std(field))
        if std > 1e-9:
            field /= std
        return field

    def height_to_normal_rgb(height: "np.ndarray", strength: float) -> "np.ndarray":
        """Convert periodic height field to OpenGL (+Y) tangent-space RGB normal map."""
        dh_dx = (np.roll(height, -1, axis=1) - np.roll(height, 1, axis=1)) * 0.5 * strength
        # Row index increases downward in PNG; OpenGL V increases upward (+Y), so +dH/dV = -(row+1 - row-1)
        dh_dv = -(np.roll(height, -1, axis=0) - np.roll(height, 1, axis=0)) * 0.5 * strength
        nx = -dh_dx
        ny = -dh_dv
        nz = np.ones_like(height)
        inv_len = 1.0 / np.sqrt(nx * nx + ny * ny + nz * nz)
        rgb = np.stack(
            [
                (nx * inv_len * 0.5 + 0.5) * 255.0,
                (ny * inv_len * 0.5 + 0.5) * 255.0,
                (nz * inv_len * 0.5 + 0.5) * 255.0,
            ],
            axis=-1,
        )
        return rgb

    # 1. Museum Wall Plaster (1024x1024 lossless micro-normal, 512x512 band-limited roughness; 3.2 m repeat)
    res_p = 1024
    h_plaster = periodic_fbm(
        res_p,
        seed=101,
        freq_weights=[(3, 0.30), (7, 0.35), (16, 0.45), (38, 0.55), (85, 0.65), (180, 0.50)],
    )
    n_plaster = height_to_normal_rgb(h_plaster, strength=0.14)
    # Downsample coherent roughness 2x2 box-average to 512x512 (matte mineral plaster ~0.82 - 0.92)
    h_plaster_512 = 0.25 * (
        h_plaster[0::2, 0::2] + h_plaster[1::2, 0::2] + h_plaster[0::2, 1::2] + h_plaster[1::2, 1::2]
    )
    r_plaster = (0.87 - 0.025 * np.tanh(h_plaster_512 * 0.8)) * 255.0
    write_png_u8(expected["plaster_normal"], n_plaster)
    write_png_u8(expected["plaster_roughness"], r_plaster)

    # 2. Honed Architectural Concrete Floor (1024x1024 lossless normal, 512x512 coherent basecolor & roughness; 3.0 m repeat)
    res_c = 1024
    h_cloud = periodic_fbm(res_c, seed=202, freq_weights=[(1, 0.65), (2, 0.50), (4, 0.30), (9, 0.16)])
    h_micro = periodic_fbm(res_c, seed=203, freq_weights=[(45, 0.40), (105, 0.50), (210, 0.45)])
    # Subtle micro-pores (honed limestone/concrete pinholes, very restrained)
    pores = np.minimum(0.0, h_micro + 1.75) * 0.30
    h_conc = 0.55 * h_cloud + 0.28 * h_micro + pores
    n_conc = height_to_normal_rgb(h_conc, strength=0.10)

    def box2x2(a: "np.ndarray") -> "np.ndarray":
        return 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])

    hc512 = box2x2(h_cloud)
    hm512 = box2x2(h_micro)
    po512 = box2x2(pores)

    # Neutral near-white variation [238..252] with subtle warm-cool mineral tone (~1.2% tint delta)
    # so `Mat_Floor_Concrete` baseColorFactor (#AEAAA1) produces refined warm neutral gray AND remains recolorable!
    lum = 0.960 + 0.024 * np.tanh(0.70 * hc512 + 0.18 * hm512)
    warm = 0.005 * np.tanh(hc512)
    c_rgb = np.stack(
        [
            (lum + warm) * 255.0,
            lum * 255.0,
            (lum - warm * 1.1) * 255.0,
        ],
        axis=-1,
    )
    # Restrained satin honed concrete roughness: 0.44 on honed plateaus to 0.56 in softer mineral zones (never mirror-like!)
    r_conc = (0.49 - 0.042 * np.tanh(0.7 * hc512 + 0.4 * hm512) - 0.05 * po512) * 255.0
    write_png_u8(expected["concrete_basecolor"], c_rgb)
    write_png_u8(expected["concrete_normal"], n_conc)
    write_png_u8(expected["concrete_roughness"], r_conc)

    # 3. Acoustic Mineral Ceiling Plaster (512 x 512, fine matte acoustic plaster micro-texture)
    res_ceil = 512
    h_ceil = periodic_fbm(res_ceil, seed=303, freq_weights=[(8, 0.30), (24, 0.45), (64, 0.65), (140, 0.60)])
    n_ceil = height_to_normal_rgb(h_ceil, strength=0.12)
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


def create_materials(clay_mode: bool) -> Dict[str, bpy.types.Material]:
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
                # Transparent clay glass so daylight illuminates the clay interior cleanly
                m.blend_method = "BLEND" if hasattr(m, "blend_method") else "OPAQUE"
                bsdf.inputs["Base Color"].default_value = hex_rgba("#EAECEF", 0.08)
                bsdf.inputs["Alpha"].default_value = 0.06
                bsdf.inputs["Roughness"].default_value = 0.10
                # Let shadow rays pass cleanly through glass in Cycles
                lp = nt.nodes.new("ShaderNodeLightPath")
                tr = nt.nodes.new("ShaderNodeBsdfTransparent")
                mx = nt.nodes.new("ShaderNodeMixShader")
                out = nt.nodes.get("Material Output")
                nt.links.new(lp.outputs["Is Shadow Ray"], mx.inputs["Fac"])
                nt.links.new(bsdf.outputs["BSDF"], mx.inputs[1])
                nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
                nt.links.new(mx.outputs["Shader"], out.inputs["Surface"])
            else:
                # Warm architectural limestone-clay study palette
                tone = "#DCD7CE" if nm != "Mat_Floor_Concrete" else "#CFC9BE"
                bsdf.inputs["Base Color"].default_value = hex_rgba(tone)
                bsdf.inputs["Roughness"].default_value = 0.85
                bsdf.inputs["Metallic"].default_value = 0.0
            mats[nm] = m
        return mats

    tex = ensure_pbr_textures()

    def make_textured_pbr(
        name: str,
        base_hex: str,
        metallic: float,
        roughness: float,
        base_map: Optional[Path] = None,
        rough_map: Optional[Path] = None,
        norm_map: Optional[Path] = None,
        norm_strength: float = 0.35,
    ) -> bpy.types.Material:
        m = bpy.data.materials.new(name)
        nt = _ensure_nodes(m)
        bsdf = nt.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = hex_rgba(base_hex)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = 1.48

        if base_map is not None:
            tex_c = nt.nodes.new("ShaderNodeTexImage")
            tex_c.image = _load_img(base_map, non_color=False)
            # Multiply neutral near-white map by `base_hex` factor so glTF exports both texture + baseColorFactor!
            # Wait: Blender's glTF exporter exports BOTH `baseColorTexture` and `baseColorFactor` cleanly when
            # `Mix (Multiply)` or direct `Base Color`? Let's use `MixColor (MULTIPLY, Factor=1.0)` between
            # `tex_c` (A) and `RGB(base_hex)` (B), which Blender 5.x glTF exporter recognizes natively as
            # `baseColorTexture` * `baseColorFactor`!
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

    # 1. Mat_Wall_Plaster — Warm gallery lime-mineral plaster (#F3EFE8), matte, zero plastic sheen
    mats["Mat_Wall_Plaster"] = make_textured_pbr(
        "Mat_Wall_Plaster",
        base_hex="#F3EFE8",
        metallic=0.0,
        roughness=0.87,
        rough_map=tex["plaster_roughness"],
        norm_map=tex["plaster_normal"],
        norm_strength=0.32,
    )

    # 2. Mat_Floor_Concrete — Honed architectural warm-gray concrete/limestone (#AEAAA1), restrained satin sheen
    mats["Mat_Floor_Concrete"] = make_textured_pbr(
        "Mat_Floor_Concrete",
        base_hex="#AEAAA1",
        metallic=0.0,
        roughness=0.49,
        base_map=tex["concrete_basecolor"],
        rough_map=tex["concrete_roughness"],
        norm_map=tex["concrete_normal"],
        norm_strength=0.28,
    )

    # 3. Mat_Ceiling — Calm warm-neutral acoustic mineral ceiling (#ECE9E2)
    mats["Mat_Ceiling"] = make_textured_pbr(
        "Mat_Ceiling",
        base_hex="#ECE9E2",
        metallic=0.0,
        roughness=0.91,
        norm_map=tex["ceiling_normal"],
        norm_strength=0.25,
    )

    # 4. Mat_Structural_Beam — Architectural matte painted steel/mineral louver finish (#EFECE5)
    mats["Mat_Structural_Beam"] = make_textured_pbr(
        "Mat_Structural_Beam",
        base_hex="#EFECE5",
        metallic=0.06,
        roughness=0.64,
        norm_map=tex["ceiling_normal"],
        norm_strength=0.14,
    )

    # 5. Mat_Skylight_Frame — Powder-coated warm silver-gray aluminum (#D6D3CC)
    mats["Mat_Skylight_Frame"] = make_textured_pbr(
        "Mat_Skylight_Frame",
        base_hex="#D6D3CC",
        metallic=0.38,
        roughness=0.40,
    )

    # 6. Mat_Skylight_Glass — Clear low-iron architectural glazing with real-time glTF BLEND fallback
    mg = bpy.data.materials.new("Mat_Skylight_Glass")
    nt = _ensure_nodes(mg)
    if hasattr(mg, "surface_render_method"):
        mg.surface_render_method = "BLENDED"
    elif hasattr(mg, "blend_method"):
        mg.blend_method = "BLEND"
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = hex_rgba("#EEF5F8", 1.0)
    bsdf.inputs["Metallic"].default_value = 0.04
    bsdf.inputs["Roughness"].default_value = 0.07
    bsdf.inputs["Alpha"].default_value = 0.16
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.52
    mats["Mat_Skylight_Glass"] = mg

    # 7. Mat_Entrance_Frame — Powder-coated dark warm architectural bronze-charcoal (#383532)
    mats["Mat_Entrance_Frame"] = make_textured_pbr(
        "Mat_Entrance_Frame",
        base_hex="#383532",
        metallic=0.45,
        roughness=0.38,
    )

    # 8. Mat_Lighting_Fixture — Matte architectural graphite spotlight & track housing (#282726)
    mats["Mat_Lighting_Fixture"] = make_textured_pbr(
        "Mat_Lighting_Fixture",
        base_hex="#282726",
        metallic=0.35,
        roughness=0.45,
    )

    # 9. Mat_Trim — Deep architectural shadow-gap reveal channel finish (#222120)
    mats["Mat_Trim"] = make_textured_pbr(
        "Mat_Trim",
        base_hex="#222120",
        metallic=0.28,
        roughness=0.55,
    )

    return mats


# ---------------------------------------------------------------------------
#Cycles Render Engine, Lighting Scenarios (A, B, C), & Temporary Exhibition (Stage E)
# ---------------------------------------------------------------------------


def configure_cycles(samples: int = 96, res_x: int = 1600, res_y: int = 1000) -> None:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 8
    scene.cycles.diffuse_bounces = 4
    scene.cycles.glossy_bounces = 3
    scene.cycles.transmission_bounces = 4
    scene.cycles.transparent_max_bounces = 8

    # Enable Apple Metal GPU acceleration when available
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
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.0


def setup_lighting_scenario(
    scenario: str,
    col_studio: bpy.types.Collection,
) -> None:
    """
    Configure Blender authoring lighting scenario in `Studio_Preview` collection (excluded from GLB).
    Scenarios:
      - 'soft_daylight' : Scenario A — diffused overcast/bright sky dome + soft skylight fill
      - 'direct_sun'    : Scenario B — crisp angled sun beams through the 4x4 skylight coffer + sky dome
      - 'evening'       : Scenario C — twilight sky + warm 3000K gallery track spotlights on all 9 anchors
    """
    # Clear previous lights/backdrop in Studio_Preview
    for obj in list(col_studio.objects):
        if obj.type in ("LIGHT", "MESH") and obj.name.startswith("Studio_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    # Make Skylight_Glass invisible to shadow rays in Cycles so sunlight casts crisp architectural shadows
    glass_obj = bpy.data.objects.get("Skylight_Glass")
    if glass_obj is not None and hasattr(glass_obj, "visible_shadow"):
        glass_obj.visible_shadow = False

    # Subtle exterior arrival court bounce plane beyond entrance (+Z = +16 m) so views toward entrance feel real
    court = ArchMesh("Studio_Exterior_Court", uv_scale_meters=4.0)
    court.add_box_g(-16.0, 16.0, -0.32, 0.0, HALF_D + PORTAL_DEPTH, 19.0)
    court.add_box_g(-16.0, 16.0, 0.0, 9.2, 18.8, 19.2)
    mat_court = bpy.data.materials.get("Studio_Mat_Court") or bpy.data.materials.new("Studio_Mat_Court")
    _ensure_nodes(mat_court)
    mat_court.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_rgba("#DDD8CF")
    mat_court.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.90
    court.finalize(None, col_studio, mat_court)

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
        lo.matrix_world = look_at_blender_native(pos_g, target_g)
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

    def _configure_sky(sky_node, elev_deg: float, rot_deg: float) -> None:
        for candidate in ("MULTIPLE_SCATTERING", "SINGLE_SCATTERING", "NISHITA", "HOSEK_WILKIE"):
            try:
                sky_node.sky_type = candidate
                break
            except TypeError:
                continue
        if hasattr(sky_node, "sun_disc"):
            sky_node.sun_disc = False
        if hasattr(sky_node, "sun_elevation"):
            sky_node.sun_elevation = math.radians(elev_deg)
        if hasattr(sky_node, "sun_rotation"):
            sky_node.sun_rotation = math.radians(rot_deg)

    if scenario == "soft_daylight":
        sky = wnt.nodes.new("ShaderNodeTexSky")
        _configure_sky(sky, 58.0, 28.0)
        bg.inputs["Strength"].default_value = 0.11
        wnt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        # Large soft sky diffuser panel directly above skylight glazing (Y = 11.2 m)
        add_area_light(
            "Studio_Skylight_Soft_Dome",
            (0.0, 11.20, 0.0),
            (0.0, 0.0, -0.5),
            energy=3400.0,
            size_x=13.4,
            size_y=11.2,
            color_hex="#F7F8FA",
            spread_deg=130.0,
        )
        # Gentle exterior arrival daylight outside entrance portal
        add_area_light(
            "Studio_Portal_Daylight",
            (0.0, 4.2, 13.5),
            (0.0, 1.6, 2.0),
            energy=650.0,
            size_x=7.0,
            size_y=4.5,
            color_hex="#F8F6F0",
            spread_deg=120.0,
        )
        bpy.context.scene.view_settings.exposure = -0.15

    elif scenario == "direct_sun":
        sky = wnt.nodes.new("ShaderNodeTexSky")
        _configure_sky(sky, 52.0, 34.0)
        bg.inputs["Strength"].default_value = 0.08
        wnt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        # Soft blue-neutral zenith sky fill above skylight
        add_area_light(
            "Studio_Skylight_SkyFill",
            (0.0, 11.40, 0.0),
            (0.0, 0.0, 0.0),
            energy=1750.0,
            size_x=13.4,
            size_y=11.2,
            color_hex="#EAF2FC",
            spread_deg=140.0,
        )
        # Controlled directional sunlight raking diagonally through the 4x4 skylight coffer onto floor & walls
        sun_d = bpy.data.lights.new("Studio_Direct_Sun", type="SUN")
        sun_d.energy = 3.1
        sun_d.angle = math.radians(1.15)  # Realistic soft penumbra sun disc
        sun_d.color = hex_rgba("#FFF5E4")[:3]
        sun_o = bpy.data.objects.new("Studio_Direct_Sun", sun_d)
        # Sun coming from (+6.8, +15.0, +4.4) toward (-2.4, 0.0, -2.6) -> casts architectural coffer shadows on floor & left/rear walls!
        sun_o.matrix_world = look_at_blender_native((6.8, 15.0, 4.4), (-2.4, 0.0, -2.6))
        col_studio.objects.link(sun_o)
        bpy.context.scene.view_settings.exposure = -0.30

    elif scenario == "evening":
        # Deep twilight blue exterior sky visible faintly through the overhead skylight
        bg.inputs["Color"].default_value = hex_rgba("#182438")
        bg.inputs["Strength"].default_value = 0.35
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        # Subtle cool twilight sky glow from skylight
        add_area_light(
            "Studio_Twilight_Skylight",
            (0.0, 11.10, 0.0),
            (0.0, 0.0, 0.0),
            energy=280.0,
            size_x=13.2,
            size_y=11.0,
            color_hex="#9DB4D4",
            spread_deg=145.0,
        )
        # Warm 3000K gallery track spotlights illuminating all 9 artwork anchors
        for spec in ARTWORK_SPECS:
            tx, ty, tz = spec["track_pos"]
            px, py, pz = spec["pos"]
            add_spot_light(
                f"Studio_Spot_{spec['name']}",
                (tx, ty - 0.06, tz),
                (px, py + 0.05, pz),
                energy=720.0,
                spot_deg=40.0,
                blend=0.45,
                color_hex="#FFEED8",
            )
        # Soft warm central ceiling wash & perimeter circulation fill
        add_area_light(
            "Studio_Evening_Ambient",
            (0.0, 8.85, 0.0),
            (0.0, 0.0, 0.0),
            energy=520.0,
            size_x=9.0,
            size_y=7.0,
            color_hex="#FFEED8",
            spread_deg=135.0,
        )
        bpy.context.scene.view_settings.exposure = 0.15


# ---------------------------------------------------------------------------
# Temporary 9-Artwork Exhibition Demonstration (Stage E — Never Exported to GLB)
# ---------------------------------------------------------------------------


def ensure_demo_artworks(demo_dir: Path) -> List[Path]:
    """Generate 9 original abstract architectural/editorial fine-art textures of varied aspect ratios."""
    demo_dir.mkdir(parents=True, exist_ok=True)
    paths = [demo_dir / f"demo_art_{i:02d}.png" for i in range(1, 10)]
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

    # Curated fine-art minimalist abstract compositions (Rothko / Agnes Martin / Hiroshi Sugimoto / editorial inspired)
    palettes = [
        ((512, 680), "#EAE4D8", "#2B3A42", "#C47D56"),   # 01 Portrait warm terracotta & slate
        ((820, 540), "#F0ECE3", "#1F2426", "#8A969C"),   # 02 Hero landscape Sugimoto horizon
        ((512, 680), "#EBE6DC", "#5C6B5E", "#D6C4A8"),   # 03 Portrait botanical sage &linen
        ((640, 640), "#EFECE6", "#3E352F", "#B59B7C"),   # 04 Square architectural monolith
        ((760, 520), "#E8E4DC", "#27313B", "#C9B89E"),   # 05 Landscape deep indigo & sand
        ((500, 680), "#F2EEE7", "#7A4E3D", "#DECBB4"),   # 06 Portrait ochre & sienna
        ((760, 520), "#ECE8E0", "#303633", "#9BA399"),   # 07 Landscape mist & graphite
        ((640, 640), "#F1EDE4", "#242220", "#C89D66"),   # 08 Square warm gold-ochre & charcoal
        ((512, 680), "#EAE5DB", "#3D4A52", "#B8AFA2"),   # 09 Portrait Nordic slate & stone
    ]

    def hex_u8(hx: str) -> "np.ndarray":
        h = hx.lstrip("#")
        return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=np.float64)

    for idx, ((w, h), bg_h, fg1_h, fg2_h) in enumerate(palettes):
        yy, xx = np.meshgrid(np.linspace(0.0, 1.0, h), np.linspace(0.0, 1.0, w), indexing="ij")
        bg = hex_u8(bg_h)
        c1 = hex_u8(fg1_h)
        c2 = hex_u8(fg2_h)
        img = np.broadcast_to(bg, (h, w, 3)).copy()

        # Mat-board off-white border (9% margin)
        in_art = (xx > 0.09) & (xx < 0.91) & (yy > 0.09) & (yy < 0.91)
        ax = np.clip((xx - 0.09) / 0.82, 0.0, 1.0)
        ay = np.clip((yy - 0.09) / 0.82, 0.0, 1.0)

        if idx % 3 == 0:
            # Minimalist architectural arch + horizon study
            grad = 0.35 + 0.65 * ay
            art = c2 * grad[..., None] * 0.85 + bg * 0.15
            circle = ((ax - 0.5) ** 2 + (ay - 0.54) ** 2) < 0.075
            band = ay > 0.64
            art = np.where(band[..., None], c1, art)
            art = np.where(circle[..., None], c2, art)
        elif idx % 3 == 1:
            # Serene Sugimoto-inspired sea/horizon tonal field
            horizon = 1.0 / (1.0 + np.exp(-(ay - 0.52) * 38.0))
            sky_tone = bg * 0.72 + c2 * 0.28 * (1.0 - ay[..., None] * 0.5)
            sea_tone = c1 * (0.65 + 0.35 * (1.0 - ay[..., None]))
            art = sky_tone * (1.0 - horizon[..., None]) + sea_tone * horizon[..., None]
        else:
            # Geometric modernist diptych blocks
            art = bg * 0.90
            blk1 = (ax > 0.14) & (ax < 0.56) & (ay > 0.16) & (ay < 0.82)
            blk2 = (ax > 0.48) & (ax < 0.86) & (ay > 0.34) & (ay < 0.86)
            art = np.where(blk1[..., None], c2, art)
            art = np.where(blk2[..., None], c1, art)

        img = np.where(in_art[..., None], art, img)
        save_rgb(paths[idx], img)

    return paths


def populate_exhibition_demo(col_demo: bpy.types.Collection) -> None:
    """Temporarily mount 9 varied-aspect-ratio framed artworks + 2 minimalist museum benches in `col_demo`."""
    demo_dir = WORK_DIR / "demo_artwork"
    art_paths = ensure_demo_artworks(demo_dir)

    #Varied realistic gallery frame dimensions (width, height in meters) matching each artwork's aspect ratio
    dims = [
        (1.65, 2.20),  # Back_01 portrait
        (3.20, 2.10),  # Back_02 hero landscape
        (1.65, 2.20),  # Back_03 portrait
        (1.90, 1.90),  # Left_01 square
        (2.55, 1.75),  # Left_02 landscape
        (1.60, 2.15),  # Left_03 portrait
        (2.55, 1.75),  # Right_01 landscape
        (1.90, 1.90),  # Right_02 square
        (1.65, 2.20),  # Right_03 portrait
    ]

    mat_frame = bpy.data.materials.new("Demo_Mat_Frame")
    _ensure_nodes(mat_frame)
    mat_frame.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_rgba("#2D2926")
    mat_frame.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.48

    for idx, (spec, (fw, fh), img_p) in enumerate(zip(ARTWORK_SPECS, dims, art_paths)):
        anchor = bpy.data.objects[spec["name"]]
        hw, hh = fw * 0.5, fh * 0.5
        fd = 0.042  # 42 mm museum walnut/ash box frame depth
        ft = 0.026  # 26 mm frame moulding width

        # Build frame & canvas directly in anchor local XY (+Z outward), then assign `anchor.matrix_world`!
        bm_f = bmesh.new()
        def add_local_box(bm_t, x0, x1, y0, y1, z0, z1):
            # In Blender Empty local space before R_B2G? Wait: remember M_b = R_G2B @ M_g @ R_B2G!
            # So to place a point in anchor glTF local (lx, ly, lz), its glTF world coord is M_g @ (lx, ly, lz, 1)!
            pass

        # Compute glTF world transform M_g directly from `spec["pos"]` and `spec["axes"]`!
        ax_x, ax_y, ax_z = [Vector(a) for a in spec["axes"]]
        origin_g = Vector(spec["pos"])

        def local_to_gltf(lx: float, ly: float, lz: float) -> Tuple[float, float, float]:
            p = origin_g + ax_x * lx + ax_y * ly + ax_z * lz
            return (p.x, p.y, p.z)

        # Frame mesh (4 perimeter bars)
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
            fm.add_quad_g(p101, p100, p110, p111)
            fm.add_quad_g(p000, p001, p011, p010)
        fm.finalize(None, col_demo, mat_frame)

        # Artwork front plane with exact 0..1 UVs
        bm_a = bmesh.new()
        z_art = 0.028
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
        bsdf.inputs["Roughness"].default_value = 0.62
        tex_n = nt.nodes.new("ShaderNodeTexImage")
        tex_n.image = _load_img(img_p, non_color=False)
        nt.links.new(tex_n.outputs["Color"], bsdf.inputs["Base Color"])
        m_art.materials.append(mat_a)
        o_art = bpy.data.objects.new(f"Demo_Art_{idx+1:02d}", m_art)
        col_demo.objects.link(o_art)

    # Minimalist oak museum gallery benches at Anchor_Place_Bench_01 & 02 (temporary scale reference only)
    mat_oak = bpy.data.materials.new("Demo_Mat_Bench_Oak")
    _ensure_nodes(mat_oak)
    mat_oak.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_rgba("#C4AE8E")
    mat_oak.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.65

    for bx in (-3.40, 3.40):
        bench = ArchMesh(f"Demo_Bench_{'L' if bx < 0 else 'R'}", uv_scale_meters=1.0)
        bench.add_box_g(bx - 1.35, bx + 1.35, 0.36, 0.44, 1.52, 2.08, bevel=0.004)
        bench.add_box_g(bx - 1.15, bx - 0.98, 0.0, 0.36, 1.56, 2.04, bevel=0.003)
        bench.add_box_g(bx + 0.98, bx + 1.15, 0.0, 0.36, 1.56, 2.04, bevel=0.003)
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
    # Keep verticals plumb when shift_y != 0 by aiming horizontally at eye level when desired
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


def build_museum_scene(clay_mode: bool, detailed: bool) -> Tuple[bpy.types.Collection, bpy.types.Collection]:
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

    # Root hierarchy nodes
    root = _new_empty("Museum_Open_Hall", None, col_export, Matrix.Identity(4), 1.0)
    root["assetId"] = "architecture/museum-open-hall"
    root["coordinateSystem"] = "glTF-Y-up-meters"
    root["walkableBoundsMeters"] = {
        "interiorMin": [-11.65, 0.0, -8.65],
        "interiorMax": [11.65, 2.60, 8.65],
        "entrancePortalMin": [-2.50, 0.0, 8.65],
        "entrancePortalMax": [2.50, 2.60, 10.20],
    }

    arch_grp = _new_empty("Architecture", root, col_arch, Matrix.Identity(4), 0.6)
    sky_grp = _new_empty("Skylight", root, col_sky, Matrix.Identity(4), 0.6)
    fix_grp = _new_empty("Lighting_Fixtures", root, col_fix, Matrix.Identity(4), 0.6)

    mats = create_materials(clay_mode=clay_mode)

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


def export_canonical_glb(glb_path: Path, col_studio: bpy.types.Collection, col_demo: Optional[bpy.types.Collection] = None) -> None:
    """Export only the canonical `Museum_Export` hierarchy to a self-contained GLB."""
    # Exclude Studio_Preview and any temporary Demo collection from view layer during export
    vl = bpy.context.view_layer
    studio_lc = vl.layer_collection.children.get(col_studio.name)
    demo_lc = vl.layer_collection.children.get(col_demo.name) if col_demo else None
    if studio_lc:
        studio_lc.exclude = True
    if demo_lc:
        demo_lc.exclude = True

    # Ensure Skylight_Glass uses direct Principled BSDF alpha blend for clean glTF export
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
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()

    if args.stage == "massing":
        out_dir = WORK_DIR / "stage-a-massing"
        _, col_studio = build_museum_scene(clay_mode=True, detailed=False)
        configure_cycles(samples=48, res_x=1280, res_y=800)
        setup_lighting_scenario("soft_daylight", col_studio)
        render_camera_view(out_dir / "01_massing_entrance.png", (0.0, 1.65, 8.6), (0.0, 2.5, -9.0), lens_mm=22.0, shift_y=0.05, col_studio=col_studio)
        render_camera_view(out_dir / "02_massing_center.png", (0.0, 1.65, 2.2), (0.0, 2.8, -9.0), lens_mm=24.0, shift_y=0.04, col_studio=col_studio)
        render_camera_view(out_dir / "03_massing_rear_to_entrance.png", (0.0, 1.65, -7.8), (0.0, 2.5, 9.0), lens_mm=22.0, shift_y=0.04, col_studio=col_studio)
        render_camera_view(out_dir / "04_massing_side.png", (8.2, 1.65, 1.5), (-12.0, 2.6, -2.0), lens_mm=24.0, shift_y=0.04, col_studio=col_studio)
        # Top-down architectural roof/skylight perspective looking into the hall through the skylight
        render_camera_view(out_dir / "05_massing_topdown.png", (0.0, 24.5, 3.0), (0.0, 0.0, 0.0), lens_mm=24.0, col_studio=col_studio)
        print("Stage A massing studies rendered to:", out_dir)
        return

    if args.stage == "detail":
        out_dir = WORK_DIR / "stage-b-detail"
        _, col_studio = build_museum_scene(clay_mode=True, detailed=True)
        configure_cycles(samples=64, res_x=1440, res_y=900)
        setup_lighting_scenario("direct_sun", col_studio)
        render_camera_view(out_dir / "01_detail_entrance.png", (0.0, 1.65, 8.4), (0.0, 2.6, -9.0), lens_mm=22.0, shift_y=0.05, col_studio=col_studio)
        render_camera_view(out_dir / "02_detail_skylight.png", (0.0, 1.65, 3.8), (0.0, 9.6, -2.2), lens_mm=20.0, col_studio=col_studio)
        render_camera_view(out_dir / "03_detail_portal_and_reveal.png", (-4.8, 1.60, 2.4), (1.8, 2.2, 9.4), lens_mm=26.0, shift_y=0.03, col_studio=col_studio)
        render_camera_view(out_dir / "04_detail_wall_floor_junction.png", (-8.5, 0.95, 3.2), (-12.0, 0.35, -3.5), lens_mm=35.0, col_studio=col_studio)
        print("Stage B clay detailing studies rendered to:", out_dir)
        return

    # Stage `final`: Full PBR Materials, GLB Export, Blend Save, and 12 Visualization Renders
    ensure_pbr_textures(force=False)
    _, col_studio = build_museum_scene(clay_mode=False, detailed=True)

    # First export clean canonical `model.glb` before attaching Cycles-only shadow shader nodes or demo exhibits
    glb_path = ASSET_DIR / "model.glb"
    export_canonical_glb(glb_path, col_studio)

    # Make glass shadow-transparent for crisp Cycles visualization & save editable `model.blend`
    make_glass_cycles_friendly()
    setup_lighting_scenario("soft_daylight", col_studio)

    # Set a reproducible 2-point tilt-shift Studio_Preview hero camera in `model.blend` (plumb verticals)
    hero_cam_d = bpy.data.cameras.new("Preview_Camera")
    hero_cam_d.lens = 22.0
    hero_cam_d.sensor_width = 36.0
    hero_cam_d.shift_y = 0.082
    hero_cam_o = bpy.data.objects.new("Preview_Camera", hero_cam_d)
    hero_cam_o.matrix_world = look_at_blender_native((0.0, 1.65, 8.2), (0.0, 1.65, -9.0))
    col_studio.objects.link(hero_cam_o)
    bpy.context.scene.camera = hero_cam_o

    blend_path = ASSET_DIR / "model.blend"
    # Save dummy first or make all external texture paths strictly relative (`//textures/...`) to `ASSET_DIR`
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
    # Uses level optical axes (`target_y == eye_y`) + vertical lens shift (`shift_y`) for plumb architectural verticals!
    renders_dir = WORK_DIR / "renders"
    configure_cycles(samples=80, res_x=1600, res_y=1000)

    # Scenario A — Soft Daylight (Views 1..8, 12)
    setup_lighting_scenario("soft_daylight", col_studio)
    render_camera_view(renders_dir / "01_empty_entrance.png", (0.0, 1.65, 8.2), (0.0, 1.65, -9.0), lens_mm=22.0, shift_y=0.082, col_studio=col_studio)
    render_camera_view(renders_dir / "02_empty_center.png", (0.0, 1.65, 2.0), (0.0, 1.65, -9.0), lens_mm=23.0, shift_y=0.085, col_studio=col_studio)
    render_camera_view(renders_dir / "03_left_exhibition_wall.png", (4.8, 1.65, 1.2), (-12.0, 1.65, -1.2), lens_mm=24.0, shift_y=0.072, col_studio=col_studio)
    render_camera_view(renders_dir / "04_right_exhibition_wall.png", (-4.8, 1.65, 1.2), (12.0, 1.65, -1.2), lens_mm=24.0, shift_y=0.072, col_studio=col_studio)
    render_camera_view(renders_dir / "05_rear_exhibition_wall.png", (0.0, 1.65, -0.8), (0.0, 1.65, -9.0), lens_mm=24.0, shift_y=0.078, col_studio=col_studio)
    render_camera_view(renders_dir / "06_skylight_and_ceiling.png", (0.0, 1.65, 4.4), (0.0, 9.7, -1.6), lens_mm=21.0, col_studio=col_studio)
    render_camera_view(renders_dir / "07_floor_and_wall_material_detail.png", (-8.8, 0.85, 2.6), (-12.0, 0.45, -3.2), lens_mm=38.0, col_studio=col_studio)
    render_camera_view(renders_dir / "08_soft_daylight_environment.png", (-5.6, 1.65, 6.8), (2.2, 1.65, -9.0), lens_mm=22.0, shift_y=0.080, col_studio=col_studio)
    render_camera_view(renders_dir / "12_human_eye_navigation.png", (2.8, 1.60, 4.6), (-4.2, 1.60, -9.0), lens_mm=30.0, shift_y=0.045, col_studio=col_studio)

    # Scenario B — Direct Sunlight (View 9 + Hero Catalog Preview)
    setup_lighting_scenario("direct_sun", col_studio)
    render_camera_view(renders_dir / "09_direct_sunlight_environment.png", (-4.6, 1.65, 7.2), (1.6, 1.65, -9.0), lens_mm=22.0, shift_y=0.082, col_studio=col_studio)

    # Scenario C — Evening Exhibition (View 10 — empty architectural evening)
    setup_lighting_scenario("evening", col_studio)
    render_camera_view(renders_dir / "10_evening_exhibition_environment.png", (-4.2, 1.65, 6.8), (1.4, 1.65, -9.0), lens_mm=22.0, shift_y=0.080, col_studio=col_studio)

    # Stage E — Temporary 9-Artwork Exhibition Demonstration (View 11 — Daylight & Evening)
    col_demo = bpy.data.collections.new("Demo_Exhibition")
    bpy.context.scene.collection.children.link(col_demo)
    populate_exhibition_demo(col_demo)

    setup_lighting_scenario("soft_daylight", col_studio)
    for spec in ARTWORK_SPECS:
        tx, ty, tz = spec["track_pos"]
        px, py, pz = spec["pos"]
        ld = bpy.data.lights.new(f"Demo_DaySpot_{spec['name']}", type="SPOT")
        ld.energy = 320.0
        ld.spot_size = math.radians(40.0)
        ld.spot_blend = 0.45
        ld.color = hex_rgba("#FFF5E6")[:3]
        lo = bpy.data.objects.new(ld.name, ld)
        lo.matrix_world = look_at_blender_native((tx, ty - 0.06, tz), (px, py, pz))
        col_demo.objects.link(lo)

    render_camera_view(renders_dir / "11_nine_artwork_exhibition.png", (0.0, 1.65, 7.8), (0.0, 1.65, -9.0), lens_mm=22.0, shift_y=0.075, col_studio=col_studio)
    setup_lighting_scenario("evening", col_studio)
    render_camera_view(renders_dir / "11b_nine_artwork_evening.png", (-4.4, 1.65, 6.8), (1.6, 1.65, -9.0), lens_mm=22.0, shift_y=0.075, col_studio=col_studio)

    # Convert the flagship architectural view (`09_direct_sunlight_environment.png`) to catalog `preview.webp`
    preview_webp = ASSET_DIR / "preview.webp"
    cwebp = shutil.which("cwebp")
    if cwebp:
        subprocess.run(
            [cwebp, "-q", "90", str(renders_dir / "09_direct_sunlight_environment.png"), "-o", str(preview_webp)],
            check=True,
        )
    print("Completed all 12 architectural renders and catalog preview.webp")


if __name__ == "__main__":
    main()
