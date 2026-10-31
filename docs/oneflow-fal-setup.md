# OneFlow 低成本真实生图：fal.ai FLUX.1 Schnell

**状态**：适配器代码和离线单元测试，不代表已配置 API Key 或完成云端真实生图。GitHub 仅在手动勾选单张可能付费调用后才会请求模型。

## 选择与成本

- 默认 provider: `fal`；兼容旧的 `huggingface` 选项，绝不在一种服务失败后自动换另一种服务扣费。
- 模型：`fal-ai/flux/schnell`，一次请求严格 `num_images=1`。
- 根据 fal.ai 列示的每百万像素 $0.003、按百万像素向上取整规则，768×1344 = 1,032,192 像素，**每张约 $0.006**。报价只是估算，可能变动；实际按 fal.ai 账单。
- 模型默认输出为可供图生视频输入的 PNG 主帧，人物/车辆、版权、机械结构与视觉连贯性仍需人工审核。
- 模型的标注不能代替真的 8K 分辨率；默认输出 768×1344，不能宣称原生 8K。

## 需要用户完成的密钥设置

1. 在 https://fal.ai/dashboard/keys 创建并安全保存仅用于 API 调用的密钥，并确认账户有可用额度。
2. 在 GitHub 仓库的 **Settings → Secrets and variables → Actions → New repository secret**：
   - Name: `FAL_KEY`
   - Secret: 刚刚生成的 fal.ai API key
3. 不要发送密钥给聊天助手，不要写进代码、Issues、日志或仓库文件。
4. 旧 `HF_TOKEN` 可以保留，不需要重填；但默认 provider 不会调用它。

## 一次真实生图

在 GitHub Actions 选择 **OneFlow REAL image generation (FLUX.1 via fal.ai or HF)** → **Run workflow**。
- Branch: `main`（仅在此变更经合并后）
- image_provider: `fal`
- one_sentence: 你的一句话提示词
- approve_paid_image: **手动勾选**，许可最多单次付费生图。
- 最后点一次 Run workflow。不能反复提交同一任务。

工作流先跑免费预检；若缺少 `FAL_KEY` 直接报错、不会向 fal 发起生成请求。成功后从该次运行的 **Artifacts** 下载 `S01.png` 与 `S01.json`。元数据提供提供商、模型、尺寸、SHA256 和估算价格，`status=IMAGE_GENERATED_REVIEW_REQUIRED` 不是人工审核通过。

## 研发/预检

```bash
python -m pip install 'Pillow>=11,<13'
python -m unittest discover -s tests -p 'test_oneflow_fal_image.py' -v
python -m oneflow.fal_image --brief "电影级超跑赛道画面" --dry-run
```

单元测试使用模拟的提供商响应以及可验证的 PNG 字节，**没有真实模型请求**。真实云端验证必须在用户设置 FAL_KEY、选择 provider=fal、勾选单次授权之后进行。

可核对官方资料：
- https://fal.ai/models/fal-ai/flux/schnell
- https://fal.ai/models/fal-ai/flux/schnell/api

已知边界：目前只接通**单张真实图片的可执行适配器**。尚未把生成图片自动接入 Runpod/Wan 图生视频，也尚未真正验证最终跨平台发布。
