# Open Skylight Museum Hall (`architecture/museum-open-hall`)

## 1. Overview & Architectural Concept

**Open Skylight Museum Hall** (`v0.2.0`) is a contemporary, real-world-scale museum exhibition hall designed for photography galleries, fine-art exhibitions, sculptural installations, digital showrooms, and interactive WebGL experiences across **FrilCraft**, **FrilStudio**, and **FrilRemotion**.

Key architectural features:
- **Monumental clear exhibition volume**: `24.00 m` wide × `18.00 m` deep × `9.00 m` ceiling height (`432.0 m²` column-free exhibition floor).
- **Floating architectural ceiling canopy & perimeter side daylight coves**: The `9.00 m` acoustic mineral ceiling canopy spans cleanly from `Wall_Back` (`Z = -9.00 m`) to `Wall_Entrance` (`Z = +9.00 m`) while stopping `680 mm` short of `Wall_Left` and `Wall_Right` (`X = ±11.32 m`), forming two full-length `760 mm`-tall perimeter architectural coves (`Y = 9.00 m` to `9.76 m`, sealed light-tight above by the `9.76–10.68 m` structural roof slab) that wash the side exhibition walls in soft vertical daylight or warm evening grazing light.
- **Integrated 5-bay canted skylight coffer**: `13.60 m × 11.80 m` ceiling aperture rising through a solid-manifold `4.8°` canted plaster daylight well (`Y = 9.00 m` to `10.68 m`, `13.88 m × 12.08 m` at top), articulated by four slender tapered transverse skylight blades (`Ceiling_Beams`, recessed mid-well at `Y = 9.82–10.60 m`), perimeter bearing channels & `18 mm` low-profile structural glass splines (`Skylight_Supports`), a powder-coated pale aluminum curb & transom system (`Skylight_Frame`), and fifteen independently toggleable low-iron laminated glazing panes (`Skylight_Glass`).
- **Tectonic architectural detailing**: `400 mm` structural exterior walls, a `1.60 m`-deep stepped monumental entrance portal (`5.60 m × 4.80 m` clear opening) lined with a `55 mm` anodized warm pewter-bronze reveal band (`Entrance_Frame`), subtle `24 mm × 24 mm` recessed wall-to-floor shadow-gap channels (`Wall_Floor_Transitions`), power-troweled honed architectural concrete slabs with `2.8 mm` micro-beveled saw-cut control joints aligned with the entrance portal jambs (`±2.80 m`) and a flush `260 mm × 260 mm` gallery floor service hatch inlay (`Floor`), and a recessed U-shaped lighting track slot centered on the floating soffit wings (`X = ±9.06 m`, `Z = -7.35 m`) housing fifteen compact semi-recessed spotlights and ten trimless pinhole downlights (`Lighting_Fixtures`).

---

## 2. Sourcing Gate Record (`docs/asset-sourcing.md`)

- **Asset ID**: `architecture/museum-open-hall`
- **Search dates**: `2026-11-27` and `2026-11-28`
- **Local packages checked**: `assets/wedding/wedding-envelope`, `assets/stationery/fril-signature-seal`, `assets/objects/editorial-magazine`, `materials/*`, `textures/*`, `environments/*`, plus read-only checks of sibling workspaces (`frilcarft`, `fril-studio`, `friladd`). No reusable architectural hall, skylight, track fixture, mineral plaster, or honed concrete package existed locally.

