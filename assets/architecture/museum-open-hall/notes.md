# Open Skylight Museum Hall (`architecture/museum-open-hall`)

## 1. Overview & Architectural Concept

**Open Skylight Museum Hall** is a contemporary, real-world-scale museum exhibition hall designed for photography galleries, fine-art exhibitions, sculptural installations, digital showrooms, and interactive WebGL experiences across **FrilCraft**, **FrilStudio**, and **FrilRemotion**.

Key architectural features:
- **Monumental clear exhibition volume**: `24.00 m` wide × `18.00 m` deep × `9.00 m` ceiling height (`432.0 m²` column-free exhibition floor).
- **Integrated 4 × 4 skylight coffer**: `13.60 m × 11.40 m` ceiling aperture rising through a `3.6°` canted daylight reveal well (`Y = 9.00 m` to `10.28 m`), articulated by three slender tapered transverse structural beams (`Ceiling_Beams`), three notched longitudinal daylight-baffle supports (`Skylight_Supports`), a powder-coated aluminum mullion system (`Skylight_Frame`), and sixteen independently toggleable low-iron glazing panes (`Skylight_Glass`).
- **Tectonic architectural detailing**: `400 mm` structural exterior walls, a `1.20 m`-deep monumental entrance portal (`5.60 m × 4.60 m` clear opening) lined with a `60 mm` dark bronze-charcoal metal frame (`Entrance_Frame`) and `12 mm` shadow quirks, continuous `65 mm × 28 mm` recessed base shadow-gap reveals and `25 mm` ceiling perimeter reveals (`Wall_Floor_Transitions`), honed poured-in-place architectural concrete floor bays with `3.2 mm` micro-beveled control joints aligned to the skylight grid (`Floor`), and a recessed U-shaped architectural lighting track channel housing fifteen aimed museum spotlights and ten trimless perimeter downlights (`Lighting_Fixtures`).

---

## 2. Sourcing Gate Record (`docs/asset-sourcing.md`)

- **Asset ID**: `architecture/museum-open-hall`
- **Search date**: `2026-11-27`
- **Local packages checked**: `assets/wedding/wedding-envelope`, `assets/stationery/fril-signature-seal`, `assets/objects/editorial-magazine`, `materials/*`, `textures/*`, `environments/*`, plus read-only checks of sibling workspaces (`frilcarft`, `fril-studio`, `friladd`). No reusable architectural hall, skylight, track fixture, plaster, or honed concrete package existed locally.

| Query / Source | Candidate URL | Creator | License Evidence URL | Suitability / Blockers |
| :--- | :--- | :--- | :--- | :--- |
| Sketchfab (`art+gallery`, CC0 downloadable) | `https://sketchfab.com/3d-models/none-79805169b85e47d9a60be25035e387f2` (*Arts of Southeast Asia gallery*) | Minneapolis Institute of Art (`artsmia`) | `https://creativecommons.org/publicdomain/zero/1.0/` | Rejected: photogrammetry scan (`99,610` faces) with permanently baked display cases, exhibits, and baked lighting; lacks modular walls, skylight, and semantic anchors. |
| Sketchfab (`museum+hall`, CC0 downloadable) | `https://sketchfab.com/3d-models/none-97673d5721d743328022c282b77b33ae` (*Wan fa Gui yi Hall*) | Världskulturmuseerna | `https://creativecommons.org/publicdomain/zero/1.0/` | Rejected: `2.83M`-face museum artifact scan of a historic temple model rather than an interior exhibition hall. |
| Sketchfab / Poly Haven (`skylight`, `track+light`, CC0) | `https://polyhaven.com/models` | Poly Haven contributors | `https://polyhaven.com/license` | `0` CC0 gallery track-light systems or skylight hall models available (`modern_ceiling_lamp_01` is a domestic pendant/ceiling lamp). |
| Poly Haven (`white_plaster_02`) | `https://polyhaven.com/a/white_plaster_02` | Rob Tuytel | `https://polyhaven.com/license` | Rejected after visual inspection: coarse pitted exterior sand stucco (`1 m × 1 m`), unsuitable for calm contemporary museum gallery walls. |
| Poly Haven (`smooth_concrete_floor`, `concrete_floor_01`) | `https://polyhaven.com/a/smooth_concrete_floor` | Dimitrios Savva / Rob Tuytel | `https://polyhaven.com/license` | Rejected after visual inspection: `smooth_concrete_floor` has heavy reddish-brown industrial staining and cracks; `concrete_floor_01` is rough outdoor gravel aggregate. |
| ambientCG (`Plaster001`, `PaintedPlaster017`) | `https://ambientcg.com/a/Plaster001`, `https://ambientcg.com/a/PaintedPlaster017` | Lennart Demes (ambientCG) | `https://docs.ambientcg.com/license/` | Rejected after visual inspection: `Plaster001` has directional exterior trowel gouges that stripe visibly across `24 m × 9 m` walls; `PaintedPlaster017` contains a prominent central crack that tiles repetitively. |
| ambientCG (`Concrete042A`, `Concrete046`, `Terrazzo004`) | `https://ambientcg.com/a/Concrete042A`, `https://ambientcg.com/a/Concrete046`, `https://ambientcg.com/a/Terrazzo004` | Lennart Demes (ambientCG) | `https://docs.ambientcg.com/license/` | Rejected after visual inspection: `Concrete042A` has dark exterior formwork pits; `Concrete046` has greenish weathering stains; `Terrazzo004` has large high-contrast aggregate chips that compete with floor sightlines. |

