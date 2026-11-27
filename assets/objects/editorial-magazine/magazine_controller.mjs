/**
 * Reusable Three.js Runtime Controller for `objects/editorial-magazine` (`model.glb`).
 *
 * Reference implementation of the FrilAssets Editorial Magazine runtime contract:
 *   - Supports configurable interior page counts (any even count >= 2, e.g. 4..200 pages = 2..100 physical leaves)
 *     and configurable cover / interior sheet calipers using the single canonical `model.glb`.
 *   - Preserves physical leaf conservation across inactive stacks, visible resting sheets, and active turning sheet.
 *   - Uses bind-space `Thickness_Scale` morph targets + 32-bone Elastica tangent-angle integration so stack thickness
 *     scales along the curved sheet normal without world-Y shear and without artificial gaps when a stack is empty.
 *   - Supports opening/closing both Front Cover and Back Cover, forward/backward single-leaf turns, normalized
 *     progress seeking [0, 1], pause, resume, mid-turn reversal, turn cancellation, boundary protection, per-instance
 *     material isolation, and bounded LRU GPU texture caching.
 */

import * as THREE from "three";

const PAGE_W = 0.21000;
const BONE_S_NODES = [
  ...Array.from({ length: 12 }, (_, i) => 0.0030 * i),
  ...Array.from({ length: 21 }, (_, j) => 0.0360 + (PAGE_W - 0.0360) * (j / 20.0)),
];
const N_SHEET_BONES = 32;
const BONE_S_MIDS = Array.from({ length: N_SHEET_BONES }, (_, k) => 0.5 * (BONE_S_NODES[k] + BONE_S_NODES[k + 1]));
const BONE_DS = Array.from({ length: N_SHEET_BONES }, (_, k) => BONE_S_NODES[k + 1] - BONE_S_NODES[k]);
const N_SPINE_BONES = 8;

// Canonical rest thicknesses baked into `model.glb`
const REF_T_COVER = 0.000320;
const REF_T_PAGE = 0.000145;
const REF_T_BLOCK_R = 0.001820;
const REF_T_BLOCK_L = 0.001680;

const ARTWORK_SLOTS = {
  frontOuter: "Mat_Cover_Front_Outer",
  frontInner: "Mat_Cover_Front_Inner",
  backOuter: "Mat_Cover_Back_Outer",
  backInner: "Mat_Cover_Back_Inner",
  pageLeft: "Mat_Page_Left",
  pageRight: "Mat_Page_Right",
  turningFront: "Mat_Page_Turning_Front",
  turningBack: "Mat_Page_Turning_Back",
};

function clamp01(x) {
  return x < 0 ? 0 : x > 1 ? 1 : x;
}

function smoothstep(e0, e1, x) {
  if (e1 === e0) return 0;
  const t = clamp01((x - e0) / (e1 - e0));
  return t * t * (3 - 2 * t);
}

function smootherstep(e0, e1, x) {
  if (e1 === e0) return 0;
  const t = clamp01((x - e0) / (e1 - e0));
  return t * t * t * (t * (t * 6 - 15) + 10);
}

/**
 * Solve discrete 32-bone Elastica angle profile theta[0..31] so the sheet emerges smoothly
 * from the binding gutter, forms a natural editorial arch, flattens onto the resting stack
 * for u >= flatStartU, and lands at exact `zTarget` to < 1e-14 m precision.
 */
function solveBoneArchTheta(z0, zTarget, side, archDeg, flatStartU = 0.76) {
  const sgn = side === "right" ? +1.0 : -1.0;
  const thetaEnd = side === "right" ? 0.0 : Math.PI;
  const archRad = (archDeg * Math.PI) / 180.0;

  const baseNoDip = new Float64Array(N_SHEET_BONES);
  const dipKernel = new Float64Array(N_SHEET_BONES);

  for (let k = 0; k < N_SHEET_BONES; k++) {
    const u = BONE_S_MIDS[k] / PAGE_W;
    const uArch = Math.min(1.0, Math.max(0.0, u / 0.34));
    const archEnv = 0.5 * (1.0 + Math.cos(Math.PI * uArch));
    baseNoDip[k] = thetaEnd + sgn * archRad * archEnv;

    const dipU = clamp01((u - 0.16) / (flatStartU - 0.16));
    const s = Math.sin(Math.PI * dipU);
    dipKernel[k] = s * s * (1.0 - smoothstep(flatStartU - 0.04, flatStartU, u));
  }

  const endZ = (dipAmp) => {
    let z = z0;
    for (let k = 0; k < N_SHEET_BONES; k++) {
      z += BONE_DS[k] * Math.sin(baseNoDip[k] - sgn * dipAmp * dipKernel[k]);
    }
    return z;
  };

  let lo = -1.45;
  let hi = +1.45;
  let fLo = endZ(lo) - zTarget;
  for (let it = 0; it < 46; it++) {
    const mid = 0.5 * (lo + hi);
    const fMid = endZ(mid) - zTarget;
    if ((fLo <= 0 && fMid <= 0) || (fLo > 0 && fMid > 0)) {
      lo = mid;
      fLo = fMid;
    } else {
      hi = mid;
    }
  }
  const dipBest = 0.5 * (lo + hi);
  const out = new Float64Array(N_SHEET_BONES);
  for (let k = 0; k < N_SHEET_BONES; k++) {
    out[k] = baseNoDip[k] - sgn * dipBest * dipKernel[k];
  }
  return out;
}

const _qY = new THREE.Quaternion();
const _qBaseSheet = new THREE.Quaternion(0, 0, -Math.SQRT1_2, Math.SQRT1_2); // Qz(-90 deg)
const _qBaseSpine = new THREE.Quaternion(Math.SQRT1_2, 0, 0, Math.SQRT1_2);  // Qx(+90 deg)
const _yAxis = new THREE.Vector3(0, 1, 0);

