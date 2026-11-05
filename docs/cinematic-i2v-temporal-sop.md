# 文档 3｜电影级图生视频时序运动约束与审片 SOP V3.0

> 链路：文档1正向生图 → 文档2负面生图 → **静态底图人工批准** → 本文I2V时序运动 → 审片 → 合成调色与版权/技术终审。
> 适配 Seedance 2.0/2.5、Vidu Q3 Pro（如用户称 VQ3-Pro，需核对其实际产品/API）、Wan/ComfyUI、Remotion 后期。**提示词不等于引擎真正执行 IK、Navier–Stokes、光追或运动矢量控制。** 功能需按供应商接口独立验证。

## 0. 首帧准入（硬门禁）
- source_image_status 必须为 `PASS_HUMAN`；保存原图 hash、尺寸、角色卡/场景卡/机械卡/灯光卡、授权与故事时间线；若缺少证据则 `REVIEW_REQUIRED`，**不得宣称自动验证通过**。
- 已批准画面中的刚性结构、人物身份、服装轮廓、机械组件及世界坐标均是不可擅改的真值。图生视频不能当作静态穿帮的修复工具。
- 特殊设计（飞行超跑喷口、魔法悬浮、二次元角色）用 `allowed_exceptions` 显式记载，不能以常规物理否定剧本规定。
- 精确品牌标识/“造镜者”动态水印优先在 Remotion/FFmpeg 合成，原始图像如存在不受控乱码先修复。

## 1. 七模块正向时序 Prompt（复制模板）
```text
1. REFERENCE LOCK: Approved reference frame is the absolute starting frame and source of truth. Preserve character identity, facial bone structure, eyes, hair roots, costume design, rigid vehicle geometry, architecture, static props, camera-facing side, scene map and approved world state. No spontaneous scene reconstruction or unauthorized object additions.
2. SUBJECT MICRO-MOTION: Animate only the specified action phase; preserve natural articulated joint movement, contact, support, weight shift, acceleration, inertia and deceleration. Hair, cloth and foliage respond smoothly to motivated forces, with consistent wind conditions. Keep all rigid surfaces dimensionally stable.
3. ENVIRONMENT DYNAMICS: Weather, fire, fog, smoke, splashes, dust and light beams evolve continuously with spatial depth, believable source, particle lifetime, gravity and environment. No random emission or scene resets.
4. SINGLE CAMERA MOTION: One deliberate camera operation per shot (e.g. slow push-in, horizontal track, orbit around established pivot, or expressly scripted dolly-zoom). Maintain coherent projection, parallax, focal behavior and scene world coordinates; do not blend independent random shake/rotation/zoom.
5. TIME-CONTINUOUS LIGHTING AND MATERIALS: Lock motivated lights, color treatment, surface roughness/metalness and identity of reflectors. Shadows, highlights, reflections, volume scattering and exposure evolve only for valid viewpoint/subject changes or explicit lighting events. No frame-to-frame relighting or material shimmer.
6. CINEMATIC OUTPUT: Temporal coherence, stable focus and bokeh, plausible camera/subject-relative motion blur, clean optical flow without double interpolation, approved framing and target frame rate. 180-degree shutter is an OPTIONAL cinematic baseline where controllable, not a requirement for every action. Keep image look and grading consistent. Use true delivered resolution only; ACES, 8K and physical simulation only if pipeline actually implements them.
7. NEGATIVE / FAILURE AVOIDANCE: No face swaps, identity drift, finger-count mutation, moving static geometry, object teleportation, flicker, exposure pumping, material crawling, random light or lens flare, reverse-parallax illusion, incoherent optical flow, excessive ghosting, or unmotivated camera jitter. Preserve screenplay exceptions and approved motion requirements.
```

### 独立负面提示词（仅适用于支持 negative_prompt 的引擎）
A 严重（示意相对优先级 1.4）：temporal flicker, face swapping, topology morphing, rigid object deformation, changing finger count, prop teleportation, severe clipping, world layout rebuild, impossible action order, spatially inconsistent optical flow。
B 严重（示意 1.2）：shadow jumps, exposure pumping, roughness flicker, wrong motion blur direction, ghosting, reversed parallax where camera geometry forbids it, unsupported inertia, random camera shake, cloth/hair twitch, volume flashing, inconsistent specular tracks。
C 一般（示意 1.0）：heavy compression, color banding, noisy grain chatter, excessive flare, unwanted stylistic shifts, low detail, bad frame interpolation。

**权重语法不是跨模型通用格式**；未经供应商确认不得发送 `(term:1.4)`。不支持独立 negative 时将关键禁止行为放到正向第7模块，另外记录审核数据，不伪称API已接受 negative。

## 2. 分层运动权限
| 层 | 允许的变化 | 驳回事项 |
| --- | --- | --- |
| 静态刚性：建筑、地面、固定桌椅、车体骨架 | 相机投影变化；剧情明确允许的门轴转动/机械可动件 | 刚性墙门轮廓蠕动、车轮/喷口数量随机改变、纹理游走 |
| 柔性：布料、发丝、植物、旗帜 | 风/惯性/接触驱动的连续摆动、自然阻尼 | 高频抽动、发丝穿头骨、布料穿体、无因拉扯 |
| 主动驱动：人物/动物/有动力设备 | 解剖关节范围内运动、支撑及重心变化、驱动力的正确因果顺序 | 突然变脸、手部逐帧生长、脚底滑移、无因瞬移 |
| 体积/粒子：雨雾烟火/水花 | 发生、发展、消散的连续体积与生命周期 | 全屏逐帧刷新、无源烟火、无重力/风向关系 |

