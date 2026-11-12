# Pre-S07-01 24-shot audit — 2026-11-12

Scope: S01-01 through S06-04, original 48-shot script.
Policy: **NO IMAGE GENERATION BEFORE G3-S PREFLIGHT PASS**. S07-01 suspended.

## Evidence tally
- 24 scoped shots
- 14 matched to at least one archived candidate image across retrieved candidate bundles and local review frames
- 6 historical G4 hard-blocks: S04-01 through S05-02
- Other candidates are NOT automatically approved; 9 shots lack directly matched archived candidates; S06-04 has director-accepted version not hash-linked to approved shot registry
- No newly generated images in this audit
- BX05 approved CURRENT hash: ffdb980270e40c8ca48f8c730c7dc07ad7b616a6b9837a5a16d841067a905b2f
- Chat acknowledgements S05-01, S05-02, S06-03, S06-04 must be reconciled to exact image digests; historic reports predate some acknowledgements.

## Earliest stop
S01-01: dark spiral cloud over coast, village lights. Missing G3-S bound shot plate, approved camera axis, and scene master reference. **BLOCKED. No generation allowed.**

## Production rules
1. Resolve original script shot ID and all appearances.
2. Validate bound original character, prop, animal, scene and style assets (SHA-256).
3. G3-S metadata + human preproduction review PASS before any image call, including conversational image tools.
4. Generate ONE independent image using actual approved references; G4 compare pixels, physics and style.
5. Director approval then promote approved image digest only.
6. Stay before S07-01 until all 24 prior shots are evidenced and gaps closed.

Full 24-shot JSON and Markdown audit: /八仙过海/制作储备库_八仙大显神通_20261111/13_S01-S06-04_全量回检_先预检后补图_20261112 in persistent project Library.

**Limitation:** GitHub scripts cannot intercept all ChatGPT image-generation calls automatically. Operator must not invoke generation on blocked manifest.
