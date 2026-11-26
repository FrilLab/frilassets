# Asset layout

Each asset belongs to `assets/<category>/<slug>/` (lowercase kebab-case). Example, not an existing asset:

```text
assets/wedding/wedding-rings/
  generate.py
  model.blend
  model.glb
  preview.webp
  manifest.json
  textures/  # optional, only if necessary
```

Keep source and deliverables together. Do not commit temporary renders or Blender backups. Use `.work/` for local experiments; ignored files are not a privacy boundary. Review public content before committing. For large binaries, decide on Git LFS or release storage before committing; neither is configured yet.

Use meters and document axes, origin, dimensions and movable parts. Validate GLB loading and inspect visual quality and mobile cost. Record license, source provenance, AI assistance, version and validation status. Only reviewed assets may be released as CC0. Sketchfab publication is a separate manual step; use its current AI disclosure and licensing options.
