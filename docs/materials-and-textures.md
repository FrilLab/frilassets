# Materials and textures

A texture is image data; a material defines how a surface responds to light using parameters and optional maps. A standalone texture can be reused without a material.

## Production

- Generate a flat, evenly illuminated source with no baked highlights, shadows, perspective, watermark, or visible sheet edges.
- Target 2048 x 2048 source resolution when available; record actual resolution, not requested resolution. Prefer 1024 or 512 web derivatives as appropriate.
- For tileable maps, inspect a 3 x 3 tiled preview and repair seams. Non-tileable artwork must be marked as such.
- Keep maps spatially aligned. Derive normal from a coherent height field when appropriate; do not treat luminance as measured height or roughness. Inspect and tune inferred maps.
- Use sRGB for base color; linear/non-color for normal, roughness, metallic, height and AO. Use glTF/OpenGL tangent-space normals (+Y); document conversions.
- Use scalar roughness and metallic values when maps add no value. Paper and wax are normally dielectric (metallic 0); metallic foil is a separate material.
- glTF metallic-roughness packing uses G for roughness and B for metallic; R may hold AO when explicitly shared and compatible. Do not confuse independent source maps with packed runtime maps.
- Height maps are optional authoring data, not a core glTF displacement feature. Bake or use runtime-specific handling only when required and documented.
- Preserve lossless data maps where necessary; avoid lossy normal-map artifacts. KTX2 compression is optional and requires compatible consumer decoding; no encoder is configured here.
- Record physical repeat size in meters, intended UV scale, map dimensions, color space and measured file sizes.

## Material package

Use `templates/material.json` as a descriptive starting point, not an implemented loader contract. Relative map paths are local to the material package. Remove entries for maps not supplied and record actual parameters.

Validate on a flat surface, a sphere, and a representative object. Compare Blender and Three.js under controlled lighting when both are available. Report unperformed checks explicitly. Aim for subtle surface variation rather than noisy, exaggerated bumps.

## Runtime customization

For arbitrary recoloring, prefer no base-color texture or a neutral near-white texture with subtle surface variation. glTF base color factors multiply the sampled base-color texture; a saturated baked color cannot be reliably recolored to arbitrary hues. Keep normals and roughness independent. Do not bake lighting into recolorable surfaces. Preserve intentionally colored illustrations as separate artwork, with separate UV mapping or material slots where needed.

Use parameter presets for color and finish variants rather than duplicate geometry or GLB files. A material library package is justified by reusable surface data or a distinct physical finish, not merely a new hex color. Consumers should clone mutable shared materials per instance or customization group and dispose owned clones on teardown, without disposing shared textures. For example, body and flap can intentionally share one exterior material; the letter and wax seal must not share that mutable material. See [modeling and customization](modeling-and-customization.md).
