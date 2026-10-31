# OneFlow GitHub 一句话自动生图

## 新增：浏览器一键授权（推荐先试）

Hugging Face 已提供官方 **Device Code OAuth** 授权流程。我们复用其官方 CLI `hf auth login --format agent`。GitHub 工作流会在同一次运行中显示授权链接和一次性验证码，由用户打开 Hugging Face 官方网页确认，完成后使用**仅存在该次临时 GitHub runner** 的 OAuth 访问令牌调用 FLUX.1-schnell 生图。无需向聊天粘贴 API Key、也无需手工创建 `HF_TOKEN`。

实际操作（必须拥有 Hugging Face 账户与可用推理额度）：

1. 打开 [GitHub 一句话生图入口](https://github.com/huuchaujfj102-beep/5588a/actions/workflows/oneflow-generate-image.yml)，点击 **Run workflow**。
2. `authorization_mode` 选择 **browser**（默认）；`one_sentence` 留空即使用《白雪公主》S01；勾选 `approve_paid_image` 允许**一次**可能收费的生图请求。
3. 点 Run workflow 后打开该次 Run 的 `real-hf-image` → **Browser authorization** 步骤实时日志，点击日志提供的 **huggingface.co 官方验证码页面**，输入显示的一次性验证码并确认权限（验证码通常15分钟内有效）。这属于 Hugging Face 官方授权页面，并非 ChatGPT 内置弹框。
4. 返回 GitHub 看执行结果；成功时从本次 Run 下方下载 `oneflow-real-FLUX-S01-...` Artifact 中的 `S01.png` 和 `S01.json`。

**重要边界：** 这个浏览器授权针对每次 GitHub workflow 的临时执行环境；新的一次运行通常仍需重新批准。我们并没有将可长期使用的用户令牌自动写入 GitHub Secrets，也不会自动为用户创建 Hugging Face 账户或付费。若批准后模型返回权限不足或提供商额度不足，工作流会失败；可使用下方长期 `HF_TOKEN` 方式作为备选，仍需实际验证提供商。OAuth 登录成功**不等于**已经获得某个模型的推理权限，也不等于生成成功。

**安全规则：** 授权令牌只在临时执行器的 `HF_HOME` 中使用，清理步骤会删除临时认证文件；不能把令牌写进日志、GitHub 源码或视频发布草稿。GitHub Actions 运行日志中公开显示的是**一次性设备验证码**，请不要转发它或授权陌生的请求。生成图片的 GitHub Artifact 也不适合储存秘密资料。

如果你希望以后 GitHub 点运行后无需重复授权，可以采用下方仅设置一次的 `HF_TOKEN` 私密密钥方案。这个长期密钥必须由用户在 GitHub 官方 Secrets 页面手工保存，无法仅靠当前连接自动获取或代存。

---


**状态：GitHub 端的真实模型调用程序、付费授权门禁与 PNG 文件审核已通过离线 CI；没有授权令牌时不会调用 Hugging Face，更不把模拟 PNG 冒充用户作品。**

## 可选：设置一次长期 HF_TOKEN（以后无需每次浏览器授权）

1. 登录 https://huggingface.co/settings/tokens ，创建细粒度 Access Token，授予 Inference Providers 权限。若模型提出条款或访问确认，在官方 Hugging Face 页面完成。
2. 打开 https://github.com/huuchaujfj102-beep/5588a/settings/secrets/actions ，点击 **New repository secret**。
3. Name 填 **HF_TOKEN**，Secret 填 Hugging Face 令牌并保存。**不要把令牌发送到聊天、Issues 或公开代码。**
4. 查看 https://huggingface.co/settings/inference-providers 的可用额度和账单。首次只运行一张图，Hugging Face 可能收取云推理费用，不属于 ChatGPT 或 Runpod 的额度。
5. 由于 5588a 是公开仓库，不要把病患照片、私密剧本或身份资料作为 Actions 输入；Actions artifact 不等同于私密存储。

## 一句话触发真实生图

打开 https://github.com/huuchaujfj102-beep/5588a/actions/workflows/oneflow-generate-image.yml ，点击 **Run workflow**：

- **one_sentence**：留空则自动生成已入库的《白雪公主》S01 王后与魔镜；也可输入原创一句话。
- **authorization_mode**：使用长期密钥时选择 `secret`；需要浏览器授权时选择 `browser`（默认）。
- **approve_paid_image**：勾选授权进行且仅进行**一次** Hugging Face 云端生图调用，否则只做离线测试。
- 点击 **Run workflow**。第一阶段是无模型调用的预检，第二阶段检测 HF_TOKEN，且在用户勾选授权时才真实调用 FLUX.1 Schnell。

若真实生成成功，在此次 Actions 页面底部 Artifacts 下载 **oneflow-real-FLUX-S01-运行编号**，其中有：

- **S01.png**：经 PIL 验证真实解码的 PNG 文件。
- **S01.json**：实际像素尺寸、模型名称、生成时刻、seed、文件 SHA-256、待人工审核项目。

若输出 MISSING_HF_TOKEN、额度不足、模型请求失败，工作流应为失败状态；不会生成占位图或伪造 SUCCESS。

## 默认生图策略及边界

采用 Hugging Face Inference Providers 的 FLUX.1 Schnell，模型权重许可证 Apache-2.0，默认请求 768 × 1344 竖屏首帧、seed=128839、一次请求、四步采样。后端提供商可能有服务可用性和参数限制；首次真实调用结果才是最终判断依据。此任务 **没有给 GitHub CPU runner 安装整套 FLUX 权重**，也 **没有消耗 Runpod GPU**。

模型信息：https://huggingface.co/black-forest-labs/FLUX.1-schnell

API 信息：https://huggingface.co/docs/inference-providers/tasks/text-to-image

计费信息：https://huggingface.co/docs/inference-providers/pricing

## 与 Wan2.2 对接的后续

人工审核 S01.png 里的王后、服装、魔镜等是否合格；通过后，把首帧经安全通道传到自己的 Runpod Pod（不要提交私人图片至公开仓库），实际执行 Wan2.2 图生视频。图片生成完成不意味着 I2V、配音、合成、自动返修和平台发布已实机打通。

本阶段只有自动生图与图像有效性检测，版权证明与跨镜人物一致性仍必须人工把关。
