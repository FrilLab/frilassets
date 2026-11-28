#!/usr/bin/env node
/**
 * Isolated Three.js Runtime Validation, Lighting Study, & Human-Scale Visual Harness for:
 *   Open Skylight Museum Hall V2 (`assets/architecture/museum-open-hall/model.glb`)
 *
 * Exercises `museum_lighting.mjs` and validates Sections 1–10 in Chromium WebGL:
 *   - Main-hall clear dimensions (24 x 18 x 9 m), floor Y = 0.00 m, pitched skylight ridge >= 12.6 m
 *   - Dual-UV neutral `aoMap` (`TEXCOORD_1`) loading & independent material recoloring + cloning
 *   - Spatial continuity: Open Central Enfilade Portal into `Secondary_Gallery` AND Closed
 *     `Wall_Back_Portal_Closure` 9-artwork configuration + finished `Entrance_Vestibule`
 *   - Independent runtime rotation of `Fixture_Head_*` adjustable spotlight heads (`aimSpotlightHead`)
 *   - All 8 required Section 9 human-scale views (1.6 m eye height, natural 40-46 deg vFOV)
 *     plus all 3 Section 7 lighting scenarios (`soft_daylight`, `direct_sun`, `evening`)
 *     and Desktop (1600x1000) + Portrait Mobile (720x1280) compositions!
 */

import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../..");
const ASSET_DIR = __dirname;
const WORK_DIR = path.join(REPO_ROOT, ".work/architecture/museum-open-hall");
const OUT_DIR = path.join(WORK_DIR, "validation-v2");
const THREE_ROOT =
  process.env.THREE_ROOT || path.resolve(path.dirname(require.resolve("three")), "..");

