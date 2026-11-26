# Editorial Magazine (`objects/editorial-magazine`)

## 1. Sourcing & Provenance Record (`docs/asset-sourcing.md`)

- **Asset ID**: `objects/editorial-magazine`
- **Search Date**: `2026-11-26`
- **Intended Use & Requirements**: Photorealistic A4 (`210 × 297 mm`) perfect-bound softcover editorial magazine supporting configurable page counts (`4` to `200` printed interior pages, including the mandatory `100`-page / `50`-leaf configuration), configurable cover and interior paper calipers, natural Elastica page-turn and front/back cover animations (`< 1%` arc-length error), layered trimmed paper edges, and `8` independent unmirrored `[0, 1]` full-page artwork material slots.
- **Local Packages Checked**:
  - Checked `assets/`, `materials/paper/`, `textures/`, `images/` in `frilassets` and inspected sibling repositories (`fril-studio`, `frilcraft`, `frilremotion`, `friladd`) read-only. No existing magazine model or coated paper PBR map package exists.

| Query / Source | Candidate URL | Creator / Provider | License Evidence URL | Suitability / Blockers |
| :--- | :--- | :--- | :--- | :--- |
| Poly Haven: `magazine book open pages` | `https://polyhaven.com/a/decorative_book_set_01` | James Ray Cock / Poly Haven | `https://polyhaven.com/license` (CC0) | Static closed decorative shelf prop blocks with baked cover graphics; lacks open spread geometry, flexible softcover hinge, independent page UVs, and length-preserving page-turn deformation. |
| ambientCG: `Paper001`, `Paper005`, `Paper006` | `https://ambientcg.com/view?id=Paper001` | Lennart Demes / ambientCG | `https://docs.ambientcg.com/license/` (CC0) | `Paper001` is coarse uncoated white office paper; `Paper005` / `Paper006` are brown kraft/cardboard packaging surfaces. None represent fine calendered `135 gsm` silk-matte editorial stock, `280 gsm` satin-laminated cover board, or `0.15 mm` guillotine-trimmed layered page-stack edges. |
| Sketchfab: `editorial magazine softcover open animated page turn CC0` | `https://sketchfab.com/search?features=downloadable&licenses=7c23a1ba438d4306920229c12afcb5f9&q=magazine+animated` | Various Sketchfab contributors | Individual model pages verified | Downloadable animated page-turn models on Sketchfab are predominantly `CC BY` or paid rather than `CC0`, or use rigid/linearly interpolated planes without 8 independent right-reading artwork UV slots. |

- **Decision**: **Create** (`procedural-blender-python` + reference ES module controller).
- **Status & License**: `status: "draft"`, `assetLicense: null` pending human visual and rights review per `docs/publication.md`. Generator, controller, and validation code retain the repository `MIT` license.

---

## 2. Physical Specification, Coordinates & Page-Count Convention

- **Units**: Meters (`1.0` unit = `1.0 m`).
- **Exported glTF Coordinate System (`+Y` Up)**:
  - **Root Node & Origin**: `Magazine_Root` at `(0.0, 0.0, 0.0)` on the resting tabletop plane (`Y = 0`), centered longitudinally and laterally at the binding.
  - **Axes**: `+X` right (right-hand spread / closed front fore-edge), `-X` left (left-hand spread / closed back fore-edge), `+Y` up above resting surface, `-Z` head/top edge (`V = 1`), `+Z` foot/bottom edge toward viewer (`V = 0`).
