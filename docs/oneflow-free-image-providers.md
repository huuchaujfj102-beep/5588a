# OneFlow 免费生图渠道验收（2026-11-01）

## 已完成的真实免费出图

- 供应商：OVHcloud AI Endpoints，模型 `stable-diffusion-xl-base-v10`（底层 SDXL 1.0）。
- 官方标价：Free；匿名限流：每 IP、每模型每分钟 2 次。官方文档：https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/stable-diffusion-xl/
- 实测工作流：https://github.com/huuchaujfj102-beep/5588a/actions/runs/41233163317
- 结果：2026-10-31 19:13 UTC GitHub Actions **success**，真实模型请求成功，返回 1024×1024 图像，经 Pillow 解码、转为 PNG、验证 SHA-256；上传 `S01.png` 与 `S01.json`。
- GitHub 成品 Artifact: `ovh-free-sdxl-S01-41233163317`，保留 7 天。
- 准确边界：模型出图成功 **不等于** 物理/车辆结构/版权或视频连续性审核合格。OVH 的 SDXL 固定输出为 **1024×1024 方图，不是 9:16/8K**。需要重新构图或裁切时必须人工复核，不能谎称原生 8K。

## 如何自己一句话生成新图（无需密钥）

待本变更合并到 `main` 后，进入仓库 Actions → `OneFlow REAL image generation (free OVH / fal.ai / HF)` → Run workflow：

1. `image_provider` 选 `ovh_free`（默认）。
2. `one_sentence` 填你要的英文提示词（例如一辆黑色碳纤维赛车在雨夜赛道，低机位电影照明）。
3. **仅勾选** `approve_free_image`。不要勾选 `approve_paid_image`。
4. 提交一次，进入新运行记录查看 `real-free-ovh-image`。
5. 在 Artifacts 下载 `S01.png` 与 `S01.json`。

每次手动调用最多 1 张。程序不带密钥，不自动重试、不自动切换付费供应商。若超过匿名速率限制，明确报错（通常为 HTTP 429），不会重试。

## 可选供应商对照

| Provider | 本账号实测 | 是否直接支持 Actions | 密钥 | 额度/收费 | 限制 |
|---|---|---|---|---|---|
| OVHcloud SDXL | **已通过一次真实匿名调用** | **是** | 不需要 | 官方标价 Free | 1024²，匿名 2 次/分/IP |
| Runway ChatGPT 插件 Nano Banana 2 Lite | **已生成实图** | **否，插件授权不等于 GitHub API 密钥** | 插件连接已授权 | 用户账户已有赠送积分 | 不可直接视作免费开放 API |
| Cloudflare Workers AI FLUX.1 schnell | 未在本账号实际调用 | 需要账户设置 | Account ID + Workers AI API Token | Free Workers 每日 10,000 Neurons，超出停止；Paid 方案可能计费 | 要独立授权和额外防预算超额 |
| fal.ai FLUX.1 Schnell | 适配器和离线测试已写好，真实未运行 | 需密钥 | FAL_KEY | 按量计费 | **非免费**，默认不调用 |
| Hugging Face FLUX.1 Schnell | 实际调用返回 HTTP 402 无可用余额 | 是 | HF_TOKEN | 免费月度额度已耗尽 | 非当前首选 |

官方文档：
- OVHcloud: https://www.ovhcloud.com/en/public-cloud/ai-endpoints/catalog/stable-diffusion-xl/
- Cloudflare free allowance: https://developers.cloudflare.com/workers-ai/platform/pricing/
- Cloudflare FLUX: https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/

## 用途与权限

- GitHub 推送后只做**免费离线测试**。专用验收工作流 `oneflow-ovh-free-smoke.yml` 的首次特意标记 `[onefree-test]` 的提交只运行一次真实免费请求。以后普通提交不会启动外部推理，人工触发也必须明确勾选。
- 真实输出进入 GitHub Actions Artifacts，不写入 Git 跟踪历史；任何产物需要人审后才可用于 Wan 视频。
- 现阶段 **只验证“一句话 → GitHub → 免费 SDXL 图片 Artifact”**，未验证从图到视频、音效、发布的完整链路。
