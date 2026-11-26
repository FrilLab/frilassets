# Agent instructions

- This repository creates reusable digital assets, not a production application.
- Read `docs/asset-layout.md` and the relevant type-specific guidelines before creating an asset. Keep source, generation code when applicable, exports, previews and metadata together in a single asset directory.
- Work on a dedicated branch and do not modify FrilStudio, FrilCraft, FrilRemotion, or FrilAdd. Consult their contracts read-only when relevant.
- Prefer Blender Python and standard glTF/GLB for 3D. Use the appropriate image-generation or procedural workflow for raster assets. Do not introduce application frameworks or dependencies without approval.
- Validate actual output, not only code: geometry and pivots for models, map alignment and color spaces for materials, repeat boundaries for tileable textures, alpha and composition for images, and lighting range for HDR environments. Record file sizes and provenance.
- Do not generate unrelated PBR maps independently; derive or author coherent maps and inspect the results. Never claim measured physical accuracy without evidence.
- Never include secrets, private client media, unlicensed references or third-party content without compatible rights. Only mark reviewed assets CC0. A public branch is already public; keep uncleared source material local. Do not publish to Sketchfab or other external platforms without approval.
- Keep public documentation in English. Do not claim unimplemented tools or unverified results.
- Preserve existing model paths and public mesh names. Do not change shared material files when a model-specific adjustment is sufficient. Document versioned dependencies and do not reference mutable remote URLs at runtime.