- **Page-Count, Leaf, Spread & Cover Convention**:
  - **Covers** (`Cover_Front`, `Cover_Back`): Separate physical sheets (`default = 0.320 mm` / `280 gsm` C2S satin-laminated art stock with `4.8 mm` outer hinge score grooves), providing `4` cover surfaces (`Mat_Cover_Front_Outer`, `Mat_Cover_Front_Inner`, `Mat_Cover_Back_Inner`, `Mat_Cover_Back_Outer`). Covers are **never** counted as interior pages.
  - **Interior Printed Pages vs. Physical Leaves**: Let $P = 2 N_{\text{leaves}}$ be the configured even count of printed interior pages ($N_{\text{leaves}} = P / 2$ double-sided physical leaves, `default = 56` pages = `28` leaves; mandatory acceptance case = `100` pages = `50` leaves; stress case = `200` pages = `100` leaves; `default leaf caliper = 0.145 mm` / `135 gsm` silk-matte stock).
  - Each physical leaf $\ell \in \{1, \dots, N_{\text{leaves}}\}$ carries **Printed Page $2\ell - 1$** on its recto (front / right-hand odd surface) and **Printed Page $2\ell$** on its verso (back / left-hand even surface).
  - **Open Spread Index $k \in \{0, 1, \dots, N_{\text{leaves}}\}$** (committed count of interior leaves resting on the left):
    - $k = 0$ (**First Interior Spread**): Inside Front Cover (`Mat_Cover_Front_Inner`) on left | Page `1` (`Mat_Page_Right`) on right (`0` left leaves, $N_{\text{leaves}}$ right leaves).
    - $1 \le k \le N_{\text{leaves}} - 1$ (**Interior Spread $k$**): Page `2k` (`Mat_Page_Left`) on left | Page `2k + 1` (`Mat_Page_Right`) on right ($k$ left leaves, $N_{\text{leaves}} - k$ right leaves).
    - $k = N_{\text{leaves}}$ (**Last Interior Spread**): Page $P$ (`Mat_Page_Left`) on left | Inside Back Cover (`Mat_Cover_Back_Inner`) on right ($N_{\text{leaves}}$ left leaves, `0` right leaves).
  - **Leaf Conservation Law**: At every idle or turning state,
    $$\text{leftInactiveLeaves} + \text{leftVisibleLeaf} + \text{activeTurningLeaf} + \text{rightVisibleLeaf} + \text{rightInactiveLeaves} \equiv N_{\text{leaves}}$$
    so the active turning sheet (`Page_Turning`) is never double-counted.

---

## 3. Hierarchy, Bones, Morph Targets & Animation Isolation (`model.glb`)

- **Canonical GLB Size & SHA-256**: `3,754,828` bytes | `e1f8298778aa95a98d6ac9e055f01f31078f94ac250f5d42a378c4a750736260`

### Public Scene Hierarchy
```text
Magazine_Root (Object3D at (0, 0, 0))
├── Binding           — Deformable perfect-bound cover spine wrap + inner PUR adhesive cradle (1,096 tris)
├── Cover_Front       — Unified manifold front cover; morphTarget: Thickness_Scale (2,460 tris)
├── Cover_Back        — Unified manifold back cover; morphTarget: Thickness_Scale (2,460 tris)
├── Pages_Block_Left  — Deformable left inactive stack (8 terraced edge layers); morphTarget: Thickness_Scale (4,280 tris)
├── Pages_Block_Right — Deformable right inactive stack (8 terraced edge layers); morphTarget: Thickness_Scale (4,280 tris)
├── Page_Left         — Unified manifold visible left sheet; morphTarget: Thickness_Scale (2,460 tris)
├── Page_Right        — Unified manifold visible right sheet; morphTarget: Thickness_Scale (2,460 tris)
├── Page_Turning      — Unified manifold active turning sheet; morphTarget: Thickness_Scale (2,460 tris)
└── Rig_Origin        — Skeletal joint hierarchy (233 joints: Spine_00..07 + 7 × 32-bone Elastica chains)
```

### Dynamic Stack & Paper Thickness Control (`Thickness_Scale` Morph Target)
Because glTF 2.0 and Three.js evaluate morph targets in **bind space** (prior to skeletal skinning), setting `primitive.morphTargetInfluences[0] = (targetThicknessMeters / defaultThicknessMeters) - 1.0` scales sheet or inactive-stack thickness strictly along the **local curved Elastica surface normal** $\mathbf{n}(s)$ across all 32 bones without world-`Y` shear. Reference default thicknesses in `model.glb`:
- `Cover_Front`, `Cover_Back`: `0.000320 m`
- `Page_Left`, `Page_Right`, `Page_Turning`: `0.000145 m`
- `Pages_Block_Left`: `0.001680 m` | `Pages_Block_Right`: `0.001820 m`
- When `leftInactiveLeaves === 0` or `rightInactiveLeaves === 0`, hide the empty block (`visible = false`) and rest the exposed sheet directly on the cover (`0` artificial gap).