export class EditorialMagazineController {
  /**
   * @param {THREE.Object3D} sceneRoot Cloned or loaded `gltf.scene` containing `Magazine_Root`.
   * @param {object} [options]
   * @param {number} [options.pageCount=56] Even number of printed interior pages (2 pages = 1 physical leaf).
   * @param {number} [options.leafThickness=0.000145] Physical interior leaf thickness in meters.
   * @param {number} [options.coverThickness=0.000320] Physical cover stock thickness in meters.
   * @param {number} [options.airGap=0.000018] Inter-sheet stacked air cushion in meters.
   * @param {number} [options.maxCachedPages=16] Maximum simultaneously resident page textures in GPU LRU cache.
   */
  constructor(sceneRoot, options = {}) {
    this.root = sceneRoot.getObjectByName("Magazine_Root") || sceneRoot;
    this.maxCachedPages = options.maxCachedPages ?? 16;

    // Collect named mesh groups and bone joints
    this.groups = {};
    this.primitivesByGroup = {};
    this.bones = {};
    this.materials = {};
    this._ownedMaterials = [];
    this._pageArtworkSources = new Map();
    this._pageArtworkProvider = null;
    this._lruTextures = new Map(); // key -> { tex, owned }
    this._coverTextures = new Map();

    const groupNames = [
      "Binding",
      "Cover_Front",
      "Cover_Back",
      "Pages_Block_Left",
      "Pages_Block_Right",
      "Page_Left",
      "Page_Right",
      "Page_Turning",
    ];

    // Clone mutable materials per controller instance so multiple magazines never leak state
    const clonedMatMap = new Map();
    const mutableNames = new Set(Object.values(ARTWORK_SLOTS));

    this.root.traverse((obj) => {
      if (obj.isBone) {
        this.bones[obj.name] = obj;
      }
      for (const g of groupNames) {
        if (obj.name === g && !obj.isBone && !this.groups[g]) {
          this.groups[g] = obj;
        }
      }
      if (obj.isMesh) {
        const base = obj.name.replace(/_\d+$/, "");
        if (!this.primitivesByGroup[base]) this.primitivesByGroup[base] = [];
        this.primitivesByGroup[base].push(obj);

        const replaceMat = (m) => {
          if (!mutableNames.has(m.name)) {
            this.materials[m.name] = m;
            return m;
          }
          if (!clonedMatMap.has(m.name)) {
            const c = m.clone();
            c.name = m.name;
            clonedMatMap.set(m.name, c);
            this._ownedMaterials.push(c);
            this.materials[c.name] = c;
          }
          return clonedMatMap.get(m.name);
        };
        obj.material = Array.isArray(obj.material) ? obj.material.map(replaceMat) : replaceMat(obj.material);
      }
    });

    // State machine
    // state: 'CLOSED_FRONT' | 'OPENING_FRONT' | 'CLOSING_FRONT' | 'OPEN_SPREAD' | 'TURNING' | 'CLOSING_BACK' | 'OPENING_BACK' | 'CLOSED_BACK'
    this.leafThickness = options.leafThickness ?? REF_T_PAGE;
    this.coverThickness = options.coverThickness ?? REF_T_COVER;
    this.airGap = options.airGap ?? 0.000018;
    this.pageCount = 56;
    this.leafCount = 28;
    this.leftLeaves = 0;         // Committed number of physical leaves on left side (0 .. leafCount)
    this._turnBaseLeaves = 0;    // Active sheet base index in [0 .. leafCount - 1] during TURNING
    this.state = "CLOSED_FRONT";
    this.transitionProgress = 0; // Normalized [0, 1] for active cover or page transition
    this.turnDirection = 0;      // +1 forward (right -> left), -1 backward (left -> right), 0 idle
    this.isPaused = false;       // Explicit pause flag for interactive turn control

    this.setPageCount(options.pageCount ?? 56);
    this._applyPose();
  }

  get effectiveLeafPitch() {
    return this.leafThickness + this.airGap;
  }

  get spineSpanMeters() {
    // Total centerline-to-centerline spine span across Cover_Back + all interior leaves + Cover_Front
    return this.coverThickness + this.leafCount * this.effectiveLeafPitch + 2 * this.airGap;
  }

  /**
   * Configure total printed interior page count (2 printed pages = 1 double-sided physical leaf).
   * Front and back covers are separate physical sheets (4 cover surfaces).
   */
  setPageCount(interiorPageCount) {
    const n = Math.floor(Number(interiorPageCount));
    if (!Number.isFinite(n) || n < 2 || n % 2 !== 0) {
      throw new RangeError(`interiorPageCount must be an even integer >= 2 (got ${interiorPageCount})`);
    }
    if (this.state === "TURNING") {
      this.cancelTurn();
    }
    if (this.pageCount !== n) {
      this._clearLruPageTextures();
    }
    this.pageCount = n;
    this.leafCount = n / 2;
    this.leftLeaves = Math.min(this.leftLeaves, this.leafCount);
    if (this.state === "CLOSED_FRONT") this.leftLeaves = 0;
    if (this.state === "CLOSED_BACK") this.leftLeaves = this.leafCount;
    this._updateSheetBaseMorphs();
    this._syncVisibleArtworks();
    this._applyPose();
    return this;
  }

  setPaperThickness({ leafMeters, coverMeters, airGapMeters } = {}) {
    if (leafMeters !== undefined) {
      if (!(leafMeters > 0.00003 && leafMeters <= 0.001)) throw new RangeError("Invalid leafMeters");
      this.leafThickness = leafMeters;
    }
    if (coverMeters !== undefined) {
      if (!(coverMeters > 0.00008 && coverMeters <= 0.002)) throw new RangeError("Invalid coverMeters");
      this.coverThickness = coverMeters;
    }
    if (airGapMeters !== undefined && airGapMeters >= 0) {
      this.airGap = airGapMeters;
    }
    this._updateSheetBaseMorphs();
    this._applyPose();
    return this;
  }

  _setGroupMorphThickness(groupName, targetThickness, refThickness) {
    const prims = this.primitivesByGroup[groupName] || [];
    const w = (targetThickness / refThickness) - 1.0;
    for (const p of prims) {
      if (p.morphTargetInfluences && p.morphTargetInfluences.length > 0) {
        p.morphTargetInfluences[0] = w;
      }
    }
  }

  _setGroupVisible(groupName, vis) {
    if (this.groups[groupName]) this.groups[groupName].visible = vis;
    for (const p of this.primitivesByGroup[groupName] || []) p.visible = vis;
  }

  _updateSheetBaseMorphs() {
    this._setGroupMorphThickness("Cover_Front", this.coverThickness, REF_T_COVER);
    this._setGroupMorphThickness("Cover_Back", this.coverThickness, REF_T_COVER);
    this._setGroupMorphThickness("Page_Left", this.leafThickness, REF_T_PAGE);
    this._setGroupMorphThickness("Page_Right", this.leafThickness, REF_T_PAGE);
    this._setGroupMorphThickness("Page_Turning", this.leafThickness, REF_T_PAGE);
  }

  // -------------------------------------------------------------------------
  // Artwork Management & Bounded LRU GPU Texture Cache
  // -------------------------------------------------------------------------
  _clearLruPageTextures() {
    for (const entry of this._lruTextures.values()) {
      if (entry.owned) entry.tex.dispose();
    }
    this._lruTextures.clear();
  }

  setPageArtworkProvider(providerFn) {
    this._clearLruPageTextures();
    this._pageArtworkProvider = providerFn;
    this._syncVisibleArtworks();
    return this;
  }

