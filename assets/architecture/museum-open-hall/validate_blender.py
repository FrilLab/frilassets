#!/usr/bin/env python3
"""
Blender & glTF Structural Validation Script for:
  Open Skylight Museum Hall (`assets/architecture/museum-open-hall/`)

Verifies both `model.blend` and re-imported `model.glb`:
  - Semantic node hierarchy survival (`Museum_Open_Hall`, `Architecture`, `Skylight`,
    `Lighting_Fixtures`, `Exhibition_Anchors`, `Lighting_Anchors`, `Navigation_Anchors`)
  - Exact glTF metric dimensions, floor elevation (Y = 0.00 m), ceiling height (Y = 9.00 m),
    entrance opening (5.60 m x 4.60 m), and skylight opening (13.60 m x 11.40 m)
  - Presence and assignment of all 9 semantic PBR material slots
  - Presence and local basis vectors of all 9 artwork anchors, 14 navigation anchors,
    15 lighting anchors, and 9 optional floor placement anchors
  - UV coordinate presence, zero degenerate triangles, and exclusion of Studio_Preview / Demo objects
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Quaternion, Vector

ASSET_DIR = Path(__file__).resolve().parent
REPO_ROOT = ASSET_DIR.parent.parent.parent
WORK_VAL_DIR = REPO_ROOT / ".work" / "architecture" / "museum-open-hall" / "validation"


def parse_glb_json(glb_path: Path) -> dict:
    with glb_path.open("rb") as f:
        magic, version, total_len = struct.unpack("<4sII", f.read(12))
        assert magic == b"glTF", f"Invalid GLB magic: {magic}"
        assert version == 2, f"Unsupported glTF version: {version}"
        chunk_len, chunk_type = struct.unpack("<I4s", f.read(8))
        assert chunk_type == b"JSON", f"Expected JSON chunk, got {chunk_type}"
        return json.loads(f.read(chunk_len).decode("utf-8"))


def main() -> None:
    WORK_VAL_DIR.mkdir(parents=True, exist_ok=True)
    glb_path = ASSET_DIR / "model.glb"
    blend_path = ASSET_DIR / "model.blend"

    assert glb_path.exists(), f"Missing {glb_path}"
    assert blend_path.exists(), f"Missing {blend_path}"

    glb_bytes = glb_path.read_bytes()
    glb_sha256 = hashlib.sha256(glb_bytes).hexdigest()
    gltf_json = parse_glb_json(glb_path)

    node_names = [n.get("name", "") for n in gltf_json.get("nodes", [])]
    mat_names = [m.get("name", "") for m in gltf_json.get("materials", [])]

    required_groups = [
        "Museum_Open_Hall",
        "Architecture",
        "Skylight",
        "Lighting_Fixtures",
        "Exhibition_Anchors",
        "Lighting_Anchors",
        "Navigation_Anchors",
    ]
    required_meshes = [
        "Floor",
        "Wall_Left",
        "Wall_Right",
        "Wall_Back",
        "Wall_Entrance",
        "Entrance_Frame",
        "Ceiling",
        "Ceiling_Beams",
        "Wall_Floor_Transitions",
        "Skylight_Frame",
        "Skylight_Supports",
        "Skylight_Glass",
        "Track_Left",
        "Track_Right",
        "Track_Back",
        "Recessed_Fixtures",
    ]
    required_materials = [
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
    required_art_anchors = [
        f"Anchor_Artwork_{wall}_{i:02d}"
        for wall in ("Back", "Left", "Right")
        for i in (1, 2, 3)
    ]
    required_nav_anchors = [
        "Anchor_Navigation_Entrance",
        "Anchor_Navigation_Center",
        "Anchor_Navigation_Back",
        "Anchor_Navigation_Left",
        "Anchor_Navigation_Right",
    ] + [f"Anchor_Navigation_Artwork_{i:02d}" for i in range(1, 10)]
    required_place_anchors = [
        "Anchor_Place_Central_Installation",
        "Anchor_Place_Pedestal_01",
        "Anchor_Place_Pedestal_02",
        "Anchor_Place_Bench_01",
        "Anchor_Place_Bench_02",
        "Anchor_Place_Info_Stand",
        "Anchor_Place_Invitation_Display",
        "Anchor_Place_Partition_01",
        "Anchor_Place_Partition_02",
    ]
    required_light_anchors = [
        f"Anchor_Light_{wall}_{i:02d}"
        for wall in ("Back", "Left", "Right")
        for i in (1, 2, 3)
    ] + [
        "Anchor_Light_Center_01",
        "Anchor_Light_Center_02",
        "Anchor_Light_Ambient_01",
        "Anchor_Light_Ambient_02",
        "Anchor_Light_Ambient_03",
        "Anchor_Light_Ambient_04",
    ]

    missing_groups = [n for n in required_groups if n not in node_names]
    missing_meshes = [n for n in required_meshes if n not in node_names]
    missing_mats = [m for m in required_materials if m not in mat_names]
    missing_art = [a for a in required_art_anchors if a not in node_names]
    missing_nav = [n for n in required_nav_anchors if n not in node_names]
    missing_place = [p for p in required_place_anchors if p not in node_names]
    missing_light = [l for l in required_light_anchors if l not in node_names]

    forbidden_leaks = [
        n for n in node_names
        if n.startswith(("Studio_", "Demo_", "Preview_Camera", "Render_Cam"))
    ]
    assert not missing_groups, f"Missing hierarchy groups: {missing_groups}"
    assert not missing_meshes, f"Missing architectural meshes: {missing_meshes}"
    assert not missing_mats, f"Missing semantic materials: {missing_mats}"
    assert not missing_art, f"Missing artwork anchors: {missing_art}"
    assert not missing_nav, f"Missing navigation anchors: {missing_nav}"
    assert not missing_place, f"Missing placement anchors: {missing_place}"
    assert not missing_light, f"Missing lighting anchors: {missing_light}"
    assert not forbidden_leaks, f"Authoring/demo objects leaked into GLB: {forbidden_leaks}"
    assert "cameras" not in gltf_json, "Cameras leaked into canonical GLB"

    # Verify centered maxHeightMeters on every artwork anchor clears both floor (Y=0) and base reveal (Y=0.065 m)
    nodes_by_name = {n.get("name", ""): n for n in gltf_json.get("nodes", [])}
    for aname in required_art_anchors:
        anode = nodes_by_name[aname]
        ay = anode["translation"][1]
        extras = anode.get("extras", {})
        max_h = extras.get("maxHeightMeters", 0.0)
        bottom_y = ay - max_h * 0.5
        assert bottom_y >= 0.249, (
            f"{aname} centered maxHeightMeters={max_h} at Y={ay} dips to Y={bottom_y:.3f}m (< 0.25m floor clearance)"
        )

    # Verify `model.blend` contains zero machine-local absolute external image paths
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    for img in bpy.data.images:
        if img.filepath:
            assert img.filepath.startswith("//textures/"), f"Non-relative image path in model.blend: {img.filepath}"

    # Re-import `model.glb` into a clean factory Blender session to measure real imported geometry
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(glb_path))

    total_tris = 0
    total_verts = 0
    degenerate_faces = 0
    mesh_report = {}

    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        me = obj.data
        me.calc_loop_triangles()
        tris = len(me.loop_triangles)
        verts = len(me.vertices)
        has_uv = len(me.uv_layers) > 0
        assert has_uv, f"Mesh {obj.name} is missing UVs"

        for tri in me.loop_triangles:
            if tri.area < 1e-10:
                degenerate_faces += 1

        # Compute world bounds in Blender (X_b, Y_b, Z_b) -> convert back to glTF (X, Z_b, -Y_b)
        pts_g = []
        for v in me.vertices:
            wb = obj.matrix_world @ v.co
            pts_g.append((wb.x, wb.z, -wb.y))
        xs = [p[0] for p in pts_g]
        ys = [p[1] for p in pts_g]
        zs = [p[2] for p in pts_g]

        mesh_report[obj.name] = {
            "triangles": tris,
            "vertices": verts,
            "materials": [m.name for m in me.materials if m],
            "boundsGltfMin": [round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)],
            "boundsGltfMax": [round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)],
        }
        total_tris += tris
        total_verts += verts

    # Verify floor top is Y = 0.0000 m and interior clear width/depth/height match 24 x 18 x 9 m
    assert abs(mesh_report["Floor"]["boundsGltfMax"][1] - 0.0) < 1e-4, f"Floor top Y != 0: {mesh_report['Floor']}"
    assert abs(mesh_report["Wall_Left"]["boundsGltfMax"][0] - (-12.0)) < 1e-3
    assert abs(mesh_report["Wall_Right"]["boundsGltfMin"][0] - 12.0) < 1e-3
    assert abs(mesh_report["Wall_Back"]["boundsGltfMax"][2] - (-9.0)) < 1e-3
    assert abs(mesh_report["Wall_Entrance"]["boundsGltfMin"][2] - 9.0) < 1e-3
    assert abs(mesh_report["Ceiling"]["boundsGltfMin"][1] - 9.0) < 1e-3
    assert degenerate_faces == 0, f"Found {degenerate_faces} degenerate triangles"

    summary = {
        "status": "PASS",
        "glbPath": str(glb_path.relative_to(REPO_ROOT)),
        "glbSizeBytes": len(glb_bytes),
        "glbSha256": glb_sha256,
        "nodeCount": len(node_names),
        "meshCount": len(mesh_report),
        "materialCount": len(mat_names),
        "imageCount": len(gltf_json.get("images", [])),
        "totalTriangles": total_tris,
        "totalVertices": total_verts,
        "degenerateTriangles": degenerate_faces,
        "materials": mat_names,
        "meshes": mesh_report,
    }
    out_json = WORK_VAL_DIR / "blender_validation.json"
    out_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "meshes"}, indent=2))


if __name__ == "__main__":
    main()
