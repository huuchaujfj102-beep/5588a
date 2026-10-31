# OneFlow V2.2：已验证真实生图 → 影视制作交接包（不调用视频 GPU）

2026-11-01 状态：已开发 SHA256 校验、9:16 无裁切参考图、镜头任务单、原创音效需求单、六平台编辑草稿、静帧诊断预览及发布门禁。仓库中的 **Cloudflare #44** 真图已成功生成（https://github.com/huuchaujfj102-beep/5588a/actions/runs/41239793072）。这项交接 **不会运行 Wan2.2、不会生成真实运动、不会自动发布**。

## 自动跟随真实生图

每次 OneFlow 的 `OneFlow REAL image generation (OVH free / Cloudflare FLUX / fal / HF)` 在 **main** 分支由人工授权手动启动并成功完成时，下游 `OneFlow verified image -> video-prep handoff (NO GPU)` 自动尝试读取对应运行的 OVH / Cloudflare S01 Artifact。失败任务、dry-run、普通 PR 不生成新的交接包；下游不调用任何图片、视频或音效模型。

可手动重做历史图片的**交接处理**（不会重新生图）：Actions → `OneFlow verified image -> video-prep handoff (NO GPU)` → Run workflow → main，`source_run_id=41239793072`、`seconds=35`，`one_sentence` 可留空自动读取原始图片元数据里的原提示词。仅对来源于本仓库 main 的成功手动 OneFlow 生图运行有效。Artifact 保留期过期后需重新取得源文件，不能伪造来源。

## 文件清单

- `S01_original.png`：从 GitHub 真实图像 Artifact 复制，逐字节 SHA256 与来源 JSON 记录比对。
- `S01_portrait_letterbox.png`：1080x1920 **非裁切**黑底竖屏合成图；不是模型原生 9:16，也不是素材通过一致性审核。
- `handoff.json`：5/15/35/60 秒的确定性镜头草案，35 秒时 7 镜，每镜 7 模块提示词与原始参照锁定记录；其余镜头**仅为计划，尚无图、无视频**。
- `wan_s01_prompt.txt`：可人工修改的 Wan I2V 文本草稿；**未连接 Runpod**，不是可直接投喂任意 GPU 模型的已验证节点图。
- `publication_drafts.json`：抖音、快手、小红书、B站、YouTube、TikTok 标题/描述**草稿**，不是经平台 API 验证的可发布规格。
- `delivery.json`：已校验的来源信息、审核和分发门禁。`readiness.video_generated=false`，`published=false`。
- `STATIC_PREVIEW_NO_AI_MOTION.mp4`：5 秒 **静帧** MP4，用 FFmpeg 测试 1080×1920/H.264/静音声轨和合成通路。画面上明确标注 `STILL PREVIEW - NO AI MOTION`。**不能当作图生视频或正式作品**。
- `README.txt`：操作、风险及下一步审核提醒。

## 已实际确认与尚待确认的界限

1. Cloudflare / OVH 真实生图：已确认；Cloudflare #44 真实 PNG 为 1024×1024。
2. 从 GitHub 生图成品自动获取并校验到交接包：**已用真实 #44 完成第一次端到端验收，成功**：运行 https://github.com/huuchaujfj102-beep/5588a/actions/runs/41240879475 ，Artifact `oneflow-video-PREP-NO-GPU-41240879475`（ID 13056844422，约 2.25 MB），原始图 SHA256 `85b2df4369ae187b3815977e292f7768948cd40a1e356f381a81ff265118b734`，静帧 MP4 已实际生成并通过 FFmpeg/ffprobe 检查，无额外模型推理。
3. FFmpeg 静帧 MP4：能验证格式处理与来源素材读取，**不能**验证动画、物理运动或音效质量。
4. Runpod Wan GPU 真实 5 秒 I2V：代码/离线预检已有，仍需要运行的 GPU Pod、24 GB 级别显存、对应模型权重、Github self-hosted runner `runpod-wan22`，以及独立明确收费授权。当前还未验证一条真实 Wan MP4。
5. 音效：仅 cue sheet 与先前 FFmpeg 混音测试；没有真实 AI/专业录制引擎与喷焰音效。
6. 逐镜画面连续性/版权/发布合规：必须人工确认。视觉审核工具不会自动代替审核人签字。
7. 各平台发布：缺少逐平台独立官方 OAuth/审核/上传成功回执。任何无权限行为都默认**阻止**。

## 安全限制

- 此工作流所有触发器都只有 GitHub `contents:read`、`actions:read` 权限，**没有仓库写入、无 GPU/Cloudflare Token、无社交账号发布权限**。
- 输入只限受信任的本仓库 `main` 成功人工生图运行；下载文件后对 PNG 文件类型、尺寸、实际 SHA256、来源模型及报告状态作硬验证。来源不符立即失败。
- 不裁切汽车/人物：原生 1024 正方图无论如何放入 9:16 都无法自动补全新的上下场景。竖屏图是等比例 letterbox，画面质量仍需审片。不得暗称 8K。
- 对后续付费 GPU 的授权**不会**由此前免费生图授权继承；要在 Runpod GPU 独立确认。
- 发布前必须取得素材许可、核准原创音效、技术参数、视觉连续性、人工放行及各平台有效的授权与回执。

最直接的下一项真正商业/成片验收：**用同一 S01.png 在 Runpod 上生成一条 5 秒真实 Wan2.2 MP4（带实际运动）→ 拿到原始 MP4 + ffprobe/审核 JSON + GPU 帐单**。这个步骤不能用本次静帧测试替代。
