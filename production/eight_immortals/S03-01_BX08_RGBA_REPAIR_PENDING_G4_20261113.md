# S03-01 V3.8.0 segmentation progress — 2026-11-13

Current approved BX08 Cao Guojiu (white-cloud jade and green-dragon jade tablets) is being isolated from the exact CURRENT mother image.
- Alpha extraction attempted against the correct version only; original RGB pixels have not been re-rendered.
- First matte QA detected missing feet, so both footwear regions were restored using source pixels with manually authored alpha masks.
- Source/full layer RGB bytewise pixel comparison: **0 changed RGB pixels**. This verifies no repaint; it does not prove alpha edge quality.
- G4 manual review is still required for crown/hair/cloth/jade/boot edges. This layer is **work in progress**.
- S03-01 G3-S remains **BLOCK**, no Eight Immortals group generation and no S03-02.

Library archive: /八仙过海/制作储备库_八仙大显神通_20261111/32_S03-01_BX08受控分层精修_20261113
Includes a true RGBA PNG, preview, JSON source hash/QA record and ZIP.

Do not reuse older seven mismatched-source masks or treat the archive as a director-approved composite.