- **Decision**: **`create`**
- **Reason**: No rights-cleared CC0 museum hall model or clean contemporary interior museum plaster/honed-concrete map set met the architectural, modularity, non-repetitive scale, and neutral-recolorability requirements. All geometry (`generate.py`) and coherent band-limited periodic PBR maps (`textures/*.png`) are authored originally from deterministic Python code with zero third-party content.

---

## 3. Coordinate System & Dimensions

Exported glTF 2.0 coordinate convention (`+Y` up, metric meters, no manual Three.js transform required):

- **`X` axis**: Hall width — `-12.00 m` (`Wall_Left` interior face) to `+12.00 m` (`Wall_Right` interior face) → **`24.00 m`** clear width (`24.80 m` outer structural width including `0.40 m` walls).
- **`Y` axis**: Vertical height — **`0.00 m`** interior finished floor surface, **`9.00 m`** primary ceiling soffit, **`10.35 m–10.368 m`** skylight laminated glass, **`10.52 m`** exterior skylight curb cap, **`-0.32 m`** structural slab soffit.
- **`Z` axis**: Hall depth — `-9.00 m` (`Wall_Back` main exhibition wall interior face) to `+9.00 m` (`Wall_Entrance` interior face) → **`18.00 m`** clear depth (`-9.40 m` rear outer face to `+10.20 m` exterior entrance portal face = `19.60 m` total depth).
- **Origin `(0, 0, 0)`**: Exact center of the interior finished floor at `Y = 0.00 m`.
- **Main Entrance Opening**: Centered on `+Z` wall (`Z = +9.00 m` to `+10.20 m`), **`5.60 m` wide × `4.60 m` high** (`X ∈ [-2.80, +2.80]`, `Y ∈ [0.00, 4.60]`).
- **Primary Skylight Opening**: Centered overhead, **`13.60 m` wide × `11.40 m` deep** (`X ∈ [-6.80, +6.80]`, `Z ∈ [-5.70, +5.70]`) at `Y = 9.00 m`, expanding gently to `13.76 m × 11.56 m` at `Y = 10.28 m`.
- **Blender-to-glTF Conversion**: Geometry is authored via the proper `+90°` X-axis rotation `(X_blender, Y_blender, Z_blender) = (X_gltf, -Z_gltf, Y_gltf)`, and Empty anchor transforms use `M_blender = R_G2B @ M_gltf @ R_B2G`, which Blender's `export_yup=True` glTF 2.0 exporter maps back to exact `(X_gltf, Y_gltf, Z_gltf)` world coordinates and local axes.