  setPageArtwork(pageNumber, source) {
    const p = Math.floor(Number(pageNumber));
    if (p < 1 || p > this.pageCount) {
      throw new RangeError(`pageNumber ${pageNumber} out of range [1, ${this.pageCount}]`);
    }
    this._pageArtworkSources.set(p, source);
    // Invalidate cached GPU texture if already materialized
    const key = `page_${p}`;
    if (this._lruTextures.has(key)) {
      const entry = this._lruTextures.get(key);
      if (entry.owned) entry.tex.dispose();
      this._lruTextures.delete(key);
    }
    this._syncVisibleArtworks();
    return this;
  }

  setCoverArtwork(side, source) {
    const matName = ARTWORK_SLOTS[side];
    if (!matName || !side.startsWith("front") && !side.startsWith("back")) {
      throw new RangeError(`Unknown cover slot '${side}'. Expected frontOuter | frontInner | backOuter | backInner.`);
    }
    const prev = this._coverTextures.get(side);
    if (prev && prev.owned) prev.tex.dispose();
    if (!source) {
      this._coverTextures.delete(side);
      this._bindMaterialMap(matName, null);
      return this;
    }
    const entry = this._materializeTexture(source);
    this._coverTextures.set(side, entry);
    this._bindMaterialMap(matName, entry.tex);
    return this;
  }

  _materializeTexture(source) {
    if (source && source.isTexture) {
      source.flipY = false;
      source.colorSpace = THREE.SRGBColorSpace;
      return { tex: source, owned: false };
    }
    const tex = new THREE.CanvasTexture(source);
    tex.flipY = false;
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.needsUpdate = true;
    return { tex, owned: true };
  }

  _getPageTexture(pageNumber, activeProtectedKeys) {
    if (pageNumber < 1 || pageNumber > this.pageCount) return null;
    const key = `page_${pageNumber}`;
    if (this._lruTextures.has(key)) {
      const entry = this._lruTextures.get(key);
      this._lruTextures.delete(key);
      this._lruTextures.set(key, entry);
      return entry.tex;
    }
    let src = this._pageArtworkSources.get(pageNumber);
    if (!src && this._pageArtworkProvider) {
      src = this._pageArtworkProvider(pageNumber);
    }
    if (!src) return null;

    const entry = this._materializeTexture(src);
    this._lruTextures.set(key, entry);

    // Evict oldest unused page textures beyond maxCachedPages
    if (this._lruTextures.size > this.maxCachedPages) {
      for (const [oldKey, oldEntry] of this._lruTextures.entries()) {
        if (this._lruTextures.size <= this.maxCachedPages) break;
        if (activeProtectedKeys && activeProtectedKeys.has(oldKey)) continue;
        if (oldEntry.owned) oldEntry.tex.dispose();
        this._lruTextures.delete(oldKey);
      }
    }
    return entry.tex;
  }

  _bindMaterialMap(matName, tex) {
    const mat = this.materials[matName];
    if (!mat) return;
    if (mat.map === tex) return;
    mat.map = tex || null;
    if (tex) {
      mat.color.setHex(0xffffff);
    } else {
      mat.color.setHex(matName.includes("Cover") ? 0xfaf7f2 : 0xf7f4ee);
    }
    mat.needsUpdate = true;
  }

  get cachedTextureCount() {
    return this._lruTextures.size;
  }

  // -------------------------------------------------------------------------
  // Exact Leaf Accounting & Visible Surface Mapping
  // -------------------------------------------------------------------------
  /**
   * Compute exact physical leaf distribution (guaranteed sum === this.leafCount, active leaf NEVER double-counted!).
   */
  getLeafAccounting() {
    const N = this.leafCount;
    if (this.state === "CLOSED_FRONT" || this.state === "OPENING_FRONT" || this.state === "CLOSING_FRONT") {
      const rVis = N >= 1 ? 1 : 0;
      const rInact = Math.max(0, N - rVis);
      return {
        leftInactiveLeaves: 0,
        leftVisibleLeaf: 0,
        activeTurningLeaf: 0,
        rightVisibleLeaf: rVis ? 1 : 0,
        rightInactiveLeaves: rInact,
        totalAccountedLeaves: rVis + rInact,
        visibleLeftPage: this.state === "CLOSED_FRONT" ? null : 0, // 0 = Inside Front Cover
        visibleRightPage: this.state === "CLOSED_FRONT" ? null : 1,
        turningFrontPage: null,
        turningBackPage: null,
      };
    }

    if (this.state === "CLOSED_BACK" || this.state === "CLOSING_BACK" || this.state === "OPENING_BACK") {
      const lVis = N >= 1 ? 1 : 0;
      const lInact = Math.max(0, N - lVis);
      return {
        leftInactiveLeaves: lInact,
        leftVisibleLeaf: lVis ? N : 0,
        activeTurningLeaf: 0,
        rightVisibleLeaf: 0,
        rightInactiveLeaves: 0,
        totalAccountedLeaves: lInact + lVis,
        visibleLeftPage: this.state === "CLOSED_BACK" ? null : 2 * N,
        visibleRightPage: this.state === "CLOSED_BACK" ? null : 2 * N + 1, // Inside Back Cover
        turningFrontPage: null,
        turningBackPage: null,
      };
    }

    if (this.state === "TURNING") {
      // `_turnBaseLeaves` is pinned when the turn begins so activeLeaf === _turnBaseLeaves + 1 stays invariant
      // across mid-turn reversals (`reverseTurnDirection`, `beginTurnForward`, `beginTurnBackward`)!
      const baseK = this._turnBaseLeaves;
      const activeLeaf = baseK + 1; // 1-based leaf index in [1..N]
      const leftRest = baseK;       // Total resting leaves on left [0..N-1]
      const rightRest = N - baseK - 1; // Total resting leaves on right [0..N-1]

      const lVis = leftRest >= 1 ? 1 : 0;
      const lInact = Math.max(0, leftRest - lVis);
      const rVis = rightRest >= 1 ? 1 : 0;
      const rInact = Math.max(0, rightRest - rVis);

      return {
        leftInactiveLeaves: lInact,
        leftVisibleLeaf: lVis ? leftRest : 0,
        activeTurningLeaf: activeLeaf,
        rightVisibleLeaf: rVis ? baseK + 2 : 0,
        rightInactiveLeaves: rInact,
        totalAccountedLeaves: lInact + lVis + 1 + rVis + rInact,
        visibleLeftPage: lVis ? 2 * leftRest : 0, // 0 = Inside Front Cover
        visibleRightPage: rVis ? 2 * (baseK + 1) + 1 : 2 * N + 1, // 2N+1 = Inside Back Cover
        turningFrontPage: 2 * activeLeaf - 1,
        turningBackPage: 2 * activeLeaf,
      };
    }

    // Idle OPEN_SPREAD at committed `k = this.leftLeaves` in [0..N]
    const k = this.leftLeaves;
    const rightRest = N - k;
    const lVis = k >= 1 ? 1 : 0;
    const lInact = Math.max(0, k - lVis);
    const rVis = rightRest >= 1 ? 1 : 0;
    const rInact = Math.max(0, rightRest - rVis);

    return {
      leftInactiveLeaves: lInact,
      leftVisibleLeaf: lVis ? k : 0,
      activeTurningLeaf: 0,
      rightVisibleLeaf: rVis ? k + 1 : 0,
      rightInactiveLeaves: rInact,
      totalAccountedLeaves: lInact + lVis + rVis + rInact,
      visibleLeftPage: lVis ? 2 * k : 0,
      visibleRightPage: rVis ? 2 * k + 1 : 2 * N + 1,
      turningFrontPage: null,
      turningBackPage: null,
    };
  }

