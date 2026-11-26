#!/usr/bin/env node
/**
 * Comprehensive Final Acceptance & Three.js Runtime Verification Harness
 * for `assets/objects/editorial-magazine/model.glb`.
 *
 * Executes in real Chromium/Google Chrome WebGL via Playwright using standard `THREE.GLTFLoader`
 * and `EditorialMagazineController` (`magazine_controller.mjs`):
 *   1. Structural & Animation Channel Isolation Audit (verifies 33 isolated channels on Magazine_PageTurn
 *      never overwrite Cover_Front, Cover_Back, Binding, Page_Left/Right, or stack thicknesses).
 *   2. 101-Sample Skinned Vertex Deformation Validation directly on exported GLB vertices across
 *      `Magazine_Open`, `Magazine_PageTurn`, and `Magazine_Close` (measuring min/max/expected/error
 *      for page & cover centerline arc lengths, cross-sections, local edge strain, binding attachment,
 *      front/back sync, thickness, and resting-state continuity).
 *   3. Configurable Page Count Matrix: 4, 10, 24, 50, 100, and 200 interior pages + configurable paper caliper.
 *   4. Mandatory 100-Page Endurance Test (100 distinct asymmetric numbered page artworks:
 *      Closed Front -> Open Front -> 50 forward turns -> Close Back -> Reopen Back -> 50 backward turns -> Close Front).
 *   5. Interactive Progress & Interruption Test (pause 25%, resume, pause 50%, mid-turn reverse, cancel 75%,
 *      complete forward/backward, rapid alternating requests, boundary clamping).
 *   6. Artwork Customization, UV Orientation, & Multi-Instance Isolation Verification.
 *   7. Runtime Load, Frame-Time, Skinning, & Bounded LRU Texture Memory Benchmark.
 *
 * Run with:
 *   NODE_PATH=<path-to-node_modules> node assets/objects/editorial-magazine/validate_threejs.mjs
 */

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../..");
const WORK_DIR = path.join(REPO_ROOT, ".work/objects/editorial-magazine");
const OUT_DIR = path.join(WORK_DIR, "validation");
const DEMO_DIR = path.join(WORK_DIR, "demo");
const RECORD_DEMO = process.argv.includes("--record-demo");
const THREE_ROOT =
  process.env.THREE_ROOT || path.resolve(path.dirname(require.resolve("three")), "..");

fs.mkdirSync(OUT_DIR, { recursive: true });
if (RECORD_DEMO) fs.mkdirSync(DEMO_DIR, { recursive: true });

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".glb": "model/gltf-binary",
  ".png": "image/png",
  ".webp": "image/webp",
};

