# S03-01 Eight Immortals layer preparation — 2026-11-12

Original 48-shot screenplay: eight actors form two rows, all looking toward the disaster sea; one 16:9 shot.

## Completed (safe non-generative extraction)
- Retrieved 8 director-approved current mother images, including the latest BX05 Zhang Guolao CURRENT rather than older V2.
- For each: preserved complete original pixels, source SHA-256, non-repainted face/upper-body crop, non-repainted prop/person crop, provisional per-actor foreground matte.
- Standalone prop sources preserved where available: BX04 flower basket, BX05 fish drum reference, BX06 purple flute, BX08 two jade plates.
- Corrected an earlier BX06 inspection mistake: the flute-only source is **not** an approved BX06 actor portrait. The true actor mother photo is `BX06_韩湘子_定型母图_LOCK_V2_20261111.png` SHA-256 `7dc62ebdae359fefc318ce91392688c031203147a26b97def06f47bc55330395`.
- Created a **draft** two-row layout, not an accepted assembled keyframe.

## Failing G4 findings (critical)
Automatic rough GrabCut foreground mattes **FAIL**: BX05 and BX06 faces are missing; BX04 and BX08 have missing edges/feet, among other extraction artifacts. Do not use these masks in production. Restore heads, feet, hair, donkey and props from lossless approved masters using hand-checked segmentation. This draft does not authorize generation.

## Pending G3-S
1. Manually repair isolated full-body reference layers, including BX05 donkey and authentic fish drum without swapping identity.
2. Verify each of 8 identities, props and support points independently.
3. Choose/director-approve fixed coastline background and camera axis.
4. Resolve S02-04 director-approved images versus G4 technical final.
5. Confirm real adapter input bindings for all references before single-frame composite. No image generation or next shot while G3-S BLOCK.

Archive: ChatGPT Library `/八仙过海/制作储备库_八仙大显神通_20261111/25_S03-01_八人定型资产拆解_20261112` contains a 41-file source and work-layer zip, SHA manifest and fail report. The zip includes failed masks for debugging only.
