# OneFlow Cloudflare Workers AI FLUX.1 Schnell 接入（待账户授权）

**2026-11-01 状态**：官方 API 和免费额度已核验，代码/离线测试/Actions 调用入口已编写。**未取得用户 Cloudflare 凭证，也没有发起 Cloudflare 真实生图**；只能在用户完成安全配置后验证。

## 免费额度（以 Cloudflare 官方账单为准）

- Workers **Free**：所有 Workers AI 模型每天合计 10,000 Neurons 免费额度；到限额请求将失败，不需要自动升级。按 UTC 00:00 重置。
- Workers **Paid**：同样包含每天 10,000 Neurons，但超过后可按量计费。当前程序**无法通过 API 证明用户套餐必然是 Free**，所以提供两重人工确认，禁止自动切换付费渠道。
- 模型：`@cf/black-forest-labs/flux-1-schnell`；官方定价按照每 512×512 tile 和 diffusion step 计算 Neurons。默认测试仅 1 张、4 steps。
- 一次 1024×1024、4 steps 的纯**推算**：若按 4 tile、4 steps 计算约 57.6 Neurons；具体以账单和实际尺寸为准，**不保证一次等于精确此额度**。

官方来源：
- https://developers.cloudflare.com/workers-ai/models/flux-1-schnell/
- https://developers.cloudflare.com/workers-ai/platform/pricing/
- https://developers.cloudflare.com/workers-ai/get-started/rest-api/

## 用户完成授权（手机即可）

1. 打开 https://dash.cloudflare.com/ ，登录 Cloudflare。在 Workers AI 面板检查是否 **Workers Free**，确认无 Workers Paid 计费。
2. 在 Workers AI 选择 **Use REST API**，点击 **Create a Workers AI API Token**。使用预设的 Workers AI 权限，尽量限制到此账户；不要使用 Global API Key。
3. 同一页面复制 **Account ID** 和 API Token。**不要把 Token 或 Account ID 发到聊天、公开 Issue 或代码里**。
4. 打开仓库 `https://github.com/huuchaujfj102-beep/5588a/settings/secrets/actions`，点击 **New repository secret**，分别创建：
   - `CLOUDFLARE_ACCOUNT_ID`：你的 Cloudflare Account ID（32 位十六进制）
   - `CLOUDFLARE_API_TOKEN`：刚刚复制的 Cloudflare Workers AI API Token
5. 再打开 `https://github.com/huuchaujfj102-beep/5588a/actions/workflows/oneflow-generate-image.yml`：
   - Run workflow → main
   - image_provider → `cloudflare_free`
   - one_sentence → 输入英文赛车场景（空白则用预设超跑测试图）
   - **勾选** `approve_free_image` 和 `confirm_cloudflare_workers_free`
   - **不要勾选** `approve_paid_image`
   - 点击最下方 Run workflow **一次**
6. 成功的任务 `real-free-cloudflare-image` 在 **Artifacts** 输出 `S01.png` 和 `S01.json`。记录模型、SHA256、尺寸和审核状态，不自动将图片放入公开 Git 仓库。

## 防止意外消费和重复生图

- GitHub push/PR **只运行离线测试**；不会调用 Cloudflare。Cloudflare 真生图只在人工选择提供商并勾选双重确认的 workflow_dispatch 下进行。
- 如果账户是 Paid 或不确定，请勿勾选确认；**本代码的 Free 计划确认是人工申明，不是 Cloudflare 计费系统的技术硬限制**。
- 真实模型请求最大 1 次，`steps <= 4`，无自动重试、无队列恢复自动再发、无 fal.ai/Hugging Face 付费回退。
- 如果密钥未添加/无效、免费额度不足 (429)、账号无此模型权限 (403)、输出解析失败，工作流报错并停止。
- 无自动视频合成、图生视频或发布。先人审画质/机械结构，再单独使用现有 Runpod/Wan 管线。
