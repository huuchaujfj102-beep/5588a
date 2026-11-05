# 文档 2｜负面抑制 Prompt · 分层完整母版 V2.1

适用：模型提供独立 negative_prompt 接口时使用。**权重语法 (term:1.4) 并非通用标准**：仅在模型/后端明确支持时使用；其他模型使用纯文本版。部分模型忽略负面词，此时须改写正向约束、使用参考图和后期审图。负面项不能覆盖明确批准的艺术设定。

## A｜致命拓扑、身份、机械结构（最高优先级 1.4）
```text
anatomical defect, extra limb, missing limb, extra digits, fused fingers, inverted palm, twisted wrist, dislocated joint, duplicated face or eye, deformed facial topology, detached hair mass, self-intersection, geometry clipping, mesh penetration, floating prop without story motivation, broken support, wrong number of wheels, disconnected engine component, wrong prop attachment, duplicated subject, identity drift
```
**审核**：出现非剧情允许的断肢、多肢、手指畸形、穿体、车体结构变化、镜头间身份漂移，直接 FAIL。

## B｜遮挡、透视、光影、连续物理（优先级 1.3）
```text
broken occlusion, phantom geometry through walls, inconsistent camera projection, contradictory vanishing geometry, implausible scale, warped architecture, ground-plane discontinuity, inconsistent lighting with motivated light sources, impossible shadow placement, reflection of nonexistent objects, inconsistent time of day, unsupported object motion, teleporting assets, impossible action order, weather continuity error
```
**审核**：空间反转、前后帧门窗/道具世界坐标变化、无动机投影/反光、动作时序矛盾，直接 FAIL。允许合理多光源及经设定的魔法/飞行。

## C｜文字、材质、成像与生成伪影（优先级 1.15）
```text
garbled glyphs, accidental text, inaccurate logo, clock dial anomaly, gauge marking inconsistency, wrong material roughness, fake metal, plastic skin, stretched texture, random stains without contact cause, broken glass refraction, fake planar smoke, flat flames, depth-of-field inconsistency, unnatural bokeh, extreme chromatic aberration, random lens flare, banding, moire, checkerboard artifact, compression blocks, hallucinated microdetails, noisy texture seams
```
**审核**：可读品牌信息失真按 P0 处理；其他缺陷按可见程度 FAIL 或修复。

## D｜风格污染、一般画质瑕疵（较低优先级 1.0）
```text
cartoonish toy look, unwanted illustration, oversaturated fluorescent palette, overprocessed skin, waxy face, excessive sharpening, crushed shadows, clipped highlights, uneven grain, blurry primary subject, low resolution, distracting color noise, arbitrary dust overlays
```
**审核**：仅当目标是写实电影风格时使用“不要卡通/动漫”，若项目要求动漫或幻想美学，应移除冲突词。

## 直接粘贴的加权版（只用于确认支持权重的模型）
```text
(anatomical defect, extra limbs, fused fingers, inverted palms, duplicated faces, geometry penetration, broken machinery, identity drift:1.4),
(broken occlusion, incompatible perspective, wrong asset scale, conflicting motivated lighting, impossible shadows, teleporting props, action-order errors:1.3),
(garbled text, fake materials, distorted texture, broken glass refraction, planar smoke, incorrect focus, chromatic aberration, moire, compression artifacts:1.15),
(unwanted cartoon toy aesthetic, oversaturation, wax skin, clipped highlights, crushed shadows, blurry subject, noisy grain:1.0)
```

## 纯文本版（推荐跨平台默认）
```text
Anatomical defects, extra limbs or digits, fused fingers, duplicated faces, self-intersecting or penetrating geometry, detached or floating props without narrative support, changed character identity, changed vehicle structure; broken occlusion, incompatible perspective, contradictory scale, physically inconsistent motivated light and shadow, impossible reflections, teleporting assets or impossible action order; garbled glyphs and unauthorized logos, wrong PBR surfaces, stretched or synthetic textures, fake smoke and flames, conflicting focus and bokeh, optical aberrations, compression blocks, checkerboards, moire, color banding and hallucinated detail; unwanted toy-like style, waxy skin, excessive saturation or sharpening, clipped highlights, crushed shadows, heavy noise and blurred subject.
```

## 模型路由与三条红线
- **支持独立 Negative + 权重**：使用加权版；不要自行假设 Seedance、VQ3-Pro 或某个 API 支持 `:1.4`。
- **仅支持独立 Negative**：使用纯文本版；按 A → B → C → D 顺序，不发送权重符号。
- **无独立 Negative（当前 HF FLUX 调用路径）**：仅在 plan 中保存建议；关键硬约束写入正向前置块；不得声称负面参数已被模型执行。
- **硬红线**：未批准的 A/B 类严重穿帮、镜头身份/结构/空间不连续必须重生/修复；人工签核前禁止图生视频和发布。
- **豁免机制**：允许经过角色/世界设定批准的飞行、悬浮、特殊结构、动漫风格，不应被负面词错误抑制。
- **权重不是质量保证**：需要针对目标模型小样 A/B 测试，评估是否出现提示词过载或损害创意。