### Exported Standalone GLB Animation Clips (`t ∈ [0.0000, 2.0000 s]`, `61` frames)
| Clip Name | Channels | Controlled Joints | Standalone Lifecycle Role & Isolation Guarantee |
| :--- | :---: | :--- | :--- |
| `Magazine_Open` | `240` | `Spine_00..07` + all `7` chains | **Front cover opening**: Closed front cover on `+X` (`t = 0`) → open spread (`t = 1`). |
| `Magazine_Close` | `240` | `Spine_00..07` + all `7` chains | **Front cover closing**: Open spread (`t = 0`) → closed front cover on `+X` (`t = 1`). |
| `Magazine_PageTurn` | **`33`** | **Strictly `Page_Turning_00..31` only** | **Forward page turning** (`+X → -X`): **`0.000000 mm` drift** on covers, spine, resting pages, and stacks. |
| `Magazine_PageTurn_Back` | **`33`** | **Strictly `Page_Turning_00..31` only** | **Backward page turning** (`-X → +X`): **`0.000000 mm` drift** on covers, spine, resting pages, and stacks. |
| `Magazine_Close_Back` | `240` | `Spine_00..07` + all `7` chains | **Back cover closing**: Final open spread (`t = 0`) → closed magazine on `-X` resting on `Cover_Front` with `Cover_Back` outer surface visible on top (`t = 1`). |
| `Magazine_Open_Back` | `240` | `Spine_00..07` + all `7` chains | **Back cover opening**: Closed back cover on `-X` (`t = 0`) → reopens to final spread (`t = 1`). |

---

## 4. Material Slots & Dual-UV Customization Contract

- **`UVMap` (`TEXCOORD_0` / `uv`)**: Full-page `[0, 1] × [0, 1]` right-reading artwork coordinates (`u: 0 → 1` left-to-right when viewing each surface face-on; configure Three.js artwork textures with `tex.flipY = false` and `tex.colorSpace = THREE.SRGBColorSpace`).
- **`UVMap_Detail` (`TEXCOORD_1` / `uv1`, `channel = 1`)**: Physical-scale (`0.0525 m` repeat) micro-paper `normalMap` and `roughnessMap`, completely independent of `material.map`.
- **Replaceable Artwork Materials (`8`)**: `Mat_Cover_Front_Outer`, `Mat_Cover_Front_Inner`, `Mat_Cover_Back_Outer`, `Mat_Cover_Back_Inner`, `Mat_Page_Left`, `Mat_Page_Right`, `Mat_Page_Turning_Front`, `Mat_Page_Turning_Back`.
- **Structural Paper Materials (`3`)**: `Mat_Spine_Exterior`, `Mat_Paper_Interior`, `Mat_Paper_Edges`.

---

## 5. Reference Controller Contract (`magazine_controller.mjs`) & Consumer Distribution

### Role Separation: `model.glb` vs. `EditorialMagazineController`
- **`model.glb` alone** provides the 3D geometry, PBR paper/edge materials, dual UVs, `Thickness_Scale` morph targets, 233-joint skeletal rig, and the 6 standalone 2-second animation clips. It does **not** by itself manage configurable page counts, dynamic stack recalculation, artwork assignment, or interactive turn state.
- **[`magazine_controller.mjs`](./magazine_controller.mjs) (`EditorialMagazineController`)** is the preserved asset-level ES module reference controller (`import * as THREE from "three"`, verified with `three@0.186.1`) providing configurable $N$-page lifecycle control.

### Public Interface, Ownership & Disposal Rules (`EditorialMagazineController`)
- **Constructor**: `new EditorialMagazineController(sceneRoot, { pageCount = 56, leafThickness = 0.000145, coverThickness = 0.000320, airGap = 0.000018, maxCachedPages = 16 })`
  - Clones only the `8` mutable artwork materials for that instance (preserving shared embedded PBR normal/roughness maps across `SkeletonUtils.clone(gltf.scene)` instances).