  _syncVisibleArtworks() {
    const acc = this.getLeafAccounting();
    const protectedKeys = new Set();
    for (const p of [acc.visibleLeftPage, acc.visibleRightPage, acc.turningFrontPage, acc.turningBackPage]) {
      if (p && p >= 1 && p <= this.pageCount) protectedKeys.add(`page_${p}`);
    }

    const texL = acc.visibleLeftPage >= 1 && acc.visibleLeftPage <= this.pageCount
      ? this._getPageTexture(acc.visibleLeftPage, protectedKeys) : null;
    const texR = acc.visibleRightPage >= 1 && acc.visibleRightPage <= this.pageCount
      ? this._getPageTexture(acc.visibleRightPage, protectedKeys) : null;
    const texTF = acc.turningFrontPage
      ? this._getPageTexture(acc.turningFrontPage, protectedKeys) : null;
    const texTB = acc.turningBackPage
      ? this._getPageTexture(acc.turningBackPage, protectedKeys) : null;

    this._bindMaterialMap(ARTWORK_SLOTS.pageLeft, texL);
    this._bindMaterialMap(ARTWORK_SLOTS.pageRight, texR);
    this._bindMaterialMap(ARTWORK_SLOTS.turningFront, texTF);
    this._bindMaterialMap(ARTWORK_SLOTS.turningBack, texTB);

    // Preload immediate neighbor pages within LRU budget
    const centerPage = acc.turningFrontPage || acc.visibleRightPage || acc.visibleLeftPage || 1;
    for (const dp of [-2, -1, +1, +2]) {
      const np = centerPage + dp;
      if (np >= 1 && np <= this.pageCount && this._lruTextures.size < this.maxCachedPages) {
        this._getPageTexture(np, protectedKeys);
      }
    }
  }

