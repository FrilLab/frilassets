# Asset sourcing — search first, create last

## Required gate

Before any new model, material, texture, illustration, background or environment generation:

1. Define intended use, visual requirements, formats, runtime customization and performance constraints.
2. Search existing FrilAssets packages and relevant consumer assets read-only. Avoid duplicating existing assets.
3. Search relevant external sources (normally at least two where applicable). Prefer original publisher pages and exact asset license evidence. Record query, date, candidate URL, author/provider, license URL and decision. Do not treat a search result or a free download as proof of CC0.
4. Compare visual quality, geometry, UVs, pivots, maps, formats, file size and expected adaptation work. Inspect actual files before marking them technically accepted.
5. Choose **reuse** if suitable, **adapt** if focused changes suffice, or **create** only if no suitable cleared candidate is found or adaptation is demonstrably less efficient. Record why. If search is unavailable, report the blocker and do not claim absence of candidates.

## Discovery sources

| Source | Typical use | License verification |
| --- | --- | --- |
| [Poly Haven](https://polyhaven.com/) | models, materials, HDRIs | [CC0 asset policy](https://polyhaven.com/license) |
| [ambientCG](https://ambientcg.com/) | PBR materials, HDRIs, models | [CC0 asset policy](https://docs.ambientcg.com/license/) |
| [Sketchfab](https://sketchfab.com/) | models | verify exact downloadable model and CC0 grant |
| [Kenney](https://kenney.nl/assets) | stylized assets | [support](https://kenney.nl/support); verify pack and archive |
| [Quaternius](https://quaternius.com/) | stylized models | [FAQ](https://quaternius.com/faq.html); CC0 and QAL are distinct, reject non-CC0 for the CC0 collection |
| [Openverse](https://openverse.org/) | images and illustrations | filter CC0, confirm on original publisher page |
| [Wikimedia Commons](https://commons.wikimedia.org/) | illustrations and images | verify exact file page and underlying rights |

The list is a search starting point, not blanket approval. Recheck current terms, file-specific exceptions, and rights in trademarks, depicted people and third-party components.

## Provenance and publication

Keep a sourcing record in notes.md or a linked package record. For imported assets record exact source URL, title, creator, license identifier and evidence URL, access date, downloaded version/file name and checksum when available, local file scope, modifications and measured validation. Preserve original notices and license evidence. Mark origin as third-party or adapted; record AI assistance accurately. CC0 does not require attribution but retain provenance for traceability. Do not claim authorship over unchanged external work or upload it as original work to Sketchfab. Review platform terms before any redistribution there.

Keep only needed, rights-cleared files; avoid mirroring entire libraries. Do not download restricted files, bypass access controls, or commit uncleared inputs. Public-domain marks and other licenses are not interchangeable with CC0; record separately and seek approval before including them. Prefer provider links when local redistribution is unnecessary. Do not introduce mutable remote runtime dependencies.

Use [the sourcing template](../templates/sourcing.md). This policy does not implement automated search or download tooling.
