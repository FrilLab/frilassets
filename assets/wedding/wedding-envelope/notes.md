# Wedding Envelope (`wedding/wedding-envelope`)

## Mesh Names & Structure

The asset exports strictly three standalone, single-primitive meshes (compatible with `THREE.GLTFLoader` so each node resolves directly to a `THREE.Mesh`):

1. `Envelope_Body` — 1,424 triangles (714 vertices)
2. `Envelope_Flap` — 330 triangles (167 vertices)
3. `Letter_Card` — 380 triangles (192 vertices)

- **Total geometry**: 2,134 triangles (1,073 vertices)
- **Standalone GLB size**: ~58.5 KB (`58,480` bytes), zero external files or image textures

## Dimensions (Meters)

Coordinate conventions:
- **Blender**: `+X` right, `-Y` front, `+Z` up
- **glTF / Three.js (`+Y` up)**: `+X` right, `+Y` up, `+Z` front

| Part | Width (`X`) | Height | Thickness / Depth | Notes |
| :--- | :---: | :---: | :---: | :--- |
| `Envelope_Body` | `0.2200 m` | `0.1100 m` | `0.0056 m` | Hollow manifold pocket (`0.7 mm` cotton stock walls, `3.7 mm` internal slot clearance) |
| `Envelope_Flap` | `0.2184 m` | `0.0700 m` (length) | `0.0007 m` (sheet) | Editorial rounded Euro-flap (`16.8 mm` apex radius) with gentle natural paper bow |
| `Letter_Card` | `0.2050 m` | `0.0950 m` | `0.0008 m` | Flat heavy cotton card with `3.0 mm` rounded corners and normalized `[0, 1]` planar UVs |
| **Assembled Bounds** | `0.2200 m` | `0.1790 m` | `0.0178 m` | Includes opened tilted flap height (`Z_max = 0.1790 m`) and rear tilt |

## Letter Card Visibility & Clearance

- The top edge of `Letter_Card` sits at `0.1380 m` above the ground plane (`Z = 0` in Blender / `Y = 0` in Three.js), with its bottom edge at `0.0430 m` inside the pocket.
- **Extension above the `0.1100 m` upper envelope edge**: **`0.0280 m` (`28.0 mm`)**, or **`29.5%`** of the `0.0950 m` card height.
- **Extension above the `0.1048 m` tailored front pocket lip**: **`0.0332 m` (`33.2 mm`)**, or **`34.9%`** of the card height.
- Both measurements sit cleanly within the `25%–35%` target visibility window.
- Horizontal clearance inside the pocket is `5.0 mm` per side (`7.5 mm` inset from the outer `0.2200 m` envelope edges), and front/back slot clearance exceeds `1.1 mm` on both sides with zero BVH triangle intersections.

## Flap & Card Origins / Animation Pivots

- **`Envelope_Flap` pivot**:
  - Placed directly on the horizontal fold line along the back upper edge: `(0.0, +0.00245, 0.11039)` in Blender (`[0.0, 0.11039, -0.00245]` in glTF/Three.js).
  - Local mesh geometry is authored in its neutral vertical hinge frame with a rounded semi-cylindrical hinge edge, and rotated `-11.5°` around the horizontal `X` axis (`flap.rotation.x` in Three.js) for a natural just-opened presentation pose.
  - Animating `Envelope_Flap.rotation.x` in Three.js pivots cleanly around the back upper crease without detaching or clipping.
- **`Letter_Card` origin**:
  - Placed at the exact geometric center of the card: `(0.0, +0.0001, 0.0905)` in Blender (`[0.0, 0.0905, -0.0001]` in glTF/Three.js).
  - Animating `Letter_Card.position.y` in Three.js slides the card straight up and down through the envelope mouth without colliding with `Envelope_Body` or `Envelope_Flap`.

## Material Summary

No image textures are used in v1:
- **`Mat_Envelope`** (`Principled BSDF`, `Roughness = 0.84`, `Metallic = 0.0`, `IOR = 1.48`):
  - Driven by face-corner vertex color attribute `Color` (`COLOR_0` in glTF) so exterior and interior tones export inside a single glTF primitive per mesh:
    - **Envelope exterior**: Warm ivory / soft cream (`#F1E7D6` sRGB)
    - **Envelope interior & bespoke flap liner**: Slightly darker warm champagne ivory (`#DBC9B0` sRGB), inset `4.8 mm` from the flap edge like a traditional lined wedding envelope
- **`Mat_Letter_Card`** (`Principled BSDF`, `Roughness = 0.76`, `Metallic = 0.0`, `IOR = 1.48`):
  - Uniform clean pearl off-white (`#FCFBF7` sRGB), subtly brighter than the envelope exterior to ensure clear visual separation at the pocket opening.

## Key Modeling Decisions

- **Pocket-side front presentation**: Oriented with the tailored pocket facing forward (`+Z` in glTF / `-Y` in Blender) and the continuous rear sheet + flap hinge along the back upper edge, allowing `Envelope_Flap` to frame the emerging `Letter_Card` with its warmer interior liner while keeping the front of `Letter_Card` completely unobstructed for future typography or texture overlays.
- **Seam-aligned manifold topology**: Dedicated edge loops track the diagonal front pocket overlap seams (`0.28 mm` paper step with tight normal-support loops) and true parallel Minkowski contour offsets form the Euro-flap, ensuring crisp editorial shading with zero non-manifold edges, zero degenerate faces, and zero self-intersections.
- **Studio preview separation**: Camera, backdrop, and studio area lights live in a dedicated `Studio_Preview` collection in `model.blend` for reproducible `preview.webp` rendering, and are excluded from `model.glb`.