相机**横移**导致的视差与空间深度有关，前景通常比远景位移显著；但纯旋转/变焦不应套用“前景必大于远景”的硬规则。运动模糊由快门时间与相机/物体相对运动决定；180°仅是常用创作选项，非每镜头硬性标准。胶片颗粒参数可稳定，但颗粒图样可按胶片仿真随帧随机，重点是不能出现非意图的闪烁与斑块。

## 3. 场景光影、PBR 与时序锁定
- 光源的**世界位置与规则**保持稳定；移动物体或相机时，阴影、高光、反射本来就会变化，要求变化连续而非坐标完全不变。
- 曝光、白平衡与 LUT 在单镜头内通常锁定；明显进入暗室/逆光、剧本指定灯光启动时可记录合理的连续调整。
- 金属度/粗糙度/表面纹理是资产属性而不是帧帧重绘变量；水、雨、湿润、磨损等剧情变化须有连续因果。
- 角色毛发根部、服装版型、饰品和痣疤不漂移；自然眨眼/表情允许细节变化。
- 雾火烟花须有空间深度、来源与消散过程，但不声称生成模型真的执行 Navier–Stokes。
- 运动模糊方向与相对运动一致；不允许将散焦景深当成运动模糊或大面积涂抹。

## 4. 运镜与连续镜头
- 每段记录 `camera_move`、`camera_axis`、`focal_length_intent`、`subject_motion`、`action_start/end`、`continuation_of`、`target_seconds`、`target_fps`。
- 慢推：单轴、缓慢连贯，保持主体与空间连续；横移：深度视差正确；环绕：围绕稳定枢轴，背景随视角正确揭示；Dolly Zoom：明确相机位移与变焦联动。禁止未经脚本批准的多运镜混杂。
- 长段可拆成短镜，但**不是规定只能 2–4 秒**；取决于平台有效时长、镜头动作和连续性实测；跨镜用上一镜批准尾帧与场景/角色卡作为参考。
- 两次插帧容易放大鬼影：明确主插帧工具，避免多级重复插帧；Remotion 主要合成/叠加，不能靠它直接修复变脸和空间重组。

## 5. 参数档位与供应商兼容
| 参数 | 建议 | 注意 |
| --- | --- | --- |
| 运动强度 | 优先低幅度小样，但赛车高速/搏斗/动作需求不得被强制低幅度覆盖 | `0.25–0.4` **不是** Seedance/Vidu 通用单位或可移植取值 |
| 参考强度/时序权重 | 如接口可调，先做低/中/高 3 档 A/B | `0.75–0.92` 没有跨平台一致意义 |
| 快门角 | 180°作为可选实拍基准 | 模型常不暴露该参数，仅能用语言描述 |
| 帧率/分辨率/时长 | 从调用接口实际可用值选择并记录返回值 | 后期输出 8K 不等于原生 8K |
| 自动抖动 | 关掉不受控效果（如果可配置） | 有意手持镜头可开受控抖动 |
| 背景重绘 | 若明确支持冻结参考背景，应优先使用 | 不能假设所有引擎存在该开关 |

## 6. 审片等级与人工签核
- **BLOCK / 致命**：身份/脸部结构突变、严重几何重构、主体物品凭空消失、镜头逆转、可见的强闪烁/光流爆破、重大物理因果错误。禁止交付，须修复/重生成。
- **REWORK / 严重**：连续手指畸变、反光跳闪、穿插、严重鬼影、错误模糊、柔体抽搐或难以接受的视差问题，重生成/重审优先。
- **MINOR / 可修**：少量颗粒、轻度色差/高光扰动、远景细节闪烁；可后期处理后重新审片。
- **REVIEW_REQUIRED**：无法仅凭两张抽帧确定的运动、动作/物理、权利或异常；保留待审核，**不自动 PASS**。

### 审片清单（必须实际看片）
- [ ] 参考首帧身份、场景、道具、品牌均批准且保存 SHA
- [ ] 刚性结构不蠕动、位移仅来自相机/剧情事件
- [ ] 人物面孔/手指/衣服/饰品/道具无跨帧突变
- [ ] 相机单一主运动、视差/空间方向合理
- [ ] 主辅光/阴影/高光/反射连续，不频闪
- [ ] PBR纹理与场景色调时序稳定
- [ ] 发丝布料风场/碰撞/重力合理
- [ ] 烟雾、火、水、雨粒子有来源和生命周期
- [ ] 运动模糊合理、无明显重影、无不受控插帧
- [ ] 曝光、对焦、散景、镜头眩光合理
- [ ] 首帧/尾帧与前后镜头剧情、时间线一致
- [ ] 审核记录：时间码、问题类别、截帧证据、修复版本与审核人

**审核限制**：自动工具能读视频元数据、抽帧及对比部分像素特征；两张抽帧的视觉模型意见只是咨询，无法覆盖整段视频细微频闪、真实物理或版权。必须抽查开头、中段、结尾和疑似缺陷区；重大问题人工逐帧核对。

## 7. 运行状态 JSON 示意
```json
{
  "scene_id": "SC01",
  "shot_id": "S01",
  "source_image_sha256": "approved-reference-hash",
  "source_image_status": "PASS_HUMAN",
  "character_asset_ids": ["C01"],
  "scene_asset_ids": ["ENV01"],
  "camera_move": "slow push-in",
  "action_phase": "vehicle accelerates before takeoff",
  "target_seconds": 5,
  "target_fps": 24,
  "allowed_exceptions": ["fictional vehicle propulsion"],
  "engine_profile": "provider-verified-options-only",
  "review_status": "REVIEW_REQUIRED",
  "findings": []
}
```
版本 V3.0 / 2026-11-05。与 `docs/cinematic-positive-global-prompt.md`、`docs/cinematic-negative-suppression-prompt.md` 联动，统一遵循已批准资产、合法授权、人工终审门禁。
