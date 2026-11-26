# Collection 001 — Wedding Stationery

Proposed production backlog, not a list of released assets. Begin with the existing wedding envelope project, then create reusable material and image packages independently.

- [ ] `assets/wedding/wedding-envelope/` — envelope, flap, card, optional wax seal.
- [ ] `materials/paper/ivory-cotton/` — subtle matte cotton fibers.
- [ ] `materials/wax/champagne-wax/` — muted warm sealing wax.
- [ ] `materials/paper/premium-cardstock/` — brighter, fine-grain cardstock.
- [ ] `images/botanical/olive-branch/` — original transparent illustration.
- [ ] `images/botanical/white-rose/` — original transparent illustration.
- [ ] `materials/fabric/ivory-silk/` — reusable silk surface.
- [ ] `materials/metal/gold-foil/` — restrained metallic foil.
- [ ] `images/backgrounds/wedding-editorial/` — neutral editorial background.
- [ ] `environments/studio/soft-studio/` — validated studio environment or documented procedural lighting setup.

Art direction: warm ivory, cream, soft botanical greens, muted champagne accents, restrained editorial composition. Avoid baked invitation text and unnecessary ornament. Each item needs independent source, preview, metadata and applicable review before publication.

Consumers may reuse individual packages; do not require the complete collection to load one asset.

## Envelope assembly contract

Keep envelope body, flap, letter card and optional wax seal in one GLB with independent transforms and material groups. Reuse a single geometry for color presets. Use a neutral paper texture and a separately addressable front card artwork slot; do not bake invitation text. The initial seal may use one original botanical motif. Additional seal designs are optional geometry or relief-map variants, not color duplicates. Standalone seal exports are optional when a consumer needs them. Preserve the existing asset path and published object names; see [model customization](../modeling-and-customization.md). This is a specification, not a claim that the model exists or passes tests.

## Sourcing-first backlog

All items above are needs, not instructions to generate from scratch. Search before producing each item. Initial candidates (not downloaded or technically approved): ambientCG [Paper 001](https://ambientcg.com/view?id=Paper001), [Paper 005](https://ambientcg.com/view?id=Paper005), [Paper 006](https://ambientcg.com/view?id=Paper006), and [Poly Haven Studio](https://polyhaven.com/a/poly_haven_studio). Check actual texture appearance, maps, physical scale, lighting and mobile budget. For envelopes and seals, verify pocket geometry, independently movable parts, pivots and UVs; adapt suitable existing assets or create only when no candidate meets the requirements.
