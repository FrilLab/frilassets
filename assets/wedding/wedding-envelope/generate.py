#!/usr/bin/env python3
"""Procedural Blender generator for FrilAssets: wedding/wedding-envelope.

Generates:
  - model.blend   (editable Blender scene with Envelope_Body, Envelope_Flap, Letter_Card)
  - model.glb     (standard glTF 2.0 binary with only the 3 required meshes)
  - preview.webp  (clean 3/4 studio preview render)

Run with:
  /Applications/Blender.app/Contents/MacOS/Blender --background --python assets/wedding/wedding-envelope/generate.py
"""

from __future__ import annotations

import math
import shutil
import subprocess
import tempfile
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Vector


ASSET_DIR = Path(__file__).resolve().parent
BLEND_PATH = ASSET_DIR / "model.blend"
GLB_PATH = ASSET_DIR / "model.glb"
PREVIEW_WEBP_PATH = ASSET_DIR / "preview.webp"

# Target real-world dimensions in meters (Blender: X=width, Y=depth, Z=height)
ENV_WIDTH = 0.2200
ENV_HEIGHT = 0.1100
ENV_DEPTH = 0.0056  # Within 0.004-0.008 m target range

CARD_WIDTH = 0.2050
CARD_HEIGHT = 0.0950
CARD_THICKNESS = 0.0008
CARD_CORNER_RADIUS = 0.0030
# Visible height above 0.1100 m back upper edge: 0.0280 m (29.5% of 0.095 m card height)
# Visible height above 0.1048 m front pocket lip: 0.0332 m (34.9% of 0.095 m card height)
CARD_TOP_Z = 0.1380
CARD_CENTER_Z = CARD_TOP_Z - 0.5 * CARD_HEIGHT  # 0.0905 m
CARD_CENTER_Y = 0.00010

FLAP_PIVOT_Y = 0.00245
FLAP_PIVOT_Z = ENV_HEIGHT  # 0.1100 m at back upper edge
FLAP_LENGTH = 0.0685
FLAP_THICKNESS = 0.0007
FLAP_OPEN_ANGLE_DEG = -11.5  # Slightly open presentation angle around hinge X axis


def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def srgb_hex_to_linear_rgba(hex_str: str) -> tuple[float, float, float, float]:
    h = hex_str.lstrip("#")
    r = srgb_to_linear(int(h[0:2], 16) / 255.0)
    g = srgb_to_linear(int(h[2:4], 16) / 255.0)
    b = srgb_to_linear(int(h[4:6], 16) / 255.0)
    return (r, g, b, 1.0)


# Subtle, soft, luxurious editorial palette
COL_ENV_EXTERIOR = srgb_hex_to_linear_rgba("#F1E7D6")  # Warm ivory / soft cream
COL_ENV_INTERIOR = srgb_hex_to_linear_rgba("#DBC9B0")  # Slightly darker warm ivory liner
COL_LETTER_CARD = srgb_hex_to_linear_rgba("#FCFBF7")   # Clean off-white, brighter than envelope
COL_STUDIO_BG = srgb_hex_to_linear_rgba("#CFC9C0")     # Calm neutral warm-stone studio backdrop


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 0.0
    t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
    return t * t * (3.0 - 2.0 * t)


def clear_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0


def create_vertex_color_material(name: str, roughness: float = 0.84) -> bpy.types.Material:
    """Single Principled BSDF driven by loop Color Attribute ('Color') so multi-tone
    surfaces export as a single glTF primitive (preserving 1 Mesh = 1 THREE.Mesh)."""
    mat = bpy.data.materials.new(name=name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new(type="ShaderNodeOutputMaterial")
    out_node.location = (300, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.48
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.28

    vcol = nodes.new(type="ShaderNodeVertexColor")
    vcol.location = (-260, 0)
    vcol.layer_name = "Color"

    links.new(vcol.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])
    return mat


def create_uniform_material(
    name: str, rgba: tuple[float, float, float, float], roughness: float = 0.78
) -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new(type="ShaderNodeOutputMaterial")
    out_node.location = (300, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (0, 0)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = 0.0
    if "IOR" in bsdf.inputs:
        bsdf.inputs["IOR"].default_value = 1.48
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.26

    links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])
    return mat


def assign_face_colors(
    mesh: bpy.types.Mesh, face_is_interior: list[bool]
) -> None:
    color_attr = mesh.color_attributes.new(
        name="Color", type="BYTE_COLOR", domain="CORNER"
    )
    mesh.color_attributes.active_color = color_attr
    mesh.color_attributes.render_color_index = 0

    for poly_idx, poly in enumerate(mesh.polygons):
        col = COL_ENV_INTERIOR if face_is_interior[poly_idx] else COL_ENV_EXTERIOR
        for loop_idx in poly.loop_indices:
            color_attr.data[loop_idx].color = col


