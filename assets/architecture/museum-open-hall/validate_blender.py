#!/usr/bin/env python3
"""
Blender & glTF Structural Validation Script for:
  Open Skylight Museum Hall V2 (`assets/architecture/museum-open-hall/`)

Verifies both `model.blend` and re-imported `model.glb`:
  - Preservation of all 7 hierarchy groups, all 16 original semantic meshes + V2 spatial-continuity
    meshes (`Secondary_Gallery`, `Wall_Back_Portal_Closure`, `Entrance_Vestibule`) + all 15
    independently addressable `Fixture_Head_*` spotlight nodes
  - Exact main-hall clear dimensions (24.00 x 18.00 x 9.00 m), floor Y = 0.00 m, pitched skylight
    ridge elevation (Y >= 12.50 m), and all 9 semantic PBR materials
  - Presence of dual-UV `occlusionTexture` (`texCoord: 1`) on `Mat_Wall_Plaster`,
    `Mat_Floor_Concrete`, and `Mat_Ceiling`
  - Preservation of all 9+1 artwork anchors, 9 floor placement anchors, 15 lighting anchors,
    and 14+1 navigation anchors, zero degenerate triangles, and relative `//textures/` paths
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import bpy

ASSET_DIR = Path(__file__).resolve().parent
REPO_ROOT = ASSET_DIR.parent.parent.parent
WORK_VAL_DIR = REPO_ROOT / ".work" / "architecture" / "museum-open-hall" / "validation"


def parse_glb_json(glb_path: Path) -> dict:
    with glb_path.open("rb") as f:
        magic, version, _ = struct.unpack("<4sII", f.read(12))
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
    mats_by_name = {m.get("name", ""): m for m in gltf_json.get("materials", [])}
    mat_names = list(mats_by_name.keys())

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
        "Wall_Back_Portal_Closure",
        "Secondary_Gallery",
        "Wall_Entrance",
        "Entrance_Vestibule",
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
    required_heads = [
        f"Fixture_Head_{grp}_{i:02d}"
        for grp in ("Back", "Left", "Right")
        for i in range(1, 6)
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
    ] + ["Anchor_Artwork_Secondary_01"]
    required_nav_anchors = [
        "Anchor_Navigation_Entrance",
        "Anchor_Navigation_Center",
        "Anchor_Navigation_Back",
        "Anchor_Navigation_Left",
        "Anchor_Navigation_Right",
        "Anchor_Navigation_Secondary",
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

    for label, req in [
        ("groups", required_groups),
        ("meshes", required_meshes),
        ("fixture_heads", required_heads),
        ("materials", required_materials),
        ("art_anchors", required_art_anchors),
        ("nav_anchors", required_nav_anchors),
        ("place_anchors", required_place_anchors),
        ("light_anchors", required_light_anchors),
    ]:
        pool = mat_names if label == "materials" else node_names
        missing = [x for x in req if x not in pool]
        assert not missing, f"Missing {label}: {missing}"

    forbidden_leaks = [
        n for n in node_names
        if n.startswith(("Studio_", "Demo_", "Preview_Camera", "Render_Cam"))
    ]
    assert not forbidden_leaks, f"Authoring/demo objects leaked into GLB: {forbidden_leaks}"
    assert "cameras" not in gltf_json, "Cameras leaked into canonical GLB"
    assert "lights" not in gltf_json.get("extensions", {}), "Punctual lights leaked into canonical GLB"

    # Verify dual-UV neutral `occlusionTexture` (`texCoord == 1`) on primary architectural surfaces
    for ao_mat_name in ("Mat_Wall_Plaster", "Mat_Floor_Concrete", "Mat_Ceiling"):
        occ = mats_by_name[ao_mat_name].get("occlusionTexture")
        assert occ is not None, f"{ao_mat_name} missing glTF occlusionTexture"
        assert occ.get("texCoord") == 1, f"{ao_mat_name} occlusionTexture expected texCoord=1, got {occ}"

    nodes_by_name = {n.get("name", ""): n for n in gltf_json.get("nodes", [])}
    for aname in required_art_anchors:
        anode = nodes_by_name[aname]
        ay = anode["translation"][1]
        max_h = anode.get("extras", {}).get("maxHeightMeters", 0.0)
        bottom_y = ay - max_h * 0.5
        assert bottom_y >= 0.249, f"{aname} centered maxHeightMeters={max_h} dips to Y={bottom_y:.3f}m"

    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    for img in bpy.data.images:
        if img.filepath:
            assert img.filepath.startswith("//textures/"), f"Non-relative image path in model.blend: {img.filepath}"

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
        assert len(me.uv_layers) > 0, f"Mesh {obj.name} is missing UVs"

        for tri in me.loop_triangles:
            if tri.area < 1e-10:
                degenerate_faces += 1

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

    # Verify exact 24 x 18 x 9 m main-hall clear bounds AND pitched skylight ridge height > 12.6 m!
    assert abs(mesh_report["Floor"]["boundsGltfMax"][1] - 0.0) < 1e-4
    assert abs(mesh_report["Wall_Left"]["boundsGltfMax"][0] - (-12.0)) < 1e-3
    assert abs(mesh_report["Wall_Right"]["boundsGltfMin"][0] - 12.0) < 1e-3
    assert abs(mesh_report["Wall_Back"]["boundsGltfMax"][2] - (-9.0)) < 1e-3
    assert abs(mesh_report["Wall_Entrance"]["boundsGltfMin"][2] - 9.0) < 1e-3
    assert abs(mesh_report["Ceiling"]["boundsGltfMin"][1] - 9.0) < 1e-3
    assert mesh_report["Skylight_Glass"]["boundsGltfMax"][1] >= 12.60, (
        f"Expected pitched skylight glass ridge >= 12.60 m, got {mesh_report['Skylight_Glass']}"
    )
    assert degenerate_faces == 0, f"Found {degenerate_faces} degenerate triangles"

    summary = {
        "status": "PASS",
        "glbPath": str(glb_path.relative_to(REPO_ROOT)),
        "glbSizeBytes": len(glb_bytes),
        "glbSha256": glb_sha256,
        "nodeCount": len(node_names),
        "meshObjectCount": len(mesh_report),
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
