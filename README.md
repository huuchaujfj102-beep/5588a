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