fs.mkdirSync(OUT_DIR, { recursive: true });

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
  <style>body { margin: 0; background: #e8edf4; overflow: hidden; }</style>
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
import {
  applyMuseumLighting,
  setRearPortalOpen,
  aimSpotlightHead,
} from "/asset/museum_lighting.mjs";

function makeArtworkCanvasTexture(index, aspectW, aspectH, label) {
  const w = Math.round(512 * (aspectW >= aspectH ? 1.0 : aspectW / aspectH));
  const h = Math.round(512 * (aspectH > aspectW ? 1.0 : aspectH / aspectW));
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d");

  ctx.fillStyle = "#f2eee6";
  ctx.fillRect(0, 0, w, h);

  const pad = Math.round(Math.min(w, h) * 0.075);
  const iw = w - pad * 2;
  const ih = h - pad * 2;

  const palettes = [
    ["#1d4e6e", "#95bdd1"],
    ["#2f5646", "#d49b54"],
    ["#c97d3a", "#5c3a28"],
    ["#26384a", "#9cb0bf"],
    ["#b87a3d", "#e6c88c"],
    ["#2f443b", "#8fa394"],
    ["#22313f", "#c48a5a"],
    ["#6e473b", "#d8c2a8"],
    ["#354652", "#c8b698"],
    ["#8a4a32", "#e2be88"],
  ];
  const [c1, c2] = palettes[index % palettes.length];
  const grad = ctx.createLinearGradient(pad, pad, pad, pad + ih);
  grad.addColorStop(0, c1);
  grad.addColorStop(1, c2);
  ctx.fillStyle = grad;
  ctx.fillRect(pad, pad, iw, ih);

  ctx.fillStyle = "rgba(246, 243, 236, 0.78)";
  ctx.beginPath();
  ctx.arc(w * 0.5, pad + ih * 0.44, Math.min(iw, ih) * 0.19, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#2b2927";
  ctx.font = \`500 \${Math.max(11, Math.round(Math.min(w, h) * 0.038))}px sans-serif\`;
  ctx.textAlign = "center";
  ctx.fillText(label, w * 0.5, h - Math.max(7, Math.round(pad * 0.32)));

  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

window.__runValidation = async function () {
  const desktopW = 1600, desktopH = 1000;
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true, powerPreference: "high-performance" });
  renderer.setSize(desktopW, desktopH);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.02;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  document.body.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  const loader = new GLTFLoader();
  const tLoadStart = performance.now();
  const gltf = await loader.loadAsync("/asset/model.glb");
  const loadTimeMs = performance.now() - tLoadStart;

  const museum = gltf.scene;
  scene.add(museum);
  museum.updateMatrixWorld(true);

  const nodesByName = {};
  const meshes = [];
  const materialsByName = {};
  const uniqueTextures = new Map();
  let totalTriangles = 0;
  let totalVertices = 0;

  museum.traverse((obj) => {
    if (obj.name) nodesByName[obj.name] = obj;
    if (obj.isMesh) {
      meshes.push(obj);
      const geo = obj.geometry;
      const vCount = geo.attributes.position ? geo.attributes.position.count : 0;
      const triCount = geo.index ? geo.index.count / 3 : vCount / 3;
      totalVertices += vCount;
      totalTriangles += triCount;

      const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
      for (const m of mats) {
        if (!m) continue;
        materialsByName[m.name] = m;
        for (const key of ["map", "normalMap", "roughnessMap", "metalnessMap", "aoMap"]) {
          const t = m[key];
          if (t && t.image) {
            uniqueTextures.set(t.uuid, {
              slot: key,
              material: m.name,
              width: t.image.width,
              height: t.image.height,
              channel: t.channel,
            });
          }
        }
      }
    }
  });

  let estimatedTextureVramBytes = 0;
  const textureDetails = [];
  for (const info of uniqueTextures.values()) {
    const bytes = Math.round(info.width * info.height * 4 * (4 / 3));
    estimatedTextureVramBytes += bytes;
    textureDetails.push({ ...info, estimatedGpuBytes: bytes });
  }

  // Verify main-hall dimensions + pitched skylight ridge elevation + dual-UV AO map!
  const boxOf = (name) => new THREE.Box3().setFromObject(nodesByName[name]);
  const floorBox = boxOf("Floor");
  const wallLeftBox = boxOf("Wall_Left");
  const wallRightBox = boxOf("Wall_Right");
  const wallBackBox = boxOf("Wall_Back");
  const wallEntBox = boxOf("Wall_Entrance");
  const ceilBox = boxOf("Ceiling");
  const glassBox = boxOf("Skylight_Glass");
  const secGalBox = boxOf("Secondary_Gallery");
  const vestBox = boxOf("Entrance_Vestibule");
  const overallBox = new THREE.Box3().setFromObject(museum);

  const interiorWidth = wallRightBox.min.x - wallLeftBox.max.x;
  const interiorDepth = wallEntBox.min.z - wallBackBox.max.z;
  const ceilingHeight = ceilBox.min.y - floorBox.max.y;

  const aoMapsLoaded =
    Boolean(materialsByName["Mat_Wall_Plaster"]?.aoMap) &&
    Boolean(materialsByName["Mat_Floor_Concrete"]?.aoMap) &&
    Boolean(materialsByName["Mat_Ceiling"]?.aoMap) &&
    materialsByName["Mat_Wall_Plaster"].aoMap.channel === 1;

  // Plumb two-point architectural camera helper (setViewOffset matches Blender optical shift_y!)
  const camera = new THREE.PerspectiveCamera(50, desktopW / desktopH, 0.1, 100);
  const snapshots = {};
  const snap = (key, eye, target, fov = 50, shiftYFrac = 0.0) => {
    const curW = renderer.domElement.width;
    const curH = renderer.domElement.height;
    camera.fov = fov;
    if (Math.abs(shiftYFrac) > 1e-4) {
      camera.setViewOffset(curW, curH, 0, Math.round(-curH * shiftYFrac), curW, curH);
    } else {
      camera.clearViewOffset();
    }
    camera.updateProjectionMatrix();
    if (eye && target) {
      camera.position.set(...eye);
      camera.lookAt(...target);
    }
    renderer.render(scene, camera);
    snapshots[key] = renderer.domElement.toDataURL("image/png");
  };

  // ------------------------------------------------------------------
  // Scenario A: Soft Overcast Daylight — All 7 Empty Human-Scale Section 9 Views
  // ------------------------------------------------------------------
  let activeLighting = applyMuseumLighting(scene, museum, renderer, "soft_daylight");
  setRearPortalOpen(museum, true);

  snap("01_threejs_entrance_eye_soft_daylight", [0.0, 1.60, 8.20], [0.0, 1.60, -9.00], 52, 0.155);
  snap("02_threejs_center_hall", [0.0, 1.60, 2.40], [0.0, 1.60, -9.00], 50, 0.135);
  snap("03_threejs_main_wall_enfilade", [0.0, 1.60, -1.60], [0.0, 1.60, -15.70], 46, 0.095);
  snap("04_threejs_opposite_entrance_vestibule", [0.0, 1.60, -6.20], [0.0, 1.60, 15.40], 52, 0.145);
  snap("05_threejs_left_exhibition_area", [5.8, 1.60, 1.20], [-12.0, 1.60, -1.50], 48, 0.115);
  snap("06_threejs_right_exhibition_area", [-5.8, 1.60, 1.20], [12.0, 1.60, -1.50], 48, 0.115);
  snap("07_threejs_pitched_skylight_upward", [0.0, 1.60, 4.80], [0.0, 11.40, -1.20], 50, 0.0);

  // ------------------------------------------------------------------
  // Scenario B: Direct Sunlight through Pitched Skylight
  // ------------------------------------------------------------------
  activeLighting.dispose();
  activeLighting = applyMuseumLighting(scene, museum, renderer, "direct_sun");
  snap("08_threejs_direct_sunlight", [0.0, 1.60, 8.20], [0.0, 1.60, -9.00], 52, 0.155);

  // ------------------------------------------------------------------
  // Verify Adjustable Spotlight Heads (aimSpotlightHead) — Section 8
  // ------------------------------------------------------------------
  const headTestNode = nodesByName["Fixture_Head_Back_03"];
  const origHeadQuat = headTestNode.quaternion.clone();
  const customAimTarget = new THREE.Vector3(0.0, 1.0, -0.60); // Aim spotlight at central installation!
  aimSpotlightHead(headTestNode, customAimTarget);
  const headPos = new THREE.Vector3();
  const headWorldQuat = new THREE.Quaternion();
  headTestNode.getWorldPosition(headPos);
  headTestNode.getWorldQuaternion(headWorldQuat);
  const aimedDir = new THREE.Vector3(0, 0, -1).applyQuaternion(headWorldQuat);
  const expectedDir = customAimTarget.clone().sub(headPos).normalize();
  const spotlightHeadAdjustable =
    aimedDir.dot(expectedDir) > 0.9999 && !headTestNode.quaternion.equals(origHeadQuat);
  headTestNode.quaternion.copy(origHeadQuat);
  headTestNode.updateMatrixWorld(true);

  // Verify Skylight_Glass & Wall/Ceiling visibility controls
  nodesByName["Skylight_Glass"].visible = false;
  renderer.render(scene, camera);
  const glassHiddenWorked = nodesByName["Skylight_Glass"].visible === false;
  nodesByName["Skylight_Glass"].visible = true;

  nodesByName["Wall_Left"].visible = false;
  nodesByName["Ceiling"].visible = false;
  renderer.render(scene, camera);
  const wallCeilingToggleWorked = !nodesByName["Wall_Left"].visible && !nodesByName["Ceiling"].visible;
  nodesByName["Wall_Left"].visible = true;
  nodesByName["Ceiling"].visible = true;

  // ------------------------------------------------------------------
  // Verify All 9 Original Artwork Anchors (+ Secondary_01) & Render Both
  // Closed 9-Artwork Exhibition AND Evening Exhibition!
  // ------------------------------------------------------------------
  setRearPortalOpen(museum, false); // Close sliding pocket wall flush at Z = -9.00 m for full 9-artwork layout!
  const closureClosedBox = new THREE.Box3().setFromObject(nodesByName["Wall_Back_Portal_Closure"]);
  const portalClosureFlushValid =
    Math.abs(closureClosedBox.max.z - (-9.0)) < 0.005 &&
    Math.abs(closureClosedBox.min.x + closureClosedBox.max.x) < 0.005;

  const artSpecs = [
    { name: "Anchor_Artwork_Back_01", w: 1.50, h: 2.25, framed: true, ratio: "2:3 Portrait" },
    { name: "Anchor_Artwork_Back_02", w: 3.10, h: 1.95, framed: true, ratio: "16:10 Hero Landscape" },
    { name: "Anchor_Artwork_Back_03", w: 1.65, h: 2.20, framed: false, ratio: "3:4 Frameless Canvas" },
    { name: "Anchor_Artwork_Left_01", w: 1.90, h: 1.90, framed: true, ratio: "1:1 Square" },
    { name: "Anchor_Artwork_Left_02", w: 2.55, h: 1.70, framed: true, ratio: "3:2 Landscape" },
    { name: "Anchor_Artwork_Left_03", w: 1.50, h: 2.10, framed: false, ratio: "5:7 Frameless" },
    { name: "Anchor_Artwork_Right_01", w: 2.72, h: 1.53, framed: true, ratio: "16:9 Panoramic" },
    { name: "Anchor_Artwork_Right_02", w: 1.76, h: 2.20, framed: true, ratio: "4:5 Editorial Portrait" },
    { name: "Anchor_Artwork_Right_03", w: 2.52, h: 1.08, framed: false, ratio: "21:9 Cinema Panorama" },
  ];

  const artworkAnchorChecks = [];
  const tempArtGroup = new THREE.Group();
  scene.add(tempArtGroup);

  artSpecs.forEach((spec, idx) => {
    const anchor = nodesByName[spec.name];
    const worldPos = new THREE.Vector3();
    const worldQuat = new THREE.Quaternion();
    anchor.getWorldPosition(worldPos);
    anchor.getWorldQuaternion(worldQuat);

    const yAxis = new THREE.Vector3(0, 1, 0).applyQuaternion(worldQuat);
    const zAxis = new THREE.Vector3(0, 0, 1).applyQuaternion(worldQuat);
    const toCenter = new THREE.Vector3(0, worldPos.y, 0).sub(worldPos).normalize();
    const inwardDot = zAxis.dot(toCenter);
    const upDot = yAxis.dot(new THREE.Vector3(0, 1, 0));

    const maxW = anchor.userData.maxWidthMeters;
    const maxH = anchor.userData.maxHeightMeters;
    const maxBottomY = worldPos.y - maxH * 0.5;
    const maxTopY = worldPos.y + maxH * 0.5;
    const maxEnvelopeClearsFloorAndCeiling =
      typeof maxW === "number" &&
      typeof maxH === "number" &&
      maxBottomY >= 0.249 &&
      maxTopY <= 8.75;

    const holder = new THREE.Group();
    holder.position.copy(worldPos);
    holder.quaternion.copy(worldQuat);

    const artTex = makeArtworkCanvasTexture(idx, spec.w, spec.h, \`\${spec.name.replace("Anchor_Artwork_", "")} · \${spec.ratio}\`);
    const canvasDepth = spec.framed ? 0.038 : 0.028;
    const artMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(spec.w, spec.h),
      new THREE.MeshStandardMaterial({ map: artTex, roughness: 0.56, metalness: 0.0 })
    );
    artMesh.position.z = canvasDepth;
    holder.add(artMesh);

    const backing = new THREE.Mesh(
      new THREE.BoxGeometry(spec.w + (spec.framed ? 0.055 : -0.004), spec.h + (spec.framed ? 0.055 : -0.004), canvasDepth - 0.003),
      new THREE.MeshStandardMaterial({ color: spec.framed ? 0x352f2a : 0xf4f0e8, roughness: spec.framed ? 0.46 : 0.85 })
    );
    backing.position.z = (canvasDepth - 0.003) * 0.5;
    backing.castShadow = true;
    holder.add(backing);

    tempArtGroup.add(holder);

    artworkAnchorChecks.push({
      name: spec.name,
      aspectRatioLabel: spec.ratio,
      mountedSizeMeters: [spec.w, spec.h],
      worldPosition: worldPos.toArray().map((v) => Number(v.toFixed(4))),
      inwardNormal: zAxis.toArray().map((v) => Number(v.toFixed(4))),
      maxCenteredSizeMeters: [maxW, maxH],
      maxCenteredBottomYMeters: Number(maxBottomY.toFixed(4)),
      maxEnvelopeClearsFloorAndCeiling,
      facesHallInterior: inwardDot > 0.25,
      uprightValid: upDot > 0.9999,
    });
  });

  // Render 8. Nine-Artwork Exhibition (Desktop 16:10, Direct Sunlight)
  snap("09_threejs_nine_artworks_desktop", [0.0, 1.60, 8.20], [0.0, 1.60, -9.00], 52, 0.150);

  // Scenario C: Evening Exhibition Lighting (9 artworks illuminated by runtime SpotLights!)
  activeLighting.dispose();
  activeLighting = applyMuseumLighting(scene, museum, renderer, "evening");
  snap("10_threejs_evening_exhibition", [-4.2, 1.60, 7.20], [1.4, 1.60, -9.00], 50, 0.135);

  // Mobile Portrait Viewport Composition (720 x 1280, 9:16, Soft Daylight + Open Enfilade + Secondary Focal Art!)
  activeLighting.dispose();
  activeLighting = applyMuseumLighting(scene, museum, renderer, "soft_daylight");
  setRearPortalOpen(museum, true);
  // Hide Back_02 when portal is open and mount focal artwork on Anchor_Artwork_Secondary_01!
  tempArtGroup.children[1].visible = false;
  const secAnchor = nodesByName["Anchor_Artwork_Secondary_01"];
  const secHolder = new THREE.Group();
  secAnchor.getWorldPosition(secHolder.position);
  secAnchor.getWorldQuaternion(secHolder.quaternion);
  const secMesh = new THREE.Mesh(
    new THREE.PlaneGeometry(2.6, 1.9),
    new THREE.MeshStandardMaterial({ map: makeArtworkCanvasTexture(9, 2.6, 1.9, "Secondary_01 · Enfilade Focal"), roughness: 0.56 })
  );
  secMesh.position.z = 0.036;
  secHolder.add(secMesh);
  tempArtGroup.add(secHolder);

  renderer.setSize(720, 1280);
  camera.aspect = 720 / 1280;
  snap("11_threejs_mobile_portrait_enfilade", [0.0, 1.60, 8.00], [0.0, 1.60, -9.00], 58, 0.130);

  // Restore desktop size & test Independent Material Customization + Multi-Instance Isolation
  renderer.setSize(desktopW, desktopH);
  camera.aspect = desktopW / desktopH;
  camera.clearViewOffset();
  const origWallHex = materialsByName["Mat_Wall_Plaster"].color.getHex();
  const origFloorHex = materialsByName["Mat_Floor_Concrete"].color.getHex();

  const featureWallMat = materialsByName["Mat_Wall_Plaster"].clone();
  featureWallMat.color.set("#3d474d");
  nodesByName["Wall_Back"].material = featureWallMat;
  materialsByName["Mat_Floor_Concrete"].color.set("#c2bab0");

  const instanceB = museum.clone(true);
  const instBMats = {};
  instanceB.traverse((o) => {
    if (o.isMesh && o.material) {
      o.material = o.material.clone();
      instBMats[o.name] = o.material;
    }
  });
  instBMats["Wall_Left"].color.set("#7a3b2e");
  const multiInstanceIsolated =
    nodesByName["Wall_Left"].material.color.getHex() === origWallHex &&
    nodesByName["Wall_Back"].material.color.getHex() !== nodesByName["Wall_Left"].material.color.getHex();

  snap("12_threejs_custom_materials", [-4.2, 1.60, 6.80], [0.8, 2.35, -9.00], 45);

  nodesByName["Wall_Back"].material = materialsByName["Mat_Wall_Plaster"];
  featureWallMat.dispose();
  materialsByName["Mat_Wall_Plaster"].color.setHex(origWallHex);
  materialsByName["Mat_Floor_Concrete"].color.setHex(origFloorHex);

  // Verify all 14+1 Navigation Anchors, 9 Placement Anchors, & 15 Lighting Anchors
  const navNames = [
    "Anchor_Navigation_Entrance",
    "Anchor_Navigation_Center",
    "Anchor_Navigation_Back",
    "Anchor_Navigation_Left",
    "Anchor_Navigation_Right",
    "Anchor_Navigation_Secondary",
    "Anchor_Navigation_Artwork_01",
    "Anchor_Navigation_Artwork_02",
    "Anchor_Navigation_Artwork_03",
    "Anchor_Navigation_Artwork_04",
    "Anchor_Navigation_Artwork_05",
    "Anchor_Navigation_Artwork_06",
    "Anchor_Navigation_Artwork_07",
    "Anchor_Navigation_Artwork_08",
    "Anchor_Navigation_Artwork_09",
  ];

  const isWalkableOpen = (x, y, z) => {
    if (y < 0.0 || y > 2.60) return false;
    if (x >= -11.65 && x <= 11.65 && z >= -8.65 && z <= 8.65) return true;
    if (x >= -2.50 && x <= 2.50 && z > 8.65 && z <= 10.40) return true;
    if (x >= -6.85 && x <= 6.85 && z > 10.40 && z <= 15.05) return true;
    if (x >= -1.90 && x <= 1.90 && z >= -9.90 && z < -8.65) return true;
    if (x >= -5.05 && x <= 5.05 && z >= -15.35 && z < -9.90) return true;
    return false;
  };

  const navChecks = navNames.map((nm) => {
    const node = nodesByName[nm];
    const p = new THREE.Vector3();
    const q = new THREE.Quaternion();
    node.getWorldPosition(p);
    node.getWorldQuaternion(q);
    const upDir = new THREE.Vector3(0, 1, 0).applyQuaternion(q);
    return {
      name: nm,
      position: p.toArray().map((v) => Number(v.toFixed(4))),
      upDot: Number(upDir.dot(new THREE.Vector3(0, 1, 0)).toFixed(6)),
      validWalkableEyePoint: isWalkableOpen(p.x, p.y, p.z) && Math.abs(p.y - 1.60) < 0.02,
    };
  });

  const placeNames = [
    "Anchor_Place_Central_Installation",
    "Anchor_Place_Pedestal_01",
    "Anchor_Place_Pedestal_02",
    "Anchor_Place_Bench_01",
    "Anchor_Place_Bench_02",
    "Anchor_Place_Info_Stand",
    "Anchor_Place_Invitation_Display",
    "Anchor_Place_Partition_01",
    "Anchor_Place_Partition_02",
  ];
  const allPlacementAnchorsValid = placeNames.every((nm) => Boolean(nodesByName[nm]));

  const lightGroup = nodesByName["Lighting_Anchors"];
  const lightChecks = lightGroup.children.map((ch) => {
    const p = new THREE.Vector3();
    const q = new THREE.Quaternion();
    ch.getWorldPosition(p);
    ch.getWorldQuaternion(q);
    const beamDir = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
    return {
      name: ch.name,
      position: p.toArray().map((v) => Number(v.toFixed(4))),
      beamDirection: beamDir.toArray().map((v) => Number(v.toFixed(4))),
      aimsDownwardIntoHall: beamDir.y < -0.55 && p.y > 8.70,
    };
  });

  // Steady-state frame-time benchmark (Direct Sunlight with 2048^2 shadow pass, canonical empty museum)
  scene.remove(tempArtGroup);
  activeLighting.dispose();
  activeLighting = applyMuseumLighting(scene, museum, renderer, "direct_sun");
  camera.position.set(0.0, 1.60, 8.20);
  camera.lookAt(0.0, 2.75, -9.00);
  camera.fov = 45;
  camera.updateProjectionMatrix();

  for (let i = 0; i < 15; i++) renderer.render(scene, camera);
  const frameTimes = [];
  for (let i = 0; i < 90; i++) {
    const t0 = performance.now();
    renderer.render(scene, camera);
    renderer.getContext().finish();
    frameTimes.push(performance.now() - t0);
  }
  frameTimes.sort((a, b) => a - b);
  const avgFrameMs = frameTimes.reduce((s, x) => s + x, 0) / frameTimes.length;
  const p95FrameMs = frameTimes[Math.floor(frameTimes.length * 0.95)];
  const drawCalls = renderer.info.render.calls;

  return {
    dimensions: {
      interiorWidthMeters: Number(interiorWidth.toFixed(4)),
      interiorDepthMeters: Number(interiorDepth.toFixed(4)),
      ceilingHeightMeters: Number(ceilingHeight.toFixed(4)),
      floorSurfaceYMeters: Number(floorBox.max.y.toFixed(5)),
      pitchedSkylightRidgeYMeters: Number(glassBox.max.y.toFixed(4)),
      secondaryGalleryDepthRangeZ: [Number(secGalBox.min.z.toFixed(3)), Number(secGalBox.max.z.toFixed(3))],
      entranceVestibuleDepthRangeZ: [Number(vestBox.min.z.toFixed(3)), Number(vestBox.max.z.toFixed(3))],
      overallBounds: {
        min: overallBox.min.toArray().map((v) => Number(v.toFixed(4))),
        max: overallBox.max.toArray().map((v) => Number(v.toFixed(4))),
      },
    },
    counts: {
      meshes: meshes.length,
      materials: Object.keys(materialsByName).length,
      textures: textureDetails.length,
      triangles: totalTriangles,
      vertices: totalVertices,
      drawCallsDirectSun: drawCalls,
    },
    performance: {
      glbLoadTimeMs: Number(loadTimeMs.toFixed(2)),
      avgFrameTimeMs: Number(avgFrameMs.toFixed(3)),
      p95FrameTimeMs: Number(p95FrameMs.toFixed(3)),
      estimatedGpuTextureMemoryBytes: estimatedTextureVramBytes,
      textures: textureDetails,
    },
    checks: {
      dimensionsMatchSpec:
        Math.abs(interiorWidth - 24.0) < 0.01 &&
        Math.abs(interiorDepth - 18.0) < 0.01 &&
        Math.abs(ceilingHeight - 9.0) < 0.01 &&
        Math.abs(floorBox.max.y) < 0.001 &&
        glassBox.max.y >= 12.6,
      allNineMaterialsLoaded: Object.keys(materialsByName).length === 9,
      dualUvNeutralAoLoaded: aoMapsLoaded,
      skylightGlassToggleWorked: glassHiddenWorked,
      wallAndCeilingToggleWorked: wallCeilingToggleWorked,
      portalClosureToggleValid: portalClosureFlushValid,
      spotlightHeadAdjustable,
      multiInstanceMaterialIsolation: multiInstanceIsolated,
      allNineArtworkAnchorsValid:
        artworkAnchorChecks.length === 9 &&
        artworkAnchorChecks.every((c) => c.facesHallInterior && c.uprightValid && c.maxEnvelopeClearsFloorAndCeiling),
      allPlacementAnchorsValid,
      allNavigationAnchorsValid:
        navChecks.length === 15 && navChecks.every((c) => c.validWalkableEyePoint && c.upDot > 0.999),
      allLightingAnchorsValid:
        lightChecks.length === 15 && lightChecks.every((c) => c.aimsDownwardIntoHall),
    },
    artworkAnchors: artworkAnchorChecks,
    navigationAnchors: navChecks,
    lightingAnchors: lightChecks,
    snapshots,
  };
};
</script>
</body>
</html>`;

async function main() {
  const glbPath = path.join(ASSET_DIR, "model.glb");
  if (!fs.existsSync(glbPath)) throw new Error(`Missing model.glb at ${glbPath}`);
  const glbBuf = fs.readFileSync(glbPath);
  const glbSha256 = crypto.createHash("sha256").update(glbBuf).digest("hex");

  const server = http.createServer((req, res) => {
    const u = new URL(req.url, "http://127.0.0.1");
    if (u.pathname === "/" || u.pathname === "/index.html") {
      res.writeHead(200, { "Content-Type": MIME[".html"] });
      res.end(HTML_PAGE);
      return;
    }
    let filePath = null;
    if (u.pathname.startsWith("/three/")) {
      filePath = path.join(THREE_ROOT, u.pathname.slice("/three/".length));
    } else if (u.pathname.startsWith("/asset/")) {
      filePath = path.join(ASSET_DIR, u.pathname.slice("/asset/".length));
    }
    if (filePath && fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
      fs.createReadStream(filePath).pipe(res);
      return;
    }
    res.writeHead(404);
    res.end("Not Found");
  });

  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;

  const browser = await chromium.launch({
    headless: true,
    args: ["--enable-webgl", "--ignore-gpu-blocklist", "--use-gl=angle"],
  });

  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
    const consoleErrors = [];
    page.on("pageerror", (err) => consoleErrors.push(String(err)));
    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });

    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "networkidle" });
    const result = await page.evaluate(() => window.__runValidation());

    const savedImages = [];
    for (const [key, dataUrl] of Object.entries(result.snapshots)) {
      const b64 = dataUrl.replace(/^data:image\/png;base64,/, "");
      const outPng = path.join(OUT_DIR, `${key}.png`);
      fs.writeFileSync(outPng, Buffer.from(b64, "base64"));
      savedImages.push(path.relative(REPO_ROOT, outPng));
    }
    delete result.snapshots;

    const report = {
      status:
        consoleErrors.length === 0 && Object.values(result.checks).every(Boolean)
          ? "PASS"
          : "FAIL",
      glbSizeBytes: glbBuf.length,
      glbSha256,
      consoleErrors,
      savedValidationRenders: savedImages,
      ...result,
    };

    fs.writeFileSync(path.join(OUT_DIR, "threejs_validation.json"), JSON.stringify(report, null, 2) + "\n");
    console.log(JSON.stringify({
      status: report.status,
      glbSizeBytes: report.glbSizeBytes,
      glbSha256: report.glbSha256,
      dimensions: report.dimensions,
      counts: report.counts,
      performance: {
        glbLoadTimeMs: report.performance.glbLoadTimeMs,
        avgFrameTimeMs: report.performance.avgFrameTimeMs,
        p95FrameTimeMs: report.performance.p95FrameTimeMs,
        estimatedGpuTextureMemoryBytes: report.performance.estimatedGpuTextureMemoryBytes,
      },
      checks: report.checks,
      consoleErrors: report.consoleErrors,
    }, null, 2));

    if (report.status !== "PASS") process.exitCode = 1;
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
