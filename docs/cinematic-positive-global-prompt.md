# 文档 1｜正向全局约束 Prompt · 工业影视序列专业完整版 V2.1

适用：静态关键帧生成、Seedance 2.0/2.5 与 VQ3-Pro 等视频生成的参考帧准备、Remotion 合成前检查、UE5 渲染参考。**文本约束不能保证模型实际使用 UE5、路径追踪、ACES 或原生 8K；这些仅在真实渲染管线可验证。**

## 可直接挂载到正向词头部（英文母版）
```text
CINEMATIC SERIES MASTER CONSTRAINT — APPROVED SHOT BIBLE IS THE SOURCE OF TRUTH.
Feature-film-grade cinematic photorealism; finely resolved organic texture, realistic dynamic range, carefully graded cinematic color, physically based materials and believable optics. UE5 path tracing, ACES color management, ray-traced indirect light, and native 8K are TARGETS ONLY when the selected engine/pipeline truly supports and verifies them.
Preserve approved subject identity, facial structure, skin tone, iris color, hair, costumes, accessories, wear state, prop inventory, vehicle geometry, signage orientation and exact scene-world coordinates across contiguous shots. Use approved reference images and recorded asset IDs; no unauthorized additions or redesigns.
Anatomically coherent bodies and living creatures: valid skeleton, joints, finger anatomy and natural articulation; one human hand has five digits in its anatomy, although fingers may be hidden by pose/occlusion. Hair and costume attach to their correct origins and respond to gravity/contact.
Coherent rigid-object structure, stable silhouettes, structurally plausible connections and supports; accurate spatial occlusion, surface contact, grounded shadows and believable scale. Preserve mechanically motivated motion and any explicit fantasy propulsion system.
One consistent camera projection and shot-defined camera position, height, orientation, focal length, focus and depth of field; valid perspective with appropriate vanishing points for each family of parallel world lines, without incompatible projections.
Motivated primary/key lighting with coherent fill, bounce and practical lights; shadows and reflections match actual emitters, geometry and surface properties. Consistent scene time-of-day and color pipeline; physically credible umbra, penumbra, Fresnel, appropriate subsurface scattering and atmospheric attenuation.
PBR response appropriate to each substance: base color, metalness, roughness, micro-normal, anisotropy where applicable, glass transmission/refraction, volume absorption and scattering; natural texture continuity and localized wear/contact staining.
Temporal state continuity: preserve object positions, character look, door state, hand occupancy, weather, light direction and action phase across adjacent frames unless a recorded story event changes them. Camera moves must respect scene world coordinates; prefer approved-base-frame animation for continuous push/pan/tracking.
Typography, exact branding and watermarks are applied from approved source assets or in post-production; otherwise leave clean surfaces or intentional optical defocus, with no invented glyphs.
Weather, vegetation, liquid, smoke, flame and particles show physically motivated source, direction, density and depth; no flat particle billboards unless explicitly selected as art direction.
A single self-consistent decisive cinematic still frame, optimized as a robust reference for sequential shot assembly and subsequent image-to-video animation. Honor specified artistic exceptions and never sacrifice established asset truth for spectacle.
```

## 中文施工说明
1. **先资产真值，再导演创意**：角色卡、场景卡、机械卡、镜头卡、灯光卡、状态时间线必须锁定。人物脸/服装/伤痕/道具、门窗/招牌/喷口坐标及左右方位跨镜头不改。
2. **相机与透视**：一个统一投影模型并不意味着只有一个消失点；两点/三点透视中的各组平行线存在不同消失点。镜头改变可引起画面投影变化，不能因此改世界坐标。
3. **人体与遮挡**：人手解剖学上五指，不要求被遮挡的五指全部露出；复杂手势要描述握持、接触、手背/手心方向。
4. **光影**：允许多光源，要求明确主光、辅光、实景灯及各自投影；阴影可能不完全平行，不能用绝对单一光向误判。
5. **PBR / 体积介质**：玻璃、织物、金属、皮肤各自遵循相应光学属性；反光必须映射实际环境；体积雾、火焰、水流有来源和连续变化。
6. **镜头参数**：写入机位位置/朝向、焦距、焦点、景别、光圈/快门意图；不能混用冲突的景深、透视及运动模糊。
7. **精确文字**：logo、中文招牌、品牌水印优先由批准素材/Remotion 后期合成；禁止依赖扩散模型自行拼准字符。
8. **跨镜头时间线**：动作前后顺序、物体启停、门开关、手持道具及天气由镜头状态表驱动，不允许“重生”背景。
9. **8K**：仅真实 7680×4320（16:9）或约 8K 等效规格时才能标记 8K，竖版要记录真实像素，放大不得冒充原生。
10. **可用性**：长版是工程母版；对提示词长度敏感的模型使用压缩版。效果必须以实际样图/人工审图验证。

## 每镜头填写字段（在全局正向约束之后）
```yaml
scene_id: SC01
shot_id: S01
continuation_of: null
asset_reference_ids: [CHAR01, VEH01, ENV01]
approved_reference_hashes: []
world_state: "黄昏 / 无雨 / 地面干燥"
action_phase: "引擎启动之前"
camera: "高度1.4m / 35mm / 右前45° / 中景 / 眼部焦点"
lighting: "右后方暖夕阳主光；天空冷蓝环境辅光"
materials: "金属车身清漆与玻璃折射真实"
allowed_exceptions: []
target_output_pixels: "1344x768"
review_status: PENDING
```

## 制作流程
全局规则版本固定 + 批准资产卡 → 分镜局部描述 → 渲染首帧 → QA（解剖/机械/空间/光影/材质/文字） → 人工签核 → 图生视频 → 首尾帧一致性检查 → Remotion 合成/技术/版权终检。未核准不自动发布。
