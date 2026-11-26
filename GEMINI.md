# Gemini workspace

Follow `AGENTS.md`, `docs/asset-layout.md`, and the relevant type-specific guidelines.

Create one asset at a time in its own category and slug directory. For models, preserve reproducible Blender Python scripts and export a standalone GLB. For images, preserve the cleared original generation output and record the prompt, model/tool, and editing steps. For materials, derive aligned maps from a coherent surface source and document physical scale and color spaces. If image generation is unavailable, report it rather than substituting unrelated assets.

Inspect actual renders or images, record measured validation results, and leave the asset unreleased until review. Do not change other repositories or install dependencies without approval. Keep experiments in local `.work/`; ignored files are not a security boundary.

See `docs/production-workflow.md` for the review gates and `docs/collections/wedding-stationery.md` for the first proposed collection.

For every 3D task, follow `docs/modeling-and-customization.md`. Keep envelope, flap, letter, and optional seal in one assembly GLB; do not duplicate geometry for color variants. Use neutral textures, stable semantic material slots, explicit pivots, and a separate letter-front content surface. Keep standalone seal or letter exports optional rather than mandatory. Test the exported GLB, not just the Blender source.

Before any image or model generation, perform the sourcing gate in `docs/asset-sourcing.md`. Prefer reuse, then adaptation, then original creation. Do not generate new assets when a suitable CC0 package already exists. Record sources and decisions in the asset notes; if web access is unavailable, stop at the sourcing blocker and report it.
