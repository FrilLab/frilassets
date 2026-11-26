# Production workflow

1. Select a single asset and stable slug. Read the type-specific rules.
2. Complete the [sourcing gate](asset-sourcing.md) before any generation: search local and external CC0 assets, record evidence, and choose reuse, adapt, or create. If search is blocked, report the limitation before proceeding.
3. Work in a dedicated branch and package; do not modify other repositories.
4. Generate original source or use documented rights-cleared inputs. Record tool/model, prompt, settings and edits. Save reproducible scripts where applicable; stochastic AI image generation may not be exactly reproducible.
5. Build optimized deliverables and previews. Use actual measured properties, not estimates.
6. Inspect output visually and run relevant checks: GLB load and motion clearance for models, seams/map alignment for materials, alpha/crop for images, and range/projection for environments.
7. Record results in the manifest. Keep status draft and license null until human visual and rights review.
8. Open a focused PR. Publish reviewed assets only after approval; use explicit versioned references when consuming them elsewhere.

Start with the source and a small preview before expanding variants. Use higher reasoning effort only for difficult geometry or debugging when available; visual verification remains mandatory.

No generation pipeline, package installer, automatic validation, or publication automation is provided by this scaffold. Suggested checks are manual until tooling is implemented.

For customizable 3D assets, include the exported-runtime checks described in [modeling and customization](modeling-and-customization.md). Check two differently colored instances when instance isolation matters. Do not mark runtime validation successful from Blender renders alone.
