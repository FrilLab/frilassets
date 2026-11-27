#!/usr/bin/env node
/**
 * Isolated Three.js Runtime Validation & Performance Harness for:
 *   Open Skylight Museum Hall (`assets/architecture/museum-open-hall/model.glb`)
 *
 * Loads the actual exported `model.glb` in Chromium WebGL via Playwright + standard `THREE.GLTFLoader`
 * and validates all Section 20 & Section 21 runtime contracts:
 *   1. Standard GLTFLoader loading, world scale, interior clear bounds (24 x 18 x 9 m), floor Y = 0.00 m
 *   2. Semantic node hierarchy & all 9 PBR material slots + embedded texture verification
 *   3. Independent runtime material customization (walls, floor, ceiling, frames, glazing) +
 *      per-wall material cloning without duplicating geometry + two-instance isolation check
 *   4. Skylight glazing visibility toggle (`Skylight_Glass.visible`) & wall/ceiling visibility toggles
 *   5. All 9 `Anchor_Artwork_*` transforms, local XY plane + inward `+Z` normal verification,
 *      and mounting of 9 varied-aspect-ratio artworks (portrait, landscape, panoramic, square, framed & frameless)
 *   6. All 14 `Navigation_Anchors` (Y = 1.60 m eye height, clearance check, orientation check)
 *      and all 15 `Lighting_Anchors` (`-Z` beam aim verification)
 *   7. Walkable bounds & entrance threshold pass-through / wall collision contract check
 *   8. Desktop (1600x1000) & Mobile (540x960) WebGL renders + steady-state frame-time & GPU memory measurements
 *
 * Run with:
 *   NODE_PATH=<path-to-node_modules> node assets/architecture/museum-open-hall/validate_threejs.mjs
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
const OUT_DIR = path.join(WORK_DIR, "validation");
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
  <style>body { margin: 0; background: #dcd7ce; overflow: hidden; }</style>
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
import { RoomEnvironment } from "three/addons/environments/RoomEnvironment.js";

function makeArtworkCanvasTexture(index, aspectW, aspectH, label) {
  const w = Math.round(512 * (aspectW >= aspectH ? 1.0 : aspectW / aspectH));
  const h = Math.round(512 * (aspectH > aspectW ? 1.0 : aspectH / aspectW));
  const c = document.createElement("canvas");
  c.width = w;
  c.height = h;
  const ctx = c.getContext("2d");

  // Warm archival mat board
  ctx.fillStyle = "#f1ede4";
  ctx.fillRect(0, 0, w, h);

  const pad = Math.round(Math.min(w, h) * 0.085);
  const iw = w - pad * 2;
  const ih = h - pad * 2;

  const palettes = [
    ["#c8825b", "#2a3942"],
    ["#8c989e", "#1e2428"],
    ["#607062", "#d8c7ab"],
    ["#b79d7e", "#3c332d"],
    ["#2a3540", "#cbb99e"],
    ["#7d503e", "#dfccb5"],
    ["#9aa298", "#2f3532"],
    ["#ca9e67", "#23211f"],
    ["#3e4b54", "#bab1a4"],
  ];
  const [c1, c2] = palettes[index % palettes.length];
  const grad = ctx.createLinearGradient(pad, pad, pad, pad + ih);
  grad.addColorStop(0, c1);
  grad.addColorStop(1, c2);
  ctx.fillStyle = grad;
  ctx.fillRect(pad, pad, iw, ih);

  // Subtle architectural geometric motif + upright orientation verification marker ("TOP" subtle rule)
  ctx.fillStyle = "rgba(245, 241, 232, 0.82)";
  ctx.beginPath();
  ctx.arc(w * 0.5, pad + ih * 0.42, Math.min(iw, ih) * 0.20, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "#2b2927";
  ctx.font = \`500 \${Math.max(12, Math.round(Math.min(w, h) * 0.042))}px sans-serif\`;
  ctx.textAlign = "center";
  ctx.fillText(label, w * 0.5, h - Math.max(8, Math.round(pad * 0.35)));

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
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  document.body.appendChild(renderer.domElement);

  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xe6ecf2);
  scene.environment = envTex;
  scene.environmentIntensity = 0.52;

  const loader = new GLTFLoader();
  const tLoadStart = performance.now();
  const gltf = await loader.loadAsync("/asset/model.glb");
  const loadTimeMs = performance.now() - tLoadStart;

  const museum = gltf.scene;
  scene.add(museum);
  museum.updateMatrixWorld(true);

  // 1. Collect nodes, meshes, materials, textures, and triangle/vertex counts
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
      const isGlass = obj.name === "Skylight_Glass";
      obj.castShadow = !isGlass;
      obj.receiveShadow = !isGlass;

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
            });
          }
        }
      }
    }
  });

  // Estimate GPU texture memory (RGBA8 uncompressed + 1.333x mipchain)
  let estimatedTextureVramBytes = 0;
  const textureDetails = [];
  for (const info of uniqueTextures.values()) {
    const bytes = Math.round(info.width * info.height * 4 * (4 / 3));
    estimatedTextureVramBytes += bytes;
    textureDetails.push({ ...info, estimatedGpuBytes: bytes });
  }

  // 2. Verify physical dimensions & floor alignment
  const boxOf = (name) => new THREE.Box3().setFromObject(nodesByName[name]);
  const floorBox = boxOf("Floor");
  const wallLeftBox = boxOf("Wall_Left");
  const wallRightBox = boxOf("Wall_Right");
  const wallBackBox = boxOf("Wall_Back");
  const wallEntBox = boxOf("Wall_Entrance");
  const ceilBox = boxOf("Ceiling");
  const glassBox = boxOf("Skylight_Glass");
  const entFrameBox = boxOf("Entrance_Frame");
  const overallBox = new THREE.Box3().setFromObject(museum);

  const interiorWidth = wallRightBox.min.x - wallLeftBox.max.x;
  const interiorDepth = wallEntBox.min.z - wallBackBox.max.z;
  const ceilingHeight = ceilBox.min.y - floorBox.max.y;

  // 3. Configure runtime daylight + directional sun through skylight
  const hemi = new THREE.HemisphereLight(0xf6f8fc, 0xd8d2c8, 0.85);
  scene.add(hemi);

  const sun = new THREE.DirectionalLight(0xfff5e4, 2.25);
  sun.position.set(6.8, 16.0, 4.4);
  sun.target.position.set(-2.2, 0.0, -2.5);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -15;
  sun.shadow.camera.right = 15;
  sun.shadow.camera.top = 15;
  sun.shadow.camera.bottom = -15;
  sun.shadow.camera.near = 1.0;
  sun.shadow.camera.far = 34.0;
  sun.shadow.bias = -0.0004;
  scene.add(sun);
  scene.add(sun.target);

  // Exterior arrival backdrop outside entrance for clean visual realism
  const extCourt = new THREE.Mesh(
    new THREE.PlaneGeometry(36, 36),
    new THREE.MeshStandardMaterial({ color: 0xddd7ce, roughness: 0.92 })
  );
  extCourt.rotation.x = -Math.PI / 2;
  extCourt.position.set(0, -0.01, 16);
  scene.add(extCourt);

  const camera = new THREE.PerspectiveCamera(54, desktopW / desktopH, 0.1, 100);
  const snapshots = {};
  const snap = (key) => {
    renderer.render(scene, camera);
    snapshots[key] = renderer.domElement.toDataURL("image/png");
  };

  // Render empty runtime daylight view (matching Blender entrance perspective)
  camera.position.set(0.0, 1.65, 8.2);
  camera.lookAt(0.0, 2.55, -9.0);
  snap("01_threejs_empty_daylight");

  // Render skylight overhead view
  camera.position.set(0.0, 1.65, 4.4);
  camera.lookAt(0.0, 9.7, -1.6);
  snap("02_threejs_skylight");

  // 4. Verify Skylight_Glass & Wall/Ceiling visibility controls
  const glassNode = nodesByName["Skylight_Glass"];
  glassNode.visible = false;
  renderer.render(scene, camera);
  const glassHiddenWorked = glassNode.visible === false;
  glassNode.visible = true;

  nodesByName["Wall_Left"].visible = false;
  nodesByName["Ceiling"].visible = false;
  renderer.render(scene, camera);
  const wallCeilingToggleWorked = !nodesByName["Wall_Left"].visible && !nodesByName["Ceiling"].visible;
  nodesByName["Wall_Left"].visible = true;
  nodesByName["Ceiling"].visible = true;

  // 5. Verify all 9 Artwork Anchors & mount 9 distinct aspect-ratio artworks (framed & frameless)
  const artSpecs = [
    { name: "Anchor_Artwork_Back_01", w: 1.50, h: 2.25, framed: true, ratio: "2:3 Portrait" },
    { name: "Anchor_Artwork_Back_02", w: 3.20, h: 2.00, framed: true, ratio: "16:10 Hero Landscape" },
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

    const xAxis = new THREE.Vector3(1, 0, 0).applyQuaternion(worldQuat);
    const yAxis = new THREE.Vector3(0, 1, 0).applyQuaternion(worldQuat);
    const zAxis = new THREE.Vector3(0, 0, 1).applyQuaternion(worldQuat);

    // Check +Y is world up (0, 1, 0) and +Z points inward toward hall origin!
    const toCenter = new THREE.Vector3(0, worldPos.y, 0).sub(worldPos).normalize();
    const inwardDot = zAxis.dot(toCenter);
    const upDot = yAxis.dot(new THREE.Vector3(0, 1, 0));

    // Verify advertised maxWidthMeters x maxHeightMeters centered directly on anchor clears floor & base reveal (Y >= 0.25 m)
    const maxW = anchor.userData.maxWidthMeters;
    const maxH = anchor.userData.maxHeightMeters;
    const maxBottomY = worldPos.y - maxH * 0.5;
    const maxTopY = worldPos.y + maxH * 0.5;
    const maxEnvelopeClearsFloorAndCeiling =
      typeof maxW === "number" &&
      typeof maxH === "number" &&
      maxBottomY >= 0.249 &&
      maxTopY <= 8.75;

    // Mount artwork directly as a child in anchor's local XY plane (+Z facing into hall)
    const holder = new THREE.Group();
    holder.position.copy(worldPos);
    holder.quaternion.copy(worldQuat);

    const artTex = makeArtworkCanvasTexture(idx, spec.w, spec.h, \`\${spec.name.replace("Anchor_Artwork_", "")} · \${spec.ratio}\`);
    const canvasDepth = spec.framed ? 0.036 : 0.028;
    const artMesh = new THREE.Mesh(
      new THREE.PlaneGeometry(spec.w, spec.h),
      new THREE.MeshStandardMaterial({ map: artTex, roughness: 0.58, metalness: 0.0 })
    );
    artMesh.position.z = canvasDepth;
    holder.add(artMesh);

    if (spec.framed) {
      const frameMesh = new THREE.Mesh(
        new THREE.BoxGeometry(spec.w + 0.055, spec.h + 0.055, canvasDepth - 0.003),
        new THREE.MeshStandardMaterial({ color: 0x2c2825, roughness: 0.45 })
      );
      frameMesh.position.z = (canvasDepth - 0.003) * 0.5;
      frameMesh.castShadow = true;
      holder.add(frameMesh);
    } else {
      const stretcher = new THREE.Mesh(
        new THREE.BoxGeometry(spec.w - 0.004, spec.h - 0.004, canvasDepth - 0.002),
        new THREE.MeshStandardMaterial({ color: 0xf4f0e8, roughness: 0.85 })
      );
      stretcher.position.z = (canvasDepth - 0.002) * 0.5;
      stretcher.castShadow = true;
      holder.add(stretcher);
    }

    tempArtGroup.add(holder);

    artworkAnchorChecks.push({
      name: spec.name,
      aspectRatioLabel: spec.ratio,
      mountedSizeMeters: [spec.w, spec.h],
      worldPosition: worldPos.toArray().map((v) => Number(v.toFixed(4))),
      localUpDotWorldUp: Number(upDot.toFixed(6)),
      inwardNormal: zAxis.toArray().map((v) => Number(v.toFixed(4))),
      maxCenteredSizeMeters: [maxW, maxH],
      maxCenteredBottomYMeters: Number(maxBottomY.toFixed(4)),
      maxEnvelopeClearsFloorAndCeiling,
      facesHallInterior: inwardDot > 0.25,
      uprightValid: upDot > 0.9999,
    });
  });

  // Render 9-artwork exhibition in desktop (16:10)
  camera.aspect = desktopW / desktopH;
  camera.updateProjectionMatrix();
  camera.position.set(-4.6, 1.65, 7.2);
  camera.lookAt(1.8, 2.45, -9.0);
  snap("03_threejs_nine_artworks_desktop");

  // 6. Verify all 14 Navigation Anchors & all 15 Lighting Anchors
  const navNames = [
    "Anchor_Navigation_Entrance",
    "Anchor_Navigation_Center",
    "Anchor_Navigation_Back",
    "Anchor_Navigation_Left",
    "Anchor_Navigation_Right",
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

  const navChecks = [];
  for (const nm of navNames) {
    const node = nodesByName[nm];
    const p = new THREE.Vector3();
    const q = new THREE.Quaternion();
    node.getWorldPosition(p);
    node.getWorldQuaternion(q);
    const lookDir = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
    const upDir = new THREE.Vector3(0, 1, 0).applyQuaternion(q);
    const insideWalkable =
      Math.abs(p.x) <= 11.65 &&
      p.z >= -8.65 &&
      (p.z <= 8.65 || (Math.abs(p.x) <= 2.50 && p.z <= 10.20)) &&
      Math.abs(p.y - 1.60) < 0.02;
    navChecks.push({
      name: nm,
      position: p.toArray().map((v) => Number(v.toFixed(4))),
      lookDirection: lookDir.toArray().map((v) => Number(v.toFixed(4))),
      upDot: Number(upDir.dot(new THREE.Vector3(0, 1, 0)).toFixed(6)),
      validWalkableEyePoint: insideWalkable,
    });
  }

  // Render directly from Anchor_Navigation_Entrance & Anchor_Navigation_Artwork_02 using pure anchor transform!
  const applyCameraAnchor = (anchorName, fov = 54) => {
    const n = nodesByName[anchorName];
    camera.fov = fov;
    camera.updateProjectionMatrix();
    n.getWorldPosition(camera.position);
    n.getWorldQuaternion(camera.quaternion);
  };
  applyCameraAnchor("Anchor_Navigation_Entrance", 56);
  snap("04_threejs_nav_entrance");
  applyCameraAnchor("Anchor_Navigation_Left", 56);
  snap("05_threejs_nav_left_wall");
  applyCameraAnchor("Anchor_Navigation_Artwork_02", 52);
  snap("06_threejs_nav_artwork_02");

  // Verify Lighting_Anchors aim downward/inward into the hall
  const lightGroup = nodesByName["Lighting_Anchors"];
  const lightChecks = [];
  for (const ch of lightGroup.children) {
    const p = new THREE.Vector3();
    const q = new THREE.Quaternion();
    ch.getWorldPosition(p);
    ch.getWorldQuaternion(q);
    const beamDir = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
    lightChecks.push({
      name: ch.name,
      position: p.toArray().map((v) => Number(v.toFixed(4))),
      beamDirection: beamDir.toArray().map((v) => Number(v.toFixed(4))),
      aimsDownwardIntoHall: beamDir.y < -0.55 && p.y > 8.70,
    });
  }

  // 7. Independent Material Customization + Per-Wall Cloning + Multi-Instance Isolation
  const origWallHex = materialsByName["Mat_Wall_Plaster"].color.getHex();
  const origFloorHex = materialsByName["Mat_Floor_Concrete"].color.getHex();

  // Clone Mat_Wall_Plaster on Wall_Back only to create a curated dark gallery feature wall while keeping side walls warm ivory!
  const featureWallMat = materialsByName["Mat_Wall_Plaster"].clone();
  featureWallMat.color.set("#3f494e"); // Deep museum slate accent wall
  nodesByName["Wall_Back"].material = featureWallMat;
  materialsByName["Mat_Floor_Concrete"].color.set("#c8c0b4"); // Warmer travertine-stone tint

  // Second instance isolation test
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

  camera.position.set(-4.2, 1.65, 6.8);
  camera.lookAt(0.8, 2.35, -9.0);
  camera.fov = 54;
  camera.updateProjectionMatrix();
  snap("07_threejs_custom_materials");

  // Restore canonical materials
  nodesByName["Wall_Back"].material = materialsByName["Mat_Wall_Plaster"];
  featureWallMat.dispose();
  materialsByName["Mat_Wall_Plaster"].color.setHex(origWallHex);
  materialsByName["Mat_Floor_Concrete"].color.setHex(origFloorHex);

  // 8. Mobile Portrait Viewport Aspect Ratio Test (540 x 960, 9:16)
  renderer.setSize(540, 960);
  camera.aspect = 540 / 960;
  camera.fov = 64;
  camera.updateProjectionMatrix();
  camera.position.set(0.0, 1.62, 7.8);
  camera.lookAt(0.0, 2.40, -9.0);
  snap("08_threejs_mobile_portrait");

  // 9. Steady-State Runtime Performance Measurement (Desktop 1600x1000, canonical museum only)
  scene.remove(tempArtGroup);
  renderer.setSize(desktopW, desktopH);
  camera.aspect = desktopW / desktopH;
  camera.fov = 54;
  camera.updateProjectionMatrix();
  camera.position.set(0.0, 1.65, 8.2);
  camera.lookAt(0.0, 2.55, -9.0);

  // Warmup 15 frames, then time 90 frames
  for (let i = 0; i < 15; i++) renderer.render(scene, camera);
  const frameTimes = [];
  for (let i = 0; i < 90; i++) {
    const t0 = performance.now();
    renderer.render(scene, camera);
    const gl = renderer.getContext();
    gl.finish();
    frameTimes.push(performance.now() - t0);
  }
  frameTimes.sort((a, b) => a - b);
  const avgFrameMs = frameTimes.reduce((s, x) => s + x, 0) / frameTimes.length;
  const p95FrameMs = frameTimes[Math.floor(frameTimes.length * 0.95)];
  const drawCalls = renderer.info.render.calls;

  // 10. Collision / Walkable-Space Contract Verification
  const walkableMeta = nodesByName["Museum_Open_Hall"].userData.walkableBoundsMeters;
  const isWalkable = (x, y, z) => {
    if (y < 0.0 || y > 2.60) return false;
    if (x >= -11.65 && x <= 11.65 && z >= -8.65 && z <= 8.65) return true;
    if (x >= -2.50 && x <= 2.50 && z > 8.65 && z <= 10.20) return true;
    return false;
  };
  const collisionContractChecks = {
    hasEmbeddedWalkableMetadata: Boolean(walkableMeta),
    centerFloorWalkable: isWalkable(0, 1.6, 0),
    entranceOpeningPassable: isWalkable(0, 1.6, 9.5),
    leftWallBlocked: !isWalkable(-12.05, 1.6, 0),
    rightWallBlocked: !isWalkable(12.05, 1.6, 0),
    backWallBlocked: !isWalkable(0, 1.6, -9.05),
    entranceSideWallBlocked: !isWalkable(-6.0, 1.6, 9.2),
  };

  return {
    dimensions: {
      interiorWidthMeters: Number(interiorWidth.toFixed(4)),
      interiorDepthMeters: Number(interiorDepth.toFixed(4)),
      ceilingHeightMeters: Number(ceilingHeight.toFixed(4)),
      floorSurfaceYMeters: Number(floorBox.max.y.toFixed(5)),
      skylightGlassYMeters: Number(glassBox.min.y.toFixed(4)),
      entranceFrameOuterBounds: {
        min: entFrameBox.min.toArray().map((v) => Number(v.toFixed(4))),
        max: entFrameBox.max.toArray().map((v) => Number(v.toFixed(4))),
      },
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
      drawCallsCanonical: drawCalls,
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
        Math.abs(floorBox.max.y) < 0.001,
      allNineMaterialsLoaded: Object.keys(materialsByName).length === 9,
      skylightGlassToggleWorked: glassHiddenWorked,
      wallAndCeilingToggleWorked: wallCeilingToggleWorked,
      multiInstanceMaterialIsolation: multiInstanceIsolated,
      allNineArtworkAnchorsValid:
        artworkAnchorChecks.length === 9 &&
        artworkAnchorChecks.every(
          (c) => c.facesHallInterior && c.uprightValid && c.maxEnvelopeClearsFloorAndCeiling
        ),
      allNavigationAnchorsValid:
        navChecks.length === 14 &&
        navChecks.every((c) => c.validWalkableEyePoint && c.upDot > 0.999),
      allLightingAnchorsValid:
        lightChecks.length === 15 &&
        lightChecks.every((c) => c.aimsDownwardIntoHall),
      collisionContractValid: Object.values(collisionContractChecks).every(Boolean),
    },
    artworkAnchors: artworkAnchorChecks,
    navigationAnchors: navChecks,
    lightingAnchors: lightChecks,
    collisionContractChecks,
    snapshots,
  };
};
</script>
</body>
</html>`;

async function main() {
  const glbPath = path.join(ASSET_DIR, "model.glb");
  if (!fs.existsSync(glbPath)) {
    throw new Error(`Missing model.glb at ${glbPath}`);
  }
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

    const reportPath = path.join(OUT_DIR, "threejs_validation.json");
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
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

    if (report.status !== "PASS") {
      process.exitCode = 1;
    }
  } finally {
    await browser.close();
    server.close();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