def pocket_seam_x(z: float) -> float:
    """X coordinate (>0) of the diagonal front pocket flap overlap seam at height z."""
    t = max(0.0, min(1.0, z / 0.1048))
    return 0.1005 - 0.0295 * t  # Straight diagonal from x=0.1005 (bottom) to x=0.0710 (lip)


def front_throat_z(x: float) -> float:
    """Tailored envelope front pocket opening: clean horizontal lip across center,
    sloping smoothly up the side-flap shoulders and leveling off before the outer folds."""
    ax = abs(x)
    t = smoothstep(0.0710, 0.1005, ax)
    return 0.1048 + (ENV_HEIGHT - 0.1048) * t


def seam_aligned_front_stations(x_straight: float, z_ref: float) -> list[tuple[float, float]]:
    """Return 17 interior (x, overlap_weight) stations across (-x_straight, +x_straight)
    with tight support loops flanking the diagonal pocket fold bevel so planar surfaces
    have zero smooth-normal shading bleed."""
    xs_seam = min(x_straight - 0.0035, pocket_seam_x(z_ref))
    bevel_half = 0.00035   # Crisp 0.70 mm folded-paper bevel
    support_gap = 0.00055  # Tight support loop isolating normals to the paper fold edge

    x_side_outer = x_straight
    x_side_sup = xs_seam + bevel_half + support_gap
    x_side_bev = xs_seam + bevel_half
    x_cent_bev = xs_seam - bevel_half
    x_cent_sup = xs_seam - bevel_half - support_gap

    stations: list[tuple[float, float]] = [
        (-0.5 * (x_side_outer + x_side_sup), 0.0),
        (-x_side_sup, 0.0),
        (-x_side_bev, 0.0),
        (-x_cent_bev, 1.0),
        (-x_cent_sup, 1.0),
    ]
    for u in (-0.68, -0.35, 0.0, 0.35, 0.68):
        stations.append((u * x_cent_sup, 1.0))
    stations.extend(
        [
            (+x_cent_sup, 1.0),
            (+x_cent_bev, 1.0),
            (+x_side_bev, 0.0),
            (+x_side_sup, 0.0),
            (+0.5 * (x_side_outer + x_side_sup), 0.0),
        ]
    )
    return stations  # 15 interior stations with crisp support loops!


