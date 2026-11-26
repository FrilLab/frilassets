# Asset file policy

Track useful, durable files rather than every output of an asset production session. Minimize storage without sacrificing source fidelity, editability, reproducibility, provenance or runtime compatibility.

## File roles

| Role | Default policy |
| --- | --- |
| Canonical source | Track original, rights-cleared inputs and editable source needed to preserve the asset. |
| Generator | Track when used; retain required scripts, configuration and inputs. |
| Runtime deliverables | Track optimized exports required by consumers, including external dependencies if not embedded. |
| Metadata | Track manifest, actual validation results, version, license scope and provenance. |
| Catalog preview | Track one representative preview by default. |
| Diagnostic outputs | Keep local under root `.work/<asset-id>/`; commit only when justified as durable documentation or release evidence. |

A generated file is not automatically disposable. Preserve non-deterministic AI originals, unique hand edits, essential source references, and any input that cannot reliably be regenerated. Never discard license or sourcing records. Consolidate notes into the manifest only if no information is lost; retain notes.md or a separate sourcing record when appropriate.

## Model example

```text
assets/stationery/fril-signature-seal/
  generate.py
  manifest.json
  model.blend
  model.glb
  preview.webp
  material-presets.json  # when used
  source/emblem.svg      # canonical emblem
  textures/              # only required source/runtime maps
```

This is a proposed layout, not a claim that this asset exists in main. Keep the editable Blender source by default. Omit a redundant generated Blender file only when reproducibility and editability are demonstrated and the package explicitly documents that decision. Preserve source/reference.png if it is an essential or irreplaceable design source or needed as evidence. Preserve emblem-mask.png if required and not reproducibly generated from the SVG. Preserve wax-micro-normal.png if the generator or editable source requires it; embedding it in a GLB alone does not prove the authoring dependency is removable.

Use one geometry export for color presets. Keep separate GLBs only for genuinely distinct geometry or independently consumed exports.

## Local work

```text
.work/stationery/fril-signature-seal/
  previews/
  intermediate/
  references/
  validation/
```

The existing .gitignore excludes .work/. Direct generators to write diagnostic views, comparison renders, temporary masks and experiments there. Do not globally ignore PNG, WebP, textures, source, or previews directories: legitimate runtime assets and provenance can use these names. A gitignore rule does not untrack existing files and is not a privacy boundary. Do not rewrite history or delete user work for routine cleanup.

## Distribution boundary

The authoring repository is not the consumer install payload. A self-contained model GLB normally needs no separate texture files at runtime. Include optional presets only when consumers use them, and include required external files and applicable license notices. Do not install Blender files, generation scripts, or diagnostic previews into application runtime bundles. Catalog metadata or preview may be distributed separately if needed.

Document the explicit runtime file list and source dependencies in manifest.json or notes.md. This is a documentation convention, not a new mandatory schema or implemented FrilAdd contract. Do not assume an installer exists or supports these fields.

## Before committing

1. Inspect generator inputs, Blender external/packed resources, exported GLB references and consumer requirements.
2. Keep rights-cleared canonical sources, required dependency files and provenance. Move redundant diagnostics to .work/ without deleting irreplaceable inputs.
3. Verify the package from a clean checkout or isolated copy containing only proposed tracked files. Run the documented generator when applicable, open the editable source, and load the runtime export. Verify no dependency on .work/ or absolute machine-local paths.
4. Record actual validation results and any blocked checks. If dependency closure cannot be established, retain the questionable files rather than removing them.
5. Report the proposed tracked file list, runtime distribution list, measured byte sizes and any exceptions. Review git status and diff before committing.

Large binaries require a deliberate storage decision; this policy does not configure Git LFS, release hosting, automated cleanup or packaging.
