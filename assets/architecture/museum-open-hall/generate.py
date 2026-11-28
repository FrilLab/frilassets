#!/usr/bin/env python3
"""
Reproducible Blender Python Architectural Generator for:
  Open Skylight Museum Hall V2 (`assets/architecture/museum-open-hall/`)

Architectural V2 Capabilities:
  1. Preserves exact 24.00 x 18.00 x 9.00 m main exhibition hall clear dimensions,
     Y = 0.00 m finished floor, all 16 original semantic mesh names, all 9 semantic PBR
     material slots, all 9 artwork anchors, 9 floor placement anchors, 15 lighting anchors,
     and 14 navigation anchors.
  2. Reconstructs the skylight into an expressive 17.0-degree pitched glass conservatory
     lantern roof (`Y = 10.52 m` eaves rising to `Y = 12.72 m` central structural ridge)
     with layered recessed architectural cornice reveals, slender painted-steel king-post
     collar trusses (`Ceiling_Beams`), pitched steel rafters & ridge beam (`Skylight_Supports`),
     fine conservatory glazing mullions & glazed gable ends (`Skylight_Frame`), and sloped
     laminated low-iron glass (`Skylight_Glass`).
  3. Establishes multi-room spatial continuity with zero empty doorway voids:
     - `+Z` Main Entrance opens into an architectural `Entrance_Vestibule` arrival gallery
       (`Z = +10.40..+15.40 m`) with baffled sightline walls and recessed vestibule skylight.
     - `-Z` Main Exhibition Wall features a monumental `4.40 x 4.40 m` central enfilade portal
       connecting to a sunlit `Secondary_Gallery` (`Z = -9.90..-15.70 m`) with overhead daylight
       clerestory, PLUS a sliding architectural pocket partition (`Wall_Back_Portal_Closure`)
       that slides from `x = -4.60 m` (open enfilade) to `x = 0.00 m` (closed flush 24 m wall
       supporting the full 9-artwork configuration including `Anchor_Artwork_Back_02`).
  4. Separates static recessed lighting tracks (`Track_Left`, `Track_Right`, `Track_Back`)
     from 15 independently rotatable spotlight heads (`Fixture_Head_*`, pivoted at yoke
     hinges with local `-Z` optical emission axis).
  5. Bakes a physically path-traced neutral Cycles Ambient Occlusion / Sky-Access atlas
     (`textures/museum_ao.png`) onto secondary UV channel `UVMap_AO` (`TEXCOORD_1`) wired to
     standard glTF `occlusionTexture`, while keeping `TEXCOORD_0` tiling basecolor, roughness,
     and normal maps strictly unbaked and independently customizable.
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

# Core Main Hall Clear Dimensions (glTF meters — strictly preserved)
HALL_WIDTH = 24.00          # X: -12.00 to +12.00
HALL_DEPTH = 18.00          # Z:  -9.00 to  +9.00
CEILING_HEIGHT = 9.00       # Y:   0.00 to  +9.00 primary ceiling soffit

HALF_W = HALL_WIDTH * 0.5   # 12.00 m
HALF_D = HALL_DEPTH * 0.5   #  9.00 m

WALL_THICK = 0.40           # 400 mm structural exterior walls
PORTAL_DEPTH = 1.40         # 1400 mm deep stepped entrance portal (+9.00 to +10.40)
REAR_PORTAL_DEPTH = 0.90    # 900 mm deep double-shell rear portal (-9.00 to -9.90, housing pocket wall)
FLOOR_THICK = 0.32          # 320 mm structural slab (-0.32 to 0.00)

# Main Entrance Opening (+Z)
ENTRANCE_WIDTH = 5.60       # X: -2.80 to +2.80
ENTRANCE_HEIGHT = 4.80      # Y:  0.00 to +4.80
ENTRANCE_FRAME_T = 0.065    # 65 mm anodized bronze-charcoal portal liner

# Optional Central Rear Enfilade Portal (-Z) -> Secondary Exhibition Gallery
REAR_PORTAL_W = 4.40        # X: -2.20 to +2.20 (leaves 9.80 m solid wings on Left & Right!)
REAR_PORTAL_H = 4.40        # Y:  0.00 to +4.40
SEC_GAL_HALF_W = 5.40       # Secondary Gallery interior clear width = 10.80 m (-5.40 to +5.40)
SEC_GAL_Z_END = -15.70      # Secondary Gallery interior rear focal wall Z = -15.70 m (5.80 m clear depth)
SEC_GAL_CEIL_Y = 6.80       # Secondary Gallery ceiling soffit Y = 6.80 m (with Y = 8.10 m skylight coffer)

# Entrance Arrival Vestibule (+Z = +10.40 to +15.40 m — eliminates empty sky voids through entrance!)
VEST_HALF_W = 7.20          # Arrival Vestibule clear width = 14.40 m (-7.20 to +7.20)
VEST_Z_END = 15.40          # Arrival Vestibule rear sightline baffle wall Z = +15.40 m (5.00 m clear depth)
VEST_CEIL_Y = 6.60          # Arrival Vestibule ceiling soffit Y = 6.60 m (with Y = 7.90 m daylight slot)

# Disjoint non-overlapping wall-to-floor & ceiling architectural reveals (>= 18 mm step -> ZERO z-fighting!)
BASE_REVEAL_H = 0.032       # 32 mm recessed museum shadow-gap base height
BASE_REVEAL_D = 0.028       # 28 mm recessed base channel depth
TOP_WALL_REVEAL_H = 0.028   # 28 mm crisp ceiling shadow reveal on front & rear walls
TOP_WALL_REVEAL_D = 0.024

# Floating Ceiling Canopy & Side Daylight/Shadow Coves
COVE_SIDE_W = 0.64          # 640 mm wide architectural side coves along Wall_Left & Wall_Right
COVE_TOP_Y = 9.72           # 720 mm deep canopy fascia & side cove pocket; sealed light-tight above

# Reconstructed Pitched Lantern Skylight (15.20 m x 13.60 m opening, 17.2 deg pitched glass roof)
SKYLIGHT_W = 15.20          # X: -7.60 to +7.60 at Y = 9.00 m ceiling opening
SKYLIGHT_D = 13.60          # Z: -6.80 to +6.80 at Y = 9.00 m ceiling opening
SKY_HALF_W = SKYLIGHT_W * 0.5   # 7.60 m
SKY_HALF_D = SKYLIGHT_D * 0.5   # 6.80 m
SKY_CORNICE_Y = 9.34        # Tier 1 vertical cornice fascia top (steps out 120 mm to +-7.72 x +-6.92)
SKY_STEP_W = 7.72
SKY_STEP_D = 6.92
SKY_EAVE_W = 7.86           # Tier 2 canted plaster light-well top at Y = 10.48 m (+-7.86 x +-7.06)
SKY_EAVE_D = 7.06
SKY_WELL_TOP_Y = 10.48      # Top of canted plaster skylight well / eave springline
SKY_EAVE_Y = 10.56          # Glazing eave elevation at X = +-7.86 m
SKY_RIDGE_Y = 12.98         # Central structural ridge elevation at X = 0.00 m (2.42 m rise = 17.1 deg pitch!)

# Recessed U-shaped architectural lighting track slots centered in the floating soffit wings
TRACK_X = 9.48              # Centerline of Left/Right soffit wings ((7.60 + 11.36)/2 = 9.48 m)
TRACK_BACK_Z = -7.90        # Centerline of Rear soffit ((-8.98 + -6.80)/2 = -7.89 -> -7.90 m)
TRACK_Z_END = 7.40          # Side tracks run Z = -7.90 to +7.40 m
TRACK_SLOT_W = 0.084        # 84 mm recessed ceiling track channel width
TRACK_SLOT_D = 0.076        # 76 mm recessed ceiling track channel depth
SPOT_PIVOT_Y = 8.920        # Yoke pivot elevation of adjustable spotlight heads

# Exhibition Artwork Mounting Anchors (9 preserved primary positions + 1 optional secondary gallery focal anchor)
ARTWORK_CENTER_Y = 1.55
ARTWORK_MIN_BOTTOM_Y = 0.25
ARTWORK_MAX_CENTERED_H = round((ARTWORK_CENTER_Y - ARTWORK_MIN_BOTTOM_Y) * 2.0, 4)  # 2.60 m
ARTWORK_MAX_SHIFTED_H = 5.60
WALL_EPS = 0.003            # 3 mm proud of plaster surface

ARTWORK_SPECS = [
    # Back wall (Z = -9.00, inward normal +Z)
    {
        "name": "Anchor_Artwork_Back_01",
        "nav_name": "Anchor_Navigation_Artwork_01",
        "light_name": "Anchor_Light_Back_01",
        "head_name": "Fixture_Head_Back_01",
        "wall": "Wall_Back",
        "pos": (-6.60, ARTWORK_CENTER_Y, -HALF_D + WALL_EPS),
        "axes": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "max_width": 4.60,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.80,
        "nav_dist": 3.60,
        "track_pos": (-6.60, SPOT_PIVOT_Y, TRACK_BACK_Z),
    },
    {
        "name": "Anchor_Artwork_Back_02",
        "nav_name": "Anchor_Navigation_Artwork_02",
        "light_name": "Anchor_Light_Back_02",
        "head_name": "Fixture_Head_Back_03",
        "wall": "Wall_Back_Portal_Closure",
        "pos": (0.00, ARTWORK_CENTER_Y, -HALF_D + WALL_EPS),
        "axes": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "max_width": 4.00,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.80,
        "nav_dist": 3.80,
        "track_pos": (0.00, SPOT_PIVOT_Y, TRACK_BACK_Z),
    },
    {
        "name": "Anchor_Artwork_Back_03",
        "nav_name": "Anchor_Navigation_Artwork_03",
        "light_name": "Anchor_Light_Back_03",
        "head_name": "Fixture_Head_Back_05",
        "wall": "Wall_Back",
        "pos": (6.60, ARTWORK_CENTER_Y, -HALF_D + WALL_EPS),
        "axes": ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "max_width": 4.60,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.80,
        "nav_dist": 3.60,
        "track_pos": (6.60, SPOT_PIVOT_Y, TRACK_BACK_Z),
    },
    # Left wall (X = -12.00, inward normal +X)
    {
        "name": "Anchor_Artwork_Left_01",
        "nav_name": "Anchor_Navigation_Artwork_04",
        "light_name": "Anchor_Light_Left_01",
        "head_name": "Fixture_Head_Left_01",
        "wall": "Wall_Left",
        "pos": (-HALF_W + WALL_EPS, ARTWORK_CENTER_Y, -5.20),
        "axes": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (-TRACK_X, SPOT_PIVOT_Y, -5.20),
    },
    {
        "name": "Anchor_Artwork_Left_02",
        "nav_name": "Anchor_Navigation_Artwork_05",
        "light_name": "Anchor_Light_Left_02",
        "head_name": "Fixture_Head_Left_03",
        "wall": "Wall_Left",
        "pos": (-HALF_W + WALL_EPS, ARTWORK_CENTER_Y, 0.00),
        "axes": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        "max_width": 4.00,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (-TRACK_X, SPOT_PIVOT_Y, 0.00),
    },
    {
        "name": "Anchor_Artwork_Left_03",
        "nav_name": "Anchor_Navigation_Artwork_06",
        "light_name": "Anchor_Light_Left_03",
        "head_name": "Fixture_Head_Left_05",
        "wall": "Wall_Left",
        "pos": (-HALF_W + WALL_EPS, ARTWORK_CENTER_Y, 5.20),
        "axes": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (-TRACK_X, SPOT_PIVOT_Y, 5.20),
    },
    # Right wall (X = +12.00, inward normal -X)
    {
        "name": "Anchor_Artwork_Right_01",
        "nav_name": "Anchor_Navigation_Artwork_07",
        "light_name": "Anchor_Light_Right_01",
        "head_name": "Fixture_Head_Right_01",
        "wall": "Wall_Right",
        "pos": (HALF_W - WALL_EPS, ARTWORK_CENTER_Y, -5.20),
        "axes": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (TRACK_X, SPOT_PIVOT_Y, -5.20),
    },
    {
        "name": "Anchor_Artwork_Right_02",
        "nav_name": "Anchor_Navigation_Artwork_08",
        "light_name": "Anchor_Light_Right_02",
        "head_name": "Fixture_Head_Right_03",
        "wall": "Wall_Right",
        "pos": (HALF_W - WALL_EPS, ARTWORK_CENTER_Y, 0.00),
        "axes": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)),
        "max_width": 4.00,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (TRACK_X, SPOT_PIVOT_Y, 0.00),
    },
    {
        "name": "Anchor_Artwork_Right_03",
        "nav_name": "Anchor_Navigation_Artwork_09",
        "light_name": "Anchor_Light_Right_03",
        "head_name": "Fixture_Head_Right_05",
        "wall": "Wall_Right",
        "pos": (HALF_W - WALL_EPS, ARTWORK_CENTER_Y, 5.20),
        "axes": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0), (-1.0, 0.0, 0.0)),
        "max_width": 3.80,
        "max_height": ARTWORK_MAX_CENTERED_H,
        "clearance": 0.70,
        "nav_dist": 3.50,
        "track_pos": (TRACK_X, SPOT_PIVOT_Y, 5.20),
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
    return Vector((x, -z, y))


def g2b_vec(v: Sequence[float]) -> Vector:
    return Vector((v[0], -v[2], v[1]))


def make_gltf_basis_matrix(
    pos_g: Tuple[float, float, float],
    x_axis_g: Tuple[float, float, float],
    y_axis_g: Tuple[float, float, float],
    z_axis_g: Tuple[float, float, float],
) -> Matrix:
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
    m_g = _build_look_matrix_gltf(eye_g, target_g, up_g)
    return R_G2B.to_4x4() @ m_g @ R_B2G.to_4x4()


def look_at_blender_native(
    eye_g: Tuple[float, float, float],
    target_g: Tuple[float, float, float],
    up_g: Tuple[float, float, float] = (0.0, 1.0, 0.0),
) -> Matrix:
    m_g = _build_look_matrix_gltf(eye_g, target_g, up_g)
    return R_G2B.to_4x4() @ m_g


# ---------------------------------------------------------------------------
# Architectural Mesh Builder
# ---------------------------------------------------------------------------


class ArchMesh:
    """Accumulates clean manifold architectural geometry in glTF metric coordinates."""

    def __init__(self, name: str, uv_scale_meters: float = 6.0):
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
        bevel: float = 0.0,
    ) -> None:
        """Closed 6-face manifold hexahedron with outward-recalculated normals."""
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

    def add_pitched_prism_z(
        self,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
        thickness_up: float,
        z0: float,
        z1: float,
        bevel: float = 0.0,
    ) -> None:
        """
        Extrude a sloped architectural element (rafter, mullion, or pitched glass sheet)
        from (x0, y0) to (x1, y1) in XY with perpendicular upward thickness `thickness_up`
        spanning Z in [z0, z1]. Assumes x1 > x0 so normal (-dy, dx) points upward (+Y).
        """
        dx = x1 - x0
        dy = y1 - y0
        ln = math.hypot(dx, dy)
        if ln < 1e-6:
            return
        nx = -dy / ln * thickness_up
        ny = dx / ln * thickness_up
        self.add_hexahedron_g(
            (x0, y0, z0),
            (x1, y1, z0),
            (x1, y1, z1),
            (x0, y0, z1),
            (x0 + nx, y0 + ny, z0),
            (x1 + nx, y1 + ny, z0),
            (x1 + nx, y1 + ny, z1),
            (x0 + nx, y0 + ny, z1),
            bevel=bevel,
        )

    def add_strut_box_xy(
        self,
        p0_xy: Tuple[float, float],
        p1_xy: Tuple[float, float],
        width_xy: float,
        depth_z: float,
        z_center: float,
    ) -> None:
        """Slender rectangular steel truss member in the XY plane centered at `z_center`."""
        dx = p1_xy[0] - p0_xy[0]
        dy = p1_xy[1] - p0_xy[1]
        ln = math.hypot(dx, dy)
        if ln < 1e-6:
            return
        nx = -dy / ln * (width_xy * 0.5)
        ny = dx / ln * (width_xy * 0.5)
        hz = depth_z * 0.5
        self.add_hexahedron_g(
            (p0_xy[0] - nx, p0_xy[1] - ny, z_center - hz),
            (p1_xy[0] - nx, p1_xy[1] - ny, z_center - hz),
            (p1_xy[0] - nx, p1_xy[1] - ny, z_center + hz),
            (p0_xy[0] - nx, p0_xy[1] - ny, z_center + hz),
            (p0_xy[0] + nx, p0_xy[1] + ny, z_center - hz),
            (p1_xy[0] + nx, p1_xy[1] + ny, z_center - hz),
            (p1_xy[0] + nx, p1_xy[1] + ny, z_center + hz),
            (p0_xy[0] + nx, p0_xy[1] + ny, z_center + hz),
        )

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

        # Primary world-scale cubic box UV mapping (`UVMap` / TEXCOORD_0)
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
# Architectural Shell, Multi-Room Continuity, & Pitched Skylight Construction
# ---------------------------------------------------------------------------


def build_floor(
    arch_parent: bpy.types.Object,
    col: bpy.types.Collection,
    mat_floor: bpy.types.Material,
) -> bpy.types.Object:
    """
    Continuous poured & power-troweled architectural concrete floor across Main Hall,
    Entrance Portal, Secondary Gallery threshold, and Arrival Vestibule (top strictly Y = 0.000 m).
    Uses crisp 5 mm saw-cut control joints with 1.2 mm micro-bevels to prevent sub-pixel WebGL aliasing.
    """
    builder = ArchMesh("Floor", uv_scale_meters=6.4)
    joint_d = 0.0040  # 4.0 mm control joint base

    # 1. Structural base slab (-0.32 m to -0.004 m) under Main Hall, Portals, Secondary Gallery, and Vestibule
    builder.add_box_g(-HALF_W - WALL_THICK, HALF_W + WALL_THICK, -FLOOR_THICK, -joint_d, -HALF_D - REAR_PORTAL_DEPTH, HALF_D + PORTAL_DEPTH)
    builder.add_box_g(-SEC_GAL_HALF_W - WALL_THICK, SEC_GAL_HALF_W + WALL_THICK, -FLOOR_THICK, -joint_d, SEC_GAL_Z_END - WALL_THICK, -HALF_D - REAR_PORTAL_DEPTH)
    builder.add_box_g(-VEST_HALF_W - WALL_THICK, VEST_HALF_W + WALL_THICK, -FLOOR_THICK, -joint_d, HALF_D + PORTAL_DEPTH, VEST_Z_END + WALL_THICK)

    # 2. Main Hall finished concrete pour bays (-0.004 m to 0.000 m) aligned with portal jambs!
    gap = 0.0050
    hg = gap * 0.5
    ox = HALF_W + BASE_REVEAL_D + 0.01  # 12.038 m (extends cleanly under 28 mm base reveal)
    oz = HALF_D + BASE_REVEAL_D + 0.01  #  9.038 m
    x_cuts = [-ox, -7.00, -ENTRANCE_WIDTH * 0.5, ENTRANCE_WIDTH * 0.5, 7.00, ox]
    z_cuts = [-oz, -4.50, 0.00, 4.50, oz]

    for ix in range(len(x_cuts) - 1):
        for iz in range(len(z_cuts) - 1):
            builder.add_box_g(
                x_cuts[ix] + hg,
                x_cuts[ix + 1] - hg,
                -joint_d,
                0.0,
                z_cuts[iz] + hg,
                z_cuts[iz + 1] - hg,
                bevel=0.0012,
            )

    # 3. Entrance Portal & Arrival Vestibule finished floor slabs (+9.038 m to +15.44 m)
    ew = ENTRANCE_WIDTH * 0.5
    builder.add_box_g(-ew + hg, ew - hg, -joint_d, 0.0, oz + hg, HALF_D + PORTAL_DEPTH - hg, bevel=0.0012)
    vx = VEST_HALF_W + 0.04
    builder.add_box_g(-vx, vx, -joint_d, 0.0, HALF_D + PORTAL_DEPTH + hg, VEST_Z_END + 0.04, bevel=0.0012)

    # 4. Rear Enfilade Portal & Secondary Gallery finished floor slabs (-9.038 m to -15.74 m)
    rw = REAR_PORTAL_W * 0.5
    builder.add_box_g(-rw + hg, rw - hg, -joint_d, 0.0, -HALF_D - REAR_PORTAL_DEPTH + hg, -oz - hg, bevel=0.0012)
    sx = SEC_GAL_HALF_W + 0.04
    builder.add_box_g(-sx, -hg, -joint_d, 0.0, SEC_GAL_Z_END - 0.04, -HALF_D - REAR_PORTAL_DEPTH - hg, bevel=0.0012)
    builder.add_box_g(hg, sx, -joint_d, 0.0, SEC_GAL_Z_END - 0.04, -HALF_D - REAR_PORTAL_DEPTH - hg, bevel=0.0012)

    return builder.finalize(arch_parent, col, mat_floor)


def build_walls_portals_and_extensions(
    arch_parent: bpy.types.Object,
    col: bpy.types.Collection,
    mat_wall: bpy.types.Material,
    mat_portal: bpy.types.Material,
    mat_trim: bpy.types.Material,
) -> None:
    y_bot = BASE_REVEAL_H                                # 0.032 m (strictly disjoint above Y=0 floor!)
    y_cove_wall_top = COVE_TOP_Y                         # 9.720 m
    y_end_wall_top = CEILING_HEIGHT - TOP_WALL_REVEAL_H  # 8.972 m
    bev = 0.0025
    corner_gap = 0.0025

    # ------------------------------------------------------------------
    # 1. Wall_Left (X = -12.40 to -12.00, Z = -9.00 to +9.00)
    # ------------------------------------------------------------------
    wl = ArchMesh("Wall_Left", uv_scale_meters=6.0)
    # Outer structural backing [-12.40, -12.055] (leaves 27 mm clear behind base reveal liner!)
    wl.add_box_g(-HALF_W - WALL_THICK, -HALF_W - 0.055, 0.0, COVE_TOP_Y + 0.14, -HALF_D - REAR_PORTAL_DEPTH, HALF_D + PORTAL_DEPTH)
    # Interior exhibition plaster face [-12.055, -12.000] starting cleanly at y_bot = 0.032 m
    wl.add_box_g(-HALF_W - 0.055, -HALF_W, y_bot, y_cove_wall_top, -HALF_D + corner_gap, HALF_D - corner_gap, bevel=bev)
    wl.finalize(arch_parent, col, mat_wall)

    # ------------------------------------------------------------------
    # 2. Wall_Right (X = +12.00 to +12.40, Z = -9.00 to +9.00)
    # ------------------------------------------------------------------
    wr = ArchMesh("Wall_Right", uv_scale_meters=6.0)
    wr.add_box_g(HALF_W + 0.055, HALF_W + WALL_THICK, 0.0, COVE_TOP_Y + 0.14, -HALF_D - REAR_PORTAL_DEPTH, HALF_D + PORTAL_DEPTH)
    wr.add_box_g(HALF_W, HALF_W + 0.055, y_bot, y_cove_wall_top, -HALF_D + corner_gap, HALF_D - corner_gap, bevel=bev)
    wr.finalize(arch_parent, col, mat_wall)

    # ------------------------------------------------------------------
    # 3. Wall_Back (Z = -9.90 to -9.00, with 4.40 m x 4.40 m Central Enfilade Portal!)
    # ------------------------------------------------------------------
    wb = ArchMesh("Wall_Back", uv_scale_meters=6.0)
    rw = REAR_PORTAL_W * 0.5          # 2.20 m clear portal half-width
    rh = REAR_PORTAL_H                # 4.40 m clear portal height
    ft = ENTRANCE_FRAME_T             # 0.065 m architectural bronze reveal liner
    r_ro_w = rw + ft                  # 2.265 m rough opening

    # Left & Right structural rear wall masses (framing pocket cavity X in [-6.85, -2.265], Z in [-9.58, -9.32])
    wb.add_box_g(-HALF_W - WALL_THICK, -r_ro_w, 0.0, COVE_TOP_Y + 0.14, -HALF_D - REAR_PORTAL_DEPTH, -HALF_D - 0.58)
    wb.add_box_g(-HALF_W - WALL_THICK, -6.90, 0.0, COVE_TOP_Y + 0.14, -HALF_D - 0.58, -HALF_D - 0.055)
    wb.add_box_g(-6.90, -r_ro_w, 4.52, COVE_TOP_Y + 0.14, -HALF_D - 0.58, -HALF_D - 0.055)
    wb.add_box_g(-6.90, -r_ro_w, 0.0, 4.52, -HALF_D - 0.30, -HALF_D - 0.055)
    wb.add_box_g(r_ro_w, HALF_W + WALL_THICK, 0.0, COVE_TOP_Y + 0.14, -HALF_D - REAR_PORTAL_DEPTH, -HALF_D - 0.055)
    # Header lintel above rear portal
    wb.add_box_g(-r_ro_w, r_ro_w, rh + ft, COVE_TOP_Y + 0.14, -HALF_D - REAR_PORTAL_DEPTH, -HALF_D - 0.055)

    # Interior main-hall plaster face at Z = -9.000 m: 5-quad T-junction-free welded grid
    # so `remove_doubles` merges the entire front plaster face into ONE seamless monolithic wall & AO island!
    q_gap = 0.018
    rx_edge = r_ro_w + q_gap
    ry_edge = rh + ft + q_gap
    wb.add_box_g(-HALF_W + corner_gap, -rx_edge, y_bot, ry_edge, -HALF_D - 0.055, -HALF_D, skip_faces=("+y",))
    wb.add_box_g(rx_edge, HALF_W - corner_gap, y_bot, ry_edge, -HALF_D - 0.055, -HALF_D, skip_faces=("+y",))
    wb.add_box_g(-HALF_W + corner_gap, -rx_edge, ry_edge, y_end_wall_top, -HALF_D - 0.055, -HALF_D, skip_faces=("-y", "+x"))
    wb.add_box_g(-rx_edge, rx_edge, ry_edge, y_end_wall_top, -HALF_D - 0.055, -HALF_D, skip_faces=("-x", "+x"))
    wb.add_box_g(rx_edge, HALF_W - corner_gap, ry_edge, y_end_wall_top, -HALF_D - 0.055, -HALF_D, skip_faces=("-y", "-x"))
    # Side-cove upper closures on rear wall
    wb.add_box_g(-HALF_W + corner_gap, -HALF_W + COVE_SIDE_W, y_end_wall_top, y_cove_wall_top, -HALF_D - 0.055, -HALF_D)
    wb.add_box_g(HALF_W - COVE_SIDE_W, HALF_W - corner_gap, y_end_wall_top, y_cove_wall_top, -HALF_D - 0.055, -HALF_D)
    wb.finalize(arch_parent, col, mat_wall)

    # ------------------------------------------------------------------
    # 3b. Wall_Back_Portal_Closure (Optional Sliding Architectural Pocket Partition)
    #     Closes flush across [-2.28, +2.28] x [0.032, 4.48] at Z = -9.000 m when position == (0,0,0)!
    # ------------------------------------------------------------------
    wpc = ArchMesh("Wall_Back_Portal_Closure", uv_scale_meters=6.0)
    wpc.add_box_g(-r_ro_w - q_gap + 0.003, r_ro_w + q_gap - 0.003, y_bot, rh + ft + q_gap - 0.003, -HALF_D - 0.16, -HALF_D, bevel=0.0015)
    wpc_obj = wpc.finalize(arch_parent, col, mat_wall)
    wpc_obj.matrix_world = make_gltf_basis_matrix(
        (-4.62, 0.0, -0.38),
        (1.0, 0.0, 0.0),
        (0.0, 1.0, 0.0),
        (0.0, 0.0, 1.0),
    )
    wpc_obj["portalClosureRole"] = "sliding-pocket-wall"
    wpc_obj["openPositionGltf"] = [-4.62, 0.0, -0.38]
    wpc_obj["closedPositionGltf"] = [0.0, 0.0, 0.0]

    # ------------------------------------------------------------------
    # 3c. Secondary_Gallery (Modular Apse Exhibition Extension Z = -9.90 to -15.70 m)
    #     Features warm exhibition walls + overhead canted daylight clerestory skylight!
    # ------------------------------------------------------------------
    sgal = ArchMesh("Secondary_Gallery", uv_scale_meters=6.0)
    sw = SEC_GAL_HALF_W       # 5.40 m
    sz0 = SEC_GAL_Z_END       # -15.70 m
    sz1 = -HALF_D - REAR_PORTAL_DEPTH  # -9.90 m
    sh = SEC_GAL_CEIL_Y       # 6.80 m
    # Rear focal exhibition wall (Z = -16.10 to -15.70)
    sgal.add_box_g(-sw - WALL_THICK, sw + WALL_THICK, y_bot, sh + 1.40, sz0 - WALL_THICK, sz0, bevel=bev)
    # Left & Right exhibition walls of Secondary Gallery
    sgal.add_box_g(-sw - WALL_THICK, -sw, y_bot, sh + 1.40, sz0, sz1, bevel=bev)
    sgal.add_box_g(sw, sw + WALL_THICK, y_bot, sh + 1.40, sz0, sz1, bevel=bev)
    # Front return wall wings flanking the 4.40 m portal inside Secondary Gallery (Z = -9.95 to -9.90)
    sgal.add_box_g(-sw, -r_ro_w, y_bot, sh, sz1 - 0.05, sz1, bevel=bev)
    sgal.add_box_g(r_ro_w, sw, y_bot, sh, sz1 - 0.05, sz1, bevel=bev)
    sgal.add_box_g(-r_ro_w, r_ro_w, rh + ft, sh, sz1 - 0.05, sz1, bevel=bev)
    # Secondary Gallery ceiling soffit (Y = 6.80 to 8.10 m) framing a luminous 6.80 x 2.80 m skylight well
    # centered over the focal rear wall (X in [-3.40, +3.40], Z in [-14.80, -12.00])!
    sgal.add_box_g(-sw - WALL_THICK, sw + WALL_THICK, sh, sh + 1.30, sz0 - WALL_THICK, -14.80, bevel=bev)
    sgal.add_box_g(-sw - WALL_THICK, sw + WALL_THICK, sh, sh + 1.30, -12.00, sz1, bevel=bev)
    sgal.add_box_g(-sw - WALL_THICK, -3.40, sh, sh + 1.30, -14.80, -12.00, bevel=bev)
    sgal.add_box_g(3.40, sw + WALL_THICK, sh, sh + 1.30, -14.80, -12.00, bevel=bev)
    sgal.finalize(arch_parent, col, mat_wall)

    # ------------------------------------------------------------------
    # 4. Wall_Entrance (Z = +9.00 to +10.40 with 5.60 m x 4.80 m Monumental Portal)
    # ------------------------------------------------------------------
    we = ArchMesh("Wall_Entrance", uv_scale_meters=6.0)
    ew = ENTRANCE_WIDTH * 0.5   # 2.80 m
    eh = ENTRANCE_HEIGHT        # 4.80 m
    e_ro_w = ew + ft            # 2.865 m

    # Structural piers (+9.055 to +10.40)
    we.add_box_g(-HALF_W - WALL_THICK, -e_ro_w, 0.0, COVE_TOP_Y + 0.14, HALF_D + 0.055, HALF_D + PORTAL_DEPTH)
    we.add_box_g(e_ro_w, HALF_W + WALL_THICK, 0.0, COVE_TOP_Y + 0.14, HALF_D + 0.055, HALF_D + PORTAL_DEPTH)
    we.add_box_g(-e_ro_w, e_ro_w, eh + ft, COVE_TOP_Y + 0.14, HALF_D + 0.055, HALF_D + PORTAL_DEPTH)

    # Interior plaster face at Z = +9.000 m: 5-quad T-junction-free welded monolithic grid!
    ex_edge = e_ro_w + q_gap
    ey_edge = eh + ft + q_gap
    we.add_box_g(-HALF_W + corner_gap, -ex_edge, y_bot, ey_edge, HALF_D, HALF_D + 0.055, skip_faces=("+y",))
    we.add_box_g(ex_edge, HALF_W - corner_gap, y_bot, ey_edge, HALF_D, HALF_D + 0.055, skip_faces=("+y",))
    we.add_box_g(-HALF_W + corner_gap, -ex_edge, ey_edge, y_end_wall_top, HALF_D, HALF_D + 0.055, skip_faces=("-y", "+x"))
    we.add_box_g(-ex_edge, ex_edge, ey_edge, y_end_wall_top, HALF_D, HALF_D + 0.055, skip_faces=("-x", "+x"))
    we.add_box_g(ex_edge, HALF_W - corner_gap, ey_edge, y_end_wall_top, HALF_D, HALF_D + 0.055, skip_faces=("-y", "-x"))
    we.add_box_g(-HALF_W + corner_gap, -HALF_W + COVE_SIDE_W, y_end_wall_top, y_cove_wall_top, HALF_D, HALF_D + 0.055)
    we.add_box_g(HALF_W - COVE_SIDE_W, HALF_W - corner_gap, y_end_wall_top, y_cove_wall_top, HALF_D, HALF_D + 0.055)
    we.finalize(arch_parent, col, mat_wall)

    # ------------------------------------------------------------------
    # 4b. Entrance_Vestibule (Architectural Arrival Gallery Z = +10.40 to +15.40 m)
    #     Eliminates any raw background void when viewing toward the entrance!
    # ------------------------------------------------------------------
    vest = ArchMesh("Entrance_Vestibule", uv_scale_meters=6.0)
    vw = VEST_HALF_W            # 7.20 m
    vz0 = HALF_D + PORTAL_DEPTH # +10.40 m
    vz1 = VEST_Z_END            # +15.40 m
    vh = VEST_CEIL_Y            #  6.60 m
    # Rear arrival sightline baffle wall (Z = +15.40 to +15.80)
    vest.add_box_g(-vw - WALL_THICK, vw + WALL_THICK, y_bot, vh + 1.30, vz1, vz1 + WALL_THICK, bevel=bev)
    # Side arrival gallery walls (with sheltered lateral vestibule openings beyond X = +-7.20 out of hall sightlines)
    vest.add_box_g(-vw - WALL_THICK, -vw, y_bot, vh + 1.30, vz0, vz1, bevel=bev)
    vest.add_box_g(vw, vw + WALL_THICK, y_bot, vh + 1.30, vz0, vz1, bevel=bev)
    # Inner vestibule return cheeks around entrance portal
    vest.add_box_g(-vw, -e_ro_w, y_bot, vh, vz0, vz0 + 0.05, bevel=bev)
    vest.add_box_g(e_ro_w, vw, y_bot, vh, vz0, vz0 + 0.05, bevel=bev)
    vest.add_box_g(-e_ro_w, e_ro_w, eh + ft, vh, vz0, vz0 + 0.05, bevel=bev)
    # Vestibule ceiling soffit framing an overhead 8.40 x 2.20 m daylight clerestory slot (Z = +12.20..+14.40)
    vest.add_box_g(-vw - WALL_THICK, vw + WALL_THICK, vh, vh + 1.30, vz0, 12.20, bevel=bev)
    vest.add_box_g(-vw - WALL_THICK, vw + WALL_THICK, vh, vh + 1.30, 14.40, vz1 + WALL_THICK, bevel=bev)
    vest.add_box_g(-vw - WALL_THICK, -4.20, vh, vh + 1.30, 12.20, 14.40, bevel=bev)
    vest.add_box_g(4.20, vw + WALL_THICK, vh, vh + 1.30, 12.20, 14.40, bevel=bev)
    vest.finalize(arch_parent, col, mat_wall)

    # ------------------------------------------------------------------
    # 5. Entrance_Frame (Full-Depth Architectural Dark Bronze-Oak Portal Sleeves!)
    #    Inspired directly by the deep dark-lined enfilade portals in Reference Photo 0:
    #    inset 18 mm behind plaster face (ZERO z-fighting!) and spanning the full portal depth!
    # ------------------------------------------------------------------
    ef = ArchMesh("Entrance_Frame", uv_scale_meters=2.0)
    # Main Entrance full-depth architectural sleeve: Z = +9.022 to +10.38 m
    ef.add_box_g(-e_ro_w, -ew, 0.002, eh, HALF_D + 0.022, HALF_D + PORTAL_DEPTH - 0.02, bevel=0.003)
    ef.add_box_g(ew, e_ro_w, 0.002, eh, HALF_D + 0.022, HALF_D + PORTAL_DEPTH - 0.02, bevel=0.003)
    ef.add_box_g(-e_ro_w, e_ro_w, eh, eh + ft, HALF_D + 0.022, HALF_D + PORTAL_DEPTH - 0.02, bevel=0.003)
    # Rear Enfilade Portal full-depth architectural sleeve: Z = -9.88 to -9.18 m
    # (Starts at Z = -9.18 m so when Wall_Back_Portal_Closure closes at Z = -9.16..-9.00, the sleeve sits cleanly behind it!)
    ef.add_box_g(-r_ro_w, -rw, 0.002, rh, -HALF_D - REAR_PORTAL_DEPTH + 0.02, -HALF_D - 0.18, bevel=0.003)
    ef.add_box_g(rw, r_ro_w, 0.002, rh, -HALF_D - REAR_PORTAL_DEPTH + 0.02, -HALF_D - 0.18, bevel=0.003)
    ef.add_box_g(-r_ro_w, r_ro_w, rh, rh + ft, -HALF_D - REAR_PORTAL_DEPTH + 0.02, -HALF_D - 0.18, bevel=0.003)
    ef.finalize(arch_parent, col, mat_portal)

    # ------------------------------------------------------------------
    # 6. Wall_Floor_Transitions (Disjoint Recessed Base & Ceiling Shadow-Gap Channels
    #    across Main Hall, Secondary Gallery, and Entrance Vestibule!)
    # ------------------------------------------------------------------
    wt = ArchMesh("Wall_Floor_Transitions", uv_scale_meters=1.5)
    t_th = 0.008
    d0 = BASE_REVEAL_D
    d1 = BASE_REVEAL_D + t_th
    yb0 = 0.002
    yb1 = BASE_REVEAL_H - 0.002

    # Main Hall Left & Right base channels
    wt.add_box_g(-HALF_W - d1, -HALF_W - d0, yb0, yb1, -HALF_D - d1, HALF_D + d1)
    wt.add_box_g(HALF_W + d0, HALF_W + d1, yb0, yb1, -HALF_D - d1, HALF_D + d1)
    # Main Hall Back wall base channels
    wt.add_box_g(-HALF_W - d1, -r_ro_w, yb0, yb1, -HALF_D - d1, -HALF_D - d0)
    wt.add_box_g(r_ro_w, HALF_W + d1, yb0, yb1, -HALF_D - d1, -HALF_D - d0)
    # Main Hall Entrance wall base channels
    wt.add_box_g(-HALF_W - d1, -e_ro_w, yb0, yb1, HALF_D + d0, HALF_D + d1)
    wt.add_box_g(e_ro_w, HALF_W + d1, yb0, yb1, HALF_D + d0, HALF_D + d1)
    # Secondary Gallery base shadow-reveal channels (grounds the enfilade gallery walls!)
    wt.add_box_g(-sw - d1, sw + d1, yb0, yb1, sz0 - d1, sz0 - d0)
    wt.add_box_g(-sw - d1, -sw - d0, yb0, yb1, sz0 - d1, sz1 + d1)
    wt.add_box_g(sw + d0, sw + d1, yb0, yb1, sz0 - d1, sz1 + d1)
    # Entrance Vestibule base shadow-reveal channels
    wt.add_box_g(-vw - d1, vw + d1, yb0, yb1, vz1 + d0, vz1 + d1)
    wt.add_box_g(-vw - d1, -vw - d0, yb0, yb1, vz0 - d1, vz1 + d1)
    wt.add_box_g(vw + d0, vw + d1, yb0, yb1, vz0 - d1, vz1 + d1)
    # Upper ceiling shadow-reveal channels on Rear & Entrance walls
    cx = HALF_W - COVE_SIDE_W
    td0, td1 = TOP_WALL_REVEAL_D, TOP_WALL_REVEAL_D + t_th
    wt.add_box_g(-cx, cx, y_end_wall_top + 0.002, CEILING_HEIGHT - 0.002, -HALF_D - td1, -HALF_D - td0)
    wt.add_box_g(-cx, cx, y_end_wall_top + 0.002, CEILING_HEIGHT - 0.002, HALF_D + td0, HALF_D + td1)
    wt.finalize(arch_parent, col, mat_trim)


def build_ceiling_and_pitched_skylight(
    arch_parent: bpy.types.Object,
    sky_parent: bpy.types.Object,
    col_arch: bpy.types.Collection,
    col_sky: bpy.types.Collection,
    mat_ceiling: bpy.types.Material,
    mat_beam: bpy.types.Material,
    mat_sky_frame: bpy.types.Material,
    mat_sky_glass: bpy.types.Material,
) -> None:
    """
    Reconstructed V2 Ceiling & Pitched Conservatory Lantern Skylight:
      - Floating `9.00 m` ceiling canopy with `640 mm` side coves, recessed U-shaped track slot,
        and two-tier stepped + canted architectural skylight cornice well (`Y = 9.00 -> 9.32 -> 10.48 m`).
      - Slender painted-steel king-post collar trusses (`Ceiling_Beams`) that leave the sky unobstructed.
      - 16.9-degree dual-pitched steel rafters, purlins, and central structural ridge (`Skylight_Supports`).
      - Fine conservatory glazing mullions + glazed gable end frames (`Skylight_Frame`).
      - Pitched low-iron laminated glass slopes + glazed gable ends + secondary skylight diffusers (`Skylight_Glass`).
    """
    cm = ArchMesh("Ceiling", uv_scale_meters=5.4)
    ox = HALF_W + WALL_THICK                 # 12.40 m
    oz0 = -HALF_D - REAR_PORTAL_DEPTH        # -9.90 m
    oz1 = HALF_D + PORTAL_DEPTH              # +10.40 m
    y_soffit = CEILING_HEIGHT                #  9.000 m
    y_slot_top = CEILING_HEIGHT + TRACK_SLOT_D  # 9.076 m
    y_cove_top = COVE_TOP_Y                  #  9.720 m
    y_roof_top = SKY_WELL_TOP_Y              # 10.480 m

    ix0, iz0 = SKY_HALF_W, SKY_HALF_D        # 7.00, 6.00 m at Y = 9.00 m
    sx1, sz1 = SKY_STEP_W, SKY_STEP_D        # 7.12, 6.12 m at Y = 9.32 m cornice shelf
    wx2, wz2 = SKY_EAVE_W, SKY_EAVE_D        # 7.24, 6.24 m at Y = 10.48 m eave curb
    bx, bz = wx2 + 0.12, wz2 + 0.12          # 7.36, 6.36 m outer backing plane of skylight collar

    cx = HALF_W - COVE_SIDE_W                # 11.36 m (640 mm side daylight coves!)
    cz0 = -HALF_D - TOP_WALL_REVEAL_D        # -9.024 m
    cz1 = HALF_D + TOP_WALL_REVEAL_D         # +9.024 m

    # A. Light-tight upper structural roof slab (Y = 9.720 to 10.480 m) outside [-bx, +bx] x [-bz, +bz]
    cm.add_box_g(-ox, ox, y_cove_top, y_roof_top, oz0, -bz)
    cm.add_box_g(-ox, ox, y_cove_top, y_roof_top, bz, oz1)
    cm.add_box_g(-ox, -bx, y_cove_top, y_roof_top, -bz, bz)
    cm.add_box_g(bx, ox, y_cove_top, y_roof_top, -bz, bz)

    # B. Floating canopy core (Y = 9.076 to 9.720 m) spanning [-cx, +cx] x [cz0, cz1] around [-bx, +bx] x [-bz, +bz]
    cm.add_box_g(-cx, cx, y_slot_top, y_cove_top, cz0, -bz)
    cm.add_box_g(-cx, cx, y_slot_top, y_cove_top, bz, cz1)
    cm.add_box_g(-cx, -bx, y_slot_top, y_cove_top, -bz, bz)
    cm.add_box_g(bx, cx, y_slot_top, y_cove_top, -bz, bz)
    # Structural ceiling closure above rear & entrance portals
    cm.add_box_g(-ox, ox, y_soffit, y_cove_top, oz0, cz0)
    cm.add_box_g(-ox, ox, y_soffit, y_cove_top, cz1, oz1)

    # C. Lower ceiling soffit layer (Y = 9.000 to 9.076 m) subdivided cleanly around the U-shaped recessed track slot!
    hs = TRACK_SLOT_W * 0.5                   # 0.042 m
    tx0, tx1 = TRACK_X - hs, TRACK_X + hs     # 9.138, 9.222
    tbz0, tbz1 = TRACK_BACK_Z - hs, TRACK_BACK_Z + hs  # -7.492, -7.408
    tz_end = TRACK_Z_END + hs                 # +6.842
    c_bev = 0.003

    cm.add_box_g(-cx, cx, y_soffit, y_slot_top, cz0, tbz0, bevel=c_bev)
    cm.add_box_g(-cx, -tx1, y_soffit, y_slot_top, tbz0, cz1, bevel=c_bev)
    cm.add_box_g(tx1, cx, y_soffit, y_slot_top, tbz0, cz1, bevel=c_bev)
    cm.add_box_g(-tx1, tx1, y_soffit, y_slot_top, tz_end, cz1, bevel=c_bev)
    cm.add_box_g(-tx0, tx0, y_soffit, y_slot_top, tbz1, -bz)
    cm.add_box_g(-tx0, tx0, y_soffit, y_slot_top, bz, tz_end)
    cm.add_box_g(-tx0, -bx, y_soffit, y_slot_top, -bz, bz)
    cm.add_box_g(bx, tx0, y_soffit, y_slot_top, -bz, bz)

    # D. Layered Recessed Architectural Skylight Reveals & Cornice:
    #    Tier 1 (Y = 9.000 to 9.320 m): Crisp vertical cornice fascia ring [-bx..+bx] -> [-ix0..+ix0]
    cm.add_box_g(-bx, bx, y_soffit, SKY_CORNICE_Y, -bz, -iz0, bevel=0.0025)
    cm.add_box_g(-bx, bx, y_soffit, SKY_CORNICE_Y, iz0, bz, bevel=0.0025)
    cm.add_box_g(-bx, -ix0, y_soffit, SKY_CORNICE_Y, -iz0, iz0, bevel=0.0025)
    cm.add_box_g(ix0, bx, y_soffit, SKY_CORNICE_Y, -iz0, iz0, bevel=0.0025)

    #    Tier 2 (Y = 9.320 to 10.480 m): Stepped 120 mm horizontal cornice shelf + 4 closed canted plaster well solids!
    cm.add_hexahedron_g(
        (-bx, SKY_CORNICE_Y, -bz), (bx, SKY_CORNICE_Y, -bz), (sx1, SKY_CORNICE_Y, -sz1), (-sx1, SKY_CORNICE_Y, -sz1),
        (-bx, y_roof_top, -bz), (bx, y_roof_top, -bz), (wx2, y_roof_top, -wz2), (-wx2, y_roof_top, -wz2),
    )
    cm.add_hexahedron_g(
        (-sx1, SKY_CORNICE_Y, sz1), (sx1, SKY_CORNICE_Y, sz1), (bx, SKY_CORNICE_Y, bz), (-bx, SKY_CORNICE_Y, bz),
        (-wx2, y_roof_top, wz2), (wx2, y_roof_top, wz2), (bx, y_roof_top, bz), (-bx, y_roof_top, bz),
    )
    cm.add_hexahedron_g(
        (-bx, SKY_CORNICE_Y, -bz), (-sx1, SKY_CORNICE_Y, -sz1), (-sx1, SKY_CORNICE_Y, sz1), (-bx, SKY_CORNICE_Y, bz),
        (-bx, y_roof_top, -bz), (-wx2, y_roof_top, -wz2), (-wx2, y_roof_top, wz2), (-bx, y_roof_top, bz),
    )
    cm.add_hexahedron_g(
        (sx1, SKY_CORNICE_Y, -sz1), (bx, SKY_CORNICE_Y, -bz), (bx, SKY_CORNICE_Y, bz), (sx1, SKY_CORNICE_Y, sz1),
        (wx2, y_roof_top, -wz2), (bx, y_roof_top, -bz), (bx, y_roof_top, bz), (wx2, y_roof_top, wz2),
    )
    cm.finalize(arch_parent, col_arch, mat_ceiling)

    # ------------------------------------------------------------------
    # 2. Ceiling_Beams: 5 Slender Architectural Steel King-Post Collar Trusses
    #    at Z = -4.50, -2.25, 0.00, +2.25, +4.50 m!
    # ------------------------------------------------------------------
    cb = ArchMesh("Ceiling_Beams", uv_scale_meters=3.0)
    truss_z_positions = (-4.50, -2.25, 0.00, 2.25, 4.50)
    chord_y0, chord_y1 = 10.36, 10.456
    chord_ymid = 0.5 * (chord_y0 + chord_y1)
    ridge_node_y = SKY_RIDGE_Y - 0.16

    for tz in truss_z_positions:
        cb.add_box_g(-wx2 - 0.06, wx2 + 0.06, chord_y0, chord_y1, tz - 0.032, tz + 0.032, bevel=0.002)
        cb.add_box_g(-0.018, 0.018, chord_y1, ridge_node_y, tz - 0.018, tz + 0.018)
        cb.add_strut_box_xy((-3.93, chord_ymid), (0.0, ridge_node_y - 0.04), width_xy=0.028, depth_z=0.028, z_center=tz)
        cb.add_strut_box_xy((0.0, ridge_node_y - 0.04), (3.93, chord_ymid), width_xy=0.028, depth_z=0.028, z_center=tz)
        cb.add_box_g(-3.946, -3.914, chord_y1, 11.66, tz - 0.016, tz + 0.016)
        cb.add_box_g(3.914, 3.946, chord_y1, 11.66, tz - 0.016, tz + 0.016)
    cb.finalize(arch_parent, col_arch, mat_beam)

    # ------------------------------------------------------------------
    # 3. Skylight_Supports: Central Structural Ridge Beam + 7 Pairs of Pitched
    #    Primary Steel Rafters + 4 Longitudinal Steel Purlins
    # ------------------------------------------------------------------
    ss = ArchMesh("Skylight_Supports", uv_scale_meters=3.0)
    ss.add_box_g(-0.055, 0.055, SKY_RIDGE_Y - 0.20, SKY_RIDGE_Y - 0.02, -wz2 - 0.04, wz2 + 0.04, bevel=0.003)

    rafter_z_positions = (-wz2 + 0.06, -4.50, -2.25, 0.00, 2.25, 4.50, wz2 - 0.06)
    for rz in rafter_z_positions:
        ss.add_pitched_prism_z(-wx2 - 0.02, SKY_EAVE_Y - 0.14, -0.04, SKY_RIDGE_Y - 0.15, 0.125, rz - 0.036, rz + 0.036, bevel=0.002)
        ss.add_pitched_prism_z(0.04, SKY_RIDGE_Y - 0.15, wx2 + 0.02, SKY_EAVE_Y - 0.14, 0.125, rz - 0.036, rz + 0.036, bevel=0.002)

    for px_abs in (2.62, 5.24):
        frac = 1.0 - (px_abs / wx2)
        py = (SKY_EAVE_Y - 0.06) + frac * ((SKY_RIDGE_Y - 0.06) - (SKY_EAVE_Y - 0.06))
        ss.add_box_g(-px_abs - 0.026, -px_abs + 0.026, py - 0.055, py, -wz2, wz2, bevel=0.0015)
        ss.add_box_g(px_abs - 0.026, px_abs + 0.026, py - 0.055, py, -wz2, wz2, bevel=0.0015)
    ss.finalize(sky_parent, col_sky, mat_beam)

    # ------------------------------------------------------------------
    # 4. Skylight_Frame: Perimeter Eave Curbs, Ridge Cap, 21 Pairs of Fine
    #    Conservatory Pitched Glazing Mullions, & Gable Mullions!
    # ------------------------------------------------------------------
    sf = ArchMesh("Skylight_Frame", uv_scale_meters=2.0)
    curb_t = 0.20
    sf.add_box_g(-wx2 - curb_t, wx2 + curb_t, y_roof_top, SKY_EAVE_Y + 0.06, -wz2 - curb_t, -wz2 + 0.04, bevel=0.002)
    sf.add_box_g(-wx2 - curb_t, wx2 + curb_t, y_roof_top, SKY_EAVE_Y + 0.06, wz2 - 0.04, wz2 + curb_t, bevel=0.002)
    sf.add_box_g(-wx2 - curb_t, -wx2 + 0.04, y_roof_top, SKY_EAVE_Y + 0.06, -wz2 + 0.04, wz2 - 0.04, bevel=0.002)
    sf.add_box_g(wx2 - 0.04, wx2 + curb_t, y_roof_top, SKY_EAVE_Y + 0.06, -wz2 + 0.04, wz2 - 0.04, bevel=0.002)

    sf.add_box_g(-0.085, 0.085, SKY_RIDGE_Y - 0.02, SKY_RIDGE_Y + 0.05, -wz2 - 0.05, wz2 + 0.05, bevel=0.002)

    num_bays_z = 20
    for i in range(num_bays_z + 1):
        mz = -wz2 + 0.02 + (2.0 * (wz2 - 0.02) * i) / num_bays_z
        m_hw = 0.018
        sf.add_pitched_prism_z(-wx2, SKY_EAVE_Y, 0.0, SKY_RIDGE_Y, 0.042, mz - m_hw, mz + m_hw)
        sf.add_pitched_prism_z(0.0, SKY_RIDGE_Y, wx2, SKY_EAVE_Y, 0.042, mz - m_hw, mz + m_hw)

    for px_abs in (2.62, 5.24):
        frac = 1.0 - (px_abs / wx2)
        py = SKY_EAVE_Y + frac * (SKY_RIDGE_Y - SKY_EAVE_Y)
        sf.add_box_g(-px_abs - 0.018, -px_abs + 0.018, py, py + 0.036, -wz2, wz2)
        sf.add_box_g(px_abs - 0.018, px_abs + 0.018, py, py + 0.036, -wz2, wz2)

    for gz in (-wz2 + 0.02, wz2 - 0.02):
        for gx in (-5.24, -2.62, 0.0, 2.62, 5.24):
            gy_top = SKY_EAVE_Y + (1.0 - abs(gx) / wx2) * (SKY_RIDGE_Y - SKY_EAVE_Y)
            sf.add_box_g(gx - 0.020, gx + 0.020, SKY_EAVE_Y, gy_top, gz - 0.022, gz + 0.022)
    sf.finalize(sky_parent, col_sky, mat_sky_frame)

    # ------------------------------------------------------------------
    # 5. Skylight_Glass: Pitched Laminated Glass Roof Slopes + Glazed Gable
    #    Tympanums + Secondary Gallery & Arrival Vestibule Skylight Panes
    # ------------------------------------------------------------------
    sg = ArchMesh("Skylight_Glass", uv_scale_meters=3.0)
    # Left & Right 18 mm pitched glass sheets (inset cleanly within frame)
    sg.add_pitched_prism_z(-wx2 + 0.03, SKY_EAVE_Y + 0.012, -0.02, SKY_RIDGE_Y + 0.006, 0.018, -wz2 + 0.04, wz2 - 0.04)
    sg.add_pitched_prism_z(0.02, SKY_RIDGE_Y + 0.006, wx2 - 0.03, SKY_EAVE_Y + 0.012, 0.018, -wz2 + 0.04, wz2 - 0.04)

    # North & South triangular glazed gable end panes (each built from Left + Right sloped quads = hexahedra)
    for gz in (-wz2 + 0.02, wz2 - 0.02):
        sg.add_hexahedron_g(
            (-wx2 + 0.06, SKY_EAVE_Y + 0.02, gz - 0.008),
            (-0.02, SKY_EAVE_Y + 0.02, gz - 0.008),
            (-0.02, SKY_RIDGE_Y - 0.02, gz - 0.008),
            (-wx2 + 0.08, SKY_EAVE_Y + 0.03, gz - 0.008),
            (-wx2 + 0.06, SKY_EAVE_Y + 0.02, gz + 0.008),
            (-0.02, SKY_EAVE_Y + 0.02, gz + 0.008),
            (-0.02, SKY_RIDGE_Y - 0.02, gz + 0.008),
            (-wx2 + 0.08, SKY_EAVE_Y + 0.03, gz + 0.008),
        )
        sg.add_hexahedron_g(
            (0.02, SKY_EAVE_Y + 0.02, gz - 0.008),
            (wx2 - 0.06, SKY_EAVE_Y + 0.02, gz - 0.008),
            (wx2 - 0.08, SKY_EAVE_Y + 0.03, gz - 0.008),
            (0.02, SKY_RIDGE_Y - 0.02, gz - 0.008),
            (0.02, SKY_EAVE_Y + 0.02, gz + 0.008),
            (wx2 - 0.06, SKY_EAVE_Y + 0.02, gz + 0.008),
            (wx2 - 0.08, SKY_EAVE_Y + 0.03, gz + 0.008),
            (0.02, SKY_RIDGE_Y - 0.02, gz + 0.008),
        )

    # Secondary Gallery & Entrance Vestibule skylight diffuser panes
    sg.add_box_g(-3.38, 3.38, SEC_GAL_CEIL_Y + 1.24, SEC_GAL_CEIL_Y + 1.26, -14.78, -12.02)
    sg.add_box_g(-4.18, 4.18, VEST_CEIL_Y + 1.24, VEST_CEIL_Y + 1.26, 12.22, 14.38)
    sg.finalize(sky_parent, col_sky, mat_sky_glass)


# ---------------------------------------------------------------------------
# Adjustable Exhibition Lighting Fixtures (Section 8)
# ---------------------------------------------------------------------------


def _build_shared_spotlight_head_mesh(mat_fixture: bpy.types.Material) -> bpy.types.Mesh:
    """
    Build reusable adjustable spotlight head mesh (`Spot_Head_Mesh`) in glTF local coordinates:
      - Origin `(0, 0, 0)` = yoke pivot hinge (`Y = 8.92 m` in hall).
      - Local `-Z` = optical emission axis (rear cap at `+0.052 m`, front snoot aperture at `-0.082 m`).
      - Local `+Y` = yoke stem side.
    """
    hm = ArchMesh("Spot_Head_Mesh", uv_scale_meters=0.5)
    # U-yoke stirrup arms embracing the pivot `(0, 0, 0)`
    hm.add_box_g(-0.036, 0.036, 0.026, 0.034, -0.012, 0.012)
    hm.add_box_g(-0.036, -0.030, -0.008, 0.030, -0.012, 0.012)
    hm.add_box_g(0.030, 0.036, -0.008, 0.030, -0.012, 0.012)
    # Cylindrical spotlight body aimed along local -Z!
    hm.add_cylinder_segment_g((0.0, 0.0, 0.052), (0.0, 0.0, -0.082), 0.029, 0.029, segments=16, cap_start=True, cap_end=False)
    # Recessed anti-glare snoot baffle inside front `-Z` aperture
    hm.add_cylinder_segment_g((0.0, 0.0, -0.082), (0.0, 0.0, -0.058), 0.027, 0.021, segments=16, cap_start=False, cap_end=True)

    bmesh.ops.remove_doubles(hm.bm, verts=list(hm.bm.verts), dist=1e-5)
    bmesh.ops.recalc_face_normals(hm.bm, faces=list(hm.bm.faces))
    uv_l = hm.bm.loops.layers.uv.new("UVMap")
    for f in hm.bm.faces:
        for lp in f.loops:
            lp[uv_l].uv = (0.5, 0.5)
    mesh = bpy.data.meshes.new("Spot_Head_Mesh")
    hm.bm.to_mesh(mesh)
    hm.bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.materials.append(mat_fixture)
    return mesh


def build_lighting_fixtures(
    fix_parent: bpy.types.Object,
    col_fix: bpy.types.Collection,
    mat_fixture: bpy.types.Material,
) -> None:
    hs = TRACK_SLOT_W * 0.5  # 0.042 m
    head_mesh = _build_shared_spotlight_head_mesh(mat_fixture)

    def spawn_adjustable_head(
        name: str,
        track_obj: bpy.types.Object,
        mount_x: float,
        mount_z: float,
        target_g: Tuple[float, float, float],
    ) -> None:
        ho = bpy.data.objects.new(name, head_mesh)
        ho.parent = track_obj
        ho.matrix_world = look_at_gltf_basis((mount_x, SPOT_PIVOT_Y, mount_z), target_g)
        ho["fixtureRole"] = "adjustable-spotlight-head"
        ho["opticalAxisLocal"] = [0.0, 0.0, -1.0]
        ho["defaultTargetGltf"] = list(target_g)
        col_fix.objects.link(ho)

    # 1. Track_Back (Static recessed track rail + stem adapters at Z = -7.45 m + 5 adjustable child heads)
    tb = ArchMesh("Track_Back", uv_scale_meters=1.0)
    tb.add_box_g(-TRACK_X - hs, TRACK_X + hs, 9.044, 9.075, TRACK_BACK_Z - hs, TRACK_BACK_Z + hs)
    back_xs = (-6.60, -3.50, 0.00, 3.50, 6.60)
    for sx in back_xs:
        tb.add_cylinder_segment_g((sx, 9.048, TRACK_BACK_Z), (sx, SPOT_PIVOT_Y + 0.032, TRACK_BACK_Z), 0.010, 0.010, segments=10)
    tb_obj = tb.finalize(fix_parent, col_fix, mat_fixture)
    for i, sx in enumerate(back_xs, start=1):
        spawn_adjustable_head(f"Fixture_Head_Back_{i:02d}", tb_obj, sx, TRACK_BACK_Z, (sx, ARTWORK_CENTER_Y + 0.20, -HALF_D))

    # 2. Track_Left (Static recessed track rail at X = -9.18 m + 5 adjustable child heads)
    tl = ArchMesh("Track_Left", uv_scale_meters=1.0)
    tl.add_box_g(-TRACK_X - hs, -TRACK_X + hs, 9.044, 9.075, TRACK_BACK_Z + hs + 0.002, TRACK_Z_END + hs)
    side_zs = (-5.20, -2.60, 0.00, 2.60, 5.20)
    for sz in side_zs:
        tl.add_cylinder_segment_g((-TRACK_X, 9.048, sz), (-TRACK_X, SPOT_PIVOT_Y + 0.032, sz), 0.010, 0.010, segments=10)
    tl_obj = tl.finalize(fix_parent, col_fix, mat_fixture)
    for i, sz in enumerate(side_zs, start=1):
        spawn_adjustable_head(f"Fixture_Head_Left_{i:02d}", tl_obj, -TRACK_X, sz, (-HALF_W, ARTWORK_CENTER_Y + 0.20, sz))

    # 3. Track_Right (Static recessed track rail at X = +9.18 m + 5 adjustable child heads)
    tr = ArchMesh("Track_Right", uv_scale_meters=1.0)
    tr.add_box_g(TRACK_X - hs, TRACK_X + hs, 9.044, 9.075, TRACK_BACK_Z + hs + 0.002, TRACK_Z_END + hs)
    for sz in side_zs:
        tr.add_cylinder_segment_g((TRACK_X, 9.048, sz), (TRACK_X, SPOT_PIVOT_Y + 0.032, sz), 0.010, 0.010, segments=10)
    tr_obj = tr.finalize(fix_parent, col_fix, mat_fixture)
    for i, sz in enumerate(side_zs, start=1):
        spawn_adjustable_head(f"Fixture_Head_Right_{i:02d}", tr_obj, TRACK_X, sz, (HALF_W, ARTWORK_CENTER_Y + 0.20, sz))

    # 4. Recessed_Fixtures (14 discreet trimless architectural downlights framing ceiling & skylight perimeter)
    rf = ArchMesh("Recessed_Fixtures", uv_scale_meters=0.5)
    downlight_coords = [
        (-7.40, 8.20), (-3.70, 8.20), (3.70, 8.20), (7.40, 8.20),
        (-10.42, -8.20), (10.42, -8.20),
        (-10.42, -3.90), (-10.42, 0.00), (-10.42, 3.90),
        (10.42, -3.90), (10.42, 0.00), (10.42, 3.90),
        (-3.60, 7.65), (3.60, 7.65),
    ]
    for dx, dz in downlight_coords:
        rf.add_cylinder_segment_g((dx, 9.001, dz), (dx, 9.046, dz), 0.044, 0.030, segments=14, cap_start=False, cap_end=True)
    rf.finalize(fix_parent, col_fix, mat_fixture)


# ---------------------------------------------------------------------------
# Semantic Anchors Construction (Preserving All Existing Anchors + Secondary Focal Anchor)
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
        lgt_obj["fixtureHeadNode"] = spec["head_name"]

        nd = spec["nav_dist"]
        nx_pos = (px + ax_z[0] * nd, 1.60, pz + ax_z[2] * nd)
        nav_m = look_at_gltf_basis(nx_pos, (px, 1.55, pz))
        nav_obj = _new_empty(spec["nav_name"], nav_grp, col_anchors, nav_m, 0.30)
        nav_obj["anchorRole"] = "artwork-viewpoint"
        nav_obj["targetAnchor"] = spec["name"]

    # Optional Secondary Gallery Focal Artwork Anchor (visible axially through open central portal!)
    sec_art_m = make_gltf_basis_matrix((0.00, ARTWORK_CENTER_Y, SEC_GAL_Z_END + WALL_EPS), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    sec_art = _new_empty("Anchor_Artwork_Secondary_01", exh_grp, col_anchors, sec_art_m, 0.35)
    sec_art["anchorRole"] = "artwork-mount-secondary"
    sec_art["targetWall"] = "Secondary_Gallery"
    sec_art["maxWidthMeters"] = 4.20
    sec_art["maxHeightMeters"] = ARTWORK_MAX_CENTERED_H
    sec_art["minBottomYMeters"] = ARTWORK_MIN_BOTTOM_Y
    sec_art["recommendedClearanceMeters"] = 0.80

    for pname, ppos, pfront in PLACEMENT_SPECS:
        up = (0.0, 1.0, 0.0)
        zf = Vector(pfront).normalized()
        xf = Vector(up).cross(zf).normalized()
        pm = make_gltf_basis_matrix(ppos, (xf.x, xf.y, xf.z), up, (zf.x, zf.y, zf.z))
        p_obj = _new_empty(pname, exh_grp, col_anchors, pm, 0.30)
        p_obj["anchorRole"] = "floor-placement"

    extra_lights = [
        ("Anchor_Light_Center_01", (-3.50, 8.95, 0.00), (0.00, 1.00, -0.60)),
        ("Anchor_Light_Center_02", (3.50, 8.95, 0.00), (0.00, 1.00, -0.60)),
        ("Anchor_Light_Ambient_01", (-7.40, 8.95, 7.80), (-7.40, 0.00, 7.80)),
        ("Anchor_Light_Ambient_02", (7.40, 8.95, 7.80), (7.40, 0.00, 7.80)),
        ("Anchor_Light_Ambient_03", (-10.30, 8.95, -7.80), (-10.30, 0.00, -7.80)),
        ("Anchor_Light_Ambient_04", (10.30, 8.95, -7.80), (10.30, 0.00, -7.80)),
    ]
    for lname, lpos, ltgt in extra_lights:
        lm = look_at_gltf_basis(lpos, ltgt)
        lo = _new_empty(lname, lgt_grp, col_anchors, lm, 0.25)
        lo["anchorRole"] = "architectural-light"

    primary_navs = [
        ("Anchor_Navigation_Entrance", (0.00, 1.60, 8.20), (0.00, 1.60, -9.00)),
        ("Anchor_Navigation_Center", (0.00, 1.60, 1.50), (0.00, 1.60, -9.00)),
        ("Anchor_Navigation_Back", (0.00, 1.60, -4.20), (0.00, 1.60, -9.00)),
        ("Anchor_Navigation_Left", (-6.20, 1.60, 0.00), (-12.00, 1.60, 0.00)),
        ("Anchor_Navigation_Right", (6.20, 1.60, 0.00), (12.00, 1.60, 0.00)),
        ("Anchor_Navigation_Secondary", (0.00, 1.60, -11.90), (0.00, 1.60, SEC_GAL_Z_END)),
    ]
    for nname, npos, ntgt in primary_navs:
        nm = look_at_gltf_basis(npos, ntgt)
        no = _new_empty(nname, nav_grp, col_anchors, nm, 0.35)
        no["anchorRole"] = "hall-navigation"


# ---------------------------------------------------------------------------
# Coherent Periodic PBR Texture Synthesis (Stage C)
# ---------------------------------------------------------------------------


def _write_png_u8(path: Path, arr) -> None:
    import numpy as np
    import zlib
    import struct as pystruct

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
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw_rows, level=6))
        + chunk(b"IEND", b"")
    )


def ensure_pbr_textures(force: bool = False) -> Dict[str, Path]:
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    expected = {
        "plaster_basecolor": TEX_DIR / "wall_plaster_basecolor.png",
        "plaster_normal": TEX_DIR / "wall_plaster_normal.png",
        "plaster_roughness": TEX_DIR / "wall_plaster_roughness.png",
        "concrete_basecolor": TEX_DIR / "floor_concrete_basecolor.png",
        "concrete_normal": TEX_DIR / "floor_concrete_normal.png",
        "concrete_roughness": TEX_DIR / "floor_concrete_roughness.png",
        "ceiling_normal": TEX_DIR / "ceiling_plaster_normal.png",
        "museum_ao": TEX_DIR / "museum_ao.png",
    }
    tiling_keys = [k for k in expected if k != "museum_ao"]
    if not force and all(expected[k].exists() for k in tiling_keys):
        return expected

    import numpy as np

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

    # 1. Museum Wall Plaster (6.0 m world UV repeat: ultra-clean natural off-white matte plaster)
    res_p = 1024
    h_p_macro = periodic_fbm(res_p, seed=111, freq_weights=[(1, 0.65), (2, 0.45), (5, 0.30)])
    h_p_micro = periodic_fbm(res_p, seed=112, freq_weights=[(28, 0.40), (74, 0.55), (170, 0.55)])
    h_plaster = 0.35 * h_p_macro + 0.65 * h_p_micro
    n_plaster = height_to_normal_rgb(h_plaster, strength=0.095)

    hm512 = box2x2(h_p_macro)
    hi512 = box2x2(h_p_micro)
    p_lum = 0.990 + 0.006 * np.tanh(0.65 * hm512 + 0.35 * hi512)
    p_rgb = np.stack([p_lum * 255.0, p_lum * 255.0, (p_lum - 0.001 * np.tanh(hm512)) * 255.0], axis=-1)
    r_plaster = (0.88 - 0.032 * np.tanh(0.60 * hm512 + 0.40 * hi512)) * 255.0

    _write_png_u8(expected["plaster_basecolor"], p_rgb)
    _write_png_u8(expected["plaster_normal"], n_plaster)
    _write_png_u8(expected["plaster_roughness"], r_plaster)

    # 2. Poured Power-Troweled Honed Concrete Floor (6.4 m world UV repeat: authentic mineral clouding + satin sheen!)
    res_c = 1024
    h_cloud = periodic_fbm(res_c, seed=221, freq_weights=[(1, 0.85), (2, 0.65), (4, 0.45), (8, 0.25)])
    h_trowel = periodic_fbm(res_c, seed=222, freq_weights=[(3, 0.65), (6, 0.55), (14, 0.40), (28, 0.22)])
    h_micro = periodic_fbm(res_c, seed=223, freq_weights=[(52, 0.35), (118, 0.45), (230, 0.40)])
    pores = np.minimum(0.0, h_micro + 1.90) * 0.20
    h_conc = 0.50 * h_cloud + 0.30 * h_trowel + 0.20 * h_micro + pores
    n_conc = height_to_normal_rgb(h_conc, strength=0.070)

    # Neutral near-white concrete mineral clouding [224..253] (1024x1024) so troweled gray concrete reads
    # unmistakably in both Cycles and real-time WebGL while multiplying cleanly with `material.color`!
    c_lum = 0.938 + 0.054 * np.tanh(0.62 * h_cloud + 0.32 * h_trowel + 0.14 * h_micro)
    c_warm = 0.0035 * np.tanh(h_cloud - 0.35 * h_trowel)
    c_rgb = np.stack([(c_lum + c_warm) * 255.0, c_lum * 255.0, (c_lum - c_warm) * 255.0], axis=-1)

    # Restrained satin concrete roughness: 0.235 on burnished sweeps to 0.375 in honed mineral clouds
    r_conc = (
        0.295
        - 0.055 * np.tanh(0.58 * h_trowel + 0.45 * h_cloud)
        + 0.018 * np.tanh(h_micro)
        - 0.040 * pores
    ) * 255.0

    _write_png_u8(expected["concrete_basecolor"], c_rgb)
    _write_png_u8(expected["concrete_normal"], n_conc)
    _write_png_u8(expected["concrete_roughness"], r_conc)

    # 3. Acoustic Mineral Ceiling Plaster (5.4 m UV repeat)
    res_ceil = 512
    h_ceil = periodic_fbm(res_ceil, seed=313, freq_weights=[(2, 0.35), (8, 0.35), (28, 0.45), (76, 0.55), (156, 0.50)])
    n_ceil = height_to_normal_rgb(h_ceil, strength=0.10)
    _write_png_u8(expected["ceiling_normal"], n_ceil)

    # Create placeholder white `museum_ao.png` if missing prior to scene AO bake
    if not expected["museum_ao"].exists():
        _write_png_u8(expected["museum_ao"], np.full((1024, 1024), 255, dtype=np.uint8))

    return expected


# ---------------------------------------------------------------------------
# Neutral Cycles Ambient Occlusion Atlas Unwrap & Bake (`UVMap_AO` / `TEXCOORD_1`)
# ---------------------------------------------------------------------------


AO_TARGET_MESHES = (
    "Floor",
    "Wall_Left",
    "Wall_Right",
    "Wall_Back",
    "Wall_Entrance",
    "Ceiling",
    "Secondary_Gallery",
    "Entrance_Vestibule",
)


def unwrap_secondary_ao_uvs() -> None:
    """
    Create secondary non-overlapping `UVMap_AO` (`TEXCOORD_1`) across interior architectural
    surfaces so neutral Cycles sky-access / corner AO can be applied via glTF `occlusionTexture`
    without touching `UVMap` (`TEXCOORD_0`) tiling PBR maps!
    """
    bpy.ops.object.select_all(action="DESELECT")
    ao_objs: List[bpy.types.Object] = []
    for nm in AO_TARGET_MESHES:
        o = bpy.data.objects.get(nm)
        if o and o.type == "MESH":
            uv_layers = o.data.uv_layers
            ao_uv = uv_layers.get("UVMap_AO") or uv_layers.new(name="UVMap_AO")
            uv_layers.active = ao_uv
            o.select_set(True)
            ao_objs.append(o)

    if ao_objs:
        bpy.context.view_layer.objects.active = ao_objs[0]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.015, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode="OBJECT")
        for o in ao_objs:
            o.data.uv_layers.active_index = 0

    # `Wall_Back_Portal_Closure` also uses `Mat_Wall_Plaster`: assign its `UVMap_AO` to a tiny
    # unoccluded corner patch `(0.995, 0.995)` forced to 1.0 in `museum_ao.png` so sliding it closed
    # never displays pocket shadow!
    wpc = bpy.data.objects.get("Wall_Back_Portal_Closure")
    if wpc and wpc.type == "MESH":
        ao_uv = wpc.data.uv_layers.get("UVMap_AO") or wpc.data.uv_layers.new(name="UVMap_AO")
        for poly in wpc.data.polygons:
            for li in poly.loop_indices:
                ao_uv.data[li].uv = (0.996, 0.996)
        wpc.data.uv_layers.active_index = 0


def bake_neutral_ao_atlas(ao_path: Path, force: bool = False) -> None:
    """
    Bake a true Cycles path-traced Neutral Ambient Occlusion / Sky-Access atlas (`1024x1024`)
    into `textures/museum_ao.png` with `Skylight_Glass` hidden so open skylight apertures register
    full sky illumination while architectural recesses, coves, and wall-floor junctions gain
    authentic soft contact shading!
    """
    if ao_path.exists() and not force and ao_path.stat().st_size > 25000:
        # Reload existing baked AO into Blender image datablock
        img = bpy.data.images.get("museum_ao.png")
        if img:
            img.reload()
        return

    import numpy as np

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for dev in prefs.devices:
            dev.use = True
        scene.cycles.device = "GPU"
    except Exception:
        scene.cycles.device = "CPU"

    scene.cycles.samples = 64
    scene.cycles.use_denoising = True

    world = scene.world or bpy.data.worlds.new("AO_World")
    scene.world = world
    if hasattr(world, "light_settings"):
        world.light_settings.distance = 6.2  # 6.2 m architectural corner & coffer AO reach

    # Temporarily hide Skylight_Glass and Wall_Back_Portal_Closure during AO bake
    glass = bpy.data.objects.get("Skylight_Glass")
    wpc = bpy.data.objects.get("Wall_Back_Portal_Closure")
    if glass:
        glass.hide_render = True
    if wpc:
        wpc.hide_render = True

    bake_res = 1024
    bake_img = bpy.data.images.new("AO_Bake_Temp", width=bake_res, height=bake_res, alpha=False)
    bake_img.colorspace_settings.name = "Non-Color"
    # Pre-fill clear background to 1.0 (white) so mipmap borders never bleed dark gray!
    bake_img.pixels[:] = [1.0] * (bake_res * bake_res * 4)

    target_mats = set()
    bpy.ops.object.select_all(action="DESELECT")
    ao_objs = []
    for nm in AO_TARGET_MESHES:
        o = bpy.data.objects.get(nm)
        if o and o.type == "MESH":
            o.select_set(True)
            o.data.uv_layers["UVMap_AO"].active = True
            ao_objs.append(o)
            for m in o.data.materials:
                if m:
                    target_mats.add(m)

    temp_nodes = []
    for m in target_mats:
        nt = m.node_tree
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.name = "_Temp_AO_Bake"
        tn.image = bake_img
        for n in nt.nodes:
            n.select = False
        tn.select = True
        nt.nodes.active = tn
        temp_nodes.append((nt, tn))

    bpy.context.view_layer.objects.active = ao_objs[0]
    scene.render.bake.margin = 10
    scene.render.bake.use_clear = False
    bpy.ops.object.bake(type="AO")

    px = np.array(bake_img.pixels[:], dtype=np.float32).reshape((bake_res, bake_res, 4))[..., 0]
    px_topdown = px[::-1, :].copy()
    for _ in range(2):
        px_topdown = (
            0.50 * px_topdown
            + 0.125 * np.roll(px_topdown, 1, axis=0)
            + 0.125 * np.roll(px_topdown, -1, axis=0)
            + 0.125 * np.roll(px_topdown, 1, axis=1)
            + 0.125 * np.roll(px_topdown, -1, axis=1)
        )
    # Rich, natural architectural interior AO curve [0.44..1.00]
    ao_shaped = 0.44 + 0.56 * np.clip(px_topdown ** 0.88, 0.0, 1.0)

    # Sample the exact baked AO of `Wall_Back`'s front exhibition face (-5.0, 2.0, -9.00) so
    # `Wall_Back_Portal_Closure` matches `Wall_Back`'s tone seamlessly when closed!
    wb_obj = bpy.data.objects.get("Wall_Back")
    wall_face_ao = 0.90
    if wb_obj:
        wb_uv = wb_obj.data.uv_layers["UVMap_AO"]
        for poly in wb_obj.data.polygons:
            c_b = wb_obj.matrix_world @ poly.center
            gx, gy, gz = c_b.x, c_b.z, -c_b.y
            if abs(gz - (-9.0)) < 0.01 and gy > 1.0 and gy < 4.0 and gx < -3.0:
                uvs = [wb_uv.data[li].uv for li in poly.loop_indices]
                u_mid = sum(u.x for u in uvs) / len(uvs)
                v_mid = sum(u.y for u in uvs) / len(uvs)
                r_idx = int(np.clip((1.0 - v_mid) * (bake_res - 1), 0, bake_res - 1))
                c_idx = int(np.clip(u_mid * (bake_res - 1), 0, bake_res - 1))
                wall_face_ao = float(ao_shaped[r_idx, c_idx])
                break
    ao_shaped[0:14, -14:] = wall_face_ao
    _write_png_u8(ao_path, ao_shaped * 255.0)

    # Clean up temp bake nodes & restore primary `UVMap` active state + visibility
    for nt, tn in temp_nodes:
        nt.nodes.remove(tn)
    bpy.data.images.remove(bake_img)
    for o in ao_objs:
        o.data.uv_layers["UVMap"].active = True
    if glass:
        glass.hide_render = False
    if wpc:
        wpc.hide_render = False

    # Reload `museum_ao.png` into its material image datablock
    for img in bpy.data.images:
        if Path(img.filepath).name == ao_path.name:
            img.reload()


# ---------------------------------------------------------------------------
# Semantic PBR Materials (Section 6 — With Dual-UV glTF `occlusionTexture`)
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


def _get_or_create_gltf_settings_group() -> bpy.types.NodeTree:
    from io_scene_gltf2.blender.com.material_helpers import create_settings_group, get_gltf_node_name
    gname = get_gltf_node_name()
    return bpy.data.node_groups.get(gname) or create_settings_group(gname)


def create_materials(force_textures: bool = False) -> Dict[str, bpy.types.Material]:
    tex = ensure_pbr_textures(force=force_textures)
    gltf_group = _get_or_create_gltf_settings_group()
    ao_img = _load_img(tex["museum_ao"], non_color=True)
    mats: Dict[str, bpy.types.Material] = {}

    def make_textured_pbr(
        name: str,
        base_hex: str,
        metallic: float,
        roughness: float,
        base_map: Optional[Path] = None,
        rough_map: Optional[Path] = None,
        norm_map: Optional[Path] = None,
        norm_strength: float = 0.20,
        ior: float = 1.48,
        use_ao_atlas: bool = False,
    ) -> bpy.types.Material:
        m = bpy.data.materials.new(name)
        nt = _ensure_nodes(m)
        bsdf = nt.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = hex_rgba(base_hex)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        if "IOR" in bsdf.inputs:
            bsdf.inputs["IOR"].default_value = ior

        uv0 = nt.nodes.new("ShaderNodeUVMap")
        uv0.uv_map = "UVMap"

        if base_map is not None:
            tex_c = nt.nodes.new("ShaderNodeTexImage")
            tex_c.image = _load_img(base_map, non_color=False)
            nt.links.new(uv0.outputs["UV"], tex_c.inputs["Vector"])
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
            nt.links.new(uv0.outputs["UV"], tex_r.inputs["Vector"])
            nt.links.new(tex_r.outputs["Color"], bsdf.inputs["Roughness"])

        if norm_map is not None:
            tex_n = nt.nodes.new("ShaderNodeTexImage")
            tex_n.image = _load_img(norm_map, non_color=True)
            nt.links.new(uv0.outputs["UV"], tex_n.inputs["Vector"])
            nmap = nt.nodes.new("ShaderNodeNormalMap")
            nmap.inputs["Strength"].default_value = norm_strength
            nt.links.new(tex_n.outputs["Color"], nmap.inputs["Color"])
            nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])

        if use_ao_atlas:
            uv_ao = nt.nodes.new("ShaderNodeUVMap")
            uv_ao.uv_map = "UVMap_AO"
            tex_ao = nt.nodes.new("ShaderNodeTexImage")
            tex_ao.image = ao_img
            nt.links.new(uv_ao.outputs["UV"], tex_ao.inputs["Vector"])
            gn = nt.nodes.new("ShaderNodeGroup")
            gn.node_tree = gltf_group
            nt.links.new(tex_ao.outputs["Color"], gn.inputs["Occlusion"])

        return m

    # 1. Mat_Wall_Plaster — Crisp natural museum off-white (#F6F4EE), matte, dual-UV neutral AO
    mats["Mat_Wall_Plaster"] = make_textured_pbr(
        "Mat_Wall_Plaster",
        base_hex="#F6F4EE",
        metallic=0.0,
        roughness=0.88,
        base_map=tex["plaster_basecolor"],
        rough_map=tex["plaster_roughness"],
        norm_map=tex["plaster_normal"],
        norm_strength=0.18,
        ior=1.46,
        use_ao_atlas=True,
    )

    # 2. Mat_Floor_Concrete — Grounded medium-gray polished/honed architectural concrete (#8E8B85)
    #    matching the real museum photographs so skylight & wall reflections read with authentic depth!
    mats["Mat_Floor_Concrete"] = make_textured_pbr(
        "Mat_Floor_Concrete",
        base_hex="#8E8B85",
        metallic=0.0,
        roughness=0.27,
        base_map=tex["concrete_basecolor"],
        rough_map=tex["concrete_roughness"],
        norm_map=tex["concrete_normal"],
        norm_strength=0.12,
        ior=1.52,
        use_ao_atlas=True,
    )

    # 3. Mat_Ceiling — Subtle warm-mineral architectural ceiling layer (#EEEBE3) + neutral AO
    mats["Mat_Ceiling"] = make_textured_pbr(
        "Mat_Ceiling",
        base_hex="#EEEBE3",
        metallic=0.0,
        roughness=0.90,
        base_map=tex["plaster_basecolor"],
        norm_map=tex["ceiling_normal"],
        norm_strength=0.18,
        ior=1.46,
        use_ao_atlas=True,
    )

    # 4. Mat_Structural_Beam — Crisp white painted architectural steel roof trusses & rafters (#F8F7F3)
    mats["Mat_Structural_Beam"] = make_textured_pbr(
        "Mat_Structural_Beam",
        base_hex="#F8F7F3",
        metallic=0.14,
        roughness=0.44,
        norm_map=tex["ceiling_normal"],
        norm_strength=0.08,
    )

    # 5. Mat_Skylight_Frame — Powder-coated pale silver-white conservatory mullions (#E4E2DC)
    mats["Mat_Skylight_Frame"] = make_textured_pbr(
        "Mat_Skylight_Frame",
        base_hex="#E4E2DC",
        metallic=0.38,
        roughness=0.34,
    )

    # 6. Mat_Skylight_Glass — Believable low-iron conservatory glass (`BLEND` fallback for WebGL)
    mg = bpy.data.materials.new("Mat_Skylight_Glass")
    nt = _ensure_nodes(mg)
    if hasattr(mg, "surface_render_method"):
        mg.surface_render_method = "BLENDED"
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = hex_rgba("#EDF4FA", 1.0)
    bsdf.inputs["Metallic"].default_value = 0.05
    bsdf.inputs["Roughness"].default_value = 0.06
    bsdf.inputs["Alpha"].default_value = 0.16
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.52
    mats["Mat_Skylight_Glass"] = mg

    # 7. Mat_Entrance_Frame — Warm architectural dark bronze-walnut portal sleeve (#423B34)
    mats["Mat_Entrance_Frame"] = make_textured_pbr(
        "Mat_Entrance_Frame",
        base_hex="#423B34",
        metallic=0.38,
        roughness=0.38,
    )

    # 8. Mat_Lighting_Fixture — Matte graphite track & adjustable spotlight heads (#2C2B29)
    mats["Mat_Lighting_Fixture"] = make_textured_pbr(
        "Mat_Lighting_Fixture",
        base_hex="#2C2B29",
        metallic=0.38,
        roughness=0.42,
    )

    # 9. Mat_Trim — Recessed architectural shadow-gap channel liner (#363431)
    mats["Mat_Trim"] = make_textured_pbr(
        "Mat_Trim",
        base_hex="#363431",
        metallic=0.28,
        roughness=0.52,
    )

    return mats


# ---------------------------------------------------------------------------
# Cycles Natural Daylight & Indirect Lighting Scenarios (Section 7)
# ---------------------------------------------------------------------------


def configure_cycles(samples: int = 80, res_x: int = 1600, res_y: int = 1000) -> None:
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


def setup_lighting_scenario(scenario: str, col_studio: bpy.types.Collection) -> None:
    for obj in list(col_studio.objects):
        if obj.type in ("LIGHT", "MESH") and obj.name.startswith("Studio_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    glass_obj = bpy.data.objects.get("Skylight_Glass")
    if glass_obj is not None and hasattr(glass_obj, "visible_shadow"):
        glass_obj.visible_shadow = False

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
        spread_deg: float = 140.0,
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
            lo.visible_camera = False
        col_studio.objects.link(lo)

    def add_spot_light(
        name: str,
        pos_g: Tuple[float, float, float],
        target_g: Tuple[float, float, float],
        energy: float,
        spot_deg: float,
        blend: float,
        color_hex: str,
    ) -> None:
        ld = bpy.data.lights.new(name, type="SPOT")
        ld.energy = energy
        ld.spot_size = math.radians(spot_deg)
        ld.spot_blend = blend
        ld.shadow_soft_size = 0.045
        ld.color = hex_rgba(color_hex)[:3]
        lo = bpy.data.objects.new(name, ld)
        lo.matrix_world = look_at_blender_native(pos_g, target_g)
        col_studio.objects.link(lo)

    def add_cove_and_secondary_lights(side_e: float, sec_e: float, vest_e: float, color_hex: str) -> None:
        add_area_light("Studio_Cove_Left", (-11.68, 9.66, 0.0), (-11.88, 2.0, 0.0), side_e, 17.4, 0.44, color_hex, 142.0, up_g=(1.0, 0.0, 0.0))
        add_area_light("Studio_Cove_Right", (11.68, 9.66, 0.0), (11.88, 2.0, 0.0), side_e, 17.4, 0.44, color_hex, 142.0, up_g=(-1.0, 0.0, 0.0))
        add_area_light("Studio_SecGal_Sky", (0.0, 8.60, -13.40), (0.0, 1.2, -14.80), sec_e, 6.4, 2.6, color_hex, 135.0)
        add_area_light("Studio_Vestibule_Sky", (0.0, 8.40, 13.30), (0.0, 1.2, 14.50), vest_e, 8.0, 2.0, color_hex, 135.0)

    if scenario == "soft_daylight":
        bg.inputs["Color"].default_value = hex_rgba("#EEF3FA")
        bg.inputs["Strength"].default_value = 2.65
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        add_area_light("Studio_Skylight_Dome", (0.0, 13.40, 0.0), (0.0, 0.0, -0.2), 4200.0, 14.2, 12.2, "#F8FAFD", 142.0)
        add_cove_and_secondary_lights(580.0, 1450.0, 1250.0, "#F6F8FC")
        bpy.context.scene.view_settings.exposure = -0.22

    elif scenario == "direct_sun":
        bg.inputs["Color"].default_value = hex_rgba("#DDE8F6")
        bg.inputs["Strength"].default_value = 2.05
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        add_area_light("Studio_Skylight_Fill", (0.0, 13.50, 0.0), (0.0, 0.0, 0.0), 2100.0, 14.2, 12.2, "#ECF3FC", 145.0)
        add_cove_and_secondary_lights(420.0, 1150.0, 1050.0, "#F4F6FB")

        sun_d = bpy.data.lights.new("Studio_Direct_Sun", type="SUN")
        sun_d.energy = 3.35
        sun_d.angle = math.radians(1.15)
        sun_d.color = hex_rgba("#FFF5E4")[:3]
        sun_o = bpy.data.objects.new("Studio_Direct_Sun", sun_d)
        sun_o.matrix_world = look_at_blender_native((6.8, 16.5, 4.0), (-2.8, 0.0, -2.2))
        col_studio.objects.link(sun_o)
        bpy.context.scene.view_settings.exposure = -0.32

    elif scenario == "evening":
        bg.inputs["Color"].default_value = hex_rgba("#162338")
        bg.inputs["Strength"].default_value = 0.55
        wnt.links.new(bg.outputs["Background"], wout.inputs["Surface"])

        add_area_light("Studio_Twilight_Fill", (0.0, 13.20, 0.0), (0.0, 0.0, 0.0), 260.0, 14.0, 12.0, "#8FAAD0", 145.0)
        add_cove_and_secondary_lights(280.0, 380.0, 320.0, "#FFEBD2")

        for spec in ARTWORK_SPECS:
            tx, ty, tz = spec["track_pos"]
            px, py, pz = spec["pos"]
            add_spot_light(f"Studio_Spot_{spec['name']}", (tx, ty - 0.05, tz), (px, py + 0.04, pz), 820.0, 38.0, 0.48, "#FFEDD6")
        add_spot_light("Studio_Spot_Secondary", (0.0, 6.65, -12.60), (0.0, 1.55, SEC_GAL_Z_END), 680.0, 42.0, 0.50, "#FFEDD6")
        add_area_light("Studio_Evening_Ambient", (0.0, 8.85, 0.0), (0.0, 0.0, 0.0), 380.0, 9.0, 7.0, "#FFEED8", 140.0)
        bpy.context.scene.view_settings.exposure = 0.12


# ---------------------------------------------------------------------------
# Temporary Exhibition Demonstration (Section 9 & 10 — Never Exported to GLB)
# ---------------------------------------------------------------------------


def ensure_demo_artworks(demo_dir: Path) -> List[Path]:
    demo_dir.mkdir(parents=True, exist_ok=True)
    paths = [demo_dir / f"demo_art_v2_{i:02d}.png" for i in range(1, 11)]
    if all(p.exists() for p in paths):
        return paths

    import numpy as np

    def hex_u8(hx: str) -> "np.ndarray":
        h = hx.lstrip("#")
        return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)], dtype=np.float64)

    specs = [
        ((540, 720), "#F2EEE6", "#1D4E6E", "#8FB8CC", "gradient_sky"),
        ((960, 600), "#1E282C", "#3A6351", "#D49B54", "triptych_horizon"),
        ((540, 720), "#EFEBE2", "#C97D3A", "#5C3A28", "luminous_orb"),
        ((640, 640), "#ECE8DF", "#26384A", "#93A8B8", "diagonal_light"),
        ((800, 540), "#F0ECE3", "#B87A3D", "#E6C88C", "luminous_orb"),
        ((520, 720), "#EAE6DC", "#2F443B", "#8FA394", "gradient_sky"),
        ((800, 540), "#EDE9E0", "#22313F", "#C48A5A", "triptych_horizon"),
        ((640, 640), "#F1EDE4", "#6E473B", "#D8C2A8", "diagonal_light"),
        ((540, 720), "#ECE7DD", "#354652", "#C8B698", "gradient_sky"),
        ((760, 560), "#F0ECE2", "#8A4A32", "#E2BE88", "luminous_orb"),  # 10 Secondary Gallery focal piece
    ]

    rng = np.random.default_rng(42)
    for idx, ((w, h), bg_h, c1_h, c2_h, mode) in enumerate(specs):
        yy, xx = np.meshgrid(np.linspace(0.0, 1.0, h), np.linspace(0.0, 1.0, w), indexing="ij")
        bg = hex_u8(bg_h)
        c1 = hex_u8(c1_h)
        c2 = hex_u8(c2_h)
        grain = rng.normal(0.0, 2.0, size=(h, w, 1))
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
        _write_png_u8(paths[idx], img)

    return paths


def populate_exhibition_demo(col_demo: bpy.types.Collection, close_rear_portal: bool = True) -> None:
    demo_dir = WORK_DIR / "demo_artwork"
    art_paths = ensure_demo_artworks(demo_dir)

    wpc = bpy.data.objects.get("Wall_Back_Portal_Closure")
    if wpc is not None:
        if close_rear_portal:
            wpc.matrix_world = Matrix.Identity(4)
        else:
            wpc.matrix_world = make_gltf_basis_matrix((-4.62, 0.0, -0.38), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    dims = [
        (1.65, 2.20),
        (3.20, 2.05),
        (1.65, 2.20),
        (1.90, 1.90),
        (2.55, 1.72),
        (1.58, 2.18),
        (2.55, 1.72),
        (1.90, 1.90),
        (1.65, 2.20),
    ]

    mat_frame = bpy.data.materials.get("Demo_Mat_Frame") or bpy.data.materials.new("Demo_Mat_Frame")
    _ensure_nodes(mat_frame)
    mat_frame.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = hex_rgba("#38312B")
    mat_frame.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.46

    def mount_framed_art(tag: str, pos_g: Tuple[float, float, float], axes_g, fw: float, fh: float, img_p: Path) -> None:
        hw, hh = fw * 0.5, fh * 0.5
        fd, ft = 0.044, 0.022
        ax_x, ax_y, ax_z = [Vector(a) for a in axes_g]
        origin_g = Vector(pos_g)

        def local_to_gltf(lx: float, ly: float, lz: float) -> Tuple[float, float, float]:
            p = origin_g + ax_x * lx + ax_y * ly + ax_z * lz
            return (p.x, p.y, p.z)

        fm = ArchMesh(f"Demo_Frame_{tag}", uv_scale_meters=1.0)
        bars = [
            (-hw - ft, hw + ft, hh, hh + ft, 0.0, fd),
            (-hw - ft, hw + ft, -hh - ft, -hh, 0.0, fd),
            (-hw - ft, -hw, -hh, hh, 0.0, fd),
            (hw, hw + ft, -hh, hh, 0.0, fd),
        ]
        for x0, x1, y0, y1, z0, z1 in bars:
            p000, p100, p101, p001 = local_to_gltf(x0, y0, z0), local_to_gltf(x1, y0, z0), local_to_gltf(x1, y0, z1), local_to_gltf(x0, y0, z1)
            p010, p110, p111, p011 = local_to_gltf(x0, y1, z0), local_to_gltf(x1, y1, z0), local_to_gltf(x1, y1, z1), local_to_gltf(x0, y1, z1)
            fm.add_quad_g(p011, p111, p110, p010)
            fm.add_quad_g(p000, p100, p101, p001)
            fm.add_quad_g(p001, p101, p111, p011)
            fm.add_quad_g(p100, p000, p010, p110)
            fm.add_quad_g(p101, p100, p110, p111)
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
        m_art = bpy.data.meshes.new(f"Demo_Art_{tag}")
        bm_a.to_mesh(m_art)
        bm_a.free()

        mat_a = bpy.data.materials.new(f"Demo_Mat_Art_{tag}")
        nt = _ensure_nodes(mat_a)
        bsdf = nt.nodes["Principled BSDF"]
        bsdf.inputs["Roughness"].default_value = 0.56
        tex_n = nt.nodes.new("ShaderNodeTexImage")
        tex_n.image = _load_img(img_p, non_color=False)
        nt.links.new(tex_n.outputs["Color"], bsdf.inputs["Base Color"])
        m_art.materials.append(mat_a)
        o_art = bpy.data.objects.new(f"Demo_Art_{tag}", m_art)
        col_demo.objects.link(o_art)

    for idx, (spec, (fw, fh)) in enumerate(zip(ARTWORK_SPECS, dims)):
        if not close_rear_portal and spec["name"] == "Anchor_Artwork_Back_02":
            continue
        mount_framed_art(f"{idx+1:02d}", spec["pos"], spec["axes"], fw, fh, art_paths[idx])

    if not close_rear_portal:
        mount_framed_art("Sec_01", (0.0, ARTWORK_CENTER_Y, SEC_GAL_Z_END + WALL_EPS), ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)), 2.60, 1.90, art_paths[9])

    mat_oak = bpy.data.materials.get("Demo_Mat_Bench_Oak") or bpy.data.materials.new("Demo_Mat_Bench_Oak")
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
# Camera Render Helper (Natural Human-Scale Focal Lengths — Section 9)
# ---------------------------------------------------------------------------


def render_camera_view(
    out_path: Path,
    eye_g: Tuple[float, float, float],
    target_g: Tuple[float, float, float],
    lens_mm: float = 28.0,
    shift_y: float = 0.0,
    res_x: Optional[int] = None,
    res_y: Optional[int] = None,
    col_studio: Optional[bpy.types.Collection] = None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    old_rx, old_ry = scene.render.resolution_x, scene.render.resolution_y
    if res_x and res_y:
        scene.render.resolution_x, scene.render.resolution_y = res_x, res_y

    cam_data = bpy.data.cameras.new("Render_Cam")
    cam_data.lens = lens_mm
    cam_data.sensor_width = 36.0
    cam_data.shift_y = shift_y
    cam_data.clip_start = 0.1
    cam_data.clip_end = 120.0

    cam_obj = bpy.data.objects.new("Render_Cam", cam_data)
    cam_obj.matrix_world = look_at_blender_native(eye_g, target_g)
    target_col = col_studio or scene.collection
    target_col.objects.link(cam_obj)
    scene.camera = cam_obj
    scene.render.filepath = str(out_path)
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam_obj, do_unlink=True)
    bpy.data.cameras.remove(cam_data)
    scene.render.resolution_x, scene.render.resolution_y = old_rx, old_ry


# ---------------------------------------------------------------------------
# Build Full Museum V2 Scene, Bake Neutral AO, & Export Canonical GLB
# ---------------------------------------------------------------------------


def build_museum_scene(force_textures: bool = False) -> Tuple[bpy.types.Collection, bpy.types.Collection]:
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
    root["version"] = "0.3.0"
    root["coordinateSystem"] = "glTF-Y-up-meters"
    root["walkableBoundsMeters"] = {
        "interiorMin": [-11.65, 0.0, -8.65],
        "interiorMax": [11.65, 2.60, 8.65],
        "entrancePortalMin": [-2.50, 0.0, 8.65],
        "entrancePortalMax": [2.50, 2.60, 10.40],
        "entranceVestibuleMin": [-6.85, 0.0, 10.40],
        "entranceVestibuleMax": [6.85, 2.60, 15.05],
        "rearPortalOpenMin": [-1.90, 0.0, -9.90],
        "rearPortalOpenMax": [1.90, 2.60, -8.65],
        "secondaryGalleryOpenMin": [-5.05, 0.0, -15.35],
        "secondaryGalleryOpenMax": [5.05, 2.60, -9.90],
    }

    arch_grp = _new_empty("Architecture", root, col_arch, Matrix.Identity(4), 0.6)
    sky_grp = _new_empty("Skylight", root, col_sky, Matrix.Identity(4), 0.6)
    fix_grp = _new_empty("Lighting_Fixtures", root, col_fix, Matrix.Identity(4), 0.6)

    mats = create_materials(force_textures=force_textures)

    build_floor(arch_grp, col_arch, mats["Mat_Floor_Concrete"])
    build_walls_portals_and_extensions(
        arch_grp,
        col_arch,
        mats["Mat_Wall_Plaster"],
        mats["Mat_Entrance_Frame"],
        mats["Mat_Trim"],
    )
    build_ceiling_and_pitched_skylight(
        arch_grp,
        sky_grp,
        col_arch,
        col_sky,
        mats["Mat_Ceiling"],
        mats["Mat_Structural_Beam"],
        mats["Mat_Skylight_Frame"],
        mats["Mat_Skylight_Glass"],
    )
    build_lighting_fixtures(fix_grp, col_fix, mats["Mat_Lighting_Fixture"])
    build_all_anchors(root, col_anc)

    # Unwrap `UVMap_AO` (`TEXCOORD_1`) and bake/load neutral Cycles AO atlas (`textures/museum_ao.png`)
    unwrap_secondary_ao_uvs()
    bake_neutral_ao_atlas(TEX_DIR / "museum_ao.png", force=force_textures)

    return col_export, col_studio


def export_canonical_glb(
    glb_path: Path,
    col_studio: bpy.types.Collection,
    col_demo: Optional[bpy.types.Collection] = None,
) -> None:
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

    # Ensure `Wall_Back_Portal_Closure` is in its canonical open-pocket state during GLB export
    wpc = bpy.data.objects.get("Wall_Back_Portal_Closure")
    if wpc is not None:
        wpc.matrix_world = make_gltf_basis_matrix((-4.62, 0.0, -0.38), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

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
    parser = argparse.ArgumentParser(description="Generate Open Skylight Museum Hall V2")
    parser.add_argument("--export-only", action="store_true", help="Build textures, AO, blend, and GLB without full render suite")
    parser.add_argument("--force-textures", action="store_true", help="Regenerate coherent PBR maps and Cycles neutral AO atlas")
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    _, col_studio = build_museum_scene(force_textures=args.force_textures)

    glb_path = ASSET_DIR / "model.glb"
    export_canonical_glb(glb_path, col_studio)

    make_glass_cycles_friendly()
    setup_lighting_scenario("soft_daylight", col_studio)

    hero_cam_d = bpy.data.cameras.new("Preview_Camera")
    hero_cam_d.lens = 26.0
    hero_cam_d.sensor_width = 36.0
    hero_cam_d.shift_y = 0.135
    hero_cam_o = bpy.data.objects.new("Preview_Camera", hero_cam_d)
    hero_cam_o.matrix_world = look_at_blender_native((0.0, 1.60, 8.2), (0.0, 1.60, -9.0))
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
    # Remove any automatic `.blend1` backup
    b1 = ASSET_DIR / "model.blend1"
    if b1.exists():
        b1.unlink()
    print(f"Saved {blend_path} and {glb_path} ({glb_path.stat().st_size} bytes)")

    if args.export_only:
        return

    # ------------------------------------------------------------------
    # Human-Scale Blender Cycles Visual Validation Suite (Sections 7 & 9)
    # Uses natural 25-32 mm architectural lenses (NOT distorted ultra-wide!) at Y = 1.60 m eye height!
    # ------------------------------------------------------------------
    renders_dir = WORK_DIR / "renders-v2"
    configure_cycles(samples=72, res_x=1600, res_y=1000)

    # Scenario A — Soft Overcast Daylight (All required Section 9 human-scale views)
    setup_lighting_scenario("soft_daylight", col_studio)
    render_camera_view(renders_dir / "01_entrance_eye_soft_daylight.png", (0.0, 1.60, 8.20), (0.0, 1.60, -9.00), lens_mm=22.5, shift_y=0.145, col_studio=col_studio)
    render_camera_view(renders_dir / "02_center_hall_soft_daylight.png", (0.0, 1.60, 2.40), (0.0, 1.60, -9.00), lens_mm=24.0, shift_y=0.130, col_studio=col_studio)
    render_camera_view(renders_dir / "03_main_wall_enfilade.png", (0.0, 1.60, -1.60), (0.0, 1.60, -15.70), lens_mm=26.0, shift_y=0.095, col_studio=col_studio)
    render_camera_view(renders_dir / "04_opposite_entrance_view.png", (0.0, 1.60, -6.20), (0.0, 1.60, 15.40), lens_mm=22.5, shift_y=0.135, col_studio=col_studio)
    render_camera_view(renders_dir / "05_left_exhibition_area.png", (5.8, 1.60, 1.20), (-12.0, 1.60, -1.50), lens_mm=24.0, shift_y=0.110, col_studio=col_studio)
    render_camera_view(renders_dir / "06_right_exhibition_area.png", (-5.8, 1.60, 1.20), (12.0, 1.60, -1.50), lens_mm=24.0, shift_y=0.110, col_studio=col_studio)
    render_camera_view(renders_dir / "07_pitched_skylight_upward.png", (0.0, 1.60, 4.80), (0.0, 11.40, -1.20), lens_mm=23.0, col_studio=col_studio)
    render_camera_view(renders_dir / "07b_mobile_portrait_daylight.png", (0.0, 1.60, 8.00), (0.0, 1.60, -9.00), lens_mm=24.0, shift_y=0.125, res_x=900, res_y=1600, col_studio=col_studio)

    # Scenario B — Direct Sunlight through Pitched Skylight
    setup_lighting_scenario("direct_sun", col_studio)
    render_camera_view(renders_dir / "08_direct_sunlight_axial.png", (0.0, 1.60, 8.20), (0.0, 1.60, -9.00), lens_mm=22.5, shift_y=0.145, col_studio=col_studio)
    render_camera_view(renders_dir / "08b_direct_sunlight_diagonal.png", (-4.6, 1.60, 7.40), (1.6, 1.60, -9.00), lens_mm=23.5, shift_y=0.135, col_studio=col_studio)

    # Scenario C — Evening Exhibition Lighting (empty hall with open enfilade)
    setup_lighting_scenario("evening", col_studio)
    render_camera_view(renders_dir / "09_evening_exhibition_empty.png", (-4.2, 1.60, 7.20), (1.4, 1.60, -9.00), lens_mm=23.5, shift_y=0.130, col_studio=col_studio)

    # Temporary Exhibition Demonstrations (Both Open-Enfilade & Original 9-Artwork Closed-Wall Layouts!)
    col_demo_open = bpy.data.collections.new("Demo_Exhibition_Open")
    bpy.context.scene.collection.children.link(col_demo_open)
    populate_exhibition_demo(col_demo_open, close_rear_portal=False)
    setup_lighting_scenario("soft_daylight", col_studio)
    render_camera_view(renders_dir / "10a_exhibition_enfilade_open.png", (0.0, 1.60, 8.20), (0.0, 1.60, -9.00), lens_mm=22.5, shift_y=0.145, col_studio=col_studio)
    bpy.context.scene.collection.children.unlink(col_demo_open)

    col_demo_closed = bpy.data.collections.new("Demo_Exhibition_Closed9")
    bpy.context.scene.collection.children.link(col_demo_closed)
    populate_exhibition_demo(col_demo_closed, close_rear_portal=True)
    setup_lighting_scenario("soft_daylight", col_studio)
    render_camera_view(renders_dir / "10b_nine_artwork_exhibition.png", (0.0, 1.60, 8.20), (0.0, 1.60, -9.00), lens_mm=22.5, shift_y=0.145, col_studio=col_studio)
    setup_lighting_scenario("evening", col_studio)
    render_camera_view(renders_dir / "10c_nine_artwork_evening.png", (-4.2, 1.60, 7.20), (1.4, 1.60, -9.00), lens_mm=23.5, shift_y=0.130, col_studio=col_studio)

    # Export flagship architectural view (`08_direct_sunlight_axial.png`) as catalog `preview.webp`
    preview_webp = ASSET_DIR / "preview.webp"
    cwebp = shutil.which("cwebp")
    if cwebp:
        subprocess.run(
            [cwebp, "-q", "90", str(renders_dir / "08_direct_sunlight_axial.png"), "-o", str(preview_webp)],
            check=True,
        )
    print("Completed all V2 architectural & exhibition renders and catalog preview.webp")


if __name__ == "__main__":
    main()