---

## 4. Semantic Node Hierarchy

```text
Museum_Open_Hall
├── Architecture
│   ├── Floor
│   ├── Wall_Left
│   ├── Wall_Right
│   ├── Wall_Back
│   ├── Wall_Entrance
│   ├── Entrance_Frame
│   ├── Ceiling
│   ├── Ceiling_Beams
│   └── Wall_Floor_Transitions
├── Skylight
│   ├── Skylight_Frame
│   ├── Skylight_Supports
│   └── Skylight_Glass
├── Lighting_Fixtures
│   ├── Track_Left
│   ├── Track_Right
│   ├── Track_Back
│   └── Recessed_Fixtures
├── Exhibition_Anchors
│   ├── Anchor_Artwork_Back_01 .. 03
│   ├── Anchor_Artwork_Left_01 .. 03
│   ├── Anchor_Artwork_Right_01 .. 03
│   ├── Anchor_Place_Central_Installation
│   ├── Anchor_Place_Pedestal_01 .. 02
│   ├── Anchor_Place_Bench_01 .. 02
│   ├── Anchor_Place_Info_Stand
│   ├── Anchor_Place_Invitation_Display
│   └── Anchor_Place_Partition_01 .. 02
├── Lighting_Anchors
│   ├── Anchor_Light_Back_01 .. 03
│   ├── Anchor_Light_Left_01 .. 03
│   ├── Anchor_Light_Right_01 .. 03
│   ├── Anchor_Light_Center_01 .. 02
│   └── Anchor_Light_Ambient_01 .. 04
└── Navigation_Anchors
    ├── Anchor_Navigation_Entrance
    ├── Anchor_Navigation_Center
    ├── Anchor_Navigation_Back
    ├── Anchor_Navigation_Left
    ├── Anchor_Navigation_Right
    └── Anchor_Navigation_Artwork_01 .. 09
```

---

## 5. Material Customization Contract

| Material Slot | Assigned Meshes | Default Tone (sRGB) | Roughness / Metallic | Maps & Customization Guidance |
| :--- | :--- | :---: | :---: | :--- |
| `Mat_Wall_Plaster` | `Wall_Back`, `Wall_Left`, `Wall_Right`, `Wall_Entrance` | `#F3EFE8` | `~0.87` / `0.00` | No baked base-color map; normal + roughness maps (`3.2 m` world UV scale). Set `material.color` freely to any gallery wall tint. To tint a single wall (e.g. a feature rear wall) without affecting other walls, clone `Wall_Back.material = Wall_Back.material.clone()` and dispose the clone on teardown without disposing shared normal/roughness textures. |
| `Mat_Floor_Concrete` | `Floor` | `#AEAAA1` | `~0.49` / `0.00` | Neutral near-white mineral cloud basecolor map multiplied by `baseColorFactor`, plus aligned normal + roughness maps (`3.0 m` UV scale). Supports tinting toward warm limestone, travertine, or charcoal concrete via `material.color`, or full map replacement. |
| `Mat_Ceiling` | `Ceiling` | `#ECE9E2` | `0.91` / `0.00` | Acoustic mineral normal map (`3.0 m` UV scale); matte warm-white base factor freely recolorable. |
| `Mat_Structural_Beam` | `Ceiling_Beams`, `Skylight_Supports` | `#EFECE5` | `0.64` / `0.06` | Architectural painted daylight-baffle finish; independently customizable from `Mat_Ceiling`. |
| `Mat_Skylight_Frame` | `Skylight_Frame` | `#D6D3CC` | `0.40` / `0.38` | Powder-coated warm-silver aluminum mullion finish. |
| `Mat_Skylight_Glass` | `Skylight_Glass` | `#EEF5F8` (`alpha 0.16`) | `0.07` / `0.04` | Exports with glTF `alphaMode: "BLEND"` (`opacity: 0.16`) so WebGL consumers get lightweight translucent skylight glass out of the box without transmission-buffer overhead. Set `Skylight_Glass.castShadow = false` at runtime so directional sun shadows pass cleanly through, upgrade optionally to `THREE.MeshPhysicalMaterial({ transmission: 0.92, ior: 1.52, thickness: 0.018 })`, or hide `Skylight_Glass.visible = false`. |
| `Mat_Entrance_Frame` | `Entrance_Frame` | `#383532` | `0.38` / `0.45` | Powder-coated dark bronze-charcoal architectural portal liner. |
| `Mat_Lighting_Fixture` | `Track_Left`, `Track_Right`, `Track_Back`, `Recessed_Fixtures` | `#282726` | `0.45` / `0.35` | Matte graphite spotlight & recessed track housing. |
| `Mat_Trim` | `Wall_Floor_Transitions` | `#222120` | `0.55` / `0.28` | Deep recessed base and ceiling shadow-gap channel liner. |

