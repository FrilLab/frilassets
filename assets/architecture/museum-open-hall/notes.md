# Open Skylight Museum Hall (`architecture/museum-open-hall`)

## 1. Overview & V2 Architectural Concept

**Open Skylight Museum Hall** (`v0.3.0` — Architectural Refinement & Visual Quality Pass) is a contemporary, real-world-scale museum exhibition hall designed for photography galleries, fine-art exhibitions, sculptural installations, digital showrooms, and interactive WebGL experiences across **FrilCraft**, **FrilStudio**, and **FrilRemotion**.

Key architectural features:
- **Monumental clear exhibition volume**: `24.00 m` wide × `18.00 m` deep × `9.00 m` ceiling height (`432.0 m²` column-free main exhibition floor), preserving every foundation coordinate, semantic mesh slot, material slot, and anchor contract.
- **Reconstructed `17.1°` pitched conservatory lantern skylight**: Replaces flat horizontal glass with a `15.20 m × 13.60 m` ceiling aperture rising through a two-tier recessed architectural cornice (`Y = 9.00 m → 9.34 m → 10.48 m`) into a `17.1°` pitched laminated glass roof (`Y = 10.56 m` eaves rising `2.42 m` to a `Y = 12.98 m` central structural ridge / `13.03 m` ridge cap). Articulated by five slender white-painted steel king-post collar trusses (`Ceiling_Beams`), seven pitched rafter pairs + longitudinal purlins + central ridge beam (`Skylight_Supports`), twenty-one conservatory glazing mullion bays + glazed triangular gable tympanums (`Skylight_Frame`), and sloped low-iron laminated glass (`Skylight_Glass`).
- **Multi-room spatial continuity (zero empty sky voids)**:
  - **`Entrance_Vestibule` (`Z = +10.40 m .. +15.40 m`)**: `14.40 m × 5.00 m × 6.60 m` architectural arrival gallery with baffled sightline wall and recessed overhead daylight clerestory beyond the `5.60 m × 4.80 m` entrance portal.
  - **`Secondary_Gallery` (`Z = -9.90 m .. -15.70 m`) & `Wall_Back_Portal_Closure`**: Central `4.40 m × 4.40 m` dark-bronze-lined enfilade portal in `Wall_Back` connecting to a `10.80 m × 5.80 m × 6.80 m` secondary exhibition room with its own overhead daylight skylight slot and axial `Anchor_Artwork_Secondary_01`. A sliding pocket partition (`Wall_Back_Portal_Closure`) rests open inside `Wall_Back` (`x = -4.62 m`, `z = -0.38 m`) by default for deep enfilade sightlines, and slides to `(0, 0, 0)` to form a flush `24.00 m` rear wall supporting the full 9-artwork layout (`Anchor_Artwork_Back_02`).
- **Tectonic architectural detailing & dual-UV neutral AO**: Welded T-junction-free plaster topology above portals, disjoint `18–22 mm` inset bronze portal sleeves (`Entrance_Frame`) and `32 mm × 28 mm` recessed shadow-gap channels (`Wall_Floor_Transitions`) that eliminate WebGL z-fighting, `640 mm`-wide perimeter side daylight coves (`Y = 9.00–9.72 m`), grounded medium-gray power-troweled concrete (`#8E8B85`, `6.40 m` UV repeat), and a path-traced neutral Cycles Ambient Occlusion / Sky-Access atlas (`textures/museum_ao.png`) on `UVMap_AO` (`TEXCOORD_1`) that gives real-time WebGL viewers soft architectural contact and ceiling-recess shading without baking directional light into replaceable `TEXCOORD_0` PBR maps.
- **Independently adjustable spotlight heads**: Static recessed tracks (`Track_Left`, `Track_Right`, `Track_Back`) are separated from 15 child spotlight head nodes (`Fixture_Head_Back_01..05`, `Fixture_Head_Left_01..05`, `Fixture_Head_Right_01..05`) pivoted at their yoke hinges (`Y = 8.92 m`) with local `-Z` optical axes.

---

## 2. Sourcing Gate Record (`docs/asset-sourcing.md`)

- **Asset ID**: `architecture/museum-open-hall`
- **Search dates**: `2026-11-27` and `2026-11-28`
- **Local packages checked**: `assets/wedding/wedding-envelope`, `assets/stationery/fril-signature-seal`, `assets/objects/editorial-magazine`, `materials/*`, `textures/*`, `environments/*`, plus read-only checks of sibling workspaces (`frilcarft`, `fril-studio`, `friladd`). No reusable architectural hall, pitched skylight, track fixture, mineral plaster, or honed concrete package existed locally.