- **Configuration & Artwork**:
  - `setPageCount(evenInteriorPageCount)` — Reconfigures total interior pages (`even integer >= 2`); flushes owned LRU page textures on change.
  - `setPaperThickness({ leafMeters, coverMeters, airGapMeters })` — Updates sheet/cover calipers and spine span.
  - `setCoverArtwork(side, source)` — `side` in `"frontOuter" | "frontInner" | "backOuter" | "backInner"`; accepts an `HTMLCanvasElement`/`Image` (controller creates & owns a `CanvasTexture` with `flipY = false`, `SRGBColorSpace`) or an external `THREE.Texture` (`owned: false`, caller retains disposal responsibility).
  - `setPageArtwork(pageNumber, source)` / `setPageArtworkProvider((pageNumber) => source)` — Lazy on-demand page artwork binding (`1..pageCount`) backed by a bounded LRU GPU cache (`maxCachedPages`, default `16`), evicting and calling `.dispose()` on oldest non-visible owned textures.
- **Lifecycle & Interruptible Progress Controls (`progress ∈ [0, 1]`)**:
  - Cover controls: `openFrontCover(progress = 1)`, `closeFrontCover(progress = 1)`, `closeBackCover(progress = 1)`, `openBackCover(progress = 1)`, plus atomic `open()` / `close()`.
  - Page-turn controls: `beginTurnForward()`, `beginTurnBackward()`, `setTurnProgress(progress)`, `setProgress(progress)`, `pauseTurn()`, `resumeTurn()`, `reverseTurnDirection()`, `cancelTurn()`, `commitTurn()`, plus atomic `next()` / `previous()`.
  - State inspection: `state` (`"CLOSED_FRONT" | "OPENING_FRONT" | "CLOSING_FRONT" | "OPEN_SPREAD" | "TURNING" | "CLOSING_BACK" | "OPENING_BACK" | "CLOSED_BACK"`), `leftLeaves`, `leafCount`, `cachedTextureCount`, `getLeafAccounting()`.
- **Disposal (`dispose()`)**:
  - Must be called when removing a magazine instance. Disposes all controller-owned `CanvasTexture` entries (LRU page cache + cover textures) and the `8` per-instance cloned artwork materials, without disposing shared GLB geometry or shared embedded PBR textures.

### Consumer Distribution Payloads (`docs/asset-file-policy.md`)
1. **Static model viewing payload (`3,754,828` bytes + license notice)**:
   - `model.glb` (`3,754,828` bytes; all `7` PBR maps embedded) + applicable license notices upon release.
2. **Interactive magazine runtime payload (`3,800,970` bytes + peer runtime + user artwork)**:
   - `model.glb` (`3,754,828` bytes)
   - `magazine_controller.mjs` (`46,142` bytes) or an equivalent compatible runtime controller
   - Runtime dependency `three` (verified with `0.186.1`), runtime configuration, consumer-supplied cover/page artwork, and applicable license notices.
3. **Excluded authoring & validation files** (repository-only): `generate.py`, `model.blend`, `textures/*.png`, `validate_blender.py`, `validate_threejs.mjs`, `preview.webp`, `manifest.json`, `notes.md`.

---

## 6. Reproducible Validation Summary & Toolchain

### Verified Toolchain (`bit-for-bit` GLB SHA-256 Reproduction)
- **Blender**: `5.2.2 LTS` (macOS arm64 Metal, build `2026-09-15`, bundled `Python 3.13.13`, `NumPy 2.3.4`) — bit-for-bit SHA-256 reproduction of `model.glb` (`e1f8298778aa95a98d6ac9e055f01f31078f94ac250f5d42a378c4a750736260`) depends on matching Blender `5.2.2 LTS` glTF exporter + `NumPy 2.3.4` floating-point output.
- **Runtime Harness**: `Node.js v26.12.1`, `three@0.186.1`, `playwright@1.64.1` (headless Google Chrome WebGL `ANGLE` on Apple M2 macOS), `ffmpeg` (optional, used only with `--record-demo`).

