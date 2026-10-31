# Film Quality Audit · 影视质量审核工作站

本仓库是**可运行的基础审核框架**，将 20 个原始审核名称整合成 7 大关卡。当前版本仅自动检查字幕 SRT 时间轴、素材授权台账字段及 FFprobe 视频元数据。其余项目均为待接入的人工/模型审核门禁，**不得把待审核当作通过**。

## 7 个关卡
1. 剧本与提示词：Story Audit / Continuity / Prompt Guardian
2. 内容和版权风控：ByeRisk / BanProof AI / Asset Copyright Audit / Ad Compliance Audit
3. 角色与镜头连续性：ContinuityGuard / Continuity Audit / Cross-Episode Cast Consistency
4. 画面与物理：Cooking Audit / Physics & Spatial Audit
5. 口型与音频字幕：LipSync Audit / Audio+Subtitle Audit / SpeechKit Audio Audit / Subtitle Checker Pro
6. OCR 水印与技术：Video OCR Auditor / Watermark Trace Audit / MediaSpec Checker
7. 综合终审：SkyProduction + 人工签核

## 执行
```bash
python -m unittest discover -s tests -v
python -m film_audit.audit --srt examples/sample.srt --assets examples/assets.csv --output audit-report.json
# 指定本地视频时需安装 ffprobe
python -m film_audit.audit --video path/to/clip.mp4 --srt path/to/clip.srt --assets path/to/assets.csv
```

push / PR 触发 GitHub Actions 的单元测试与示例审核，审核 JSON 保存在 Actions artifacts。视频与秘密授权材料不要提交到公开仓库。模型检测、口型一致性、版权实质审核尚未集成，须人工验收。

**安全原则：** 不上传 API key、医疗患者信息、未公开剧本和个人肖像参考资产。

## GLM-5.3 文本审核（可选）

已增加提示词预检、跨镜头文本设定比对、审核报告归纳接口。默认离线预演；仅显式使用 `--glm-live` 时发送文本并计费，须在运行环境配置 `RUNPOD_API_KEY`。模型建议不替代视觉/音频检查或人工签核；现有阻断项不会被撤销。

使用方法、费用估算及验证边界见 [接入说明](docs/glm-runpod.md)。


## OneFlow V1 一句话影视流水线（新模块）

新增 `oneflow/`、`docs/oneflow.md` 与 `.github/workflows/oneflow.yml`，目标串联：
**一句话 → 剧本与分镜 → ComfyUI 图像/视频/音效（需运行中的开源模型及已校验 API 图）→ FFmpeg 合成 → 5588a 技术审核 → 人工终审 → 授权发布接口 → 官方数据回流**。

安全的 GitHub Actions 一句话入口只生成分镜与测试报告，不会消费模型额度。
真实生成通过自托管 GPU + `python -m oneflow run --live --config ...` 显式执行。
平台发布必须另外完成对应平台的 OAuth/官方 API 授权，并由人工确认已审成片后操作。现阶段**不宣称**媒体生成和多平台自动发布已经实机打通。

详细步骤：[`docs/oneflow.md`](docs/oneflow.md)。


## OneFlow 一句话真实生图（FLUX.1 Schnell）

新增 GitHub Actions 一句话生图入口：通过 Hugging Face Inference Providers 调用实际图像模型。优先选择 `browser`：运行时打开 Hugging Face 官方设备授权网页并确认一次性验证码，即可在当前作业中获得临时推理令牌；也可选择已设置 `HF_TOKEN` 的 `secret` 方式。两者都须勾选一次生图费用确认；缺授权则失败，不生成占位图；离线测试不消耗云端图像额度。详见 [GitHub 生图接入指南](docs/oneflow-github-image.md) 和 [生图 Actions](.github/workflows/oneflow-generate-image.yml)。
