/**
 * Reference Three.js Lighting & Architectural Customization Controller for:
 *   Open Skylight Museum Hall V2 (`assets/architecture/museum-open-hall/`)
 *
 * Implements Section 4 (Open Enfilade vs. Closed 9-Artwork Portal Closure),
 * Section 7 (Realistic Interior Indirect Illumination via Procedural Architectural
 * Sky-Bounce PMREM + Dual-UV Neutral `aoMap` + Scenario Presets), and
 * Section 8 (Independent Orientation of `Fixture_Head_*` Adjustable Spotlights).
 *
 * Zero framework dependencies — uses only standard `three`.
 */

import * as THREE from "three";

/**
 * Build a physically plausible interior architectural PMREM environment scene
 * (zenith skylight dome + warm plaster wall horizon bounce + honed concrete floor bounce)
 * so real-time WebGL reproduces soft multi-bounce museum indirect lighting without
 * relying on flat `AmbientLight` or external HDRI files.
 */
export function createMuseumEnvironment(renderer, scenario = "soft_daylight") {
  const pmrem = new THREE.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();

  const envScene = new THREE.Scene();

  const presets = {
    soft_daylight: {
      skyZenith: 0xf4f8fd,
      skyGlow: 2.35,
      horizonPlaster: 0xe6e2d9,
      horizonGlow: 0.95,
      floorBounce: 0x9e9a93,
      floorGlow: 0.55,
      sideWindowGlow: 1.25,
    },
    direct_sun: {
      skyZenith: 0xe4effc,
      skyGlow: 2.15,
      horizonPlaster: 0xeae4d8,
      horizonGlow: 1.05,
      floorBounce: 0xa6a096,
      floorGlow: 0.65,
      sideWindowGlow: 1.35,
    },
    evening: {
      skyZenith: 0x1b2940,
      skyGlow: 0.35,
      horizonPlaster: 0xccb89e,
      horizonGlow: 0.42,
      floorBounce: 0x6e655b,
      floorGlow: 0.25,
      sideWindowGlow: 0.38,
    },
  };

  const p = presets[scenario] || presets.soft_daylight;

  const makeEmissiveMat = (hex, intensity) =>
    new THREE.MeshBasicMaterial({
      color: new THREE.Color(hex).multiplyScalar(intensity),
      side: THREE.BackSide,
    });

  // Enclosing architectural radiance shell
  const shellGeo = new THREE.SphereGeometry(30, 32, 24);
  const pos = shellGeo.attributes.position;
  const colors = new Float32Array(pos.count * 3);
  const cTop = new THREE.Color(p.skyZenith).multiplyScalar(p.skyGlow);
  const cMid = new THREE.Color(p.horizonPlaster).multiplyScalar(p.horizonGlow);
  const cBot = new THREE.Color(p.floorBounce).multiplyScalar(p.floorGlow);
  const tmp = new THREE.Color();

  for (let i = 0; i < pos.count; i++) {
    const ny = pos.getY(i) / 30.0;
    if (ny >= 0) {
      tmp.copy(cMid).lerp(cTop, Math.pow(ny, 0.75));
    } else {
      tmp.copy(cMid).lerp(cBot, Math.pow(-ny, 0.65));
    }
    colors[i * 3] = tmp.r;
    colors[i * 3 + 1] = tmp.g;
    colors[i * 3 + 2] = tmp.b;
  }
  shellGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  envScene.add(
    new THREE.Mesh(
      shellGeo,
      new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide })
    )
  );

  // Overhead pitched-skylight zenith softbox card for crisp satin floor specular reflections!
  const skyPanel = new THREE.Mesh(
    new THREE.PlaneGeometry(16, 14),
    makeEmissiveMat(p.skyZenith, p.skyGlow * 1.35)
  );
  skyPanel.rotation.x = Math.PI / 2;
  skyPanel.position.set(0, 14, 0);
  skyPanel.material.side = THREE.DoubleSide;
  envScene.add(skyPanel);

  // Subtle side-cove bounce strips so honed concrete grazing reflections look natural
  for (const sx of [-13, 13]) {
    const strip = new THREE.Mesh(
      new THREE.PlaneGeometry(18, 3.5),
      new THREE.MeshBasicMaterial({
        color: new THREE.Color(p.horizonPlaster).multiplyScalar(p.sideWindowGlow),
        side: THREE.DoubleSide,
      })
    );
    strip.position.set(sx, 7.5, 0);
    strip.rotation.y = Math.PI / 2;
    envScene.add(strip);
  }

  const rt = pmrem.fromScene(envScene, 0.035);
  pmrem.dispose();
  return rt;
}

/**
 * Configure materials on a loaded `Museum_Open_Hall` instance (`aoMapIntensity`, shadow flags).
 */
export function prepareMuseumMaterials(museum, options = {}) {
  const { aoIntensity = 0.96 } = options;
  museum.traverse((obj) => {
    if (!obj.isMesh) return;
    const isGlass = obj.name === "Skylight_Glass";
    obj.castShadow = !isGlass;
    obj.receiveShadow = !isGlass;

    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
    for (const m of mats) {
      if (!m) continue;
      if (m.aoMap) {
        m.aoMapIntensity = aoIntensity;
        m.needsUpdate = true;
      }
      if (m.name === "Mat_Skylight_Glass") {
        m.transparent = true;
        m.depthWrite = false;
      }
    }
  });
}