def build_envelope_body(mat: bpy.types.Material) -> bpy.types.Object:
    """Build Envelope_Body as a single closed watertight manifold hollow-pocket shell.

    Exact bounding box:
      X: [-0.1100, +0.1100] -> 0.2200 m
      Y: [-0.0028, +0.0028] -> 0.0056 m
      Z: [ 0.0000, +0.1100] -> 0.1100 m
    """
    bm = bmesh.new()

    half_w = 0.5 * ENV_WIDTH  # 0.1100
    wall_t = 0.00070          # 0.70 mm paper stock
    m_span = 15               # interior stations on front & back spans
    n_turn = 4                # segments around left/right rounded U-folds

    def make_perimeter_ring(
        half_width_outer: float,
        y_front_outer_base: float,
        y_back_outer_base: float,
        z_front_fn,
        z_back_val: float,
        inward_offset: float,
        relief_scale: float,
        cushion_factor: float,
    ) -> list[bmesh.types.BMVert]:
        """Generate a closed CCW ring of vertices around the envelope perimeter in XY."""
        verts: list[bmesh.types.BMVert] = []

        y_mid_edge = 0.5 * (y_front_outer_base + y_back_outer_base)
        r_edge_outer = 0.5 * (y_back_outer_base - y_front_outer_base)
        r_edge = max(0.00035, r_edge_outer - inward_offset)
        x_straight = half_width_outer - r_edge_outer

        z_center_approx = z_front_fn(0.0)
        front_stations = seam_aligned_front_stations(x_straight, z_center_approx)

        # 1. Front span: left to right (15 seam-aligned stations)
        for x, ov_weight in front_stations:
            zf = z_front_fn(x)
            cx = math.cos(0.5 * math.pi * (x / half_w))
            cushion = 0.00016 * cushion_factor * cx
            bottom_fade = smoothstep(0.0008, 0.0040, zf)
            relief = 0.00028 * relief_scale * ov_weight * bottom_fade
            y = (y_front_outer_base + inward_offset) - relief - cushion
            verts.append(bm.verts.new((x, y, zf)))

        # 2. Right rounded fold: angle from -pi/2 (front) to +pi/2 (back)
        for j in range(n_turn + 1):
            ang = -0.5 * math.pi + math.pi * (j / n_turn)
            s = j / n_turn
            x = x_straight + r_edge * math.cos(ang)
            y = y_mid_edge + r_edge * math.sin(ang)
            s_sm = smoothstep(0.0, 1.0, s)
            z_blend = (1.0 - s_sm) * z_front_fn(x_straight) + s_sm * z_back_val
            verts.append(bm.verts.new((x, y, z_blend)))

        # 3. Back span: right to left (15 smooth stations)
        for i in range(m_span - 1, -1, -1):
            u = -1.0 + 2.0 * (i + 1) / (m_span + 1)
            x = u * x_straight
            cx = math.cos(0.5 * math.pi * (x / half_w))
            cushion = 0.00018 * cushion_factor * cx
            y = (y_back_outer_base - inward_offset) + cushion
            verts.append(bm.verts.new((x, y, z_back_val)))

        # 4. Left rounded fold: angle from +pi/2 (back) to +3*pi/2 (front)
        for j in range(n_turn + 1):
            ang = 0.5 * math.pi + math.pi * (j / n_turn)
            s = j / n_turn
            x = -x_straight + r_edge * math.cos(ang)
            y = y_mid_edge + r_edge * math.sin(ang)
            s_sm = smoothstep(0.0, 1.0, s)
            z_blend = (1.0 - s_sm) * z_back_val + s_sm * z_front_fn(-x_straight)
            verts.append(bm.verts.new((x, y, z_blend)))

        return verts

    y_front_base = -0.00212
    y_back_base = +0.00262

    rings: list[list[bmesh.types.BMVert]] = []
    ring_interior_flag: list[bool] = []

    # --- A. Interior Cavity (from floor z=0.0030 up to inner lip) ---
    inner_z_levels = [0.0030, 0.0320, 0.0720, 0.0980]
    for idx, z_lvl in enumerate(inner_z_levels):
        c_fac = math.sin(math.pi * (z_lvl / ENV_HEIGHT)) * 0.4
        ring = make_perimeter_ring(
            half_width_outer=half_w,
            y_front_outer_base=y_front_base,
            y_back_outer_base=y_back_base,
            z_front_fn=lambda _x, zl=z_lvl: zl,
            z_back_val=z_lvl,
            inward_offset=wall_t,
            relief_scale=0.0,
            cushion_factor=c_fac,
        )
        rings.append(ring)
        if idx > 0:
            ring_interior_flag.append(True)

    # --- B. Rounded Top Paper Rim (rolls 180 deg from inner wall over top lip to outer wall) ---
    r_lip = 0.5 * wall_t  # 0.35 mm radius lip
    rim_angles = [0.0, 0.30 * math.pi, 0.55 * math.pi, 0.80 * math.pi, math.pi]
    for k, phi in enumerate(rim_angles):
        inward = r_lip * (1.0 + math.cos(phi))
        z_lift = r_lip * math.sin(phi)
        r_scale = smoothstep(0.55 * math.pi, math.pi, phi)
        ring = make_perimeter_ring(
            half_width_outer=half_w,
            y_front_outer_base=y_front_base,
            y_back_outer_base=y_back_base,
            z_front_fn=lambda x, zl=z_lift, r=r_lip: (front_throat_z(x) - r) + zl,
            z_back_val=(ENV_HEIGHT - r_lip) + z_lift,
            inward_offset=inward,
            relief_scale=r_scale,
            cushion_factor=0.0,
        )
        rings.append(ring)
        ring_interior_flag.append(k <= 2)

    # --- C. Exterior Walls (descending down to softly rounded bottom fold crease) ---
    outer_u_levels = [0.95, 0.80, 0.58, 0.34, 0.12, 0.03]
    z_bot_radius = 0.0014
    for u in outer_u_levels:
        c_fac = math.sin(math.pi * u)
        ring = make_perimeter_ring(
            half_width_outer=half_w,
            y_front_outer_base=y_front_base,
            y_back_outer_base=y_back_base,
            z_front_fn=lambda x, uu=u: z_bot_radius + uu * (front_throat_z(x) - r_lip - z_bot_radius),
            z_back_val=z_bot_radius + u * (ENV_HEIGHT - r_lip - z_bot_radius),
            inward_offset=0.0,
            relief_scale=1.0,
            cushion_factor=c_fac,
        )
        rings.append(ring)
        ring_interior_flag.append(False)

    # Bottom rounded crease transition rings
    for beta in (0.28 * math.pi, 0.43 * math.pi):
        inward_b = (1.0 - math.cos(beta)) * 0.0016
        z_b = z_bot_radius * (1.0 - math.sin(beta))
        w_shrink = (1.0 - math.cos(beta)) * 0.0011
        ring = make_perimeter_ring(
            half_width_outer=half_w - w_shrink,
            y_front_outer_base=y_front_base,
            y_back_outer_base=y_back_base,
            z_front_fn=lambda _x, zb=z_b: zb,
            z_back_val=z_b,
            inward_offset=inward_b,
            relief_scale=0.0,
            cushion_factor=0.0,
        )
        rings.append(ring)
        ring_interior_flag.append(False)

    face_is_interior: list[bool] = []

    ring_len = len(rings[0])
    for r_idx in range(len(rings) - 1):
        r_a = rings[r_idx]
        r_b = rings[r_idx + 1]
        is_int = ring_interior_flag[r_idx]
        for i in range(ring_len):
            i_next = (i + 1) % ring_len
            bm.faces.new((r_a[i], r_a[i_next], r_b[i_next], r_b[i]))
            face_is_interior.append(is_int)

    def cap_ring_symmetric(ring: list[bmesh.types.BMVert], z_cap: float, is_int: bool) -> None:
        front_verts = ring[0:m_span]
        right_verts = ring[m_span : m_span + n_turn + 1]
        back_verts = list(reversed(ring[m_span + n_turn + 1 : 2 * m_span + n_turn + 1]))
        left_verts = ring[2 * m_span + n_turn + 1 : 2 * m_span + 2 * n_turn + 2]

        y_spine = 0.5 * (front_verts[0].co.y + back_verts[0].co.y)
        spine = [
            bm.verts.new((0.5 * (fv.co.x + bv.co.x), 0.5 * (fv.co.y + bv.co.y), z_cap))
            for fv, bv in zip(front_verts, back_verts)
        ]

        for i in range(m_span - 1):
            bm.faces.new((front_verts[i], front_verts[i + 1], spine[i + 1], spine[i]))
            face_is_interior.append(is_int)
            bm.faces.new((spine[i], spine[i + 1], back_verts[i + 1], back_verts[i]))
            face_is_interior.append(is_int)

        r_hub = bm.verts.new((right_verts[0].co.x, y_spine, z_cap))
        bm.faces.new((front_verts[-1], right_verts[0], r_hub, spine[-1]))
        face_is_interior.append(is_int)
        bm.faces.new((spine[-1], r_hub, right_verts[-1], back_verts[-1]))
        face_is_interior.append(is_int)
        for j in range(n_turn):
            bm.faces.new((right_verts[j], right_verts[j + 1], r_hub))
            face_is_interior.append(is_int)

        l_hub = bm.verts.new((left_verts[0].co.x, y_spine, z_cap))
        bm.faces.new((back_verts[0], left_verts[0], l_hub, spine[0]))
        face_is_interior.append(is_int)
        bm.faces.new((spine[0], l_hub, left_verts[-1], front_verts[0]))
        face_is_interior.append(is_int)
        for j in range(n_turn):
            bm.faces.new((left_verts[j], left_verts[j + 1], l_hub))
            face_is_interior.append(is_int)

    cap_ring_symmetric(rings[0], z_cap=0.0030, is_int=True)
    cap_ring_symmetric(rings[-1], z_cap=0.0000, is_int=False)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    # Normalize exact bounding box to target [ENV_WIDTH, ENV_DEPTH, ENV_HEIGHT]
    bm.verts.ensure_lookup_table()
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    cx = 0.5 * (min_x + max_x)
    cy = 0.5 * (min_y + max_y)
    sx = ENV_WIDTH / (max_x - min_x)
    sy = ENV_DEPTH / (max_y - min_y)
    sz = ENV_HEIGHT / (max_z - min_z)

    for v in bm.verts:
        v.co.x = (v.co.x - cx) * sx
        v.co.y = (v.co.y - cy) * sy
        v.co.z = (v.co.z - min_z) * sz

    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    if non_manifold != 0:
        raise RuntimeError(f"Envelope_Body has {non_manifold} non-manifold edges!")

    mesh = bpy.data.meshes.new("Envelope_Body")
    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = True

    assign_face_colors(mesh, face_is_interior)
    mesh.materials.append(mat)

    obj = bpy.data.objects.new("Envelope_Body", mesh)
    obj.location = (0.0, 0.0, 0.0)
    bpy.context.collection.objects.link(obj)
    return obj