| Query / Source | Candidate URL | Creator | License Evidence URL | Suitability / Blockers |
| :--- | :--- | :--- | :--- | :--- |
| Sketchfab (`museum+skylight+gallery`, `art+gallery`, CC0 downloadable) | `https://sketchfab.com/3d-models/none-79805169b85e47d9a60be25035e387f2` (*Arts of Southeast Asia gallery*) | Minneapolis Institute of Art (`artsmia`) | `https://creativecommons.org/publicdomain/zero/1.0/` | `museum+skylight+gallery` (CC0 downloadable) returned `0` results; `art+gallery` returned photogrammetry scan (`99,610` faces) with permanently baked display cases and baked lighting; lacks modular walls, skylight, and semantic anchors. |
| Sketchfab (`museum+hall`, CC0 downloadable) | `https://sketchfab.com/3d-models/none-97673d5721d743328022c282b77b33ae` (*Wan fa Gui yi Hall*) | Världskulturmuseerna | `https://creativecommons.org/publicdomain/zero/1.0/` | Rejected: `2.83M`-face museum artifact scan of a historic temple model rather than an interior exhibition hall. |
| Poly Haven (`models`: `skylight`, `track+light`, CC0) | `https://polyhaven.com/models` | Poly Haven contributors | `https://polyhaven.com/license` | `0` CC0 gallery track-light systems or skylight hall models available. |
| Poly Haven (`white_plaster_02`, `beige_wall_001`) | `https://polyhaven.com/a/white_plaster_02`, `https://polyhaven.com/a/beige_wall_001` | Rob Tuytel / Poly Haven | `https://polyhaven.com/license` | Rejected after visual inspection: `white_plaster_02` is coarse exterior sand stucco; `beige_wall_001` has dark pinhole specks and baked muddy tan hue (`~#9A9288`) that violates neutral near-white runtime recoloring across `24 m × 9 m` walls. |
| Poly Haven (`smooth_concrete_floor`, `concrete_floor_02`) | `https://polyhaven.com/a/smooth_concrete_floor`, `https://polyhaven.com/a/concrete_floor_02` | Dimitrios Savva / Rob Tuytel | `https://polyhaven.com/license` | Rejected after visual inspection: `smooth_concrete_floor` has reddish-brown industrial staining and cracks; `concrete_floor_02` is rough, heavily pitted outdoor parking-lot concrete. |
| ambientCG (`Plaster001`, `PaintedPlaster017`, `Concrete042A`, `Terrazzo004`) | `https://ambientcg.com/a/Plaster001`, `https://ambientcg.com/a/Concrete042A`, `https://ambientcg.com/a/Terrazzo004` | Lennart Demes (ambientCG) | `https://docs.ambientcg.com/license/` | Rejected after visual inspection: directional trowel gouges, repetitive central crack, dark exterior formwork pits, or high-contrast terrazzo chips that compete with exhibition sightlines. |

- **Decision**: **`create`**
- **Reason**: No rights-cleared CC0 museum hall model or clean contemporary interior museum plaster/honed-concrete map set met the architectural, modularity, non-repetitive world scale (`4.8 m` repeat), satin Fresnel reflection, and neutral-recolorability requirements. All geometry (`generate.py`) and coherent band-limited periodic PBR maps (`textures/*.png`) are authored originally from deterministic Python code with zero third-party content.

---

## 3. Coordinate System & Dimensions

Exported glTF 2.0 coordinate convention (`+Y` up, metric meters, no manual Three.js transform required):