---

## 6. Exhibition Mounting, Placement, Lighting, & Navigation Anchors

### 6.1 Primary Wall-Mounted Artwork Anchors (`Exhibition_Anchors`)

Local coordinate convention on all 9 `Anchor_Artwork_*` nodes:
- **Local `XY` plane**: Artwork mounting plane (`+X` = viewer's right when facing the artwork, `+Y` = vertical world `+Y` up).
- **Local `+Z` axis**: Inward-facing surface normal pointing into the exhibition hall (`2 mm` proud of the finished plaster surface to prevent coplanar z-fighting).
- When loading custom artwork textures separately in Three.js onto a glTF plane, set `texture.colorSpace = THREE.SRGBColorSpace` (and `texture.flipY = false` only when reusing glTF-convention UV buffers; standard `THREE.PlaneGeometry` uses `flipY = true` default).

- **Floor clearance & tall-work vertical offset**: Centered mounting (`local Y = 0` at `Y = 1.550 m`) supports artworks up to **`2.60 m` tall** (`maxHeightMeters = 2.60`), maintaining at least **`0.250 m` floor clearance** (`0.185 m` above the `0.065 m` base shadow reveal). For monumental works taller than `2.60 m` (up to `maxShiftedHeightMeters = 5.60 m`), shift the artwork's local `+Y` by `Math.max(0, 0.25 + height * 0.5 - 1.55)` so its bottom edge remains at `Y = 0.250 m`.

| Anchor Name | Target Wall | glTF Position `(X, Y, Z)` (m) | Inward Normal `+Z` | Local Right `+X` | Max Centered `W × H` (m) | Rec. Clearance |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `Anchor_Artwork_Back_01` | `Wall_Back` | `(-6.400, 1.550, -8.998)` | `(0, 0, +1)` | `(+1, 0, 0)` | `4.80 × 2.60` | `0.80 m` |
| `Anchor_Artwork_Back_02` | `Wall_Back` | `( 0.000, 1.550, -8.998)` | `(0, 0, +1)` | `(+1, 0, 0)` | `5.20 × 2.60` | `0.80 m` |
| `Anchor_Artwork_Back_03` | `Wall_Back` | `(+6.400, 1.550, -8.998)` | `(0, 0, +1)` | `(+1, 0, 0)` | `4.80 × 2.60` | `0.80 m` |
| `Anchor_Artwork_Left_01` | `Wall_Left` | `(-11.998, 1.550, -5.200)` | `(+1, 0, 0)` | `(0, 0, -1)` | `3.80 × 2.60` | `0.70 m` |
| `Anchor_Artwork_Left_02` | `Wall_Left` | `(-11.998, 1.550,  0.000)` | `(+1, 0, 0)` | `(0, 0, -1)` | `4.00 × 2.60` | `0.70 m` |
| `Anchor_Artwork_Left_03` | `Wall_Left` | `(-11.998, 1.550, +5.200)` | `(+1, 0, 0)` | `(0, 0, -1)` | `3.80 × 2.60` | `0.70 m` |
| `Anchor_Artwork_Right_01` | `Wall_Right` | `(+11.998, 1.550, -5.200)` | `(-1, 0, 0)` | `(0, 0, +1)` | `3.80 × 2.60` | `0.70 m` |
| `Anchor_Artwork_Right_02` | `Wall_Right` | `(+11.998, 1.550,  0.000)` | `(-1, 0, 0)` | `(0, 0, +1)` | `4.00 × 2.60` | `0.70 m` |
| `Anchor_Artwork_Right_03` | `Wall_Right` | `(+11.998, 1.550, +5.200)` | `(-1, 0, 0)` | `(0, 0, +1)` | `3.80 × 2.60` | `0.70 m` |

### 6.2 Optional Floor Placement Anchors (`Exhibition_Anchors`)

All floor placement anchors rest on `Y = 0.000 m` with local `+Y` up and local `+Z` facing the primary presentation direction:
- `Anchor_Place_Central_Installation`: `(0.00, 0.00, -0.60)`, facing `+Z` `(0, 0, +1)` toward arriving visitors.
- `Anchor_Place_Pedestal_01` / `02`: `(-3.80, 0.00, -2.20)` and `(+3.80, 0.00, -2.20)`, facing `+Z`.
- `Anchor_Place_Bench_01` / `02`: `(-3.40, 0.00, +1.80)` and `(+3.40, 0.00, +1.80)`, facing `-Z` toward the main exhibition zone.
- `Anchor_Place_Info_Stand` / `Anchor_Place_Invitation_Display`: `(-3.60, 0.00, +6.80)` and `(+3.60, 0.00, +6.80)` flanking the entrance arrival zone.
- `Anchor_Place_Partition_01` / `02`: `(-4.80, 0.00, -0.60)` and `(+4.80, 0.00, -0.60)` for optional freestanding exhibition walls.

### 6.3 Lighting Anchors (`Lighting_Anchors`) & Runtime Lighting Guidance

Canonical `model.glb` intentionally omits baked directional shadows and embedded runtime lights (`export_lights=False`) so consumers control shadow budget and mood:
- `Anchor_Light_Back_01..03` (`(-6.40, 8.84, -6.50)`, `(0.00, 8.84, -6.50)`, `(+6.40, 8.84, -6.50)`), `Anchor_Light_Left_01..03` (`X = -8.80, Y = 8.84, Z = -5.20 / 0.00 / +5.20`), and `Anchor_Light_Right_01..03` (`X = +8.80, Y = 8.84, Z = -5.20 / 0.00 / +5.20`) sit at the track spotlight apertures with **local `-Z` aimed directly at the corresponding `Anchor_Artwork_*` center**.
- `Anchor_Light_Center_01..02` (`(±3.40, 8.95, 0.00)`) aim at the central installation zone `(0.00, 1.00, -0.60)`.
- `Anchor_Light_Ambient_01..04` mark perimeter ceiling downlight emission points (`(±7.60, 8.95, +7.60)` and `(±10.40, 8.95, -7.60)`).
- **Runtime Renderer Setup**:
  - *Soft Daylight*: Neutral environment IBL (`RoomEnvironment` or overcast HDRI, `environmentIntensity ~ 0.5–0.7`) + overhead `HemisphereLight(0xf6f8fc, 0xd8d2c8, 0.85)`.
  - *Direct Sunlight*: Add one shadow-casting `DirectionalLight(0xfff5e4, 2.2)` angled through the skylight (e.g. from `(6.8, 16.0, 4.4)` toward `(-2.2, 0.0, -2.5)`), with `Skylight_Glass.castShadow = false`.
  - *Evening Exhibition*: Lower environment/hemisphere intensity (`~0.15`) and attach selective `SpotLight` instances (`3000K` `#ffeed8`, `angle ~ 38°`, `penumbra ~ 0.45`, non-shadow-casting or max 1–2 shadow-casting hero lights on mobile) to active `Anchor_Light_*` transforms.

### 6.4 Navigation Anchors (`Navigation_Anchors`)

All 14 navigation anchors sit at human eye height **`Y = 1.600 m`** and follow standard Three.js / glTF camera orientation (**local `-Z` = forward look vector**, **local `+Y` = world up**), allowing direct `anchor.getWorldPosition(camera.position); anchor.getWorldQuaternion(camera.quaternion);`:
- `Anchor_Navigation_Entrance`: `(0.00, 1.60, +8.20)` → looks `-Z` across the full hall.
- `Anchor_Navigation_Center`: `(0.00, 1.60, +1.50)` → looks `-Z` toward `Wall_Back`.
- `Anchor_Navigation_Back`: `(0.00, 1.60, -4.20)` → wide view of `Wall_Back`.
- `Anchor_Navigation_Left`: `(-6.20, 1.60, 0.00)` → looks `-X` across `Wall_Left`.
- `Anchor_Navigation_Right`: `(+6.20, 1.60, 0.00)` → looks `+X` across `Wall_Right`.
- `Anchor_Navigation_Artwork_01..03`: `(-6.40 / 0.00 / +6.40, 1.60, -5.40..5.20)` (`3.60 m`–`3.80 m` viewing distance from `Anchor_Artwork_Back_01..03`).
- `Anchor_Navigation_Artwork_04..06`: `(-8.498, 1.60, -5.20 / 0.00 / +5.20)` (`3.50 m` viewing distance from `Anchor_Artwork_Left_01..03`).
- `Anchor_Navigation_Artwork_07..09`: `(+8.498, 1.60, -5.20 / 0.00 / +5.20)` (`3.50 m` viewing distance from `Anchor_Artwork_Right_01..03`).

---

## 7. Collision & Walkable-Space Contract

Rather than embedding opaque collider meshes that could accidentally render in basic glTF viewers, `Museum_Open_Hall` embeds explicit metric walkable bounds on `Museum_Open_Hall.userData.walkableBoundsMeters` (and documents wall AABBs in `manifest.json`) limited to human walking height (`Y ∈ [0.00, 2.60 m]`):
- **Primary Interior Walkable Zone (`0.35 m` player-radius buffer from `±12.0 m` / `±9.0 m` walls)**:
  `X ∈ [-11.65, +11.65]`, `Z ∈ [-8.65, +8.65]`, `Y = 0.00 m` floor.
- **Entrance Threshold Pass-Through Zone (`0.30 m` buffer inside `±2.80 m` portal jambs)**:
  `X ∈ [-2.50, +2.50]`, `Z ∈ [+8.65, +10.20]`, `Y = 0.00 m` floor.
- **Wall Blocking AABBs (`Y ∈ [0.00, 2.60 m]`)**:
  - `Wall_Back`: `[-12.40, +12.40] × [0.00, 2.60] × [-9.40, -9.00]`
  - `Wall_Left`: `[-12.40, -12.00] × [0.00, 2.60] × [-9.00, +9.00]`
  - `Wall_Right`: `[+12.00, +12.40] × [0.00, 2.60] × [-9.00, +9.00]`
  - `Wall_Entrance_Left`: `[-12.40, -2.80] × [0.00, 2.60] × [+9.00, +10.20]`
  - `Wall_Entrance_Right`: `[+2.80, +12.40] × [0.00, 2.60] × [+9.00, +10.20]`
- Consumers (such as **FrilCraft**) implement player movement clamping or physics AABBs from these bounds while allowing dynamically placed benches, pedestals, or partitions to register their own local colliders.

---

## 8. Texture Maps, Measured Performance, & File Packaging

### 8.1 Authoring & Embedded Runtime Texture Maps

| File | Resolution | Color Space | Repeat Scale | Size (Bytes) | Role |
| :--- | :---: | :---: | :---: | ---: | :--- |
| `textures/wall_plaster_normal.png` | `1024 × 1024` | Linear (`Non-Color`, OpenGL `+Y`) | `3.20 m` | `1,978,174` | Fine mineral gallery plaster micro-normal |
| `textures/wall_plaster_roughness.png` | `512 × 512` | Linear (`Non-Color`) | `3.20 m` | `133,726` | Coherent matte plaster roughness (`~0.82–0.92`) |
| `textures/floor_concrete_basecolor.png` | `512 × 512` | `sRGB` | `3.00 m` | `176,801` | Neutral near-white poured mineral clouding (multiplied by `baseColorFactor`) |
| `textures/floor_concrete_normal.png` | `1024 × 1024` | Linear (`Non-Color`, OpenGL `+Y`) | `3.00 m` | `1,148,758` | Honed concrete micro-normal and subtle pinholes |
| `textures/floor_concrete_roughness.png` | `512 × 512` | Linear (`Non-Color`) | `3.00 m` | `141,996` | Restrained satin honed concrete roughness (`~0.44–0.56`) |
| `textures/ceiling_plaster_normal.png` | `512 × 512` | Linear (`Non-Color`, OpenGL `+Y`) | `3.00 m / 2.00 m` | `504,822` | Acoustic mineral ceiling & louver micro-normal |

### 8.2 Measured Geometry & Runtime Performance

- **Total glTF nodes**: `70` (`16` single-primitive meshes, `9` semantic materials, `54` hierarchy & semantic anchor nodes)
- **Triangles / Vertices**: `6,036` triangles / `10,786` vertices (`0` degenerate faces)
- **Canonical `model.glb` size**: `4,682,292` bytes (`4.47 MiB`), SHA-256 `517029ce989a2c41c28c78112b4bbc6b2f76d9cf37c18e18f9577f656f01063a`
- **Estimated GPU texture memory (RGBA8 + mipchain)**: `16,777,214` bytes (`16.00 MiB`, reduced `-42.9%` from pre-optimization `28.00 MiB`)
- **Three.js `GLTFLoader` load time**: `35.1–72.3 ms` (local HTTP loopback in headless Chromium WebGL)
- **Draw calls (`1600×1000` with `2048²` PCFSoftShadowMap)**: `33` (`16` museum meshes + `1` exterior ground plane across shadow + main pass; `16` draw calls for the museum itself when shadows are disabled)
- **Steady-state WebGL frame time (`90`-frame benchmark after warmup, `gl.finish()`)**: `0.102–0.120 ms` average, `0.200 ms` p95 (measured on Apple Silicon Metal/ANGLE headless Chromium; physical mobile hardware was not tested)
- **Clean-checkout reproducibility**: Verified bit-for-bit identical `model.glb` SHA-256 (`517029ce989a2c41c28c78112b4bbc6b2f76d9cf37c18e18f9577f656f01063a`) regenerated from an isolated `/tmp` directory containing no `.work/` files, and verified relative `//textures/` paths in `model.blend`.

### 8.3 Consumer Distribution vs. Authoring Dependencies & Known Limitations

- **Consumer runtime distribution payload**: `model.glb` (`4,682,292` bytes — 100% self-contained with embedded textures, materials, and semantic anchors). Optional catalog files: `preview.webp` (`36,148` bytes) and `manifest.json`.
- **Authoring & validation dependencies (not bundled into runtime apps)**: Blender `5.2.2 LTS` (`bpy`, `bmesh`, bundled `numpy`) for `generate.py` and `validate_blender.py`; Node.js `>= 20` with `three` and `playwright` (`NODE_PATH`) for `validate_threejs.mjs`; optional `cwebp` for regenerating `preview.webp`.
- **Known limitations**:
  1. `model.glb` provides architectural geometry, PBR materials, semantic mounting/lighting/navigation anchors, and embedded walkable-bound metadata; camera controllers, player collision clamping, dynamic lighting rigs, and interactive exhibition UI must be supplied by the consuming application (e.g., **FrilCraft** / **FrilStudio**).
  2. `Mat_Skylight_Glass` uses standard glTF `BLEND` transparency (`opacity = 0.16`) for broad WebGL compatibility without multi-pass transmission overhead; set `Skylight_Glass.castShadow = false` in Three.js so directional sunlight passes unobstructed through the skylight.
  3. Physical mobile device GPU frame times were not measured; mobile validation covered portrait `9:16` (`540×960`) aspect-ratio rendering and GPU texture memory budgeting (`16.0 MiB`).