| Query / Source | Candidate URL | Creator | License Evidence URL | Suitability / Blockers |
| :--- | :--- | :--- | :--- | :--- |
| Sketchfab (`museum+skylight+gallery`, `art+gallery`, CC0 downloadable) | `https://sketchfab.com/3d-models/none-79805169b85e47d9a60be25035e387f2` (*Arts of Southeast Asia gallery*) | Minneapolis Institute of Art (`artsmia`) | `https://creativecommons.org/publicdomain/zero/1.0/` | `museum+skylight+gallery` (CC0 downloadable) returned `0` results; `art+gallery` returned photogrammetry scan (`99,610` faces) with permanently baked display cases and baked lighting; lacks modular walls, skylight, and semantic anchors. |
| Sketchfab (`museum+hall`, CC0 downloadable) | `https://sketchfab.com/3d-models/none-97673d5721d743328022c282b77b33ae` (*Wan fa Gui yi Hall*) | Världskulturmuseerna | `https://creativecommons.org/publicdomain/zero/1.0/` | Rejected: `2.83M`-face museum artifact scan of a historic temple model rather than an interior exhibition hall. |
| Poly Haven (`models`: `skylight`, `track+light`, CC0) | `https://polyhaven.com/models` | Poly Haven contributors | `https://polyhaven.com/license` | `0` CC0 gallery track-light systems or skylight hall models available. |
| Poly Haven (`white_plaster_02`, `beige_wall_001`) | `https://polyhaven.com/a/white_plaster_02`, `https://polyhaven.com/a/beige_wall_001` | Rob Tuytel / Poly Haven | `https://polyhaven.com/license` | Rejected after visual inspection: `white_plaster_02` is coarse exterior sand stucco; `beige_wall_001` has dark pinhole specks and baked muddy tan hue (`~#9A9288`) that violates neutral near-white runtime recoloring across `24 m × 9 m` walls. |
| Poly Haven (`smooth_concrete_floor`, `concrete_floor_02`) | `https://polyhaven.com/a/smooth_concrete_floor`, `https://polyhaven.com/a/concrete_floor_02` | Dimitrios Savva / Rob Tuytel | `https://polyhaven.com/license` | Rejected after visual inspection: `smooth_concrete_floor` has reddish-brown industrial staining and cracks; `concrete_floor_02` is rough, heavily pitted outdoor parking-lot concrete. |
| ambientCG (`Plaster001`, `PaintedPlaster017`, `Concrete042A`, `Terrazzo004`) | `https://ambientcg.com/a/Plaster001`, `https://ambientcg.com/a/Concrete042A`, `https://ambientcg.com/a/Terrazzo004` | Lennart Demes (ambientCG) | `https://docs.ambientcg.com/license/` | Rejected after visual inspection: directional trowel gouges, repetitive central crack, dark exterior formwork pits, or high-contrast terrazzo chips that compete with exhibition sightlines. |

- **Decision**: **`create`**
- **Reason**: No rights-cleared CC0 museum hall model or clean contemporary interior museum plaster/honed-concrete map set met the architectural proportions, pitched conservatory skylight design, non-repetitive world scale (`6.0–6.4 m` repeat), satin Fresnel reflection, and neutral-recolorability requirements. All geometry (`generate.py`), coherent band-limited periodic PBR maps, and neutral Cycles AO (`textures/*.png`) are authored originally from deterministic Python code with zero third-party content.

---

## 3. Coordinate System & Dimensions

Exported glTF 2.0 coordinate convention (`+Y` up, metric meters, no manual Three.js transform required):

