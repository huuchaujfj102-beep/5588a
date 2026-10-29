# Runpod GLM-5.3 文本审核接入

## 当前能力

三个环节：提示词预检（prompt_precheck）、跨镜头文本连续性（continuity_text）、综合报告归纳（review_summary）。输入是锁定规则及镜头文本，不接受视频、音频或参考图；输出是建议，不自动修改剧本或签核。

与现有 SRT 时间轴、素材台账及 FFprobe 检测并行保留。没有问题也仍为 REVIEW_REQUIRED；模型发现 blocker 为 FAIL；凭据缺失、调用失败、截断或格式/证据校验失败均保留人工审核且 CLI 返回非零。原有 blocker 不会被模型结论撤销。逐字引文校验仅证明来源存在，不证明模型判断正确。

## 使用

无需新增 Python 依赖（Python 3.11，标准库 HTTPS）。默认预演不会访问 Runpod，不会计费：

```bash
python -m film_audit.audit --assets examples/assets.csv --srt examples/sample.srt --glm-input examples/glm-input.example.json --output audit-report.json
```

实际调用前，在运行环境的密钥管理中配置 RUNPOD_API_KEY；不写进源码、参数、示例文件或公开日志。然后显式启用：

```bash
python -m film_audit.audit --assets examples/assets.csv --glm-input examples/glm-input.example.json --glm-live --output audit-report.json
```

每次最多3次模型调用，每次输出上限2048 token，reasoning_effort=low，超时120秒，不自动重试。首次应使用合成数据核对端点、响应、usage与账单；本次提交只完成离线与模拟响应测试，不代表真实端点已验证。

正式输入JSON只允许 rules 字符串及 shots 数组；每个镜头只含唯一 shot_id 与 text。最多64镜、180000字节；超限拆批并人工核对跨批连续性。CLI目前不直接解析CSV，需将已确认的规则、镜号及提示词整理成该格式。未公开剧本和肖像资产不得提交到公开仓库；正式业务内容发给服务商前须符合项目的数据授权范围。

## 费用口径

截至2026-10-29官方报价：未缓存输入 $0.77/M、缓存输入 $0.143/M、输出 $2.42/M。

费用 = (未缓存输入×0.77 + 已缓存输入×0.143 + 输出×2.42)/1000000。

一次典型32镜文本审查，三环节累计假设输入30000–100000、计费输出4000–12000 token：无缓存约 $0.03278–$0.10604；假设输入一半命中缓存约 $0.023375–$0.07469。预留一次完整重做后，按约 $0.05–$0.22/任务估算。此处是规划假设，不是实测；实际需纳入服务商计费的推理token。代码按 usage 的 prompt_tokens、completion_tokens 与 cached_tokens 记录估算，缺失/无效计数为 null，不假设缓存命中。失败请求可能收费；记录只涵盖已返回usage的请求，不是消费硬上限。

不含图像/视频生成、GPU、存储、OCR、ASR或口型检测费用。公共端点无需自部署模型或启动Pod；PyTorch模板、Wan 2.2/ComfyUI、仓库转模板是独立的生成/部署选项，本接入不启用。

## 小样验收与边界

先测5–10镜合成样本，植入换衣、道具跳变、正负提示冲突；与人工标注比较漏报、误报、引文支持率及修改建议是否越权。再使用已获授权的V5.2文本做影子审核，不自动改稿。输出保留镜号、严重度、原文证据及最小修改建议。

值得立即试用：提示词预检与报告整理。需先小样验证：跨镜头文本连续性。暂不替换：人脸视觉一致性、逐帧物理、口型同步、实际字幕识别、水印与版权实质审核、FFprobe精确参数及人工终审。Wan生成质量不能由文本模型保证。

官方端点与报价来源：https://www.runpod.io/blog/getting-started-glm-5-3-runpod-public-endpoint
