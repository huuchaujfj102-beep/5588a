# Mythic photorealism V3.1 — mandatory G4-S / G5-S addendum

2026-11-11. Applies to OneFlow ancient-myth cinema and image-to-video projects. Complements global G0-G8 QA and Baxian LOCK V2/V2.1. **Approved master assets override all generic aesthetics.**

## Eight descriptive layers
1. Identity: approved source image SHA-256, anatomy and realistic skin pores/microtexture; no unauthorized face/iris changes.
2. Historical costume: locked layers, weight, weave, cut, adornment and color.
3. Materials: translucency, PBR, wear and natural gravity/drape.
4. Divinity: at most 1-2 well-sourced local supernatural effects, never blanket glow or invented facial markings.
5. Physical force: documented contact or approved levitation, consistent cloth/hair/mist motion and center of mass.
6. Dual lighting: physical key light has position/direction/temperature; divine secondary light has an identified source, trigger, intensity and limited spill/reflection; preserve skin detail.
7. Cinematography: shot/lens/exposure, dark detail, intended color palette, depth of field, restrained film grain/bloom. Keep approved 16:9 masters; 2.35:1 only by explicit approval and safe framing.
8. Scene/props: approved scene ID, terrain, wind/rain direction, locked artifact identity and contact physics.

## Hard gate G4-S (images)
- Verify master pixels/asset hashes with documented visual comparison.
- Inspect skin texture, costume physics, limited sourced divine effects, dual-light coherence, contact/levitation and optical consistency.
- Any FAIL or NEEDS_EVIDENCE blocks APPROVED; never infer image QA from prompt alone.
- Locked Baxian characters must use approved original-image layers/compositing, not text-only character recreation.

## Hard gate G5-S (image-to-video)
- Approved first frame hash and preceding shot state required.
- Track force-field continuity, levitation transitions, primary and divine light over time, facial and prop consistency after occlusion.
- Watch whole video, additionally sample start/middle/end, motion turns, VFX triggers and occlusion recovery.
- Any FAIL/NEEDS_EVIDENCE blocks downstream. Metadata alone is not visual approval.

## Baxian locks
BX01 iron crutch and purple-gold gourd; BX02 giant green fan; BX03 back-carried sword and hand-held flywhisk; BX04 blue-green robe and flower basket; BX05 white donkey with four legs, tack and fish drum/two beaters; BX06 purple robe and purple jade flute; BX07 complete lotus/lotus pedestal; BX08 separate white and green jade boards.
No new iris color, forehead symbol, garment palette or prop design may override these LOCK V2 references.

## Recommended machine data contract
`divinity_effects`, `physical_key_light`, `divine_secondary_light`, `force_field`, `approved_levitation`, `master_sha256`, `approved_first_frame_sha256`, `G4S`, `G5S`.

This document establishes review policy only. It does NOT claim all production adapters enforce these fields at runtime. Do not merge to main until enforcement tests cover the appropriate entrances.

Full Chinese V3.1 addendum and JSON schema archived in the project's Google Drive QA rule folders.