- **`X` axis**: Main hall width — `-12.00 m` (`Wall_Left` interior face) to `+12.00 m` (`Wall_Right` interior face) → **`24.00 m`** clear width (`24.80 m` outer structural width including `0.40 m` walls).
- **`Y` axis**: Vertical height — **`0.00 m`** continuous interior finished floor across main hall, secondary gallery, and vestibule; **`9.00 m`** primary floating ceiling canopy soffit; **`9.72 m`** top of `640 mm` side daylight coves; **`10.56 m`** skylight glazing eaves rising at **`17.1°`** to **`12.98 m`** central structural ridge (`13.03 m` ridge cap); **`-0.32 m`** structural slab soffit.
- **`Z` axis**: Depth — `-9.00 m` (`Wall_Back` main exhibition wall interior face) to `+9.00 m` (`Wall_Entrance` interior face) → **`18.00 m`** main hall clear depth; `-9.90 m` to `-15.70 m` (`Secondary_Gallery`, `5.80 m` clear depth); `+10.40 m` to `+15.40 m` (`Entrance_Vestibule`, `5.00 m` clear depth); `-16.10 m` to `+15.80 m` (`31.90 m` total structural exterior depth).
- **Origin `(0, 0, 0)`**: Exact center of the main hall finished floor at `Y = 0.00 m`.
- **Main Entrance Opening (`+Z`)**: `Z = +9.00 m` to `+10.40 m`, **`5.60 m` wide × `4.80 m` high** (`X ∈ [-2.80, +2.80]`, `Y ∈ [0.00, 4.80]`).
- **Central Rear Enfilade Portal (`-Z`)**: `Z = -9.00 m` to `-9.90 m`, **`4.40 m` wide × `4.40 m` high** (`X ∈ [-2.20, +2.20]`, `Y ∈ [0.00, 4.40]`), leaving `9.80 m`-wide uninterrupted exhibition wings on both left and right (`Anchor_Artwork_Back_01` at `X = -6.60 m`, `Anchor_Artwork_Back_03` at `X = +6.60 m`), plus sliding pocket partition `Wall_Back_Portal_Closure`.

---

## 4. Semantic Node Hierarchy

```text
Museum_Open_Hall
├── Architecture
│   ├── Floor
│   ├── Wall_Left
│   ├── Wall_Right
│   ├── Wall_Back
│   ├── Wall_Back_Portal_Closure      (Open pocket @ [-4.62, 0, -0.38]; Closed flush @ [0, 0, 0])
│   ├── Secondary_Gallery             (10.80 x 5.80 x 6.80 m sunlit rear enfilade gallery)
│   ├── Wall_Entrance
│   ├── Entrance_Vestibule            (14.40 x 5.00 x 6.60 m arrival vestibule)
│   ├── Entrance_Frame
│   ├── Ceiling
│   ├── Ceiling_Beams                 (5 painted-steel king-post collar trusses)
│   └── Wall_Floor_Transitions
├── Skylight
│   ├── Skylight_Frame                (21 conservatory mullion bays + glazed gable ends)
│   ├── Skylight_Supports             (7 pitched steel rafter pairs + purlins + ridge beam)
│   └── Skylight_Glass                (17.1 deg sloped laminated panes + gable glass)
├── Lighting_Fixtures
│   ├── Track_Left
│   │   └── Fixture_Head_Left_01 .. 05
│   ├── Track_Right
│   │   └── Fixture_Head_Right_01 .. 05
│   ├── Track_Back
│   │   └── Fixture_Head_Back_01 .. 05
│   └── Recessed_Fixtures
├── Exhibition_Anchors
│   ├── Anchor_Artwork_Back_01 .. 03
│   ├── Anchor_Artwork_Left_01 .. 03
│   ├── Anchor_Artwork_Right_01 .. 03
│   ├── Anchor_Artwork_Secondary_01   (Focal anchor on Secondary_Gallery rear wall)
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
    ├── Anchor_Navigation_Secondary
    └── Anchor_Navigation_Artwork_01 .. 09
```

---

## 5. Material Customization & Dual-UV AO Contract