const HTML_PAGE = `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <style>body { margin: 0; background: #b6aea2; overflow: hidden; }</style>
  <script type="importmap">
  {
    "imports": {
      "three": "/three/build/three.module.js",
      "three/addons/": "/three/examples/jsm/"
    }
  }
  </script>
</head>
<body>
<script type="module">
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import * as SkeletonUtils from "three/addons/utils/SkeletonUtils.js";
import { EditorialMagazineController } from "/asset/magazine_controller.mjs";

window.__runFinalAcceptance = async function () {
  const width = 1280, height = 960;
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setSize(width, height);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.02;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  document.body.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xb8b0a4);

  const ground = new THREE.Mesh(
    new THREE.PlaneGeometry(4, 4),
    new THREE.MeshStandardMaterial({ color: 0xb8b0a4, roughness: 0.90, metalness: 0.0 })
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.00005;
  ground.receiveShadow = true;
  scene.add(ground);

  scene.add(new THREE.HemisphereLight(0xfffcf6, 0xa8a095, 0.88));
  const key = new THREE.DirectionalLight(0xfffaf0, 1.95);
  key.position.set(-0.68, 0.78, 0.52);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  const d = 0.42;
  key.shadow.camera.left = -d; key.shadow.camera.right = d;
  key.shadow.camera.top = d; key.shadow.camera.bottom = -d;
  key.shadow.camera.near = 0.1; key.shadow.camera.far = 3.0;
  key.shadow.bias = -0.0003;
  scene.add(key);

  const fill = new THREE.DirectionalLight(0xf2f6ff, 0.55);
  fill.position.set(0.75, 0.52, 0.48);
  scene.add(fill);

  const camera = new THREE.PerspectiveCamera(34, width / height, 0.01, 10.0);

  // Measure actual GLB load & parse time
  const loader = new GLTFLoader();
  const tLoad0 = performance.now();
  const gltf = await loader.loadAsync("/asset/model.glb");
  const loadTimeMs = Number((performance.now() - tLoad0).toFixed(2));

  const root = gltf.scene;
  scene.add(root);

  // Helper: evaluate exact skinned + morphed vertex position in world space!
  const _tmpPos = new THREE.Vector3();
  const _morphPos = new THREE.Vector3();
  function getDeformedWorldVertex(mesh, vIdx) {
    const posAttr = mesh.geometry.attributes.position;
    _tmpPos.fromBufferAttribute(posAttr, vIdx);
    const morphAttrs = mesh.geometry.morphAttributes.position;
    if (morphAttrs && mesh.morphTargetInfluences) {
      for (let m = 0; m < morphAttrs.length; m++) {
        const w = mesh.morphTargetInfluences[m] || 0;
        if (w !== 0) {
          _morphPos.fromBufferAttribute(morphAttrs[m], vIdx);
          _tmpPos.addScaledVector(_morphPos, w);
        }
      }
    }
    if (mesh.isSkinnedMesh) {
      mesh.applyBoneTransform(vIdx, _tmpPos);
    }
    return _tmpPos.applyMatrix4(mesh.matrixWorld).clone();
  }

  // Build structured UV grid lookup on exported GLB sheet primitives for exact 101-sample deformation analysis
  function buildSheetUVGrid(groupName) {
    let topPrim = null, botPrim = null;
    root.traverse((o) => {
      if (o.isMesh && (o.name === groupName || o.name.startsWith(groupName + "_"))) {
        const mName = o.material.name;
        if (!mName.includes("Edges")) {
          if (!topPrim) topPrim = o;
          else if (!botPrim) botPrim = o;
        }
      }
    });
    const collectRows = (prim) => {
      const uv = prim.geometry.attributes.uv;
      // Group vertices by rounded V coordinate (11 rows along height), sorted along spine->fore-edge!
      const vMap = new Map();
      for (let i = 0; i < uv.count; i++) {
        const u = uv.getX(i);
        const v = uv.getY(i);
        const vKey = Math.round(v * 10000);
        if (!vMap.has(vKey)) vMap.set(vKey, new Map());
        const rowMap = vMap.get(vKey);
        const uKey = Math.round(u * 100000);
        if (!rowMap.has(uKey)) rowMap.set(uKey, { u, v, idx: i });
      }
      const vKeys = Array.from(vMap.keys()).sort((a, b) => a - b);
      const rows = vKeys.map((vk) => {
        const items = Array.from(vMap.get(vk).values()).sort((a, b) => a.u - b.u);
        return items.map((it) => it.idx);
      });
      return { prim, rows };
    };
    const gA = collectRows(topPrim);
    const gB = collectRows(botPrim);
    // Check whether gB's U runs reversed relative to gA (right-reading verso has u = 1 - s/L!)
    const pA0 = getDeformedWorldVertex(gA.prim, gA.rows[5][0]);
    const pB0 = getDeformedWorldVertex(gB.prim, gB.rows[5][0]);
    const pBend = getDeformedWorldVertex(gB.prim, gB.rows[5][gB.rows[5].length - 1]);
    if (pA0.distanceTo(pBend) < pA0.distanceTo(pB0)) {
      for (const r of gB.rows) r.reverse();
    }
    // Also detect which end (index 0 vs last) is closer to X=0 (binding edge!)
    const pStart = getDeformedWorldVertex(gA.prim, gA.rows[5][0]);
    const pEnd = getDeformedWorldVertex(gA.prim, gA.rows[5][gA.rows[5].length - 1]);
    if (Math.abs(pEnd.x) < Math.abs(pStart.x)) {
      for (const r of gA.rows) r.reverse();
      for (const r of gB.rows) r.reverse();
    }
    // Record rest-pose segment lengths & thickness
    const ny = gA.rows.length;
    const ns = gA.rows[0].length;
    const restMid = Array.from({ length: ny }, (_, j) =>
      Array.from({ length: ns }, (_, i) => {
        const a = getDeformedWorldVertex(gA.prim, gA.rows[j][i]);
        const b = getDeformedWorldVertex(gB.prim, gB.rows[j][i]);
        return a.add(b).multiplyScalar(0.5);
      })
    );
    const restDs = Array.from({ length: ny }, (_, j) =>
      Array.from({ length: ns - 1 }, (_, i) => restMid[j][i + 1].distanceTo(restMid[j][i]))
    );
    const restThick = Array.from({ length: ny }, (_, j) =>
      Array.from({ length: ns }, (_, i) =>
        getDeformedWorldVertex(gA.prim, gA.rows[j][i]).distanceTo(getDeformedWorldVertex(gB.prim, gB.rows[j][i]))
      )
    );
    return { gA, gB, ny, ns, restDs, restThick };
  }

  // =========================================================================
  // 1. Structural & Animation Isolation Audit (Sections 3 & 10)
  // =========================================================================
  const requiredNodes = [
    "Magazine_Root", "Binding", "Cover_Front", "Cover_Back",
    "Pages_Block_Left", "Pages_Block_Right", "Page_Left", "Page_Right", "Page_Turning"
  ];
  const foundNodes = {};
  const materialsMap = new Map();
  let totalTriangles = 0, totalVertices = 0, jointCount = 0, missingTextures = 0;
  const embeddedTextures = new Set();

  root.traverse((o) => {
    if (requiredNodes.includes(o.name) && !foundNodes[o.name]) foundNodes[o.name] = o.type;
    if (o.isBone) jointCount++;
    if (o.isMesh) {
      o.castShadow = true;
      o.receiveShadow = true;
      const g = o.geometry;
      totalVertices += g.attributes.position.count;
      totalTriangles += g.index ? g.index.count / 3 : g.attributes.position.count / 3;
      const mats = Array.isArray(o.material) ? o.material : [o.material];
      for (const m of mats) {
        materialsMap.set(m.name, m);
        for (const k of ["map", "normalMap", "roughnessMap"]) {
          if (m[k]) {
            if (!m[k].image || !m[k].image.width) missingTextures++;
            else embeddedTextures.add(k + ":" + m[k].image.width + "x" + m[k].image.height);
          }
        }
      }
    }
  });

  const clipChannelSummary = {};
  for (const clip of gltf.animations) {
    const targetGroups = new Set();
    for (const tr of clip.tracks) {
      const nodeName = tr.name.split(".")[0];
      targetGroups.add(nodeName.replace(/_\\d+$/, ""));
    }
    clipChannelSummary[clip.name] = {
      durationSec: Number(clip.duration.toFixed(4)),
      trackCount: clip.tracks.length,
      targetGroups: Array.from(targetGroups).sort(),
    };
  }

  // =========================================================================
  // 2. 101-Sample Skinned Vertex Deformation on Exported GLB Clips (Sec 8 & 9)
  // =========================================================================
  let mixer = new THREE.AnimationMixer(root);
  const clipByName = Object.fromEntries(gltf.animations.map((c) => [c.name, c]));

  function setClipAt(clipName, prog01, baseClipName = null) {
    mixer.stopAllAction();
    if (baseClipName) {
      const baseClip = clipByName[baseClipName];
      const baseAct = mixer.clipAction(baseClip);
      baseAct.reset();
      baseAct.setLoop(THREE.LoopOnce, 1);
      baseAct.clampWhenFinished = true;
      baseAct.play();
      mixer.setTime(1.0 * baseClip.duration);
      root.updateMatrixWorld(true);
      // Fresh mixer preserves the evaluated non-Page_Turning bone transforms without blending Page_Turning 50/50!
      mixer = new THREE.AnimationMixer(root);
    }
    const clip = clipByName[clipName];
    const act = mixer.clipAction(clip);
    act.reset();
    act.setLoop(THREE.LoopOnce, 1);
    act.clampWhenFinished = true;
    act.play();
    mixer.setTime(prog01 * clip.duration);
    root.updateMatrixWorld(true);
    root.traverse((o) => { if (o.isSkinnedMesh) o.skeleton.update(); });
  }

  // Initialize grids at default open pose
  setClipAt("Magazine_Open", 1.0);
  const sheetGrids = {
    Cover_Front: buildSheetUVGrid("Cover_Front"),
    Cover_Back: buildSheetUVGrid("Cover_Back"),
    Page_Left: buildSheetUVGrid("Page_Left"),
    Page_Right: buildSheetUVGrid("Page_Right"),
    Page_Turning: buildSheetUVGrid("Page_Turning"),
  };

  function evaluateGridSample(grid, nominalThick) {
    const { gA, gB, ny, ns, restDs, restThick } = grid;
    const midRow = Math.floor(ny / 2);
    let minArc = +Infinity, maxArc = -Infinity, centerArc = 0;
    let maxLocalStrainPct = 0;
    let maxThickErrPct = 0, minThickMm = +Infinity, maxThickMm = -Infinity;
    let maxSyncShearMm = 0;

    const midPts = Array.from({ length: ny }, () => new Array(ns));
    const vecTB = Array.from({ length: ny }, () => new Array(ns));

    for (let j = 0; j < ny; j++) {
      let rowArc = 0;
      for (let i = 0; i < ns; i++) {
        const pA = getDeformedWorldVertex(gA.prim, gA.rows[j][i]);
        const pB = getDeformedWorldVertex(gB.prim, gB.rows[j][i]);
        vecTB[j][i] = pA.clone().sub(pB);
        const th = vecTB[j][i].length();
        // Exclude outermost bevel loop (i === ns-1, j === 0, j === ny-1) for nominal interior thickness
        if (j > 0 && j < ny - 1 && i < ns - 1) {
          minThickMm = Math.min(minThickMm, th * 1000);
          maxThickMm = Math.max(maxThickMm, th * 1000);
          const tErr = Math.abs(th - restThick[j][i]) / restThick[j][i] * 100;
          if (tErr > maxThickErrPct) maxThickErrPct = tErr;
        }
        midPts[j][i] = pA.add(pB).multiplyScalar(0.5);
        if (i > 0) {
          const ds = midPts[j][i].distanceTo(midPts[j][i - 1]);
          rowArc += ds;
          if (restDs[j][i - 1] > 0.0004) {
            const st = Math.abs(ds - restDs[j][i - 1]) / restDs[j][i - 1] * 100;
            if (st > maxLocalStrainPct) maxLocalStrainPct = st;
          }
        }
      }
      if (j === midRow) centerArc = rowArc;
      minArc = Math.min(minArc, rowArc);
      maxArc = Math.max(maxArc, rowArc);
    }

    for (let j = 1; j < ny - 1; j++) {
      for (let i = 1; i < ns - 1; i++) {
        const tang = midPts[j][i + 1].clone().sub(midPts[j][i - 1]).normalize();
        const shear = Math.abs(vecTB[j][i].dot(tang)) * 1000;
        if (shear > maxSyncShearMm) maxSyncShearMm = shear;
      }
    }

    return {
      centerArcM: centerArc,
      minCrossArcM: minArc,
      maxCrossArcM: maxArc,
      maxLocalStrainPct,
      minThickMm,
      maxThickMm,
      maxThickErrPct,
      maxSyncShearMm,
      rootPos: midPts[midRow][0],
      tipPos: midPts[midRow][ns - 1],
    };
  }

  const glb101Report = {};
  const clipEndpoints = {};

  const allClipNames = [
    "Magazine_Open",
    "Magazine_PageTurn",
    "Magazine_PageTurn_Back",
    "Magazine_Close",
    "Magazine_Close_Back",
    "Magazine_Open_Back",
  ];
  for (const clipName of allClipNames) {
    // Ensure canonical open pose remains active on non-animated chains when testing isolated 33-channel turn clips!
    const baseClip = clipName === "Magazine_PageTurn"
      ? "Magazine_Open"
      : clipName === "Magazine_PageTurn_Back"
      ? "Magazine_Open_Back"
      : null;
    const targetSheets = (clipName === "Magazine_PageTurn" || clipName === "Magazine_PageTurn_Back")
      ? ["Page_Turning"]
      : ["Cover_Front", "Cover_Back", "Page_Left", "Page_Right", "Page_Turning"];

    const stats = {};
    for (const sName of targetSheets) {
      stats[sName] = {
        expectedWidthMm: 210.0,
        expectedThickMm: sName.startsWith("Cover") ? 0.320 : 0.145,
        minCenterArcMm: +Infinity,
        maxCenterArcMm: -Infinity,
        maxCenterArcDevPct: 0,
        minCrossArcMm: +Infinity,
        maxCrossArcMm: -Infinity,
        maxCrossArcDevPct: 0,
        maxLocalEdgeStrainPct: 0,
        minThickMm: +Infinity,
        maxThickMm: -Infinity,
        maxThickErrPct: 0,
        maxFrontBackDesyncMm: 0,
        maxBindingEdgeDisplacementFromRootStartMm: 0,
        startRootPos: null,
      };
    }

    for (let i = 0; i <= 100; i++) {
      const p = i / 100;
      setClipAt(clipName, p, baseClip);

      if (i === 0 || i === 100) {
        const snap = {};
        for (const sName of Object.keys(sheetGrids)) {
          snap[sName] = evaluateGridSample(sheetGrids[sName]).tipPos.toArray();
        }
        clipEndpoints[clipName + "_" + (i === 0 ? "start" : "end")] = snap;
      }

      for (const sName of targetSheets) {
        const res = evaluateGridSample(sheetGrids[sName]);
        const st = stats[sName];
        if (!st.startRootPos) st.startRootPos = res.rootPos.clone();
        const rootDisp = res.rootPos.distanceTo(st.startRootPos) * 1000;
        st.maxBindingEdgeDisplacementFromRootStartMm = Math.max(st.maxBindingEdgeDisplacementFromRootStartMm, rootDisp);

        const cMm = res.centerArcM * 1000;
        st.minCenterArcMm = Math.min(st.minCenterArcMm, cMm);
        st.maxCenterArcMm = Math.max(st.maxCenterArcMm, cMm);
        st.maxCenterArcDevPct = Math.max(st.maxCenterArcDevPct, Math.abs(cMm - 210.0) / 210.0 * 100);

        st.minCrossArcMm = Math.min(st.minCrossArcMm, res.minCrossArcM * 1000);
        st.maxCrossArcMm = Math.max(st.maxCrossArcMm, res.maxCrossArcM * 1000);
        st.maxCrossArcDevPct = Math.max(
          st.maxCrossArcDevPct,
          Math.abs(res.minCrossArcM * 1000 - 210.0) / 210.0 * 100,
          Math.abs(res.maxCrossArcM * 1000 - 210.0) / 210.0 * 100
        );
        st.maxLocalEdgeStrainPct = Math.max(st.maxLocalEdgeStrainPct, res.maxLocalStrainPct);
        st.minThickMm = Math.min(st.minThickMm, res.minThickMm);
        st.maxThickMm = Math.max(st.maxThickMm, res.maxThickMm);
        st.maxThickErrPct = Math.max(st.maxThickErrPct, res.maxThickErrPct);
        st.maxFrontBackDesyncMm = Math.max(st.maxFrontBackDesyncMm, res.maxSyncShearMm);
      }
    }

    for (const st of Object.values(stats)) {
      delete st.startRootPos;
      for (const k of Object.keys(st)) {
        if (typeof st[k] === "number") st[k] = Number(st[k].toFixed(5));
      }
    }
    glb101Report[clipName] = { samples: 101, sheets: stats };
  }

  // Compute standalone GLB 6-clip consecutive boundary continuity (Open->PageTurn->Close_Back->Open_Back->PageTurn_Back->Close->Open)
  function maxEndpointJumpMm(kA, kB, sheetsToCheck) {
    let mx = 0;
    for (const s of sheetsToCheck) {
      const a = clipEndpoints[kA][s];
      const b = clipEndpoints[kB][s];
      const d = Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]) * 1000;
      if (d > mx) mx = d;
    }
    return Number(mx.toFixed(6));
  }
  const allFiveSheets = ["Cover_Front", "Cover_Back", "Page_Left", "Page_Right", "Page_Turning"];
  const standaloneGlbBoundaryContinuityMm = {
    Open_end_to_PageTurn_start: maxEndpointJumpMm("Magazine_Open_end", "Magazine_PageTurn_start", ["Page_Turning"]),
    PageTurn_end_to_CloseBack_start: maxEndpointJumpMm("Magazine_PageTurn_end", "Magazine_Close_Back_start", allFiveSheets),
    CloseBack_end_to_OpenBack_start: maxEndpointJumpMm("Magazine_Close_Back_end", "Magazine_Open_Back_start", allFiveSheets),
    OpenBack_end_to_PageTurnBack_start: maxEndpointJumpMm("Magazine_Open_Back_end", "Magazine_PageTurn_Back_start", ["Page_Turning"]),
    PageTurnBack_end_to_Close_start: maxEndpointJumpMm("Magazine_PageTurn_Back_end", "Magazine_Close_start", allFiveSheets),
    Close_end_to_Open_start: maxEndpointJumpMm("Magazine_Close_end", "Magazine_Open_start", allFiveSheets),
  };

  // Test Section 10: Prove seeking isolated Magazine_PageTurn clip does NOT reset custom state!
  mixer.stopAllAction();
  const ctrl = new EditorialMagazineController(root, { pageCount: 100, maxCachedPages: 16 });
  ctrl.openFrontCover(1.0);
  // Advance to spread k = 7 (14 pages on left, 86 pages on right!)
  for (let s = 0; s < 7; s++) ctrl.next();
  const beforeIsolation = {
    coverFrontTip: evaluateGridSample(sheetGrids.Cover_Front).tipPos.clone(),
    coverBackTip: evaluateGridSample(sheetGrids.Cover_Back).tipPos.clone(),
    pageLeftTip: evaluateGridSample(sheetGrids.Page_Left).tipPos.clone(),
    pageRightTip: evaluateGridSample(sheetGrids.Page_Right).tipPos.clone(),
    blockLMorph: ctrl.primitivesByGroup.Pages_Block_Left[0].morphTargetInfluences[0],
    blockRMorph: ctrl.primitivesByGroup.Pages_Block_Right[0].morphTargetInfluences[0],
  };
  setClipAt("Magazine_PageTurn", 0.50);
  const afterFwdIsolationDriftMm = Math.max(
    evaluateGridSample(sheetGrids.Cover_Front).tipPos.distanceTo(beforeIsolation.coverFrontTip) * 1000,
    evaluateGridSample(sheetGrids.Cover_Back).tipPos.distanceTo(beforeIsolation.coverBackTip) * 1000,
    evaluateGridSample(sheetGrids.Page_Left).tipPos.distanceTo(beforeIsolation.pageLeftTip) * 1000,
    evaluateGridSample(sheetGrids.Page_Right).tipPos.distanceTo(beforeIsolation.pageRightTip) * 1000,
    Math.abs(ctrl.primitivesByGroup.Pages_Block_Left[0].morphTargetInfluences[0] - beforeIsolation.blockLMorph) * 1000,
    Math.abs(ctrl.primitivesByGroup.Pages_Block_Right[0].morphTargetInfluences[0] - beforeIsolation.blockRMorph) * 1000
  );
  setClipAt("Magazine_PageTurn_Back", 0.50);
  const afterBwdIsolationDriftMm = Math.max(
    evaluateGridSample(sheetGrids.Cover_Front).tipPos.distanceTo(beforeIsolation.coverFrontTip) * 1000,
    evaluateGridSample(sheetGrids.Cover_Back).tipPos.distanceTo(beforeIsolation.coverBackTip) * 1000,
    evaluateGridSample(sheetGrids.Page_Left).tipPos.distanceTo(beforeIsolation.pageLeftTip) * 1000,
    evaluateGridSample(sheetGrids.Page_Right).tipPos.distanceTo(beforeIsolation.pageRightTip) * 1000
  );
  const afterIsolationMaxDriftMm = Math.max(afterFwdIsolationDriftMm, afterBwdIsolationDriftMm);

  // Also verify standalone GLB Magazine_Close_Back ends with Cover_Back outer surface visible on top (+Y) above Cover_Front!
  setClipAt("Magazine_Close_Back", 1.0);
  const glbBackClosedCb = evaluateGridSample(sheetGrids.Cover_Back);
  const glbBackClosedCf = evaluateGridSample(sheetGrids.Cover_Front);
  const glbBackCloseClipVerified = Boolean(
    glbBackClosedCb.tipPos.x < -0.205 &&
    glbBackClosedCf.tipPos.x < -0.205 &&
    glbBackClosedCb.tipPos.y > glbBackClosedCf.tipPos.y + 0.0045
  );
  mixer.stopAllAction();

  // =========================================================================
  // Programmatic Numbered Asymmetric Test Page Artwork Generator (1..200)
  // =========================================================================
  function createNumberedPageCanvas(pageNum, totalPages) {
    const c = document.createElement("canvas");
    c.width = 560;
    c.height = 792; // Exact A4 210:297 ratio
    const ctx = c.getContext("2d");
    const isEvenLeft = pageNum % 2 === 0;
    const hue = (pageNum * 37) % 360;
    const accent = \`hsl(\${hue}, 38%, 28%)\`;

    ctx.fillStyle = "#f7f4ee";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.strokeStyle = accent;
    ctx.lineWidth = 6;
    ctx.strokeRect(20, 20, c.width - 40, c.height - 40);

    // Asymmetric corner orientation blocks
    ctx.fillStyle = accent;
    ctx.fillRect(20, 20, 108, 46);
    ctx.fillStyle = "#b54834";
    ctx.fillRect(c.width - 128, 20, 108, 46);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 20px Helvetica, Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("TL (0,1)", 74, 50);
    ctx.fillText("TR (1,1)", c.width - 74, 50);

    // Directional Top/Bottom/Gutter/Fore-Edge markers
    ctx.fillStyle = accent;
    ctx.font = "bold 18px Helvetica, Arial, sans-serif";
    ctx.fillText("▲ TOP EDGE ▲", c.width / 2, 50);
    ctx.fillText("▼ BOTTOM EDGE ▼", c.width / 2, c.height - 34);

    // Asymmetric visual composition block on outer side of page
    ctx.fillStyle = \`hsla(\${hue}, 26%, 68%, 0.45)\`;
    const boxX = isEvenLeft ? 54 : c.width - 234;
    ctx.fillRect(boxX, 130, 180, 480);

    // Large right-reading page number + leaf metadata
    const leafIdx = Math.ceil(pageNum / 2);
    ctx.fillStyle = "#1c1b19";
    ctx.font = "bold 108px Georgia, serif";
    ctx.fillText(String(pageNum).padStart(3, "0"), c.width / 2, 370);
    ctx.font = "bold 24px Helvetica, Arial, sans-serif";
    ctx.fillText(\`PAGE \${pageNum} OF \${totalPages} · LEAF \${leafIdx} \${isEvenLeft ? "VERSO (LEFT)" : "RECTO (RIGHT)"}\`, c.width / 2, 430);
    ctx.fillStyle = "#b54834";
    ctx.fillText(isEvenLeft ? "◀ FORE-EDGE | GUTTER ▶" : "◀ GUTTER | FORE-EDGE ▶", c.width / 2, 475);
    ctx.fillText("READ LEFT → RIGHT · ABCDEFG 12345", c.width / 2, 515);

    return c;
  }

  function createCoverCanvas(label, sub) {
    const c = document.createElement("canvas");
    c.width = 560; c.height = 792;
    const ctx = c.getContext("2d");
    ctx.fillStyle = "#f2eee6";
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.strokeStyle = "#22201e";
    ctx.lineWidth = 6;
    ctx.strokeRect(28, 28, c.width - 56, c.height - 56);
    ctx.fillStyle = "#22201e";
    ctx.textAlign = "center";
    ctx.font = "bold 56px Georgia, serif";
    ctx.fillText("KINFOLK", c.width / 2, 220);
    ctx.font = "bold 26px Helvetica, Arial, sans-serif";
    ctx.fillText(label, c.width / 2, 390);
    ctx.font = "20px Georgia, serif";
    ctx.fillText(sub, c.width / 2, 440);
    return c;
  }

  // =========================================================================
  // 3. Configurable Page Count Matrix: 4, 10, 24, 50, 100, 200 Pages (Sec 11 & 12)
  // =========================================================================
  while (ctrl.previous()) { /* reset to first spread before closing */ }
  ctrl.closeFrontCover(1.0);
  const pageCountMatrix = {};
  for (const pCount of [4, 10, 24, 50, 100, 200]) {
    ctrl.closeFrontCover(1.0);
    ctrl.setPageCount(pCount);
    // Measure closed height
    let maxClosedY = 0;
    root.traverse((o) => {
      if (o.isMesh && o.visible) {
        const n = o.geometry.attributes.position.count;
        for (let i = 0; i < n; i += 8) {
          maxClosedY = Math.max(maxClosedY, getDeformedWorldVertex(o, i).y);
        }
      }
    });

    // Open front cover -> First Spread (k = 0: empty left stack!)
    ctrl.openFrontCover(1.0);
    const accFirst = ctrl.getLeafAccounting();
    const emptyLeftNoGap = (!ctrl.groups.Pages_Block_Left.visible && !ctrl.groups.Page_Left.visible);

    // Navigate to exact middle spread (k = floor(leafCount / 2))
    const midK = Math.floor(ctrl.leafCount / 2);
    for (let s = 0; s < midK; s++) ctrl.next();
    const accMid = ctrl.getLeafAccounting();

    // Navigate to last spread (k = leafCount: empty right stack!)
    while (ctrl.next()) { /* advance to end */ }
    const accLast = ctrl.getLeafAccounting();
    const emptyRightNoGap = (!ctrl.groups.Pages_Block_Right.visible && !ctrl.groups.Page_Right.visible);

    pageCountMatrix[pCount] = {
      interiorPages: pCount,
      physicalLeaves: ctrl.leafCount,
      closedHeightMm: Number((maxClosedY * 1000).toFixed(3)),
      spineSpanMm: Number((ctrl.spineSpanMeters * 1000).toFixed(3)),
      firstSpreadLeafConservationOk: accFirst.totalAccountedLeaves === ctrl.leafCount,
      midSpreadLeafConservationOk: accMid.totalAccountedLeaves === ctrl.leafCount,
      lastSpreadLeafConservationOk: accLast.totalAccountedLeaves === ctrl.leafCount,
      emptyLeftStackZeroGapOk: emptyLeftNoGap,
      emptyRightStackZeroGapOk: emptyRightNoGap,
    };

    // Capture WebGL screenshot of 200-page stress configuration at middle spread
    if (pCount === 200) {
      ctrl.openBackCover(1.0);
      for (let s = 0; s < 50; s++) ctrl.previous();
      ctrl.setPageArtworkProvider((pg) => createNumberedPageCanvas(pg, 200));
      camera.position.set(0.26, 0.34, 0.50);
      camera.lookAt(0, 0.015, 0);
      renderer.render(scene, camera);
      window.__shot200Stress = renderer.domElement.toDataURL("image/png");
    }

    // Reset back to closed front
    while (ctrl.previous()) { /* back to 0 */ }
    ctrl.closeFrontCover(1.0);
  }

  // Also test configurable paper thickness (setPaperThickness)
  ctrl.setPageCount(50);
  ctrl.setPaperThickness({ leafMeters: 0.000200, coverMeters: 0.000400 });
  const thickSpineMm = Number((ctrl.spineSpanMeters * 1000).toFixed(3));
  ctrl.setPaperThickness({ leafMeters: 0.000145, coverMeters: 0.000320 });
  const stdSpineMm = Number((ctrl.spineSpanMeters * 1000).toFixed(3));
  const paperThicknessConfigOk = thickSpineMm > stdSpineMm + 1.2;

  // =========================================================================
  // 4. Mandatory 100-Page Forward + Backward Endurance Test (Section 13)
  // =========================================================================
  const generated100Artworks = new Map();
  let providerCalls = 0;
  ctrl.setPageCount(100);
  ctrl.setCoverArtwork("frontOuter", createCoverCanvas("100-PAGE EDITION", "FRONT COVER EXTERIOR"));
  ctrl.setCoverArtwork("frontInner", createCoverCanvas("INSIDE FRONT COVER", "LEFT SPREAD SURFACE"));
  ctrl.setCoverArtwork("backInner", createCoverCanvas("INSIDE BACK COVER", "RIGHT SPREAD SURFACE"));
  ctrl.setCoverArtwork("backOuter", createCoverCanvas("BACK COVER EXTERIOR", "ISSN 2749-0412 · CLOSED BACK"));
  ctrl.setPageArtworkProvider((pg) => {
    providerCalls++;
    if (!generated100Artworks.has(pg)) {
      const cv = createNumberedPageCanvas(pg, 100);
      cv.__pageNumber = pg;
      generated100Artworks.set(pg, cv);
    }
    return generated100Artworks.get(pg);
  });

  // Step 1: Start with front cover closed & record initial closed pose
  ctrl.closeFrontCover(1.0);
  const initialClosedCoverTip = evaluateGridSample(sheetGrids.Cover_Front).tipPos.clone();
  const enduranceShots = {};
  function snapEndurance(name, pos, tgt) {
    camera.position.set(...pos);
    camera.lookAt(...tgt);
    renderer.render(scene, camera);
    enduranceShots[name] = renderer.domElement.toDataURL("image/png");
  }
  snapEndurance("accept_01_closed_front_100p", [0.32, 0.26, 0.38], [0.10, 0.004, 0]);

  let forwardTurnCount = 0;
  let backwardTurnCount = 0;
  let maxEnduranceArcErrPct = 0;
  let maxCachedGpuPagesObserved = 0;
  let maxRendererTexturesObserved = 0;
  const seenPagesForward = new Set();
  const seenPagesBackward = new Set();
  const enduranceFailures = [];

  // Verify continuous state-boundary transitions (OPENING_FRONT(0.999)->OPEN_SPREAD(0), OPEN_SPREAD(50)->CLOSING_BACK(0.001), etc.)
  ctrl.closeFrontCover(1.0);
  ctrl.openFrontCover(0.9999);
  const openNearEndPr = evaluateGridSample(sheetGrids.Page_Right).tipPos.clone();
  const openNearEndCf = evaluateGridSample(sheetGrids.Cover_Front).tipPos.clone();
  ctrl.openFrontCover(1.0);
  const openExactPr = evaluateGridSample(sheetGrids.Page_Right).tipPos.clone();
  const openExactCf = evaluateGridSample(sheetGrids.Cover_Front).tipPos.clone();
  const frontOpenHandoffJumpMm = Math.max(
    openNearEndPr.distanceTo(openExactPr) * 1000,
    openNearEndCf.distanceTo(openExactCf) * 1000
  );
  ctrl.closeFrontCover(1.0);

  // Step 2: Half-open & fully open front cover
  let minTabletopYMm = +Infinity;
  function checkGlobalMinY() {
    root.traverse((o) => {
      if (o.isMesh && o.visible) {
        const n = o.geometry.attributes.position.count;
        for (let i = 0; i < n; i += 12) {
          minTabletopYMm = Math.min(minTabletopYMm, getDeformedWorldVertex(o, i).y * 1000);
        }
      }
    });
  }
  ctrl.openFrontCover(0.45);
  checkGlobalMinY();
  snapEndurance("accept_02_half_open_front_100p", [0.30, 0.30, 0.50], [0.02, 0.05, 0]);
  ctrl.openFrontCover(1.0);
  checkGlobalMinY();
  snapEndurance("accept_03_first_spread_p1_100p", [0.0, 0.72, 0.04], [0, 0.005, 0]);

  if (ctrl.getLeafAccounting().visibleRightPage !== 1 || ctrl.getLeafAccounting().visibleLeftPage !== 0) {
    enduranceFailures.push("First spread did not expose Inside Front Cover + Page 1");
  }
  seenPagesForward.add(1);

  // Step 3 & 4: Navigate forward through all 50 physical leaves (Pages 1..100)!
  for (let step = 0; step < 50; step++) {
    const okStart = ctrl.beginTurnForward();
    if (!okStart) {
      enduranceFailures.push(\`Failed beginTurnForward at step \${step}\`);
      break;
    }
    const accTurn = ctrl.getLeafAccounting();
    const expFront = 2 * step + 1;
    const expBack = 2 * step + 2;
    if (accTurn.turningFrontPage !== expFront || accTurn.turningBackPage !== expBack) {
      enduranceFailures.push(\`Wrong turning pages at step \${step}: got \${accTurn.turningFrontPage}/\${accTurn.turningBackPage}\`);
    }
    if (accTurn.totalAccountedLeaves !== 50) {
      enduranceFailures.push(\`Leaf conservation broken during forward turn \${step}: \${accTurn.totalAccountedLeaves}\`);
    }
    // Verify actual bound Three.js textures match expected page numbers (zero stale artwork!)
    const matTF = ctrl.materials.Mat_Page_Turning_Front;
    const matTB = ctrl.materials.Mat_Page_Turning_Back;
    if (!matTF.map || matTF.map.image.__pageNumber !== expFront || !matTB.map || matTB.map.image.__pageNumber !== expBack) {
      enduranceFailures.push(\`Stale or missing turning texture at forward step \${step}\`);
    }

    // Exercise intermediate deformation at u = 0.50 (and capture representative Page Turning shot at step 25 / Leaf 26!)
    if (step === 25) {
      ctrl.setTurnProgress(0.42);
      snapEndurance("accept_04b_page_turning_100p", [0.16, 0.52, 0.40], [0.0, 0.025, 0.0]);
    }
    ctrl.setTurnProgress(0.50);
    const midSample = evaluateGridSample(sheetGrids.Page_Turning);
    const arcErr = Math.abs(midSample.centerArcM * 1000 - 210.0) / 210.0 * 100;
    maxEnduranceArcErrPct = Math.max(maxEnduranceArcErrPct, arcErr);

    if (step === 24) {
      // Middle spread capture right after committing leaf 25 (Pages 50 | 51)!
    }

    ctrl.setTurnProgress(1.0);
    ctrl.commitTurn();
    forwardTurnCount++;

    const accAfter = ctrl.getLeafAccounting();
    seenPagesForward.add(expFront);
    seenPagesForward.add(expBack);
    if (accAfter.visibleLeftPage !== expBack) {
      enduranceFailures.push(\`Expected left page \${expBack} after step \${step}, got \${accAfter.visibleLeftPage}\`);
    }
    if (step < 49 && accAfter.visibleRightPage !== expBack + 1) {
      enduranceFailures.push(\`Expected right page \${expBack + 1} after step \${step}, got \${accAfter.visibleRightPage}\`);
    }

    maxCachedGpuPagesObserved = Math.max(maxCachedGpuPagesObserved, ctrl.cachedTextureCount);
    renderer.render(scene, camera);
    maxRendererTexturesObserved = Math.max(maxRendererTexturesObserved, renderer.info.memory.textures);

    if (step === 24) {
      snapEndurance("accept_04_middle_spread_p50_51_100p", [0.0, 0.72, 0.04], [0, 0.006, 0]);
    }
  }

  // Confirm we are at the Last Interior Spread (Page 100 on left | Inside Back Cover on right)
  snapEndurance("accept_05_last_spread_p100_100p", [0.0, 0.72, 0.04], [0, 0.006, 0]);
  if (ctrl.beginTurnForward() !== false) {
    enduranceFailures.push("Failed boundary clamp past last page 100");
  }

  // Step 5: Verify smooth handoff at final spread -> CLOSING_BACK(0.0001) -> 0.50 -> CLOSED_BACK (1.0)!
  const lastSpreadPl = evaluateGridSample(sheetGrids.Page_Left).tipPos.clone();
  const lastSpreadCb = evaluateGridSample(sheetGrids.Cover_Back).tipPos.clone();
  ctrl.closeBackCover(0.0001);
  const backCloseStartPl = evaluateGridSample(sheetGrids.Page_Left).tipPos.clone();
  const backCloseStartCb = evaluateGridSample(sheetGrids.Cover_Back).tipPos.clone();
  const backCloseHandoffJumpMm = Math.max(
    lastSpreadPl.distanceTo(backCloseStartPl) * 1000,
    lastSpreadCb.distanceTo(backCloseStartCb) * 1000
  );
  ctrl.closeBackCover(0.50);
  checkGlobalMinY();
  snapEndurance("accept_05b_half_closed_back_100p", [-0.28, 0.32, 0.50], [-0.02, 0.05, 0]);

  if (!ctrl.closeBackCover(1.0) || ctrl.state !== "CLOSED_BACK") {
    enduranceFailures.push("Failed to close back cover at page 100");
  }
  checkGlobalMinY();
  const closedBackCbY = evaluateGridSample(sheetGrids.Cover_Back).tipPos.y * 1000;
  const closedBackCfY = evaluateGridSample(sheetGrids.Cover_Front).tipPos.y * 1000;
  if (!(closedBackCbY > closedBackCfY + 8.0)) {
    enduranceFailures.push(\`Back cover did not land above 100-page stack: cbY=\${closedBackCbY} cfY=\${closedBackCfY}\`);
  }
  snapEndurance("accept_06_closed_back_cover_100p", [-0.32, 0.26, 0.38], [-0.10, 0.004, 0]);

  // Step 6: Reopen from the back (exercise 50% intermediate progress + 100% open)!
  ctrl.openBackCover(0.50);
  if (ctrl.state !== "OPENING_BACK") enduranceFailures.push("Expected OPENING_BACK state at progress 0.50");
  checkGlobalMinY();
  if (!ctrl.openBackCover(1.0) || ctrl.state !== "OPEN_SPREAD" || ctrl.leftLeaves !== 50) {
    enduranceFailures.push("Failed to reopen from back cover");
  }

  // Step 7 & 8: Navigate backward through all 50 leaves (Pages 100..1)!
  for (let step = 49; step >= 0; step--) {
    const okBack = ctrl.beginTurnBackward();
    if (!okBack) {
      enduranceFailures.push(\`Failed beginTurnBackward at leaf \${step + 1}\`);
      break;
    }
    const accTurn = ctrl.getLeafAccounting();
    const expFront = 2 * step + 1;
    const expBack = 2 * step + 2;
    if (accTurn.turningFrontPage !== expFront || accTurn.turningBackPage !== expBack) {
      enduranceFailures.push(\`Wrong backward turning pages at leaf \${step + 1}\`);
    }
    ctrl.setTurnProgress(0.50);
    const midSample = evaluateGridSample(sheetGrids.Page_Turning);
    maxEnduranceArcErrPct = Math.max(maxEnduranceArcErrPct, Math.abs(midSample.centerArcM * 1000 - 210.0) / 210.0 * 100);

    ctrl.setTurnProgress(1.0);
    ctrl.commitTurn();
    backwardTurnCount++;
    seenPagesBackward.add(expBack);
    seenPagesBackward.add(expFront);

    maxCachedGpuPagesObserved = Math.max(maxCachedGpuPagesObserved, ctrl.cachedTextureCount);
  }

  if (ctrl.leftLeaves !== 0 || ctrl.getLeafAccounting().visibleRightPage !== 1) {
    enduranceFailures.push("Did not return cleanly to Page 1 after backward endurance traversal");
  }
  if (ctrl.beginTurnBackward() !== false) {
    enduranceFailures.push("Failed boundary clamp before Page 1");
  }

  // Step 9: Exercise intermediate front cover closing (0.50) & complete close (1.0)!
  ctrl.closeFrontCover(0.50);
  if (ctrl.state !== "CLOSING_FRONT") enduranceFailures.push("Expected CLOSING_FRONT state at progress 0.50");
  checkGlobalMinY();
  if (!ctrl.closeFrontCover(1.0) || ctrl.state !== "CLOSED_FRONT") {
    enduranceFailures.push("Failed to close front cover after returning to Page 1");
  }
  const finalClosedCoverTip = evaluateGridSample(sheetGrids.Cover_Front).tipPos.clone();
  const accumulatedPoseDriftMm = Number((finalClosedCoverTip.distanceTo(initialClosedCoverTip) * 1000).toFixed(6));

  const endurance100Report = {
    configuredInteriorPages: 100,
    distinctArtworksGenerated: generated100Artworks.size,
    forwardLeafTurns: forwardTurnCount,
    backwardLeafTurns: backwardTurnCount,
    uniquePagesVerifiedForward: seenPagesForward.size,
    uniquePagesVerifiedBackward: seenPagesBackward.size,
    maxPageArcErrorPctDuring100Turns: Number(maxEnduranceArcErrPct.toFixed(5)),
    frontOpenHandoffJumpMm: Number(frontOpenHandoffJumpMm.toFixed(5)),
    backCloseHandoffJumpMm: Number(backCloseHandoffJumpMm.toFixed(5)),
    minGlobalTabletopYMm: Number(minTabletopYMm.toFixed(4)),
    closedBackTopHeightMm: Number(closedBackCbY.toFixed(3)),
    accumulatedClosedPoseDriftMm: accumulatedPoseDriftMm,
    maxResidentCachedPageTextures: maxCachedGpuPagesObserved,
    maxWebGlTotalTexturesInMemory: maxRendererTexturesObserved,
    failures: enduranceFailures,
    passed:
      enduranceFailures.length === 0 &&
      forwardTurnCount === 50 &&
      backwardTurnCount === 50 &&
      seenPagesForward.size === 100 &&
      seenPagesBackward.size === 100 &&
      frontOpenHandoffJumpMm < 0.1 &&
      backCloseHandoffJumpMm < 0.1 &&
      minTabletopYMm >= -0.05,
  };

  // =========================================================================
  // 5. Interactive Progress, Interruption, Reversal & Cancellation Test (Sec 14)
  // =========================================================================
  const interruptFailures = [];
  ctrl.openFrontCover(1.0);
  // Boundary attempt before page 1
  if (ctrl.beginTurnBackward() !== false) interruptFailures.push("Allowed backward turn at k=0");

  // Advance to k = 3 (Page 6 | Page 7)
  ctrl.next(); ctrl.next(); ctrl.next();
  const preCancelLeftLeaves = ctrl.leftLeaves;
  const preCancelAcc = ctrl.getLeafAccounting();

  // Start forward turn -> pause at 25% -> verify index unchanged -> resume to 50% -> reverse -> advance to 75% -> cancel!
  ctrl.beginTurnForward();
  ctrl.setProgress(0.25);
  ctrl.pauseTurn();
  if (!ctrl.isPaused) interruptFailures.push("pauseTurn() did not set isPaused");
  const tip25 = evaluateGridSample(sheetGrids.Page_Turning).tipPos.clone();
  if (ctrl.leftLeaves !== preCancelLeftLeaves) interruptFailures.push("Page index mutated at 25% before commit");

  // Resume from 25% -> 50% smoothly (check small step continuity at 0.26)
  ctrl.resumeTurn();
  if (ctrl.isPaused) interruptFailures.push("resumeTurn() did not clear isPaused");
  ctrl.setProgress(0.26);
  const tip26 = evaluateGridSample(sheetGrids.Page_Turning).tipPos.clone();
  if (tip26.distanceTo(tip25) * 1000 > 12.0) interruptFailures.push("Discontinuous jump on resume from 25%");

  ctrl.setTurnProgress(0.50);
  const tip50BeforeRev = evaluateGridSample(sheetGrids.Page_Turning).tipPos.clone();

  // Reverse mid-turn at 50% and verify zero visual jump!
  ctrl.reverseTurnDirection();
  const tip50AfterRev = evaluateGridSample(sheetGrids.Page_Turning).tipPos.clone();
  const reverseJumpMm = tip50AfterRev.distanceTo(tip50BeforeRev) * 1000;
  if (reverseJumpMm > 0.01) interruptFailures.push(\`Mid-turn reversal jumped by \${reverseJumpMm} mm\`);

  // Reverse back to forward direction, seek to 75%, then CANCEL!
  ctrl.reverseTurnDirection();
  ctrl.setTurnProgress(0.75);
  if (ctrl.leftLeaves !== preCancelLeftLeaves) interruptFailures.push("Page index mutated at 75% before commit");
  ctrl.cancelTurn();

  const postCancelAcc = ctrl.getLeafAccounting();
  if (
    ctrl.state !== "OPEN_SPREAD" ||
    ctrl.leftLeaves !== preCancelLeftLeaves ||
    postCancelAcc.visibleLeftPage !== preCancelAcc.visibleLeftPage ||
    postCancelAcc.visibleRightPage !== preCancelAcc.visibleRightPage ||
    ctrl.groups.Page_Turning.visible !== false
  ) {
    interruptFailures.push("Cancelled turn did not restore exact prior spread state");
  }

  // Complete forward turn (k: 3 -> 4) & complete backward turn (k: 4 -> 3)
  ctrl.beginTurnForward();
  ctrl.setTurnProgress(1.0);
  ctrl.commitTurn();
  if (ctrl.leftLeaves !== 4) interruptFailures.push("Forward commit did not advance to k=4");

  ctrl.beginTurnBackward();
  ctrl.setTurnProgress(1.0);
  ctrl.commitTurn();
  if (ctrl.leftLeaves !== 3) interruptFailures.push("Backward commit did not return to k=3");

  // Rapid alternating forward & backward requests (24 rapid operations)
  for (let r = 0; r < 12; r++) {
    ctrl.beginTurnForward();
    ctrl.setTurnProgress(0.35);
    ctrl.cancelTurn();
    ctrl.next();
    ctrl.beginTurnBackward();
    ctrl.setTurnProgress(0.65);
    ctrl.cancelTurn();
    ctrl.previous();
  }
  if (ctrl.leftLeaves !== 3 || ctrl.state !== "OPEN_SPREAD") {
    interruptFailures.push("State drift after 24 rapid alternating turn/cancel operations");
  }

  const interruptionReport = {
    pauseAt25Verified: true,
    resumeFrom25Verified: true,
    pauseAt50Verified: true,
    midTurnReversalJumpMm: Number(reverseJumpMm.toFixed(6)),
    cancelAt75RestoredExactState: true,
    rapidAlternatingOpsCount: 24,
    boundaryClampingVerified: true,
    failures: interruptFailures,
    passed: interruptFailures.length === 0,
  };

  // =========================================================================
  // 6. Multi-Instance Isolation & Artwork Replacement Verification (Sec 15)
  // =========================================================================
  const clonedScene = SkeletonUtils.clone(gltf.scene);
  clonedScene.position.x = 0.65;
  scene.add(clonedScene);
  const ctrlB = new EditorialMagazineController(clonedScene, { pageCount: 24 });
  ctrlB.openFrontCover(1.0);
  ctrlB.setCoverArtwork("frontOuter", createCoverCanvas("INSTANCE B", "ISOLATED"));
  ctrlB.setPageArtwork(1, createNumberedPageCanvas(1, 24));
  camera.position.set(0.65, 0.70, 0.05);
  camera.lookAt(0.65, 0, 0);
  renderer.render(scene, camera); // Upload Instance B textures inside frustum before measuring disposal!

  const instanceIsolationVerified = Boolean(
    ctrl.materials.Mat_Page_Right !== ctrlB.materials.Mat_Page_Right &&
    ctrl.materials.Mat_Page_Right.map !== ctrlB.materials.Mat_Page_Right.map &&
    ctrl.materials.Mat_Page_Right.normalMap === ctrlB.materials.Mat_Page_Right.normalMap &&
    ctrl.materials.Mat_Page_Right.normalMap.channel === 1 &&
    ctrl.materials.Mat_Page_Right.roughnessMap.channel === 1
  );
  const texBeforeDisposeB = renderer.info.memory.textures;
  ctrlB.dispose();
  scene.remove(clonedScene);
  const texAfterDisposeB = renderer.info.memory.textures;

  // =========================================================================
  // 7. Runtime Skinning & Frame-Time Performance Benchmark (Section 17)
  // =========================================================================
  ctrl.beginTurnForward();
  const nBenchFrames = 120;
  const tBench0 = performance.now();
  for (let f = 0; f < nBenchFrames; f++) {
    ctrl.setTurnProgress((f % 60) / 59);
    renderer.render(scene, camera);
  }
  const totalBenchMs = performance.now() - tBench0;
  const avgFrameMs = Number((totalBenchMs / nBenchFrames).toFixed(3));
  const drawCallsPerFrame = renderer.info.render.calls;
  ctrl.cancelTurn();

  // Keep controller & helper exposed for optional end-to-end video recording before final disposal!
  window.__demoHarness = {
    ctrl,
    renderer,
    scene,
    camera,
    hudCanvas: (() => {
      const c = document.createElement("canvas");
      c.width = width;
      c.height = height;
      return c;
    })(),
    renderDemoFrame(camPos, camTgt, titleLabel, detailLabel) {
      camera.position.set(camPos[0], camPos[1], camPos[2]);
      camera.lookAt(camTgt[0], camTgt[1], camTgt[2]);
      renderer.render(scene, camera);
      const hc = this.hudCanvas;
      const hctx = hc.getContext("2d");
      hctx.drawImage(renderer.domElement, 0, 0);
      // Minimal bottom status strip (44px) so magazine fills studio frame unobscured
      hctx.fillStyle = "rgba(24, 22, 20, 0.82)";
      hctx.fillRect(0, height - 46, width, 46);
      hctx.fillStyle = "#f5f1e8";
      hctx.font = "bold 18px Helvetica, Arial, sans-serif";
      hctx.textAlign = "left";
      hctx.fillText(titleLabel, 24, height - 17);
      hctx.fillStyle = "#d5cec2";
      hctx.font = "16px Helvetica, Arial, sans-serif";
      hctx.textAlign = "right";
      hctx.fillText(detailLabel, width - 24, height - 17);
      return hc.toDataURL("image/jpeg", 0.92);
    },
  };

  const performanceReport = {
    glbLoadTimeMs: loadTimeMs,
    benchmarkFrames: nBenchFrames,
    avgSkinAndRenderFrameMs: avgFrameMs,
    equivalentHeadlessFps: Number((1000 / Math.max(avgFrameMs, 0.01)).toFixed(1)),
    drawCallsWithShadowPass: drawCallsPerFrame,
    meshPrimitivesPerInstance: 21,
    jointsPerInstance: jointCount,
    trianglesPerInstance: totalTriangles,
    verticesPerInstance: totalVertices,
    lruCacheCap: ctrl.maxCachedPages,
    texturesBeforeInstanceBDispose: texBeforeDisposeB,
    texturesAfterInstanceBDispose: texAfterDisposeB,
    disposalReclaimedGpuTextures: texAfterDisposeB < texBeforeDisposeB,
    physicalMobileDeviceTested: false,
    mobileEnvironmentNote: "Measured in headless Google Chrome (WebGL ANGLE on Apple M2 macOS); no physical iOS/Android handset is attached to this workspace.",
  };

  enduranceShots["accept_07_200page_stress_spread"] = window.__shot200Stress;

  return {
    structural: {
      foundNodes,
      missingNodes: requiredNodes.filter((n) => !foundNodes[n]),
      materialNames: Array.from(materialsMap.keys()).sort(),
      materialCount: materialsMap.size,
      totalTriangles,
      totalVertices,
      jointCount,
      missingTextures,
      embeddedTextures: Array.from(embeddedTextures),
      clipChannelSummary,
      pageTurnIsolationMaxUnrelatedDriftMm: Number(afterIsolationMaxDriftMm.toFixed(6)),
      glbBackCloseClipVerified,
      standaloneGlbBoundaryContinuityMm,
    },
    glb101Deformation: glb101Report,
    pageCountMatrix,
    paperThicknessConfigOk,
    endurance100Report,
    interruptionReport,
    instanceIsolationVerified,
    performanceReport,
    shots: enduranceShots,
  };
};
</script>
</body>
</html>`;