def euro_flap_outline_2d(
    half_base: float,
    virtual_apex_z: float,
    tip_radius: float,
    inset: float = 0.0,
    z_base: float = 0.0,
) -> list[tuple[float, float]]:
    """True parallel inward offset (by perpendicular distance `inset`) of the editorial
    Euro-flap contour, clipped cleanly at horizontal base `z = z_base`. Guarantees strictly
    nested, non-intersecting contours everywhere."""
    z_sh_0 = 0.0024
    w_s_0 = half_base - 0.0010
    dz_0 = virtual_apex_z - z_sh_0
    l_diag_0 = math.hypot(w_s_0, dz_0)
    # Unit outward normal of right diagonal line (w_s_0, z_sh_0) -> (0, virtual_apex_z)
    nx = dz_0 / l_diag_0
    nz = w_s_0 / l_diag_0

    # Parallel inward-offset apex circle: same center (0, z_c), radius reduced by `inset`!
    z_c = virtual_apex_z - tip_radius * l_diag_0 / w_s_0
    r_tip = max(0.003, tip_radius - inset)
    x_tan = r_tip * nx
    z_tan = z_c + r_tip * nz
    ang_tan = math.atan2(nz, nx)

    # Intersect offset right diagonal line `nx*x + nz*z = nx*w_s_0 + nz*z_sh_0 - inset` with `z = z_sh`
    c_line = nx * w_s_0 + nz * z_sh_0 - inset
    z_sh = z_base + 0.0016
    w_s = (c_line - nz * z_sh) / nx
    hb = w_s + 0.0008

    pts: list[tuple[float, float]] = []
    pts.append((hb, z_base))
    pts.append((hb - 0.00035, z_base + 0.45 * (z_sh - z_base)))
    pts.append((w_s, z_sh))

    for k in (0.28, 0.62):
        pts.append((w_s + (x_tan - w_s) * k, z_sh + (z_tan - z_sh) * k))

    n_arc = 12
    for j in range(n_arc + 1):
        ang = ang_tan + (math.pi - 2.0 * ang_tan) * (j / n_arc)
        pts.append((r_tip * math.cos(ang), z_c + r_tip * math.sin(ang)))

    for k in (0.38, 0.72):
        pts.append((-x_tan + (-w_s + x_tan) * k, z_tan + (z_sh - z_tan) * k))

    pts.append((-w_s, z_sh))
    pts.append((-(hb - 0.00035), z_base + 0.45 * (z_sh - z_base)))
    pts.append((-hb, z_base))

    return pts


