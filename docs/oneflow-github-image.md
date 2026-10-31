# OneFlow GitHub 一句话自动生图

**状态：GitHub 端的真实模型调用程序、付费授权门禁与 PNG 文件审核已通过离线 CI；没有授权令牌时不会调用 Hugging Face，更不把模拟 PNG 冒充用户作品。**

## 一次性连接：HF_TOKEN

1. 登录 https://huggingface.co/settings/tokens ，创建细粒度 Access Token，授予 Inference Providers 权限。若模型提出条款或访问确认，在官方 Hugging Face 页面完成。
2. 打开 https://github.com/huuchaujfj102-beep/5588a/settings/secrets/actions ，点击 **New repository secret**。
3. Name 填 **HF_TOKEN**，Secret 填 Hugging Face 令牌并保存。**不要把令牌发送到聊天、Issues 或公开代码。**
4. 查看 https://huggingface.co/settings/inference-providers 的可用额度和账单。首次只运行一张图，Hugging Face 可能收取云推理费用，不属于 ChatGPT 或 Runpod 的额度。
5. 由于 5588a 是公开仓库，不要把病患照片、私密剧本或身份资料作为 Actions 输入；Actions artifact 不等同于私密存储。

## 一句话触发真实生图

打开 https://github.com/huuchaujfj102-beep/5588a/actions/workflows/oneflow-generate-image.yml ，点击 **Run workflow**：

- **one_sentence**：留空则自动生成已入库的《白雪公主》S01 王后与魔镜；也可输入原创一句话。
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