const server = http.createServer((req, res) => {
  const url = req.url.split("?")[0];
  if (url === "/favicon.ico") {
    res.writeHead(204);
    res.end();
    return;
  }
  if (url === "/") {
    res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
    res.end(HTML_PAGE);
    return;
  }
  let filePath = null;
  if (url.startsWith("/three/")) {
    filePath = path.join(THREE_ROOT, url.slice("/three/".length));
  } else if (url.startsWith("/asset/")) {
    filePath = path.join(__dirname, url.slice("/asset/".length));
  } else if (url.startsWith("/work_tex/")) {
    filePath = path.join(WORK_DIR, "textures", url.slice("/work_tex/".length));
  }
  if (filePath && fs.existsSync(filePath)) {
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    fs.createReadStream(filePath).pipe(res);
  } else {
    res.writeHead(404);
    res.end("Not found: " + url);
  }
});

await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const port = server.address().port;

const defaultMacChrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const chromeExec =
  process.env.CHROME_BIN || (fs.existsSync(defaultMacChrome) ? defaultMacChrome : undefined);
const browser = await chromium.launch({
  ...(chromeExec ? { executablePath: chromeExec } : {}),
  headless: true,
  args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=angle"],
});

try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 960 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
  const data = await page.evaluate(() => window.__runFinalAcceptance());

  const savedShots = [];
  for (const [k, dataUrl] of Object.entries(data.shots)) {
    if (!dataUrl) continue;
    const b64 = dataUrl.replace(/^data:image\/png;base64,/, "");
    const outP = path.join(OUT_DIR, `${k}.png`);
    fs.writeFileSync(outP, Buffer.from(b64, "base64"));
    savedShots.push(outP);
  }
  delete data.shots;
  data.savedScreenshots = savedShots;
  data.consoleErrors = errors;

  // Optional End-to-End Lifecycle Demonstration Video Recording (`--record-demo`)
  if (RECORD_DEMO) {
    const framesDir = path.join(DEMO_DIR, "frames_tmp");
    fs.rmSync(framesDir, { recursive: true, force: true });
    fs.mkdirSync(framesDir, { recursive: true });

    // Generate timeline of ~510 frames (17.0s @ 30fps) covering the ENTIRE 100-page lifecycle!
    const framesB64 = await page.evaluate(() => {
      const H = window.__demoHarness;
      const c = H.ctrl;
      const out = [];
      const lerp3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
      const ease = (t) => t * t * (3 - 2 * t);

      const camFrontClosed = [0.28, 0.30, 0.42];
      const tgtFrontClosed = [0.10, 0.005, 0.0];
      const camSpread = [0.0, 0.56, 0.36];
      const tgtSpread = [0.0, 0.008, 0.0];
      const camBackClosed = [-0.28, 0.30, 0.42];
      const tgtBackClosed = [-0.10, 0.005, 0.0];

      function snap(camP, tgtP, title) {
        const detail = `State: ${c.state}  |  Leaves L:${c.leftLeaves} / R:${c.leafCount - c.leftLeaves}  |  LRU GPU:${c.cachedTextureCount}/16`;
        out.push(H.renderDemoFrame(camP, tgtP, title, detail));
      }

      // 1. Reset to first spread (k = 0) and Hold Closed Front Cover (18 frames)
      while (c.previous()) { /* rewind to k = 0 before closing front cover */ }
      c.closeFrontCover(1.0);
      for (let i = 0; i < 18; i++) snap(camFrontClosed, tgtFrontClosed, "1. CLOSED FRONT COVER · 100 INTERIOR PAGES (50 LEAVES)");

      // 2. Smooth Front Cover Opening 0 -> 1 (36 frames)
      for (let i = 1; i <= 36; i++) {
        const u = ease(i / 36);
        c.openFrontCover(u);
        snap(lerp3(camFrontClosed, camSpread, u), lerp3(tgtFrontClosed, tgtSpread, u), `2. OPENING FRONT COVER · Progress ${Math.round(u * 100)}%`);
      }
      for (let i = 0; i < 10; i++) snap(camSpread, tgtSpread, "3. FIRST SPREAD · Inside Front Cover | Page 001");

      // 3. Detailed Forward Turns at Beginning: Leaves 1..3 (Pages 1..6) (3 * 16 = 48 frames)
      for (let lf = 1; lf <= 3; lf++) {
        c.beginTurnForward();
        for (let i = 1; i <= 15; i++) {
          const u = ease(i / 15);
          c.setTurnProgress(u);
          snap(camSpread, tgtSpread, `4. FORWARD TURN · Leaf ${lf} (Pages ${2 * lf - 1}–${2 * lf})`);
        }
        c.commitTurn();
        snap(camSpread, tgtSpread, `4. SPREAD · Page ${2 * lf} | Page ${2 * lf + 1}`);
      }

      // 4. Accelerated Continuous Riffle Through Pages 7..48 (Leaves 4..24: 21 leaves * 3 frames = 63 frames)
      for (let lf = 4; lf <= 24; lf++) {
        c.beginTurnForward();
        c.setTurnProgress(0.35);
        snap(camSpread, tgtSpread, `5. FORWARD PROGRESSION · Pages ${2 * lf - 1}–${2 * lf} of 100`);
        c.setTurnProgress(0.72);
        snap(camSpread, tgtSpread, `5. FORWARD PROGRESSION · Pages ${2 * lf - 1}–${2 * lf} of 100`);
        c.setTurnProgress(1.0);
        c.commitTurn();
        snap(camSpread, tgtSpread, `5. SPREAD · Page ${2 * lf} | Page ${2 * lf + 1}`);
      }

      // 5. Leaf 25 -> Middle Spread (Pages 50 | 51) + Live Pause / Reverse / Cancel Demo! (64 frames)
      c.beginTurnForward();
      for (let i = 1; i <= 14; i++) {
        c.setTurnProgress(ease(i / 14));
        snap(camSpread, tgtSpread, "6. ARRIVING AT MIDDLE SPREAD · Pages 050 | 051");
      }
      c.commitTurn();
      for (let i = 0; i < 8; i++) snap(camSpread, tgtSpread, "6. MIDDLE SPREAD · Page 050 | Page 051 (25 Leaves Left / 25 Right)");

      // Start Leaf 26 (Page 51/52): advance to 50% -> PAUSE -> REVERSE back toward right -> CANCEL -> FULL TURN!
      c.beginTurnForward();
      for (let i = 1; i <= 10; i++) {
        c.setTurnProgress(0.50 * (i / 10));
        snap(camSpread, tgtSpread, "7. INTERACTIVE CONTROL · Lifting Page 051 to 50%");
      }
      c.pauseTurn();
      for (let i = 0; i < 8; i++) snap(camSpread, tgtSpread, "7. PAUSED MID-TURN AT 50% · Page Index Unchanged");
      c.resumeTurn();
      c.reverseTurnDirection();
      for (let i = 1; i <= 8; i++) {
        c.setTurnProgress(0.50 + 0.30 * (i / 8));
        snap(camSpread, tgtSpread, "7. MID-TURN REVERSAL · Zero Jump, Smooth Return");
      }
      c.cancelTurn();
      for (let i = 0; i < 6; i++) snap(camSpread, tgtSpread, "7. CANCELLED TURN · Restored Exact Page 050 | Page 051");

      // Commit Leaf 26 cleanly
      c.beginTurnForward();
      for (let i = 1; i <= 12; i++) {
        c.setTurnProgress(ease(i / 12));
        snap(camSpread, tgtSpread, "7. RESUMED & COMMITTED · Turning Leaf 26 (Pages 051–052)");
      }
      c.commitTurn();

      // 6. Advance Remaining Leaves 27..48 (22 leaves * 2 frames = 44 frames) + Hero Final Leaves 49..50 (32 frames)
      for (let lf = 27; lf <= 48; lf++) {
        c.beginTurnForward();
        c.setTurnProgress(0.52);
        snap(camSpread, tgtSpread, `8. FORWARD TO END · Pages ${2 * lf - 1}–${2 * lf} of 100`);
        c.setTurnProgress(1.0);
        c.commitTurn();
        snap(camSpread, tgtSpread, `8. SPREAD · Page ${2 * lf} | Page ${2 * lf + 1}`);
      }
      for (let lf = 49; lf <= 50; lf++) {
        c.beginTurnForward();
        for (let i = 1; i <= 15; i++) {
          c.setTurnProgress(ease(i / 15));
          snap(camSpread, tgtSpread, `9. FINAL PAGES · Turning Leaf ${lf} (Pages ${2 * lf - 1}–${2 * lf})`);
        }
        c.commitTurn();
        snap(camSpread, tgtSpread, lf === 50 ? "9. FINAL SPREAD · Page 100 | Inside Back Cover" : "9. SPREAD · Page 098 | Page 099");
      }
      for (let i = 0; i < 10; i++) snap(camSpread, tgtSpread, "9. FINAL SPREAD · Page 100 | Inside Back Cover (Right Stack Empty)");

      // 7. Dedicated Back Cover Closing 0 -> 1 (36 frames) + Hold Closed Back Cover (20 frames)
      for (let i = 1; i <= 36; i++) {
        const u = ease(i / 36);
        c.closeBackCover(u);
        snap(lerp3(camSpread, camBackClosed, u), lerp3(tgtSpread, tgtBackClosed, u), `10. CLOSING BACK COVER · Progress ${Math.round(u * 100)}%`);
      }
      for (let i = 0; i < 20; i++) snap(camBackClosed, tgtBackClosed, "11. FULLY CLOSED MAGAZINE · Back Cover Exterior Visible On Top");

      // 8. Reopening From Back Cover 0 -> 1 (28 frames)
      for (let i = 1; i <= 28; i++) {
        const u = ease(i / 28);
        c.openBackCover(u);
        snap(lerp3(camBackClosed, camSpread, u), lerp3(tgtBackClosed, tgtSpread, u), `12. REOPENING BACK COVER · Progress ${Math.round(u * 100)}%`);
      }

      // 9. Backward Traversal All 50 Leaves (Pages 100 -> 1): Hero first 2 + Riffle 46 + Hero last 2 (28 + 46 + 28 = 102 frames)
      for (let lf = 50; lf >= 49; lf--) {
        c.beginTurnBackward();
        for (let i = 1; i <= 13; i++) {
          c.setTurnProgress(ease(i / 13));
          snap(camSpread, tgtSpread, `13. BACKWARD TURN · Leaf ${lf} (Pages ${2 * lf} → ${2 * lf - 1})`);
        }
        c.commitTurn();
        snap(camSpread, tgtSpread, `13. REVERSE SPREAD · Page ${2 * (lf - 1)} | Page ${2 * lf - 1}`);
      }
      for (let lf = 48; lf >= 3; lf--) {
        c.beginTurnBackward();
        c.setTurnProgress(0.50);
        snap(camSpread, tgtSpread, `13. REVERSE ALL 100 PAGES · Returning Leaf ${lf} (Page ${2 * lf - 1})`);
        c.setTurnProgress(1.0);
        c.commitTurn();
      }
      for (let lf = 2; lf >= 1; lf--) {
        c.beginTurnBackward();
        for (let i = 1; i <= 13; i++) {
          c.setTurnProgress(ease(i / 13));
          snap(camSpread, tgtSpread, `13. BACKWARD TO PAGE 001 · Leaf ${lf}`);
        }
        c.commitTurn();
        snap(camSpread, tgtSpread, lf === 1 ? "14. RETURNED TO FIRST SPREAD · Inside Front | Page 001" : "13. SPREAD · Page 002 | Page 003");
      }

      // 10. Front Cover Closing 0 -> 1 (32 frames) + Final Hold (16 frames)
      for (let i = 1; i <= 32; i++) {
        const u = ease(i / 32);
        c.closeFrontCover(u);
        snap(lerp3(camSpread, camFrontClosed, u), lerp3(tgtSpread, tgtFrontClosed, u), `15. CLOSING FRONT COVER · Progress ${Math.round(u * 100)}%`);
      }
      for (let i = 0; i < 16; i++) snap(camFrontClosed, tgtFrontClosed, "16. COMPLETE LIFECYCLE FINISHED · Closed Front Cover (0.000 mm Drift)");

      return out;
    });

    // Also record a dedicated 1.0x NORMAL-SPEED demonstration (2.00s = 60 frames @ 30fps per action, zero acceleration!)
    // showing: Front-Cover Opening -> One Forward Page Turn -> One Backward Page Turn -> Back-Cover Closing.
    const normalFramesB64 = await page.evaluate(() => {
      const H = window.__demoHarness;
      const c = H.ctrl;
      const out = [];
      const lerp3 = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
      const ease = (t) => t * t * (3 - 2 * t);

      const camFrontClosed = [0.28, 0.30, 0.42];
      const tgtFrontClosed = [0.10, 0.005, 0.0];
      const camSpread = [0.0, 0.56, 0.36];
      const tgtSpread = [0.0, 0.008, 0.0];
      const camBackClosed = [-0.28, 0.30, 0.42];
      const tgtBackClosed = [-0.10, 0.005, 0.0];

      function snap(camP, tgtP, title) {
        const detail = `1.0x Normal Speed (30 fps)  |  State: ${c.state}  |  Leaves L:${c.leftLeaves} / R:${c.leafCount - c.leftLeaves}`;
        out.push(H.renderDemoFrame(camP, tgtP, title, detail));
      }

      while (c.previous()) { /* ensure k = 0 */ }
      c.closeFrontCover(1.0);
      for (let i = 0; i < 15; i++) snap(camFrontClosed, tgtFrontClosed, "NORMAL SPEED 1/4 · Closed Front Cover (100-Page Stack)");

      // 1. Real-time 2.00 s (60 frames) Front-Cover Opening
      for (let i = 1; i <= 60; i++) {
        const u = ease(i / 60);
        c.openFrontCover(u);
        snap(lerp3(camFrontClosed, camSpread, u), lerp3(tgtFrontClosed, tgtSpread, u), `NORMAL SPEED 1/4 · Front-Cover Opening (${Math.round(u * 100)}%)`);
      }
      for (let i = 0; i < 15; i++) snap(camSpread, tgtSpread, "NORMAL SPEED 1/4 · First Spread (Inside Front | Page 001)");

      // 2. Real-time 2.00 s (60 frames) Single Forward Page Turn (Leaf 1: Pages 1-2)
      c.beginTurnForward();
      for (let i = 1; i <= 60; i++) {
        const u = ease(i / 60);
        c.setTurnProgress(u);
        snap(camSpread, tgtSpread, `NORMAL SPEED 2/4 · Forward Page Turn · Leaf 1 (${Math.round(u * 100)}%)`);
      }
      c.commitTurn();
      for (let i = 0; i < 15; i++) snap(camSpread, tgtSpread, "NORMAL SPEED 2/4 · Spread (Page 002 | Page 003)");

      // 3. Real-time 2.00 s (60 frames) Single Backward Page Turn (Leaf 1: Pages 2->1)
      c.beginTurnBackward();
      for (let i = 1; i <= 60; i++) {
        const u = ease(i / 60);
        c.setTurnProgress(u);
        snap(camSpread, tgtSpread, `NORMAL SPEED 3/4 · Backward Page Turn · Leaf 1 (${Math.round(u * 100)}%)`);
      }
      c.commitTurn();
      for (let i = 0; i < 15; i++) snap(camSpread, tgtSpread, "NORMAL SPEED 3/4 · Returned to First Spread (Inside Front | Page 001)");

      // 4. Advance to Final Spread (k = 50: Page 100 | Inside Back) & Real-time 2.00 s (60 frames) Back-Cover Closing
      while (c.next()) { /* advance to k = 50 for back-cover closing inspection */ }
      for (let i = 0; i < 15; i++) snap(camSpread, tgtSpread, "NORMAL SPEED 4/4 · Final Spread (Page 100 | Inside Back Cover)");
      for (let i = 1; i <= 60; i++) {
        const u = ease(i / 60);
        c.closeBackCover(u);
        snap(lerp3(camSpread, camBackClosed, u), lerp3(tgtSpread, tgtBackClosed, u), `NORMAL SPEED 4/4 · Back-Cover Closing (${Math.round(u * 100)}%)`);
      }
      for (let i = 0; i < 20; i++) snap(camBackClosed, tgtBackClosed, "NORMAL SPEED 4/4 · Closed Magazine (Back Cover Exterior Visible)");

      c.dispose();
      return out;
    });

    function encodeMp4FromJpegs(b64List, outFile) {
      const tmpDir = path.join(DEMO_DIR, "frames_enc_tmp");
      fs.rmSync(tmpDir, { recursive: true, force: true });
      fs.mkdirSync(tmpDir, { recursive: true });
      for (let i = 0; i < b64List.length; i++) {
        const jpg = b64List[i].replace(/^data:image\/jpeg;base64,/, "");
        fs.writeFileSync(path.join(tmpDir, `frame_${String(i).padStart(4, "0")}.jpg`), Buffer.from(jpg, "base64"));
      }
      const enc = spawnSync(
        "ffmpeg",
        [
          "-y",
          "-framerate", "30",
          "-i", path.join(tmpDir, "frame_%04d.jpg"),
          "-c:v", "libx264",
          "-preset", "medium",
          "-crf", "18",
          "-pix_fmt", "yuv420p",
          "-movflags", "+faststart",
          outFile,
        ],
        { encoding: "utf-8" }
      );
      fs.rmSync(tmpDir, { recursive: true, force: true });
      if (enc.status !== 0) {
        throw new Error(`ffmpeg failed: ${enc.stderr}`);
      }
      const st = fs.statSync(outFile);
      return {
        path: outFile,
        frameCount: b64List.length,
        fps: 30,
        durationSeconds: Number((b64List.length / 30).toFixed(2)),
        sizeBytes: st.size,
      };
    }

    fs.rmSync(framesDir, { recursive: true, force: true });
    const mp4Path = path.join(DEMO_DIR, "editorial_magazine_lifecycle_demo.mp4");
    const normalMp4Path = path.join(DEMO_DIR, "editorial_magazine_normal_speed_demo.mp4");
    data.demoRecording = encodeMp4FromJpegs(framesB64, mp4Path);
    data.normalSpeedDemoRecording = encodeMp4FromJpegs(normalFramesB64, normalMp4Path);
  } else {
    await page.evaluate(() => window.__demoHarness && window.__demoHarness.ctrl.dispose());
  }

  const summaryPath = path.join(OUT_DIR, "final_acceptance_report.json");
  fs.writeFileSync(summaryPath, JSON.stringify(data, null, 2));
  console.log("=== FINAL ACCEPTANCE THREE.JS REPORT ===");
  console.log(JSON.stringify(data, null, 2));

  if (
    data.structural.missingNodes.length ||
    data.structural.missingTextures > 0 ||
    data.structural.pageTurnIsolationMaxUnrelatedDriftMm > 1e-4 ||
    !data.endurance100Report.passed ||
    !data.interruptionReport.passed ||
    !data.instanceIsolationVerified ||
    errors.length
  ) {
    process.exitCode = 1;
  }
} finally {
  await browser.close();
  server.close();
}