def build_envelope_flap(mat: bpy.types.Material, hinge_y: float) -> bpy.types.Object:
    """Build Envelope_Flap with local origin (0,0,0) right at the back-upper-edge fold line.
    Uses true parallel contour offsets and horizontal developable quad strips so there are
    zero self-intersections, zero degenerate triangles, and zero triangulation ridges."""
    bm = bmesh.new()

    half_base = 0.5 * ENV_WIDTH - 0.0018
    h_virtual = 0.0730
    r_tip = 0.0168
    half_t = 0.5 * FLAP_THICKNESS  # 0.35 mm

    outer_pts = euro_flap_outline_2d(half_base, h_virtual, r_tip, inset=0.0, z_base=0.0)
    bevel_pts = euro_flap_outline_2d(half_base, h_virtual, r_tip, inset=0.00055, z_base=0.00045)
    margin_pts = euro_flap_outline_2d(half_base, h_virtual, r_tip, inset=0.00480, z_base=0.00280)
    liner_pts = euro_flap_outline_2d(half_base, h_virtual, r_tip, inset=0.00535, z_base=0.00335)

    # Back exterior contours stay flush near the hinge line (small z_base steps) for a crisp rear fold
    back_margin_pts = euro_flap_outline_2d(half_base, h_virtual, r_tip, inset=0.00480, z_base=0.00090)
    back_liner_pts = euro_flap_outline_2d(half_base, h_virtual, r_tip, inset=0.00535, z_base=0.00135)

    def arch_y(z_loc: float) -> float:
        """Gentle natural forward bow near the tip so the opened paper flap feels alive."""
        u = max(0.0, min(1.0, z_loc / FLAP_LENGTH))
        return -0.0016 * (u ** 1.6)

    def make_contour_verts(pts_2d: list[tuple[float, float]], y_off: float):
        return [bm.verts.new((x, y_off + arch_y(z), z)) for (x, z) in pts_2d]

    v_front_liner = make_contour_verts(liner_pts, y_off=-half_t - 0.00008)
    v_front_margin = make_contour_verts(margin_pts, y_off=-half_t)
    v_front_bevel = make_contour_verts(bevel_pts, y_off=-half_t)
    v_rim_mid = make_contour_verts(outer_pts, y_off=0.0)
    v_back_bevel = make_contour_verts(bevel_pts, y_off=+half_t)
    v_back_margin = make_contour_verts(back_margin_pts, y_off=+half_t)
    v_back_liner = make_contour_verts(back_liner_pts, y_off=+half_t)

    face_is_interior: list[bool] = []

    def bridge_open_strips(
        strip_a: list[bmesh.types.BMVert],
        strip_b: list[bmesh.types.BMVert],
        is_int: bool,
        flip: bool = False,
    ) -> None:
        for i in range(len(strip_a) - 1):
            verts = (
                (strip_a[i], strip_b[i], strip_b[i + 1], strip_a[i + 1])
                if flip
                else (strip_a[i], strip_a[i + 1], strip_b[i + 1], strip_b[i])
            )
            bm.faces.new(verts)
            face_is_interior.append(is_int)

    def fill_symmetric_contour_horizontally(
        contour: list[bmesh.types.BMVert], is_int: bool, front_side: bool
    ) -> None:
        """Fill a symmetric odd-length contour [0..2M] (0=right base, M=apex, 2M=left base)
        using horizontal constant-Z quads so cylindrical arch_y(z) is 100% ridge-free."""
        mid = len(contour) // 2
        for k in range(mid - 1):
            r0, r1 = contour[k], contour[k + 1]
            l0, l1 = contour[-1 - k], contour[-2 - k]
            verts = (r0, l0, l1, r1) if front_side else (r0, r1, l1, l0)
            bm.faces.new(verts)
            face_is_interior.append(is_int)
        r_top = contour[mid - 1]
        apex = contour[mid]
        l_top = contour[mid + 1]
        tri = (r_top, l_top, apex) if front_side else (r_top, apex, l_top)
        bm.faces.new(tri)
        face_is_interior.append(is_int)

    # Fill front interior liner & outer borders
    fill_symmetric_contour_horizontally(v_front_liner, is_int=True, front_side=True)
    bridge_open_strips(v_front_liner, v_front_margin, is_int=False, flip=True)
    bridge_open_strips(v_front_margin, v_front_bevel, is_int=False, flip=True)
    bridge_open_strips(v_front_bevel, v_rim_mid, is_int=False, flip=True)

    # Fill mirror-symmetric back exterior strips & smooth horizontal core
    bridge_open_strips(v_rim_mid, v_back_bevel, is_int=False, flip=True)
    bridge_open_strips(v_back_bevel, v_back_margin, is_int=False, flip=True)
    bridge_open_strips(v_back_margin, v_back_liner, is_int=False, flip=True)
    fill_symmetric_contour_horizontally(v_back_liner, is_int=False, front_side=False)

    front_chain = [
        v_rim_mid[-1],
        v_front_bevel[-1],
        v_front_margin[-1],
        v_front_liner[-1],
        v_front_liner[0],
        v_front_margin[0],
        v_front_bevel[0],
        v_rim_mid[0],
    ]
    back_chain = [
        v_rim_mid[-1],
        v_back_bevel[-1],
        v_back_margin[-1],
        v_back_liner[-1],
        v_back_liner[0],
        v_back_margin[0],
        v_back_bevel[0],
        v_rim_mid[0],
    ]

    hinge_mid = [v_rim_mid[-1]]
    for k in range(1, len(front_chain) - 1):
        x_h = 0.5 * (front_chain[k].co.x + back_chain[k].co.x)
        hinge_mid.append(bm.verts.new((x_h, 0.0, -half_t)))
    hinge_mid.append(v_rim_mid[0])

    bm.faces.new((front_chain[0], front_chain[1], hinge_mid[1]))
    face_is_interior.append(False)
    bm.faces.new((hinge_mid[0], hinge_mid[1], back_chain[1]))
    face_is_interior.append(False)
    for k in range(1, len(front_chain) - 2):
        bm.faces.new((front_chain[k], front_chain[k + 1], hinge_mid[k + 1], hinge_mid[k]))
        face_is_interior.append(False)
        bm.faces.new((hinge_mid[k], hinge_mid[k + 1], back_chain[k + 1], back_chain[k]))
        face_is_interior.append(False)
    bm.faces.new((front_chain[-2], front_chain[-1], hinge_mid[-2]))
    face_is_interior.append(False)
    bm.faces.new((hinge_mid[-2], hinge_mid[-1], back_chain[-2]))
    face_is_interior.append(False)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    if non_manifold != 0:
        raise RuntimeError(f"Envelope_Flap has {non_manifold} non-manifold edges!")

    mesh = bpy.data.meshes.new("Envelope_Flap")
    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        # Keep the scored hinge cap crisp so bottom normals never bleed up the smooth flap faces
        poly.use_smooth = poly.normal.z >= -0.45

    assign_face_colors(mesh, face_is_interior)
    mesh.materials.append(mat)

    obj = bpy.data.objects.new("Envelope_Flap", mesh)
    obj.location = (0.0, hinge_y, FLAP_PIVOT_Z + half_t + 0.00004)
    obj.rotation_euler = Euler((math.radians(FLAP_OPEN_ANGLE_DEG), 0.0, 0.0), "XYZ")
    bpy.context.collection.objects.link(obj)
    return obj