| Material Slot | Assigned Meshes | Default Tone (sRGB) | Roughness / Metallic | Maps & Customization Guidance |
| :--- | :--- | :---: | :---: | :--- |
| `Mat_Wall_Plaster` | `Wall_Back`, `Wall_Back_Portal_Closure`, `Wall_Left`, `Wall_Right`, `Wall_Entrance`, `Secondary_Gallery`, `Entrance_Vestibule` | `#F6F4EE` | `~0.88` / `0.00` | Neutral near-white mineral clouding basecolor (`0.985–0.996`) + aligned normal & roughness maps on `TEXCOORD_0` (`6.0 m` world UV scale) + neutral Cycles AO (`textures/museum_ao.png`) on `TEXCOORD_1` (`aoMap`). Set `material.color` freely to any gallery tint without losing soft corner shading; clone `Wall_Back.material` to customize an accent wall independently. |
| `Mat_Floor_Concrete` | `Floor` | `#8E8B85` | `~0.27` (`0.235–0.375`) / `0.00` | Grounded medium-gray power-troweled concrete (`1024²` mineral clouding basecolor, micro-normal, and satin roughness on `TEXCOORD_0` at `6.4 m` UV scale, `IOR 1.52`) + neutral Cycles AO on `TEXCOORD_1`, delivering natural Fresnel reflections of the pitched skylight and artworks. |
| `Mat_Ceiling` | `Ceiling`, secondary/vestibule soffits | `#EEEBE3` | `0.90` / `0.00` | Warm mineral acoustic plaster (`TEXCOORD_0` `5.4 m` UV scale) + neutral Cycles AO (`TEXCOORD_1`) capturing soft skylight-well and perimeter cove gradation. |
| `Mat_Structural_Beam` | `Ceiling_Beams`, `Skylight_Supports` | `#F8F7F3` | `0.44` / `0.14` | Crisp white painted architectural steel king-post trusses, rafters, and central ridge beam (`2.5 m` micro-normal). |
| `Mat_Skylight_Frame` | `Skylight_Frame` | `#E4E2DC` | `0.34` / `0.38` | Powder-coated pale silver-white conservatory glazing mullions, transoms, and gable framing. |
| `Mat_Skylight_Glass` | `Skylight_Glass` | `#EDF4FA` (`alpha 0.16`) | `0.06` / `0.05` | Standard glTF `BLEND` transparency (`opacity: 0.16`, `IOR 1.52`) for fast WebGL compatibility. Set `Skylight_Glass.castShadow = false` so directional sunlight casts crisp truss/mullion shadows across the walls and floor. |
| `Mat_Entrance_Frame` | `Entrance_Frame` | `#423B34` | `0.38` / `0.38` | Warm dark bronze-walnut portal sleeve (`65 mm` deep, inset `18–22 mm` behind plaster faces on both entrance and rear enfilade portals). |
| `Mat_Lighting_Fixture` | `Track_*`, `Fixture_Head_*`, `Recessed_Fixtures` | `#2C2B29` | `0.42` / `0.38` | Matte dark graphite recessed track channels and adjustable spotlight heads. |
| `Mat_Trim` | `Wall_Floor_Transitions` | `#363431` | `0.52` / `0.28` | Disjoint `32 mm × 28 mm` recessed wall-to-floor and ceiling shadow-gap channel liner. |

---

## 6. Exhibition Configurations, Adjustable Fixtures, & Runtime Helper (`museum_lighting.mjs`)

### 6.1 Dual Exhibition Configurations (Enfilade Open vs. 9-Artwork Closed)
- **Configuration A — Open Enfilade (`default` in `model.glb`)**:
  - `Wall_Back_Portal_Closure.position` is `(-4.62, 0.0, -0.38)` (tucked inside the left double-wall pocket of `Wall_Back`).
  - Supports **8 main-hall artworks** (`Anchor_Artwork_Back_01`, `Anchor_Artwork_Back_03`, `Anchor_Artwork_Left_01..03`, `Anchor_Artwork_Right_01..03`) plus **1 axial focal artwork** in the sunlit secondary room (`Anchor_Artwork_Secondary_01` at `(0.00, 1.55, -15.697)`).
- **Configuration B — Classic 9-Artwork Main Hall (`setRearPortalOpen(root, false)`)**:
  - Slide `Wall_Back_Portal_Closure.position.set(0, 0, 0)` so its front face sits flush with `Wall_Back` at `Z = -9.00 m`.
  - Restores the full uninterrupted `24.00 m` rear wall and enables all **9 main-hall artwork anchors** (`Anchor_Artwork_Back_01..03`, `Anchor_Artwork_Left_01..03`, `Anchor_Artwork_Right_01..03`).

