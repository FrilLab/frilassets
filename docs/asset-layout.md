# Asset layout

Use lowercase kebab-case slugs. Preserve existing model paths.

| Type | Package path |
| --- | --- |
| 3D model | `assets/<category>/<slug>/` |
| Material | `materials/<category>/<slug>/` |
| Standalone texture | `textures/<category>/<slug>/` |
| Image | `images/<category>/<slug>/` |
| Environment | `environments/<category>/<slug>/` |

Examples only; these assets are not yet implemented:

```text
assets/wedding/wedding-rings/
  generate.py
  model.blend
  model.glb
  preview.webp
  manifest.json
  textures/  # optional model-specific maps

materials/paper/ivory-cotton/
  source/original.png
  maps/basecolor.webp
  maps/normal.png
  maps/roughness.png  # optional
  material.json
  generate.py         # when applicable
  preview.webp
  manifest.json

images/botanical/olive-branch/
  source/original.png
  image.webp
  preview.webp
  manifest.json
```

Keep source and deliverables together. Shared material maps belong to the material package; standalone textures belong to the texture package. A self-contained GLB may embed copies of its required maps. Record the source package path and version when reusing a material; do not rely on a network fetch.

Use `templates/manifest.json` for existing model packages and `templates/digital-asset.manifest.json` for other types. The existing model ID convention remains unchanged. New non-model IDs are namespaced by their root directory.

Do not commit temporary renders or Blender backups. Use `.work/` for local experiments; ignored files are not a privacy boundary. Review public content before committing. For large binaries, decide on Git LFS or release storage before committing; neither is configured yet.

For models, use meters and document axes, origin, dimensions and movable parts. Validate GLB loading and inspect visual quality and mobile cost. Record license, source provenance, AI assistance, version and validation status. Only reviewed assets may be released as CC0. See [publication](publication.md).
