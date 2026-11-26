# Images and environments

## Images

Create reusable illustrations, decorative overlays and backgrounds without baking user-specific names, dates or UI into the artwork. Prefer original subjects and avoid trademarks, identifiable private people, and copyrighted reference copying.

Record the actual generation tool/model, prompt, source dimensions, edits, crop, alpha handling, provenance and rights review. Keep only cleared sources in the public repository.

- Illustrations: transparent PNG or WebP when transparency is needed; inspect edges on light and dark backgrounds. Use SVG only for genuine vector artwork, not a renamed raster.
- Backgrounds: choose dimensions and aspect ratio for intended mobile, desktop, or video usage; document safe areas and crop behavior.
- Keep a high-quality source and optimized derivatives. Verify actual dimensions, transparency, compression artifacts and file sizes.

## Environments

Distinguish decorative backgrounds from lighting environments. A generated LDR panorama does not become physically meaningful HDR lighting by conversion to .hdr or .exr.

For a lighting environment, document source radiance, projection (typically equirectangular 2:1), dynamic range, orientation, exposure and intended use. Validate panorama seams and lighting/reflections on representative objects. Use procedural Blender studio lighting or properly licensed HDR sources when true HDR capture is unavailable. Do not claim HDR accuracy from an LDR source.

No environment assets or HDR processing tools are implemented yet.