def rounded_rect_2d(
    width: float, height: float, radius: float, segs_per_corner: int = 7
) -> list[tuple[float, float]]:
    """CCW 2D points (x, z) for a centered rounded rectangle."""
    hw = 0.5 * width
    hh = 0.5 * height
    r = min(radius, hw * 0.45, hh * 0.45)
    corners = [
        (+hw - r, -hh + r, -0.5 * math.pi, 0.0),
        (+hw - r, +hh - r, 0.0, 0.5 * math.pi),
        (-hw + r, +hh - r, 0.5 * math.pi, math.pi),
        (-hw + r, -hh + r, math.pi, 1.5 * math.pi),
    ]
    pts: list[tuple[float, float]] = []
    for cx, cz, a0, a1 in corners:
        for j in range(segs_per_corner + 1):
            ang = a0 + (a1 - a0) * (j / segs_per_corner)
            pts.append((cx + r * math.cos(ang), cz + r * math.sin(ang)))
    return pts


def build_letter_card(mat: bpy.types.Material) -> bpy.types.Object:
    """Build Letter_Card with centered origin (0,0,0), clean flat front/back surfaces,
    softly rounded corners, subtle beveled cotton-card edges, and normalized planar UVs."""
    bm = bmesh.new()

    half_t = 0.5 * CARD_THICKNESS  # 0.40 mm
    bevel_w = 0.00022              # 0.22 mm crisp card bevel

    pts_outer = rounded_rect_2d(CARD_WIDTH, CARD_HEIGHT, CARD_CORNER_RADIUS, segs_per_corner=7)
    pts_inner = rounded_rect_2d(
        CARD_WIDTH - 2.0 * bevel_w,
        CARD_HEIGHT - 2.0 * bevel_w,
        max(0.0005, CARD_CORNER_RADIUS - bevel_w),
        segs_per_corner=7,
    )
    pts_core = rounded_rect_2d(
        CARD_WIDTH - 0.0040,
        CARD_HEIGHT - 0.0040,
        max(0.0005, CARD_CORNER_RADIUS - 0.0020),
        segs_per_corner=7,
    )

    r_front_core = [bm.verts.new((x, -half_t, z)) for (x, z) in pts_core]
    r_front_flat = [bm.verts.new((x, -half_t, z)) for (x, z) in pts_inner]
    r_front_edge = [bm.verts.new((x, -half_t + 0.35 * half_t, z)) for (x, z) in pts_outer]
    r_back_edge = [bm.verts.new((x, +half_t - 0.35 * half_t, z)) for (x, z) in pts_outer]
    r_back_flat = [bm.verts.new((x, +half_t, z)) for (x, z) in pts_inner]
    r_back_core = [bm.verts.new((x, +half_t, z)) for (x, z) in pts_core]

    n = len(pts_outer)

    def bridge_closed(ra, rb):
        for i in range(n):
            inext = (i + 1) % n
            bm.faces.new((ra[i], ra[inext], rb[inext], rb[i]))

    bm.faces.new(list(reversed(r_front_core)))
    bridge_closed(r_front_flat, r_front_core)
    bridge_closed(r_front_edge, r_front_flat)
    bridge_closed(r_back_edge, r_front_edge)
    bridge_closed(r_back_flat, r_back_edge)
    bridge_closed(r_back_core, r_back_flat)
    bm.faces.new(r_back_core)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    planar_ngons = [f for f in bm.faces if len(f.verts) > 4]
    bmesh.ops.triangulate(bm, faces=planar_ngons, quad_method="BEAUTY", ngon_method="EAR_CLIP")

    uv_layer = bm.loops.layers.uv.new("UVMap")
    for face in bm.faces:
        for loop in face.loops:
            co = loop.vert.co
            u = (co.x / CARD_WIDTH) + 0.5
            v = (co.z / CARD_HEIGHT) + 0.5
            loop[uv_layer].uv = (u, v)

    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    if non_manifold != 0:
        raise RuntimeError(f"Letter_Card has {non_manifold} non-manifold edges!")

    mesh = bpy.data.meshes.new("Letter_Card")
    bm.to_mesh(mesh)
    bm.free()

    for poly in mesh.polygons:
        poly.use_smooth = abs(poly.normal.y) <= 0.999

    mesh.materials.append(mat)

    obj = bpy.data.objects.new("Letter_Card", mesh)
    obj.location = (0.0, CARD_CENTER_Y, CARD_CENTER_Z)
    bpy.context.collection.objects.link(obj)
    return obj