| Anchor Name | Target Wall | glTF Position `(X, Y, Z)` (m) | Inward Normal `+Z` | Max Centered `W × H` (m) | Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `Anchor_Artwork_Back_01` | `Wall_Back` | `(-6.600, 1.550, -8.997)` | `(0, 0, +1)` | `4.60 × 2.60` | Always available (`9.80 m` left wing) |
| `Anchor_Artwork_Back_02` | `Wall_Back_Portal_Closure` | `( 0.000, 1.550, -8.997)` | `(0, 0, +1)` | `4.00 × 2.60` | Use when `Wall_Back_Portal_Closure` is closed `(0,0,0)` |
| `Anchor_Artwork_Back_03` | `Wall_Back` | `(+6.600, 1.550, -8.997)` | `(0, 0, +1)` | `4.60 × 2.60` | Always available (`9.80 m` right wing) |
| `Anchor_Artwork_Left_01..03` | `Wall_Left` | `(-11.997, 1.550, -5.20 / 0.00 / +5.20)` | `(+1, 0, 0)` | `3.80–4.00 × 2.60` | Always available |
| `Anchor_Artwork_Right_01..03` | `Wall_Right` | `(+11.997, 1.550, -5.20 / 0.00 / +5.20)` | `(-1, 0, 0)` | `3.80–4.00 × 2.60` | Always available |
| `Anchor_Artwork_Secondary_01` | `Secondary_Gallery` | `( 0.000, 1.550, -15.697)` | `(0, 0, +1)` | `4.20 × 2.60` | Axial focal wall through open rear portal |

### 6.2 Adjustable Spotlight Heads & Three.js Lighting Controller (`museum_lighting.mjs`)
- Each track (`Track_Left` at `X = -9.48 m`, `Track_Right` at `X = +9.48 m`, `Track_Back` at `Z = -7.90 m`) parents 5 instanced `Fixture_Head_*` nodes pivoted at `Y = 8.920 m` with **local `-Z` aligned to the optical beam**.
- Optional companion ES module `museum_lighting.mjs` configures architectural sky-bounce PMREM, dual-UV `aoMapIntensity`, portal state, spotlight aiming, and presets (`"soft_daylight"`, `"direct_sun"`, `"evening"`):
  ```js
  import { applyMuseumLighting, setRearPortalOpen, aimSpotlightHead } from './museum_lighting.mjs';

  const rig = applyMuseumLighting(scene, renderer, gltf.scene, { mode: 'soft_daylight' });
  setRearPortalOpen(gltf.scene, true); // false closes Wall_Back_Portal_Closure for 9-artwork mode
  aimSpotlightHead(gltf.scene, 'Fixture_Head_Left_03', new THREE.Vector3(-11.997, 1.55, 0.0));
  ```

---

## 7. Collision & Walkable-Space Contract

`Museum_Open_Hall` embeds metric walkable bounds on `Museum_Open_Hall.userData.walkableBoundsMeters` (`Y ∈ [0.00, 2.60 m]`):
- **Main Hall Walkable Zone**: `X ∈ [-11.65, +11.65]`, `Z ∈ [-8.65, +8.65]`, `Y = 0.00 m`.
- **Entrance Portal & Arrival Vestibule**: `X ∈ [-2.50, +2.50]`, `Z ∈ [+8.65, +10.40]` leading into `X ∈ [-6.85, +6.85]`, `Z ∈ [+10.40, +15.05]`.
- **Rear Enfilade Portal & Secondary Gallery (when `Wall_Back_Portal_Closure` is open)**: `X ∈ [-1.90, +1.90]`, `Z ∈ [-9.90, -8.65]` leading into `X ∈ [-5.05, +5.05]`, `Z ∈ [-15.35, -9.90]`. When `Wall_Back_Portal_Closure` is closed at `(0, 0, 0)`, clamp main-hall `Z >= -8.65 m` across the full width.

---

## 8. Texture Maps, Measured Performance, & File Packaging

### 8.1 Authoring & Embedded Runtime Texture Maps (`8` PNGs, `4,799,196` bytes)

| File | Resolution | Color Space | UV Channel / Scale | Size (Bytes) | Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| `textures/wall_plaster_basecolor.png` | `512 × 512` | `sRGB` | `UVMap` (`6.00 m`) | `80,853` | Neutral near-white mineral clouding (`0.985–0.996`) |
| `textures/wall_plaster_normal.png` | `1024 × 1024` | Linear (`Non-Color`, OpenGL `+Y`) | `UVMap` (`6.00 m`) | `1,459,788` | Fine lime-mineral gallery plaster micro-normal |
| `textures/wall_plaster_roughness.png` | `512 × 512` | Linear (`Non-Color`) | `UVMap` (`6.00 m`) | `126,385` | Coherent matte plaster roughness (`~0.85–0.91`) |
| `textures/floor_concrete_basecolor.png` | `1024 × 1024` | `sRGB` | `UVMap` (`6.40 m`) | `956,375` | Neutral concrete mineral clouding (`0.88–0.99`, multiplied by `#8E8B85`) |
| `textures/floor_concrete_normal.png` | `1024 × 1024` | Linear (`Non-Color`, OpenGL `+Y`) | `UVMap` (`6.40 m`) | `860,979` | Power-troweled concrete micro-normal & fine mineral pores |
| `textures/floor_concrete_roughness.png` | `1024 × 1024` | Linear (`Non-Color`) | `UVMap` (`6.40 m`) | `574,722` | Power-troweled satin concrete roughness (`0.235–0.375`) |
| `textures/ceiling_plaster_normal.png` | `512 × 512` | Linear (`Non-Color`, OpenGL `+Y`) | `UVMap` (`5.40 m / 2.50 m`) | `476,751` | Acoustic mineral ceiling & painted steel truss micro-normal |
| `textures/museum_ao.png` | `1024 × 1024` | Linear (`Non-Color`) | `UVMap_AO` (`TEXCOORD_1`) | `263,343` | Path-traced neutral Cycles Ambient Occlusion / Sky-Access atlas (`glTF occlusionTexture`) |

