# Reusable modeling and runtime customization

## Core principles

Geometry defines shape; materials define surface response; textures provide spatial data; animations define motion. Keep these concerns independently replaceable where the asset requires customization. A color, roughness, metalness, or compatible texture change does not justify a new model. Shape changes, true relief, or substantially different mechanical construction may justify geometry variants.

Use Blender Python for reproducible procedural models where practical and standard glTF/GLB for web delivery. Keep source and outputs together. Do not introduce an application framework, rendering engine, or consumer dependency here.

## Assembly and naming

Default to one self-contained GLB per assembled asset. Preserve meaningful object/node names and hierarchy through export. Separate movable parts and independently editable surfaces; do not merge them for optimization if that breaks the contract. Internal static geometry can be joined when appropriate. Additional standalone GLBs are optional when independent distribution or use warrants them. Avoid divergent copies of generators.

Use meters, document the exported glTF local axes, dimensions, attachment points, rotation signs and transform defaults. Place hinge pivots on actual fold lines; preserve local transforms and unit scale. Verify motion clearance through intermediate poses. Do not flatten animation-critical hierarchy.

## Wedding envelope example

Suggested structure for the existing asset path `assets/wedding/wedding-envelope/`:

```text
Envelope_Root
  Envelope_Body
  Envelope_Flap_Pivot
    Envelope_Flap
  Letter_Card
  Wax_Seal (optional)
```

Preserve existing exported names if already established. The body must be a usable pocket, the flap must rotate around the hinge, the letter must slide through the opening, and the optional seal must clear the flap before opening. Do not require a separate GLB for each part. If independently distributed later, export from the canonical geometry with documented attachment conventions.

Suggested semantic material slots (preserve already established names or document mappings):

- Paper_Exterior: intentionally shared by body and flap.
- Paper_Interior: separate only if independently meaningful.
- Cardstock: card back and edges.
- Letter_Front: independently addressable artwork surface; can use the same initial paper appearance.
- Sealing_Wax: optional seal material; existing Wax_Champagne_Gold name may remain as an alias/mapping.

The letter front needs a clean, non-mirrored UV layout with documented orientation and usable 0–1 artwork region. A dedicated material slot or a separately named surface is sufficient; do not add coplanar duplicate geometry causing z-fighting. Keep user names, dates and photos out of the source geometry and default textures. The consumer supplies content at runtime.

## Materials and variants

Use standard glTF metallic-roughness PBR (physically based rendering). Prefer dielectric paper and wax. For recolorable surfaces, use neutral near-white base maps or no base map, independent normal/roughness data, and no baked directional lighting. glTF base color multiplies texture color, so a saturated source cannot be arbitrarily recolored. Preserve actual multicolor artwork separately when needed.

Store lightweight color/finish presets, not one GLB per color. Different seal motifs may use actual relief geometry or a normal map if shallow visual relief suffices. Document that normal maps do not change silhouette or collision geometry. A new standalone material package is useful when surface data is reusable, not for each color alone.

Three.js consumers should isolate mutable materials between independently customized instances, preserving intentional sharing within each instance. Clone the material, not necessarily the geometry or textures; dispose owned material clones and avoid disposing shared textures. For arbitrary replacement of a letter-front texture loaded separately in Three.js, ensure glTF-compatible orientation (typically flipY=false) and sRGB color space for color artwork. This is a consumer convention, not an implemented integration.

## Exported-runtime acceptance

When applicable, test the exported GLB with a standard GLTFLoader:

1. Required named nodes, material groups, pivots, UVs and animation clips survive export.
2. Change envelope, letter and optional wax colors independently without geometry changes. Test a light and saturated/dark color.
3. Replace the paper surface material and letter-front image independently; verify UV orientation, edges and absence of unintended changes to the back.
4. Verify independently customized instances do not leak material changes; preserve deliberate body/flap sharing.
5. Rotate flap, slide letter, release optional seal, and inspect intermediate poses for clipping.
6. Compare rendered output, count triangles and record actual GLB size. Document limits and any unavailable checks.

Record stable node names, material slot mappings, pivots, axes, UV orientation, default values, supported customization properties, and actual validation results in notes.md and manifest.json where appropriate. These are documentation conventions; no new mandatory manifest schema or loader is introduced. Do not claim completion without actual checks.