  // -------------------------------------------------------------------------
  // Navigation & Interactive Interruption API (Sections 7, 13, 14, 16)
  // -------------------------------------------------------------------------
  openFrontCover(progress = 1.0) {
    if (this.state !== "CLOSED_FRONT" && this.state !== "OPENING_FRONT" && this.state !== "CLOSING_FRONT") {
      if (this.state === "OPEN_SPREAD" && this.leftLeaves === 0 && progress >= 1.0) return true;
      return false;
    }
    const p = clamp01(progress);
    this.leftLeaves = 0;
    if (p >= 1.0) {
      this.state = "OPEN_SPREAD";
      this.transitionProgress = 0;
    } else if (p <= 0.0) {
      this.state = "CLOSED_FRONT";
      this.transitionProgress = 0;
    } else {
      this.state = "OPENING_FRONT";
      this.transitionProgress = p;
    }
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  closeFrontCover(progress = 1.0) {
    if (this.state === "TURNING") this.cancelTurn();
    if (this.state === "OPEN_SPREAD" && this.leftLeaves !== 0) return false;
    if (this.state !== "OPEN_SPREAD" && this.state !== "CLOSING_FRONT" && this.state !== "OPENING_FRONT" && this.state !== "CLOSED_FRONT") {
      return false;
    }
    const p = clamp01(progress);
    this.leftLeaves = 0;
    this.isPaused = false;
    if (p >= 1.0) {
      this.state = "CLOSED_FRONT";
      this.transitionProgress = 0;
    } else if (p <= 0.0) {
      this.state = "OPEN_SPREAD";
      this.transitionProgress = 0;
    } else {
      this.state = "CLOSING_FRONT";
      this.transitionProgress = p;
    }
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  closeBackCover(progress = 1.0) {
    if (this.state === "TURNING") this.cancelTurn();
    if (this.state === "OPEN_SPREAD" && this.leftLeaves !== this.leafCount) return false;
    if (this.state !== "OPEN_SPREAD" && this.state !== "CLOSING_BACK" && this.state !== "OPENING_BACK" && this.state !== "CLOSED_BACK") {
      return false;
    }
    const p = clamp01(progress);
    this.leftLeaves = this.leafCount;
    this.isPaused = false;
    if (p >= 1.0) {
      this.state = "CLOSED_BACK";
      this.transitionProgress = 0;
    } else if (p <= 0.0) {
      this.state = "OPEN_SPREAD";
      this.transitionProgress = 0;
    } else {
      this.state = "CLOSING_BACK";
      this.transitionProgress = p;
    }
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  openBackCover(progress = 1.0) {
    if (this.state !== "CLOSED_BACK" && this.state !== "CLOSING_BACK" && this.state !== "OPENING_BACK") {
      if (this.state === "OPEN_SPREAD" && this.leftLeaves === this.leafCount && progress >= 1.0) return true;
      return false;
    }
    const p = clamp01(progress);
    this.leftLeaves = this.leafCount;
    this.isPaused = false;
    if (p >= 1.0) {
      this.state = "OPEN_SPREAD";
      this.transitionProgress = 0;
    } else if (p <= 0.0) {
      this.state = "CLOSED_BACK";
      this.transitionProgress = 0;
    } else {
      this.state = "OPENING_BACK";
      this.transitionProgress = p;
    }
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  beginTurnForward() {
    if (this.state === "TURNING") {
      this.isPaused = false;
      if (this.turnDirection === -1) {
        return this.reverseTurnDirection();
      }
      return true;
    }
    if (this.state !== "OPEN_SPREAD" || this.leftLeaves >= this.leafCount) {
      return false; // Boundary clamped!
    }
    this.state = "TURNING";
    this._turnBaseLeaves = this.leftLeaves;
    this.turnDirection = +1;
    this.transitionProgress = 0.0;
    this.isPaused = false;
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  beginTurnBackward() {
    if (this.state === "TURNING") {
      this.isPaused = false;
      if (this.turnDirection === +1) {
        return this.reverseTurnDirection();
      }
      return true;
    }
    if (this.state !== "OPEN_SPREAD" || this.leftLeaves <= 0) {
      return false; // Boundary clamped!
    }
    this.state = "TURNING";
    this._turnBaseLeaves = this.leftLeaves - 1;
    this.turnDirection = -1;
    this.transitionProgress = 0.0; // Normalized backward progress 0 (on left) -> 1 (on right)
    this.isPaused = false;
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  pauseTurn() {
    if (this.state !== "TURNING") return false;
    this.isPaused = true;
    return true;
  }

  resumeTurn() {
    if (this.state !== "TURNING") return false;
    this.isPaused = false;
    return true;
  }

  /**
   * Set normalized turn progress in [0, 1] along the current turnDirection (+1 right->left, -1 left->right).
   * Page index `this.leftLeaves` does NOT change until `commitTurn()` is called!
   */
  setTurnProgress(progress) {
    if (this.state !== "TURNING") return false;
    this.transitionProgress = clamp01(progress);
    this._applyPose();
    return true;
  }

  /**
   * Unified normalized progress setter [0, 1] for any active cover or page transition.
   */
  setProgress(progress) {
    const p = clamp01(progress);
    if (this.state === "TURNING") return this.setTurnProgress(p);
    if (this.state === "OPENING_FRONT") return this.openFrontCover(p);
    if (this.state === "CLOSING_FRONT") return this.closeFrontCover(p);
    if (this.state === "CLOSING_BACK") return this.closeBackCover(p);
    if (this.state === "OPENING_BACK") return this.openBackCover(p);
    return false;
  }

  /**
   * Reverse an in-flight incomplete turn smoothly without any geometric, leaf-accounting, or artwork discontinuity!
   */
  reverseTurnDirection() {
    if (this.state !== "TURNING") return false;
    // Physical right->left parameter u = (dir === +1) ? progress : (1 - progress).
    // Flipping direction inverts `transitionProgress` while keeping `_turnBaseLeaves` (active turning sheet)
    // and `this.leftLeaves` (pre-turn committed spread index) invariant until `commitTurn()`.
    this.transitionProgress = 1.0 - this.transitionProgress;
    this.turnDirection = -this.turnDirection;
    this._applyPose();
    return true;
  }

  commitTurn() {
    if (this.state !== "TURNING") return false;
    if (this.turnDirection === +1) {
      this.leftLeaves = Math.min(this.leafCount, this._turnBaseLeaves + 1);
    } else if (this.turnDirection === -1) {
      this.leftLeaves = Math.max(0, this._turnBaseLeaves);
    }
    this.state = "OPEN_SPREAD";
    this.turnDirection = 0;
    this.transitionProgress = 0;
    this.isPaused = false;
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  cancelTurn() {
    if (this.state !== "TURNING") return false;
    this.state = "OPEN_SPREAD";
    this.turnDirection = 0;
    this.transitionProgress = 0;
    this.isPaused = false;
    this._syncVisibleArtworks();
    this._applyPose();
    return true;
  }

  // Convenience atomic helpers matching Section 16 conceptual controls
  open() {
    return this.state === "CLOSED_BACK" ? this.openBackCover(1.0) : this.openFrontCover(1.0);
  }

  close() {
    return this.leftLeaves === this.leafCount ? this.closeBackCover(1.0) : this.closeFrontCover(1.0);
  }

  next() {
    if (!this.beginTurnForward()) return false;
    this.setTurnProgress(1.0);
    return this.commitTurn();
  }

  previous() {
    if (!this.beginTurnBackward()) return false;
    this.setTurnProgress(1.0);
    return this.commitTurn();
  }

  // -------------------------------------------------------------------------
  // Exact 233-Joint Skeletal Elastica & Morph-Stack Pose Application
  // -------------------------------------------------------------------------
  _setChainBones(chainPrefix, x0, z0, thetaArr) {
    const rootBone = this.bones[`${chainPrefix}_00`];
    if (!rootBone) return;
    rootBone.position.set(x0, 0, z0);

    // Root bone rotation inside Rig_Origin: Ry(-theta[0]) * Qz(-90 deg)
    _qY.setFromAxisAngle(_yAxis, -thetaArr[0]);
    rootBone.quaternion.copy(_qY).multiply(_qBaseSheet);

    for (let k = 1; k < N_SHEET_BONES; k++) {
      const b = this.bones[`${chainPrefix}_${String(k).padStart(2, "0")}`];
      const dTheta = thetaArr[k] - thetaArr[k - 1];
      const half = 0.5 * dTheta;
      b.quaternion.set(Math.sin(half), 0, 0, Math.cos(half));
    }
  }

  _setSpineBones(mode, qProgress, spineSpan) {
    // mode: 'FRONT' (q=0 vertical at X=0 -> q=1 flat centered on tabletop)
    //       'BACK'  (q=0 flat centered on tabletop -> q=1 vertical at X=0 with Cover_Front anchored on tabletop
    //                at z=zBase and Cover_Back on TOP at z=zBase+spineSpan!)
    const du = spineSpan / N_SPINE_BONES;
    const zBase = 0.5 * this.coverThickness;
    const thArr = new Float64Array(N_SPINE_BONES);

    let xStart = 0;
    let zStart = zBase;

    if (mode === "FRONT") {
      xStart = qProgress * 0.5 * spineSpan;
      zStart = zBase;
      for (let i = 0; i < N_SPINE_BONES; i++) {
        const w = (i + 0.5) / N_SPINE_BONES;
        thArr[i] = 0.5 * Math.PI * (1.0 + qProgress) - 0.08 * qProgress * Math.sin(2.0 * Math.PI * w);
      }
    } else {
      // Compute exact open-state u=spineSpan endpoint so q=0 matches FRONT(1.0) to 1e-16 m,
      // and keep u=spineSpan (Cover_Front) grounded on zEnd = zBase throughout q in [0, 1]!
      let dxOpen = 0;
      for (let i = 0; i < N_SPINE_BONES; i++) {
        const w = (i + 0.5) / N_SPINE_BONES;
        dxOpen += du * Math.cos(Math.PI - 0.08 * Math.sin(2.0 * Math.PI * w));
      }
      const xEndOpen = 0.5 * spineSpan + dxOpen;

      let dxSum = 0;
      let dzSum = 0;
      for (let i = 0; i < N_SPINE_BONES; i++) {
        const w = (i + 0.5) / N_SPINE_BONES;
        thArr[i] = Math.PI + 0.5 * Math.PI * qProgress - 0.08 * (1.0 - qProgress) * Math.sin(2.0 * Math.PI * w);
        dxSum += du * Math.cos(thArr[i]);
        dzSum += du * Math.sin(thArr[i]);
      }
      const xEnd = (1.0 - qProgress) * xEndOpen;
      const zEnd = zBase;
      xStart = xEnd - dxSum;
      zStart = zEnd - dzSum;
    }

    const sp0 = this.bones["Spine_00"];
    sp0.position.set(xStart, 0, zStart);
    _qY.setFromAxisAngle(_yAxis, -(thArr[0] - 0.5 * Math.PI));
    sp0.quaternion.copy(_qY).multiply(_qBaseSpine);

    for (let i = 1; i < N_SPINE_BONES; i++) {
      const sb = this.bones[`Spine_${String(i).padStart(2, "0")}`];
      sb.position.set(0, du, 0);
      const dTh = thArr[i] - thArr[i - 1];
      const half = 0.5 * dTh;
      sb.quaternion.set(0, 0, Math.sin(half), Math.cos(half));
    }

    let xEnd = xStart;
    let zEnd = zStart;
    for (let i = 0; i < N_SPINE_BONES; i++) {
      xEnd += du * Math.cos(thArr[i]);
      zEnd += du * Math.sin(thArr[i]);
    }
    return { xBack: xStart, zBack: zStart, xFront: xEnd, zFront: zEnd };
  }

  _applyPose() {
    const acc = this.getLeafAccounting();
    const tCov = this.coverThickness;
    const tLeaf = this.leafThickness;
    const gap = Math.max(this.airGap, 0.000045);
    const span = this.spineSpanMeters;
    const flatRight = new Float64Array(N_SHEET_BONES);
    const flatLeft = new Float64Array(N_SHEET_BONES).fill(Math.PI);

    const halfCradle = Math.max(0.0012, 0.36 * span);
    const openArchForLeaves = (cnt) => Math.min(26.0, 15.5 + 0.14 * cnt);

    // 1. CLOSED_FRONT, OPENING_FRONT, or CLOSING_FRONT (pOpen in [0, 1] where 0=closed front, 1=open first spread)
    if (this.state === "CLOSED_FRONT" || this.state === "OPENING_FRONT" || this.state === "CLOSING_FRONT") {
      const pOpen =
        this.state === "CLOSED_FRONT"
          ? 0.0
          : this.state === "OPENING_FRONT"
          ? this.transitionProgress
          : 1.0 - this.transitionProgress;
      const qSp = smootherstep(0.18, 0.92, pOpen);
      const spEnds = this._setSpineBones("FRONT", qSp, span);

      this._setGroupVisible("Cover_Front", true);
      this._setGroupVisible("Cover_Back", true);
      this._setGroupVisible("Page_Left", false);
      this._setGroupVisible("Pages_Block_Left", false);
      this._setGroupVisible("Page_Turning", false);

      this._setChainBones("Cover_Back", spEnds.xBack, spEnds.zBack, flatRight);

      // Right stack (all N leaves on right side — matches OPEN_SPREAD k=0 identically at qSp=1.0!)
      const hasBlockR = acc.rightInactiveLeaves > 0;
      const hasPageR = acc.rightVisibleLeaf > 0;
      const hBlockR = acc.rightInactiveLeaves * this.effectiveLeafPitch;
      this._setGroupVisible("Pages_Block_Right", hasBlockR);
      if (hasBlockR) {
        this._setGroupMorphThickness("Pages_Block_Right", hBlockR, REF_T_BLOCK_R);
      }

      const archOpenR = openArchForLeaves(acc.rightInactiveLeaves + (hasPageR ? 1 : 0));
      const cosOpenR = Math.cos(((archOpenR + 1.0) * Math.PI) / 180.0);
      const archCur = (1.0 - qSp) * 0.45 + qSp * archOpenR;
      const flatU = (1.0 - qSp) * 0.62 + qSp * 0.76;
      const xStack = (1.0 - qSp) * 0.00028 + qSp * halfCradle;

      let zRightTopClosed = tCov;
      let zRightTopOpen = tCov;
      if (hasBlockR) {
        const zBrClosed = zRightTopClosed + gap + 0.5 * hBlockR;
        const zBrOpen = zRightTopOpen + (0.5 * hBlockR) / cosOpenR + gap;
        const zBrTarget = (1.0 - qSp) * zBrClosed + qSp * zBrOpen;
        const zBrRoot = zBrTarget + 0.00004 * qSp;
        const thBr = solveBoneArchTheta(zBrRoot, zBrTarget, "right", archCur, flatU);
        this._setChainBones("Pages_Block_Right", xStack, zBrRoot, thBr);
        zRightTopClosed = zBrClosed + 0.5 * hBlockR;
        zRightTopOpen = zBrOpen + (0.5 * hBlockR) / cosOpenR;
      }

      this._setGroupVisible("Page_Right", hasPageR);
      const zPrClosed = zRightTopClosed + gap + 0.5 * tLeaf;
      const zPrOpen = zRightTopOpen + (0.5 * tLeaf) / cosOpenR + gap;
      const zPrTarget = (1.0 - qSp) * zPrClosed + qSp * zPrOpen;
      const zPrRoot = zPrTarget + 0.00004 * qSp;
      const thPr = solveBoneArchTheta(zPrRoot, zPrTarget, "right", archCur, flatU);
      this._setChainBones("Page_Right", xStack, zPrRoot, thPr);

      // Cover_Front lifts smoothly from top of right stack (pOpen=0) across spine onto left tabletop (pOpen=1)!
      const zCfClosed = zPrClosed + 0.5 * tLeaf + gap + 0.5 * tCov;
      if (pOpen <= 0.0) {
        const thCf0 = solveBoneArchTheta(spEnds.zFront, zCfClosed, "right", 0.85, 0.68);
        this._setChainBones("Cover_Front", spEnds.xFront, spEnds.zFront, thCf0);
      } else if (pOpen >= 1.0) {
        this._setChainBones("Cover_Front", spEnds.xFront, spEnds.zFront, flatLeft);
      } else {
        const thCf0 = solveBoneArchTheta(spEnds.zFront, zCfClosed, "right", 0.85, 0.68);
        const lift = pOpen < 0.56 ? Math.pow(Math.sin((Math.PI * pOpen) / 0.56), 1.25) : 0.0;
        const land = pOpen > 0.44 ? Math.pow(Math.sin((Math.PI * (pOpen - 0.44)) / 0.56), 1.35) : 0.0;
        const thCf = new Float64Array(N_SHEET_BONES);
        for (let k = 0; k < N_SHEET_BONES; k++) {
          const u = BONE_S_MIDS[k] / PAGE_W;
          const uf = Math.pow(smoothstep(0.015, 0.92, u), 1.15);
          thCf[k] = (1.0 - pOpen) * thCf0[k] + pOpen * Math.PI + ((34 * Math.PI) / 180) * lift * uf - ((32 * Math.PI) / 180) * land * uf;
        }
        for (let guard = 0; guard < 30; guard++) {
          let zCur = spEnds.zFront;
          let minZ = +Infinity;
          for (let k = 0; k < N_SHEET_BONES; k++) {
            zCur += BONE_DS[k] * Math.sin(thCf[k]);
            if (zCur < minZ) minZ = zCur;
          }
          if (minZ >= 0.5 * tCov - 1e-6) break;
          for (let k = 0; k < N_SHEET_BONES; k++) {
            thCf[k] -= 0.012 * smoothstep(0.015, 0.92, BONE_S_MIDS[k] / PAGE_W);
          }
        }
        this._setChainBones("Cover_Front", spEnds.xFront, spEnds.zFront, thCf);
      }
      this.root.updateMatrixWorld(true);
      return;
    }

    // 2. CLOSED_BACK, CLOSING_BACK, or OPENING_BACK (pClose in [0, 1], where 0=last open spread, 1=closed back cover!)
    if (this.state === "CLOSED_BACK" || this.state === "CLOSING_BACK" || this.state === "OPENING_BACK") {
      const pClose =
        this.state === "CLOSED_BACK"
          ? 1.0
          : this.state === "CLOSING_BACK"
          ? this.transitionProgress
          : 1.0 - this.transitionProgress;
      const qSp = smootherstep(0.08, 0.85, pClose);
      const spEnds = this._setSpineBones("BACK", qSp, span);

      this._setGroupVisible("Cover_Front", true);
      this._setGroupVisible("Cover_Back", true);
      this._setGroupVisible("Page_Right", false);
      this._setGroupVisible("Pages_Block_Right", false);
      this._setGroupVisible("Page_Turning", false);

      this._setChainBones("Cover_Front", spEnds.xFront, spEnds.zFront, flatLeft);

      // Left stack (all N leaves on left side — matches OPEN_SPREAD k=N identically at qSp=0.0!)
      const hasBlockL = acc.leftInactiveLeaves > 0;
      const hasPageL = acc.leftVisibleLeaf > 0;
      const hBlockL = acc.leftInactiveLeaves * this.effectiveLeafPitch;
      this._setGroupVisible("Pages_Block_Left", hasBlockL);
      if (hasBlockL) {
        this._setGroupMorphThickness("Pages_Block_Left", hBlockL, REF_T_BLOCK_L);
      }

      const archOpenL = openArchForLeaves(acc.leftInactiveLeaves + (hasPageL ? 1 : 0));
      const cosOpenL = Math.cos(((archOpenL + 1.0) * Math.PI) / 180.0);
      const archCur = (1.0 - qSp) * archOpenL + qSp * 0.45;
      const flatU = (1.0 - qSp) * 0.76 + qSp * 0.62;
      const xStackL = -((1.0 - qSp) * halfCradle + qSp * 0.00028);

      let zLeftTopOpen = tCov;
      let zLeftTopClosed = tCov;
      if (hasBlockL) {
        const zBlOpen = zLeftTopOpen + (0.5 * hBlockL) / cosOpenL + gap;
        const zBlClosed = zLeftTopClosed + gap + 0.5 * hBlockL;
        const zBlTarget = (1.0 - qSp) * zBlOpen + qSp * zBlClosed;
        const zBlRoot = zBlTarget + 0.00004 * (1.0 - qSp);
        const thBl = solveBoneArchTheta(zBlRoot, zBlTarget, "left", archCur, flatU);
        this._setChainBones("Pages_Block_Left", xStackL, zBlRoot, thBl);
        zLeftTopOpen = zBlOpen + (0.5 * hBlockL) / cosOpenL;
        zLeftTopClosed = zBlClosed + 0.5 * hBlockL;
      }

      this._setGroupVisible("Page_Left", hasPageL);
      const zPlOpen = zLeftTopOpen + (0.5 * tLeaf) / cosOpenL + gap;
      const zPlClosed = zLeftTopClosed + gap + 0.5 * tLeaf;
      const zPlTarget = (1.0 - qSp) * zPlOpen + qSp * zPlClosed;
      const zPlRoot = zPlTarget + 0.00004 * (1.0 - qSp);
      const thPl = solveBoneArchTheta(zPlRoot, zPlTarget, "left", archCur, flatU);
      this._setChainBones("Page_Left", xStackL, zPlRoot, thPl);

      // Cover_Back folds from right tabletop (theta=0 at pClose=0) onto top of left stack (theta~pi at pClose=1)!
      const zCbClosed = zPlClosed + 0.5 * tLeaf + gap + 0.5 * tCov;
      if (pClose <= 0.0) {
        this._setChainBones("Cover_Back", spEnds.xBack, spEnds.zBack, flatRight);
      } else if (pClose >= 1.0) {
        const thCb1 = solveBoneArchTheta(spEnds.zBack, zCbClosed, "left", 0.85, 0.68);
        this._setChainBones("Cover_Back", spEnds.xBack, spEnds.zBack, thCb1);
      } else {
        const thCb1 = solveBoneArchTheta(spEnds.zBack, zCbClosed, "left", 0.85, 0.68);
        const lift = pClose < 0.56 ? Math.pow(Math.sin((Math.PI * pClose) / 0.56), 1.25) : 0.0;
        const land = pClose > 0.44 ? Math.pow(Math.sin((Math.PI * (pClose - 0.44)) / 0.56), 1.35) : 0.0;
        const thCb = new Float64Array(N_SHEET_BONES);
        for (let k = 0; k < N_SHEET_BONES; k++) {
          const u = BONE_S_MIDS[k] / PAGE_W;
          const uf = Math.pow(smoothstep(0.015, 0.92, u), 1.15);
          thCb[k] = pClose * thCb1[k] + ((34 * Math.PI) / 180) * lift * uf - ((32 * Math.PI) / 180) * land * uf;
        }
        for (let guard = 0; guard < 30; guard++) {
          let zCur = spEnds.zBack;
          let minZ = +Infinity;
          for (let k = 0; k < N_SHEET_BONES; k++) {
            zCur += BONE_DS[k] * Math.sin(thCb[k]);
            if (zCur < minZ) minZ = zCur;
          }
          if (minZ >= 0.5 * tCov - 1e-6) break;
          for (let k = 0; k < N_SHEET_BONES; k++) {
            thCb[k] += 0.012 * smoothstep(0.015, 0.92, BONE_S_MIDS[k] / PAGE_W);
          }
        }
        this._setChainBones("Cover_Back", spEnds.xBack, spEnds.zBack, thCb);
      }
      this.root.updateMatrixWorld(true);
      return;
    }

    // 3. OPEN_SPREAD or TURNING (arbitrary left/right leaf split!)
    const spEnds = this._setSpineBones("FRONT", 1.0, span);
    this._setGroupVisible("Cover_Front", true);
    this._setGroupVisible("Cover_Back", true);
    this._setChainBones("Cover_Back", spEnds.xBack, spEnds.zBack, flatRight);
    this._setChainBones("Cover_Front", spEnds.xFront, spEnds.zFront, flatLeft);

    const uTurnForArch =
      this.state === "TURNING"
        ? (this.turnDirection === +1 ? this.transitionProgress : 1.0 - this.transitionProgress)
        : 0.0;

    // Left resting stack + Page_Left
    const hasBlockL = acc.leftInactiveLeaves > 0;
    const hasPageL = acc.leftVisibleLeaf > 0;
    this._setGroupVisible("Pages_Block_Left", hasBlockL);
    this._setGroupVisible("Page_Left", hasPageL);

    const xL = -halfCradle;
    const effLeftCount = acc.leftInactiveLeaves + (hasPageL ? 1 : 0) + (this.state === "TURNING" ? uTurnForArch : 0);
    const archL = openArchForLeaves(effLeftCount);
    const cosL = Math.cos(((archL + 1.0) * Math.PI) / 180.0);
    let zLeftSurfaceTop = tCov;

    if (hasBlockL) {
      const hBl = acc.leftInactiveLeaves * this.effectiveLeafPitch;
      this._setGroupMorphThickness("Pages_Block_Left", hBl, REF_T_BLOCK_L);
      const dzBl = (0.5 * hBl) / cosL + gap;
      const zBl = zLeftSurfaceTop + dzBl;
      const thBl = solveBoneArchTheta(zBl + 0.00004, zBl, "left", archL);
      this._setChainBones("Pages_Block_Left", xL, zBl + 0.00004, thBl);
      zLeftSurfaceTop = zBl + (0.5 * hBl) / cosL;
    }

    if (hasPageL) {
      const dzPl = (0.5 * tLeaf) / cosL + gap;
      const zPl = zLeftSurfaceTop + dzPl;
      const thPl = solveBoneArchTheta(zPl + 0.00004, zPl, "left", archL);
      this._setChainBones("Page_Left", xL, zPl + 0.00004, thPl);
      zLeftSurfaceTop = zPl + (0.5 * tLeaf) / cosL;
    }

    // Right resting stack + Page_Right
    const hasBlockR = acc.rightInactiveLeaves > 0;
    const hasPageR = acc.rightVisibleLeaf > 0;
    this._setGroupVisible("Pages_Block_Right", hasBlockR);
    this._setGroupVisible("Page_Right", hasPageR);

    const xR = +halfCradle;
    const effRightCount = acc.rightInactiveLeaves + (hasPageR ? 1 : 0) + (this.state === "TURNING" ? 1.0 - uTurnForArch : 0);
    const archR = openArchForLeaves(effRightCount);
    const cosR = Math.cos(((archR + 1.0) * Math.PI) / 180.0);
    let zRightSurfaceTop = tCov;

    if (hasBlockR) {
      const hBr = acc.rightInactiveLeaves * this.effectiveLeafPitch;
      this._setGroupMorphThickness("Pages_Block_Right", hBr, REF_T_BLOCK_R);
      const dzBr = (0.5 * hBr) / cosR + gap;
      const zBr = zRightSurfaceTop + dzBr;
      const thBr = solveBoneArchTheta(zBr + 0.00004, zBr, "right", archR);
      this._setChainBones("Pages_Block_Right", xR, zBr + 0.00004, thBr);
      zRightSurfaceTop = zBr + (0.5 * hBr) / cosR;
    }

    if (hasPageR) {
      const dzPr = (0.5 * tLeaf) / cosR + gap;
      const zPr = zRightSurfaceTop + dzPr;
      const thPr = solveBoneArchTheta(zPr + 0.00004, zPr, "right", archR);
      this._setChainBones("Page_Right", xR, zPr + 0.00004, thPr);
      zRightSurfaceTop = zPr + (0.5 * tLeaf) / cosR;
    }

    // Active Turning Sheet (`Page_Turning`)
    if (this.state !== "TURNING") {
      this._setGroupVisible("Page_Turning", false);
      this.root.updateMatrixWorld(true);
      return;
    }

    this._setGroupVisible("Page_Turning", true);
    // Physical right->left progress u in [0, 1] (forward: u = progress; backward: u = 1 - progress)
    const uTurn = this.turnDirection === +1 ? this.transitionProgress : 1.0 - this.transitionProgress;

    const zPtRight = zRightSurfaceTop + (0.5 * tLeaf) / cosR + gap;
    const zPtLeft = zLeftSurfaceTop + (0.5 * tLeaf) / cosL + gap;
    const th0Rest = solveBoneArchTheta(zPtRight + 0.00004, zPtRight, "right", archR);
    const th1Rest = solveBoneArchTheta(zPtLeft + 0.00004, zPtLeft, "left", archL);

    if (uTurn <= 0.0) {
      this._setChainBones("Page_Turning", xR, zPtRight + 0.00004, th0Rest);
    } else if (uTurn >= 1.0) {
      this._setChainBones("Page_Turning", xL, zPtLeft + 0.00004, th1Rest);
    } else {
      const rProg = smootherstep(0.05, 0.95, uTurn);
      const xPt = (1.0 - rProg) * xR + rProg * xL;
      const zPt = (1.0 - rProg) * (zPtRight + 0.00004) + rProg * (zPtLeft + 0.00004) + 0.00045 * Math.sin(Math.PI * uTurn);

      const baseProg = smootherstep(0.08, 0.92, uTurn);
      const liftEnv = uTurn < 0.56 ? Math.pow(Math.sin((Math.PI * uTurn) / 0.56), 1.25) : 0.0;
      const landEnv = uTurn > 0.44 ? Math.pow(Math.sin((Math.PI * (uTurn - 0.44)) / 0.56), 1.25) : 0.0;
      const crestEnv = Math.exp(-Math.pow((uTurn - 0.50) / 0.19, 2));

      const thPt = new Float64Array(N_SHEET_BONES);
      for (let k = 0; k < N_SHEET_BONES; k++) {
        const sNorm = BONE_S_MIDS[k] / PAGE_W;
        const uFlex = Math.pow(smoothstep(0.015, 0.92, sNorm), 1.15);
        const thBase = (1.0 - baseProg) * th0Rest[k] + baseProg * th1Rest[k];
        const thWave =
          ((48.0 * Math.PI) / 180.0) * liftEnv * Math.pow(uFlex, 1.20) +
          ((16.0 * Math.PI) / 180.0) * crestEnv * Math.pow(uFlex, 1.05) -
          ((42.0 * Math.PI) / 180.0) * landEnv * Math.pow(uFlex, 1.20);
        thPt[k] = thBase + thWave;
      }
      this._setChainBones("Page_Turning", xPt, zPt, thPt);
    }

    this.root.updateMatrixWorld(true);
  }

  dispose() {
    for (const entry of this._lruTextures.values()) {
      if (entry.owned) entry.tex.dispose();
    }
    this._lruTextures.clear();
    for (const entry of this._coverTextures.values()) {
      if (entry.owned) entry.tex.dispose();
    }
    this._coverTextures.clear();
    for (const mat of this._ownedMaterials) {
      mat.dispose();
    }
    this._ownedMaterials.length = 0;
  }
}