### 8.2 Measured Geometry, Runtime Performance, & Clean-Checkout Verification

- **Total glTF nodes**: `90` (`34` mesh nodes across `20` unique mesh primitives: `19` architectural/track meshes + `15` instanced `Fixture_Head_*` nodes sharing `Spot_Head_Mesh`; `9` materials; `8` embedded images)
- **Triangles / Vertices**: `8,950` triangles / `15,042` vertices (`0` degenerate faces)
- **Canonical `model.glb` size**: `6,006,072` bytes (`5.73 MiB`), SHA-256 `dbceb3df82dc1ea52a346a03e4d355402da2a54d0e14aefd472d8a59ec25d320`
- **Estimated GPU texture memory (`10` Three.js texture bindings across `8` images, RGBA8 + mipchain)**: `43,341,138` bytes (`41.33 MiB`)
- **Three.js `GLTFLoader` load time**: `50.5 ms` (local HTTP loopback in headless Chromium WebGL)
- **Draw calls (`1600×1000` with `2048²` PCFSoftShadowMap)**: `58` across shadow + main pass (`34` unshadowed)
- **Steady-state WebGL frame time (`90`-frame benchmark after warmup, `gl.finish()`)**: `0.117 ms` average, `0.200 ms` p95 (measured on Apple Silicon Metal/ANGLE headless Chromium; physical mobile device hardware was not tested)
- **Clean-checkout reproducibility**: Verified bit-for-bit identical `model.glb` SHA-256 (`dbceb3df82dc1ea52a346a03e4d355402da2a54d0e14aefd472d8a59ec25d320`) regenerated from an isolated `/tmp` clean copy containing only tracked package files (no `.work/`), and verified relative `//textures/` paths in `model.blend`.

### 8.3 Tracked Package Files vs. Consumer Distribution & Known Limitations

- **Tracked authoring & catalog files (`17` files)**:
  - `model.glb` (`6,006,072` bytes — **sole required consumer runtime file**, 100% self-contained)
  - `museum_lighting.mjs` (`9,394` bytes — optional Three.js daylight/evening & portal/spotlight helper)
  - `preview.webp` (`32,830` bytes — optional catalog preview)
  - `manifest.json` (`~9.1 KB` — optional catalog metadata)
  - `model.blend` (`243,461` bytes — editable Blender 5.2 source)
  - `generate.py` (`113,272` bytes — deterministic Blender Python generator)
  - `textures/*.png` (`8` files, `4,799,196` bytes total — authoritative lossless PBR & neutral AO maps)
  - `validate_blender.py` (`9,597` bytes), `validate_threejs.mjs` (`27,723` bytes), `notes.md`
- **Known limitations**:
  1. `model.glb` provides architectural geometry, PBR + neutral AO materials, semantic anchors, and walkable-bound metadata; camera navigation, collision clamping, and interactive exhibition UI are supplied by the consumer (**FrilCraft** / **FrilStudio**).
  2. Generic glTF viewers that use a single directional headlight with zero hemisphere/IBL environment will still benefit from the embedded `museum_ao.png` `occlusionTexture`, while full museum daylight quality in Three.js is achieved via `museum_lighting.mjs` (or an overcast HDRI + directional sun with `Skylight_Glass.castShadow = false`).
  3. Physical mobile device GPU frame times were not measured; mobile checks covered `9:16` (`540×960`) portrait rendering and VRAM budgeting (`41.33 MiB`).
