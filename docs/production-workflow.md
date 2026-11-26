# Production workflow

1. Select a single asset and stable slug. Read the type-specific rules.
2. Work in a dedicated branch and package; do not modify other repositories.
3. Generate original source or use documented rights-cleared inputs. Record tool/model, prompt, settings and edits. Save reproducible scripts where applicable; stochastic AI image generation may not be exactly reproducible.
4. Build optimized deliverables and previews. Use actual measured properties, not estimates.
5. Inspect output visually and run relevant checks: GLB load and motion clearance for models, seams/map alignment for materials, alpha/crop for images, and range/projection for environments.
6. Record results in the manifest. Keep status draft and license null until human visual and rights review.
7. Open a focused PR. Publish reviewed assets only after approval; use explicit versioned references when consuming them elsewhere.

Start with the source and a small preview before expanding variants. Use higher reasoning effort only for difficult geometry or debugging when available; visual verification remains mandatory.

No generation pipeline, package installer, automatic validation, or publication automation is provided by this scaffold. Suggested checks are manual until tooling is implemented.