def create_studio_preview_rig() -> bpy.types.Collection:
    """Create a separate Studio_Preview collection (camera, backdrop, directional studio lights)
    for rendering preview.webp. Excluded from GLB export."""
    studio_col = bpy.data.collections.new("Studio_Preview")
    bpy.context.scene.collection.children.link(studio_col)

    def link_to_studio(obj: bpy.types.Object) -> None:
        studio_col.objects.link(obj)

    # Seamless curved cyclorama backdrop
    bm = bmesh.new()
    xs = [-1.1, -0.4, 0.0, 0.4, 1.1]
    profile_yz = [(-0.65, 0.0), (-0.05, 0.0), (0.22, 0.0)]
    r_cyc = 0.28
    for k in range(1, 12):
        ang = 0.5 * math.pi * (k / 11.0)
        profile_yz.append((0.22 + r_cyc * math.sin(ang), r_cyc * (1.0 - math.cos(ang))))
    profile_yz.append((0.22 + r_cyc, 0.85))

    grid = [[bm.verts.new((x, y, z)) for x in xs] for (y, z) in profile_yz]
    for r in range(len(grid) - 1):
        for c in range(len(xs) - 1):
            bm.faces.new((grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    bg_mesh = bpy.data.meshes.new("Studio_Backdrop")
    bm.to_mesh(bg_mesh)
    bm.free()
    for p in bg_mesh.polygons:
        p.use_smooth = True

    bg_mat = create_uniform_material("Mat_Studio_Backdrop", COL_STUDIO_BG, roughness=0.96)
    bg_mesh.materials.append(bg_mat)
    bg_obj = bpy.data.objects.new("Studio_Backdrop", bg_mesh)
    link_to_studio(bg_obj)

    # 3/4 Front Camera (72mm editorial product lens, zero wide-angle distortion)
    cam_data = bpy.data.cameras.new("Preview_Camera")
    cam_data.lens = 72.0
    cam_data.sensor_width = 36.0
    cam_data.clip_start = 0.01
    cam_data.clip_end = 10.0

    cam_obj = bpy.data.objects.new("Preview_Camera", cam_data)
    target = Vector((-0.004, 0.0, 0.086))
    cam_pos = Vector((0.225, -0.525, 0.182))
    cam_obj.location = cam_pos
    direction = target - cam_pos
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    link_to_studio(cam_obj)
    bpy.context.scene.camera = cam_obj

    def add_area_light(
        name: str,
        pos: tuple[float, float, float],
        aim: Vector,
        energy: float,
        size_x: float,
        size_y: float,
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        ldata = bpy.data.lights.new(name=name, type="AREA")
        ldata.energy = energy
        ldata.shape = "RECTANGLE"
        ldata.size = size_x
        ldata.size_y = size_y
        ldata.color = color
        if hasattr(ldata, "use_shadow"):
            ldata.use_shadow = True
        lobj = bpy.data.objects.new(name, ldata)
        lobj.location = Vector(pos)
        lobj.rotation_euler = (aim - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        link_to_studio(lobj)

    # Directional raking studio key light from front-left-upper: reveals folded pocket seams & casts
    # a gentle shadow from Letter_Card onto Envelope_Flap's warmer interior liner
    add_area_light(
        "Light_Key",
        pos=(-0.54, -0.34, 0.34),
        aim=Vector((0.0, 0.0, 0.085)),
        energy=15.5,
        size_x=0.30,
        size_y=0.26,
        color=(1.0, 0.985, 0.962),
    )
    # Soft studio fill from right-front (gentle ~3.5:1 key-to-fill contrast)
    add_area_light(
        "Light_Fill",
        pos=(0.56, -0.44, 0.22),
        aim=Vector((0.0, 0.0, 0.080)),
        energy=4.2,
        size_x=0.55,
        size_y=0.45,
        color=(0.98, 0.99, 1.0),
    )
    # Subtle rear-top rim light catching the paper edge of the flap and letter card
    add_area_light(
        "Light_Rim",
        pos=(0.14, 0.30, 0.44),
        aim=Vector((0.0, 0.0, 0.125)),
        energy=6.5,
        size_x=0.38,
        size_y=0.20,
        color=(1.0, 0.99, 0.97),
    )

    world = bpy.data.worlds.new("Studio_World")
    if world.node_tree is None:
        world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = COL_STUDIO_BG
        bg_node.inputs["Strength"].default_value = 0.22
    bpy.context.scene.world = world

    return studio_col


def render_preview_webp(width: int = 1600, height: int = 1200) -> None:
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
        avail_transforms = [
            it.identifier
            for it in scene.view_settings.bl_rna.properties["view_transform"].enum_items
        ]
        if "AgX" in avail_transforms:
            scene.view_settings.view_transform = "AgX"
            avail_looks = [
                it.identifier
                for it in scene.view_settings.bl_rna.properties["look"].enum_items
            ]
            if "AgX - Medium High Contrast" in avail_looks:
                scene.view_settings.look = "AgX - Medium High Contrast"
        scene.view_settings.exposure = -0.05

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_png = Path(tmpdir) / "preview.png"
        scene.render.filepath = str(tmp_png)
        bpy.ops.render.render(write_still=True)

        cwebp_bin = shutil.which("cwebp")
        if cwebp_bin:
            subprocess.run(
                [cwebp_bin, "-q", "93", str(tmp_png), "-o", str(PREVIEW_WEBP_PATH)],
                check=True,
            )
        else:
            scene.render.image_settings.file_format = "WEBP"
            scene.render.image_settings.quality = 93
            scene.render.filepath = str(PREVIEW_WEBP_PATH)
            bpy.ops.render.render(write_still=True)


def export_glb(asset_objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in asset_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = asset_objects[0]

    bpy.ops.export_scene.gltf(
        filepath=str(GLB_PATH),
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=True,
        export_normals=True,
        export_materials="EXPORT",
        export_vertex_color="MATERIAL",
        export_cameras=False,
        export_lights=False,
    )


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    clear_scene()

    mat_envelope = create_vertex_color_material("Mat_Envelope", roughness=0.84)
    mat_card = create_uniform_material("Mat_Letter_Card", COL_LETTER_CARD, roughness=0.76)

    env_body = build_envelope_body(mat_envelope)
    # Align flap hinge flush with the back wall of Envelope_Body (outer Y = +0.00280, wall half_t = 0.00035)
    hinge_y = 0.5 * ENV_DEPTH - 0.5 * FLAP_THICKNESS  # +0.00245 m
    env_flap = build_envelope_flap(mat_envelope, hinge_y=hinge_y)
    letter_card = build_letter_card(mat_card)
    asset_objects = [env_body, env_flap, letter_card]

    create_studio_preview_rig()

    export_glb(asset_objects)
    render_preview_webp(width=1600, height=1200)

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), compress=True)

    for obj in asset_objects:
        tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        print(
            f"{obj.name}: dims={tuple(round(d, 5) for d in obj.dimensions)}, "
            f"loc={tuple(round(c, 5) for c in obj.location)}, tris={tris}"
        )


if __name__ == "__main__":
    main()