### Clean-Checkout Reproduction Commands
```bash
# 1. Regenerate textures, model.blend, and canonical model.glb (without .work/)
/Applications/Blender.app/Contents/MacOS/Blender --background --python assets/objects/editorial-magazine/generate.py -- --skip-preview
shasum -a 256 assets/objects/editorial-magazine/model.glb

# 2. Standalone Blender 6-clip x 101-sample (606-pose) deformation & BVH collision validation
/Applications/Blender.app/Contents/MacOS/Blender --background assets/objects/editorial-magazine/model.blend --python assets/objects/editorial-magazine/validate_blender.py

# 3. Three.js WebGL runtime acceptance (6-clip GLB skinning + 4..200p matrix + 100p lifecycle + interruption + LRU)
NODE_PATH=<path-to-node_modules-with-three-and-playwright> node assets/objects/editorial-magazine/validate_threejs.mjs

# 4. Optional: also record 30 fps 100-page lifecycle MP4 and 1.0x normal-speed MP4 into .work/
NODE_PATH=<path-to-node_modules-with-three-and-playwright> node assets/objects/editorial-magazine/validate_threejs.mjs --record-demo
```

### Standalone GLB Validation vs. Controller-Level Three.js Validation
- **Standalone Blender Source & GLB Clip Results** (`validate_blender.py` + Section 2 of `validate_threejs.mjs`):
  - **Deformation (`606` samples across 6 clips)**: Max centerline arc-length deviation `0.03867%` in Blender (`209.919–210.051 mm`) and `0.03084%` on exported Three.js skinned GLB vertices (`209.935–210.000 mm`), well within `< 1%`. Max cross-section deviation `0.24857%`; sheet thickness deviation `<= 0.1289%`.
  - **Collision Methodology & Exclusions**: Exact world-space `BVHTree.FromBMesh(..., epsilon=0.0)` overlap tests across all `15` sheet-to-sheet, sheet-to-block, cover-to-block, and cover-to-cover pairs on all `606` poses returned **`0` intersections**. `Binding` is intentionally excluded from raw pair overlap because its inner PUR adhesive bed (`x <= +1.42 mm`) embeds the `s = 0..0.5 mm` spine roots by `~0.14 mm` to prevent hairline glue-slot gaps; root-to-binding attachment stays `<= 2.34 mm` everywhere.
  - **6-Clip Boundary Continuity & Isolation**: Consecutive clip boundaries (`Open → PageTurn → Close_Back → Open_Back → PageTurn_Back → Close → Open`) measure **`0.000000 mm`** vertex mismatch. Seeking `Magazine_PageTurn` or `Magazine_PageTurn_Back` (`33` channels each) produces **`0.000000 mm`** drift on covers, binding, resting sheets, and stack morphs.
- **Controller-Level Three.js WebGL Results** (`validate_threejs.mjs`):
  - **Tested Page Counts**: `4, 10, 24, 50, 100, and 200` interior pages (`2..100` physical leaves; closed heights `1.487..17.461 mm`), all preserving exact leaf conservation and zero empty-stack air gaps.
  - **100-Page Bidirectional Lifecycle**: `50` forward leaf turns + `closeBackCover` (`closedBackTopHeightMm = 8.747 mm`) + `openBackCover` + `50` backward leaf turns + `closeFrontCover` (`0.000000 mm` accumulated drift), `100` distinct asymmetric page artworks verified right-reading in both directions, max turning arc deviation `0.00244%`, cover/spread handoff continuity `<= 0.0706 mm`, tabletop clearance `minGlobalTabletopYMm = -0.0065 mm`.
  - **Interruptions & Caching**: Pause (`25%`, `50%`), resume, mid-turn reversal (`0.000000 mm` jump), cancel at `75%`, and `24` rapid alternating operations passed. Bounded `16`-page LRU cache capped WebGL memory (`<= 47` total textures across `100` pages) and `dispose()` reclaimed GPU textures (`46 → 44`).
  - **Desktop WebGL Performance**: `44.9 ms` GLB load, `0.376 ms/frame` average skin + shadow + PBR render (`22` draw calls) in headless Chrome WebGL (`ANGLE` on Apple M2 macOS).

### Remaining Limitations
- **Even interior page counts**: Physical leaves are double-sided (`1 leaf = 2 printed pages`); represent an unprinted final page by supplying blank artwork for page $P$.
- **High-bulk regime (`300+` pages)**: Validated cleanly through `200` interior pages (`100` leaves, `~17.5 mm` closed height); thicker `300+` page volumes typically require multi-signature hollow-back book construction.
- **Physical mobile hardware**: Physical iOS and Android handset frame rates remain **NOT TESTED** (no mobile device attached to this workspace).
- **Draft status**: Asset remains `status: "draft"` and `assetLicense: null` pending human visual and rights review.