- **`X` axis**: Hall width — `-12.00 m` (`Wall_Left` interior face) to `+12.00 m` (`Wall_Right` interior face) → **`24.00 m`** clear width (`24.80 m` outer structural width including `0.40 m` walls).
- **`Y` axis**: Vertical height — **`0.00 m`** interior finished floor surface, **`9.00 m`** primary floating ceiling canopy soffit, **`9.76 m`** top of `680 mm` side daylight coves, **`10.68 m–10.70 m`** skylight laminated glass, **`10.90 m`** exterior skylight curb cap, **`-0.32 m`** structural slab soffit.
- **`Z` axis**: Hall depth — `-9.00 m` (`Wall_Back` main exhibition wall interior face) to `+9.00 m` (`Wall_Entrance` interior face) → **`18.00 m`** clear depth (`-9.40 m` rear outer face to `+10.60 m` exterior entrance portal face = `20.00 m` total depth).
- **Origin `(0, 0, 0)`**: Exact center of the interior finished floor at `Y = 0.00 m`.
- **Main Entrance Opening**: Centered on `+Z` wall (`Z = +9.00 m` to `+10.60 m`), **`5.60 m` wide × `4.80 m` high** (`X ∈ [-2.80, +2.80]`, `Y ∈ [0.00, 4.80]`).
- **Primary Skylight Opening**: Centered overhead, **`13.60 m` wide × `11.80 m` deep** (`X ∈ [-6.80, +6.80]`, `Z ∈ [-5.90, +5.90]`) at `Y = 9.00 m`, expanding smoothly to `13.88 m × 12.08 m` at `Y = 10.68 m`.
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
| `Mat_Wall_Plaster` | `Wall_Back`, `Wall_Left`, `Wall_Right`, `Wall_Entrance` | `#F3EFE7` | `~0.86` / `0.00` | Neutral near-white mineral clouding basecolor (`0.98–1.00`) + aligned normal & roughness maps (`4.8 m` world UV scale). Set `material.color` freely to any light or dark gallery tint. To customize a single wall independently, clone `Wall_Back.material = Wall_Back.material.clone()` and dispose the clone on teardown without disposing shared textures. |
| `Mat_Floor_Concrete` | `Floor` | `#B4B0A8` | `~0.30` (`0.25–0.38`) / `0.00` | Neutral near-white mineral clouding basecolor map multiplied by `baseColorFactor`, plus aligned `1024²` power-troweled satin roughness & micro-normal maps (`4.8 m` UV scale, `IOR 1.52`) producing soft, realistic Fresnel reflections of skylight and artworks without mirror glare. |
| `Mat_Ceiling` | `Ceiling` | `#E9E4DA` | `0.88` / `0.00` | Neutral near-white mineral basecolor + acoustic mineral normal map (`4.2 m` UV scale); warm mineral soffit tone freely recolorable. |
| `Mat_Structural_Beam` | `Ceiling_Beams`, `Skylight_Supports` | `#F5F2EB` | `0.56` / `0.08` | Crisp warm-white painted architectural skylight blade finish; independently customizable from `Mat_Ceiling`. |
| `Mat_Skylight_Frame` | `Skylight_Frame` | `#DCD8D0` | `0.38` / `0.36` | Powder-coated pale warm aluminum curb & transom finish. |
| `Mat_Skylight_Glass` | `Skylight_Glass` | `#EEF5FA` (`alpha 0.14`) | `0.07` / `0.04` | Exports with glTF `alphaMode: "BLEND"` (`opacity: 0.14`) for broad real-time WebGL compatibility without transmission-pass overhead. Set `Skylight_Glass.castShadow = false` at runtime so directional sun shadows pass cleanly through, upgrade optionally to `THREE.MeshPhysicalMaterial({ transmission: 0.92, ior: 1.52, thickness: 0.02 })`, or hide `Skylight_Glass.visible = false`. |
| `Mat_Entrance_Frame` | `Entrance_Frame` | `#524E49` | `0.38` / `0.42` | Anodized warm pewter-bronze architectural portal reveal liner. |
| `Mat_Lighting_Fixture` | `Track_Left`, `Track_Right`, `Track_Back`, `Recessed_Fixtures` | `#302E2C` | `0.42` / `0.38` | Matte dark graphite semi-recessed spotlight & track channel housing. |
| `Mat_Trim` | `Wall_Floor_Transitions` | `#3C3935` | `0.52` / `0.25` | Subtle `24 mm` recessed base and ceiling shadow-gap channel liner. |

---

## 6. Exhibition Mounting, Placement, Lighting, & Navigation Anchors

### 6.1 Primary Wall-Mounted Artwork Anchors (`Exhibition_Anchors`)