/**
 * Toggle between Configuration A (`isOpen = true`, open central enfilade portal into
 * `Secondary_Gallery`) and Configuration B (`isOpen = false`, sliding pocket partition
 * `Wall_Back_Portal_Closure` closed flush at `Z = -9.00 m` for the 9-artwork main wall).
 */
export function setRearPortalOpen(museum, isOpen = true) {
  const closure = museum.getObjectByName("Wall_Back_Portal_Closure");
  if (!closure) return false;
  if (isOpen) {
    closure.position.set(-4.62, 0.0, -0.38);
  } else {
    closure.position.set(0.0, 0.0, 0.0);
  }
  closure.updateMatrixWorld(true);
  return true;
}

/**
 * Independently orient an adjustable spotlight head (`Fixture_Head_*`) so its local `-Z`
 * optical barrel points directly at `targetWorldPos` (matching `Anchor_Light_*` convention).
 */
export function aimSpotlightHead(headNode, targetWorldPos, up = new THREE.Vector3(0, 1, 0)) {
  if (!headNode) return;
  headNode.updateWorldMatrix(true, false);
  const headWorldPos = new THREE.Vector3();
  headNode.getWorldPosition(headWorldPos);

  const mWorld = new THREE.Matrix4().lookAt(headWorldPos, targetWorldPos, up);
  const worldQuat = new THREE.Quaternion().setFromRotationMatrix(mWorld);

  if (headNode.parent) {
    const parentQuat = new THREE.Quaternion();
    headNode.parent.getWorldQuaternion(parentQuat);
    headNode.quaternion.copy(parentQuat.invert().multiply(worldQuat));
  } else {
    headNode.quaternion.copy(worldQuat);
  }
  headNode.updateMatrixWorld(true);
}

/**
 * Apply one of the three documented reference lighting scenarios (`soft_daylight`,
 * `direct_sun`, `evening`) to a Three.js scene containing `museum`.
 * Returns `{ lightGroup, envRenderTarget, dispose }` for clean consumer lifecycle control.
 */
export function applyMuseumLighting(scene, museum, renderer, scenario = "soft_daylight", options = {}) {
  prepareMuseumMaterials(museum, options);

  const envRT = createMuseumEnvironment(renderer, scenario);
  scene.environment = envRT.texture;

  const lightGroup = new THREE.Group();
  lightGroup.name = `Museum_Runtime_Lights_${scenario}`;
  scene.add(lightGroup);

  if (scenario === "soft_daylight") {
    scene.background = new THREE.Color(0xeef3fa);
    scene.environmentIntensity = 1.06;

    // Pure IBL + subtle sky-to-ground hemisphere balance so dual-UV `aoMap` sculpts
    // every wall corner, base reveal, ceiling recess, and skylight cornice naturally!
    const hemi = new THREE.HemisphereLight(0xf6f9fe, 0xc4beb4, 0.32);
    lightGroup.add(hemi);
  } else if (scenario === "direct_sun") {
    scene.background = new THREE.Color(0xdde8f6);
    scene.environmentIntensity = 0.72;

    const hemi = new THREE.HemisphereLight(0xedf4fc, 0xcbc5ba, 0.45);
    lightGroup.add(hemi);

    const sun = new THREE.DirectionalLight(0xfff4e2, 2.35);
    sun.position.set(6.8, 16.5, 4.0);
    sun.target.position.set(-2.8, 0.0, -2.2);
    sun.castShadow = options.castShadows !== false;
    if (sun.castShadow) {
      sun.shadow.mapSize.set(2048, 2048);
      sun.shadow.camera.left = -16;
      sun.shadow.camera.right = 16;
      sun.shadow.camera.top = 18;
      sun.shadow.camera.bottom = -18;
      sun.shadow.camera.near = 1.0;
      sun.shadow.camera.far = 38.0;
      sun.shadow.bias = -0.00035;
    }
    lightGroup.add(sun);
    lightGroup.add(sun.target);
  } else if (scenario === "evening") {
    scene.background = new THREE.Color(0x162338);
    scene.environmentIntensity = 0.34;

    const twilightHemi = new THREE.HemisphereLight(0x8faad0, 0x5c534a, 0.24);
    lightGroup.add(twilightHemi);

    // Instantiate configurable gallery SpotLights from `Anchor_Light_*` (non-shadow-casting by default!)
    const anchorGroup = museum.getObjectByName("Lighting_Anchors");
    if (anchorGroup) {
      for (const anchor of anchorGroup.children) {
        if (!anchor.name.startsWith("Anchor_Light_")) continue;
        const isAmbient = anchor.name.includes("_Ambient_");
        const spot = new THREE.SpotLight(
          0xffedd6,
          isAmbient ? 14.0 : 36.0,
          22.0,
          isAmbient ? Math.PI / 3.2 : Math.PI / 4.8,
          0.52,
          1.6
        );
        spot.castShadow = false; // Zero unnecessary shadow maps by default!
        const p = new THREE.Vector3();
        const q = new THREE.Quaternion();
        anchor.getWorldPosition(p);
        anchor.getWorldQuaternion(q);
        const dir = new THREE.Vector3(0, 0, -1).applyQuaternion(q);
        spot.position.copy(p);
        spot.target.position.copy(p).addScaledVector(dir, 8.0);
        lightGroup.add(spot);
        lightGroup.add(spot.target);
      }
    }
  }

  return {
    lightGroup,
    envRenderTarget: envRT,
    dispose() {
      scene.remove(lightGroup);
      envRT.dispose();
    },
  };
}
