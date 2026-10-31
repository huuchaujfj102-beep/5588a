# OneFlow GitHub 一句话生图：最小权限授权

> 安全更新：不再使用 Hugging Face CLI 的 Device Code OAuth 浏览器授权。该模式的授权页可能包括管理所有仓库、Jobs、Webhooks、Billing 等广泛权限，不符合“一句话生图”所需的最小权限原则。用户看到原授权页时，请点击 **Deny**，不要批准宽权限。

## 只配置一次：细粒度 HF_TOKEN

1. 打开 [Hugging Face Access Tokens](https://huggingface.co/settings/tokens)，点击 **New token**，类型选择 **Fine-grained**。
2. 给令牌起个能识别的名字（例如 `oneflow-inference-only`）。仅选择 **Inference / Make calls to Inference Providers** 相关权限；不授予仓库读写/删除、Webhooks、Jobs、Billing 等无关权限。具体界面字段以 Hugging Face 当前显示为准。
3. 复制令牌，只在 GitHub 官方页面 https://github.com/huuchaujfj102-beep/5588a/settings/secrets/actions → **New repository secret** 粘贴。名称精确填写 `HF_TOKEN`。不要向聊天、截图或 GitHub Issues 粘贴访问令牌。
4. 在 https://huggingface.co/settings/inference-providers 核查模型访问、推理额度及可能产生的费用。Hugging Face 的额度与 Runpod、ChatGPT 额度独立。
5. 点击 [GitHub OneFlow 生图工作流](https://github.com/huuchaujfj102-beep/5588a/actions/workflows/oneflow-generate-image.yml) → **Run workflow**。分支选 `main`，`one_sentence` 留空可生成《白雪公主》S01 的王后与魔镜，勾选 `approve_paid_image` 后手动启动一次模型推理。

## 成功输出与限制

- 免费预检 `free-preflight` 检查提示词和程序，不调用付费模型，不会产生图片。
- `real-hf-image` 只有在用户明确勾选一次图像推理同意，且 GitHub 仓库 Secret `HF_TOKEN` 非空时才调用 Hugging Face Inference Providers 的 FLUX.1 Schnell。此模型是否被该账户可用的云端 Provider 实际支持，需要首次实测。
- 成功后会生成可解码的 `S01.png`、`S01.json`（含模型、尺寸、SHA-256 和人工审核标识），存到 7 天保留期的 GitHub Actions Artifact，不会发布平台或自动提交到公开仓库。
- 若凭据未配置、模型权限不足、额度不足或者 Provider 返回错误，工作流应失败而不是产出模拟图片。
- 图片质量、人物一致性、版权、商用权限与是否适合 Wan2.2 图生视频，必须另行审核。
- 本仓库为公开仓库：GitHub Actions Artifact 不是私密素材的安全长期存储，勿提交患者、个人敏感信息或未公开参考素材。
- **关于先前第13–15次运行：** 浏览器登录步骤可能在等待用户确认或过期后失败；那些任务没有完成图片生成。它们不是本流程的授权凭据。

## 下一步接 Wan2.2

用户审核通过 S01.png 后，安全地传到自有 Runpod Pod 的 `/workspace/approved/S01.png`，由已实际部署成功的 Wan2.2 TI2V-5B 图生视频生成五秒镜头。GPU 实机出片、配音/音效、12镜合成及发布平台 OAuth 都属于尚待验证的独立步骤。

官方参考：
- https://huggingface.co/docs/hub/security-tokens
- https://huggingface.co/docs/inference-providers/index
- https://huggingface.co/docs/inference-providers/pricing