Local coordinate convention on all 9 `Anchor_Artwork_*` nodes:
- **Local `XY` plane**: Artwork mounting plane (`+X` = viewer's right when facing the artwork, `+Y` = vertical world `+Y` up).
- **Local `+Z` axis**: Inward-facing surface normal pointing into the exhibition hall (`2 mm` proud of the finished plaster surface to prevent coplanar z-fighting).
- **Floor clearance & tall-work vertical offset**: Centered mounting (`local Y = 0` at `Y = 1.550 m`) supports artworks up to **`2.60 m` tall** (`maxHeightMeters = 2.60`), maintaining at least **`0.250 m` floor clearance** (`0.226 m` above the `0.024 m` base shadow reveal). For monumental works taller than `2.60 m` (up to `maxShiftedHeightMeters = 5.60 m`), shift the artwork's local `+Y` by `Math.max(0, 0.25 + height * 0.5 - 1.55)` so its bottom edge remains at `Y = 0.250 m`.

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
- `Anchor_Light_Back_01..03` (`(-6.40 / 0.00 / +6.40, 8.92, -7.35)`), `Anchor_Light_Left_01..03` (`(-9.06, 8.92, -5.20 / 0.00 / +5.20)`), and `Anchor_Light_Right_01..03` (`(+9.06, 8.92, -5.20 / 0.00 / +5.20)`) sit at the semi-recessed track spotlight apertures with **local `-Z` aimed directly at the corresponding `Anchor_Artwork_*` center**.
- `Anchor_Light_Center_01..02` (`(±3.40, 8.95, 0.00)`) aim at the central installation zone `(0.00, 1.00, -0.60)`.
- `Anchor_Light_Ambient_01..04` mark perimeter ceiling downlight emission points (`(±7.40, 8.95, +7.80)` and `(±10.20, 8.95, -7.80)`).
- **Blender Authoring vs. Runtime Renderer**:
  - *Blender Cycles Authoring*: Uses `Studio_Preview` collection area lights (`Studio_Skylight_Soft_Dome`, `17.4 m` linear `Studio_Cove_Left` / `Studio_Cove_Right` side-cove grazers, `Studio_Direct_Sun`, and `3000K` `Studio_Spot_*` lamps) plus `Studio_Foyer_*` arrival vestibule backdrop; all `Studio_*` and `Demo_*` objects are excluded from `model.glb`.
  - *Three.js / WebGL Runtime*: Pair neutral environment IBL (`RoomEnvironment` or overcast HDRI, `environmentIntensity ~ 0.5–0.7`) + `HemisphereLight(0xf6f8fc, 0xd8d2c8, 0.85)` for Soft Daylight; add one `DirectionalLight(0xfff5e4, 2.25)` through the skylight (`Skylight_Glass.castShadow = false`) for Direct Sunlight; or lower ambient intensity (`~0.15`) and attach selective `SpotLight` instances (`3000K` `#ffedd6`, `angle ~ 38°`, `penumbra ~ 0.48`) to `Anchor_Light_*` transforms for Evening Exhibition.

### 6.4 Navigation Anchors (`Navigation_Anchors`)

All 14 navigation anchors sit at human eye height **`Y = 1.600 m`** (`local -Z` = forward look vector, `local +Y` = world up):
- `Anchor_Navigation_Entrance`: `(0.00, 1.60, +8.20)` → looks `-Z` across the full hall.
- `Anchor_Navigation_Center`: `(0.00, 1.60, +1.50)` → looks `-Z` toward `Wall_Back`.
- `Anchor_Navigation_Back`: `(0.00, 1.60, -4.20)` → wide view of `Wall_Back`.
- `Anchor_Navigation_Left`: `(-6.20, 1.60, 0.00)` → looks `-X` across `Wall_Left`.
- `Anchor_Navigation_Right`: `(+6.20, 1.60, 0.00)` → looks `+X` across `Wall_Right`.
- `Anchor_Navigation_Artwork_01..03`: `(-6.40 / 0.00 / +6.40, 1.60, -5.398 / -5.198)` (`3.60 m`–`3.80 m` viewing distance from `Anchor_Artwork_Back_01..03`).
- `Anchor_Navigation_Artwork_04..06`: `(-8.498, 1.60, -5.20 / 0.00 / +5.20)` (`3.50 m` viewing distance from `Anchor_Artwork_Left_01..03`).
- `Anchor_Navigation_Artwork_07..09`: `(+8.498, 1.60, -5.20 / 0.00 / +5.20)` (`3.50 m` viewing distance from `Anchor_Artwork_Right_01..03`).

---

## 7. Collision & Walkable-Space Contract

`Museum_Open_Hall` embeds explicit metric walkable bounds on `Museum_Open_Hall.userData.walkableBoundsMeters` (and documents wall AABBs in `manifest.json`) limited to human walking height (`Y ∈ [0.00, 2.60 m]`):
- **Primary Interior Walkable Zone (`0.35 m` player-radius buffer from `±12.0 m` / `±9.0 m` walls)**:
  `X ∈ [-11.65, +11.65]`, `Z ∈ [-8.65, +8.65]`, `Y = 0.00 m` floor.
- **Entrance Portal Pass-Through Zone (`0.30 m` buffer inside `±2.80 m` portal jambs)**:
  `X ∈ [-2.50, +2.50]`, `Z ∈ [+8.65, +10.60]`, `Y = 0.00 m` floor.
- **Wall Blocking AABBs (`Y ∈ [0.00, 2.60 m]`)**:
  - `Wall_Back`: `[-12.40, +12.40] × [0.00, 2.60] × [-9.40, -9.00]`
  - `Wall_Left`: `[-12.40, -12.00] × [0.00, 2.60] × [-9.00, +9.00]`
  - `Wall_Right`: `[+12.00, +12.40] × [0.00, 2.60] × [-9.00, +9.00]`
  - `Wall_Entrance_Left`: `[-12.40, -2.80] × [0.00, 2.60] × [+9.00, +10.60]`
  - `Wall_Entrance_Right`: `[+2.80, +12.40] × [0.00, 2.60] × [+9.00, +10.60]`

---

## 8. Texture Maps, Measured Performance, & File Packaging

### 8.1 Authoring & Embedded Runtime Texture Maps

| File | Resolution | Color Space | Repeat Scale | Size (Bytes) | Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `textures/wall_plaster_basecolor.png` | `512 × 512` | `sRGB` | `4.80 m` | `125,838` | Neutral near-white mineral clouding (`0.98–1.00`, multiplied by `baseColorFactor`) |
| `textures/wall_plaster_normal.png` | `1024 × 1024` | Linear (`Non-Color`, OpenGL `+Y`) | `4.80 m` | `1,450,661` | Fine lime-mineral gallery plaster micro-normal |
| `textures/wall_plaster_roughness.png` | `512 × 512` | Linear (`Non-Color`) | `4.80 m` | `127,023` | Coherent matte plaster roughness (`~0.82–0.90`) |
| `textures/floor_concrete_basecolor.png` | `512 × 512` | `sRGB` | `4.80 m` | `198,960` | Neutral near-white poured concrete clouding (multiplied by `baseColorFactor`) |
| `textures/floor_concrete_normal.png` | `1024 × 1024` | Linear (`Non-Color`, OpenGL `+Y`) | `4.80 m` | `875,829` | Honed concrete micro-normal & subtle mineral pores |
| `textures/floor_concrete_roughness.png` | `1024 × 1024` | Linear (`Non-Color`) | `4.80 m` | `560,126` | Power-troweled satin concrete roughness (`0.25–0.38`) |
| `textures/ceiling_plaster_normal.png` | `512 × 512` | Linear (`Non-Color`, OpenGL `+Y`) | `4.20 m / 2.50 m` | `491,844` | Acoustic mineral ceiling & skylight blade micro-normal |

### 8.2 Measured Geometry, Runtime Performance, & Optimization Analysis

- **Total glTF nodes**: `70` (`16` single-primitive meshes, `9` semantic materials, `54` hierarchy & semantic anchor nodes)
- **Triangles / Vertices**: `5,740` triangles / `10,218` vertices (`0` degenerate faces; `-4.9%` leaner than `v0.1.0` while adding side daylight coves, solid-manifold 5-bay skylight well, stepped portal reveal, and floor hatch inlay)
- **Canonical `model.glb` size**: `4,560,896` bytes (`4.35 MiB`), SHA-256 `c233695276b3021fbe094813516931bc9513fa3ee8d1d519fd4b31da4b1cdad9`
- **Estimated GPU texture memory (`7` embedded textures, RGBA8 + mipchain)**: `22,369,619` bytes (`21.33 MiB` — uses `512×512` for low-frequency clouding maps while retaining `1024×1024` on close-up normal and power-troweled concrete roughness maps to preserve crisp satin reflection modulation)
- **Three.js `GLTFLoader` load time**: `38.9 ms` (local HTTP loopback in headless Chromium WebGL)
- **Draw calls (`1600×1000` with `2048²` PCFSoftShadowMap)**: `33` (`16` museum meshes + `1` exterior ground plane across shadow + main pass; `16` draw calls for the museum itself when shadows are disabled — Static structural elements within each semantic role are already combined into single-primitive meshes while preserving independent wall/ceiling/glazing/fixture customization)
- **Steady-state WebGL frame time (`90`-frame benchmark after warmup, `gl.finish()`)**: `0.130 ms` average, `0.200 ms` p95 (measured on Apple Silicon Metal/ANGLE headless Chromium; physical mobile device hardware was not tested)
- **Clean-checkout reproducibility**: Verified bit-for-bit identical `model.glb` SHA-256 (`c233695276b3021fbe094813516931bc9513fa3ee8d1d519fd4b31da4b1cdad9`) regenerated from an isolated `/tmp` clean copy containing only tracked package files (no `.work/`), and verified relative `//textures/` paths in `model.blend`.

### 8.3 Tracked Package Files vs. Consumer Distribution & Known Limitations

- **Tracked authoring & catalog files (`15` files, `8,772,140` bytes total)**:
  - `model.glb` (`4,560,896` bytes — **sole required consumer runtime file**, 100% self-contained)
  - `preview.webp` (`23,998` bytes — optional catalog preview)
  - `manifest.json` (`7,139` bytes — optional catalog metadata)
  - `model.blend` (`188,071` bytes — editable Blender 5.2 source)
  - `generate.py` (`99,348` bytes — deterministic Blender Python generator)
  - `textures/*.png` (`7` files, `3,830,281` bytes total — authoritative lossless PBR maps)
  - `validate_blender.py` (`9,560` bytes), `validate_threejs.mjs` (`26,995` bytes), `notes.md` (`~25.8 KB`)
- **Required authoring/validation dependencies**: Blender `5.2.2 LTS` (`bpy`, `bmesh`, bundled `numpy`); Node.js `>= 20` with `three` and `playwright` (`NODE_PATH`) for `validate_threejs.mjs`; optional `cwebp` for regenerating `preview.webp`.
- **Known limitations**:
  1. `model.glb` provides architectural geometry, PBR materials, semantic mounting/lighting/navigation anchors, and embedded walkable-bound metadata; camera navigation controllers, player collision clamping, runtime light management, and interactive exhibition UI must be supplied by the consumer (**FrilCraft** / **FrilStudio**).
  2. `Mat_Skylight_Glass` uses standard glTF `BLEND` transparency (`opacity = 0.14`) for lightweight real-time WebGL compatibility; set `Skylight_Glass.castShadow = false` in Three.js so directional sunlight casts unobstructed coffer shadows.
  3. Physical mobile device GPU frame times were not measured; mobile checks covered `9:16` (`540×960`) portrait viewport rendering and GPU texture memory budgeting (`21.33 MiB`).
