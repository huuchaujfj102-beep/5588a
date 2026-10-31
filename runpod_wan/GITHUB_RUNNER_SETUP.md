# Runpod GPU ↔ GitHub Actions：一次下单，按序执行三步

## 目标与当前状态

将 `Wan2.2` 的 **`bootstrap.sh` → `--dry-run` → 真实5秒 MP4** 编排成单次 GitHub 手工触发作业。

**此仓库目前不能替用户开通 Pod**，也没有自动获得 Runpod 账号权限。GitHub 执行器能安全确认代码和请求，但真正的 GPU 步骤需要在**用户自己租用并已连接到 GitHub 的 Runpod Pod** 上运行。本功能不表示拥有 Runpod MCP 或完成真实推理。

GitHub 工作流：`.github/workflows/runpod-wan-gpu-render.yml`  
执行脚本：`runpod_wan/run_sequence.sh`  
预检 CI：`.github/workflows/runpod-wan-preflight.yml`

## 首次连接（一次性人工操作，涉及外部账户和计费）

1. 登录 [Runpod Pods](https://www.runpod.io/console/pods)，自行启动一个有 24GB 或更高显存的 GPU Pod（建议 RTX 4090 或更高）。确保有 CUDA + Python + Git、可写的 `/workspace`，足够模型/缓存空间（建议留至少 130GiB）。**已有 Pod 可以复用，不需重复创建。**
2. 将该 Pod 注册为可信 GitHub 自托管 runner：进入本仓库 GitHub **Settings → Actions → Runners → New self-hosted runner**，选择 Linux x64，根据 GitHub 页面在该 Pod 终端复制安装/注册命令，为它添加标签 **`runpod-wan22`**。注册 token 只在 GitHub UI 与 Pod 终端中使用，**禁止粘贴到聊天、提交仓库**。运行机器应为隔离的可信设备，管理好运行用户的文件与 GPU 权限。
3. 为了实际显示用户可点击的**审批框**：在 GitHub **Settings → Environments** 创建 `runpod-paid-gpu` 环境，配置 **Required reviewers** 并选择自己为审核人。这样在执行 GPU 步骤之前，GitHub Actions 会停下并提示 **Review deployments**。注意：**仅在 YAML 中写 `environment` 并不会自动强制审核，必须亲自在仓库设置审核人。**
4. 准备好 Pod 的费用限额/停止计划。工作流不创建或删除 Pod，也不会自动停租；**Pod 启动后即可能持续计费，即使 Actions 在等待人工审核**。如不立即生成，请先停止 Pod，待点击运行前再启动。生成结束后立即停止 Pod 并核查持久存储费用。
5. 无需给此流程提供 Runpod API key：通过用户已有的 Pod 和自托管 runner 执行，避免把云账户密钥放进公开仓库。过去若在聊天中泄露过任何 API key，请先撤销旧密钥。

## 一句话启动 GPU 渲染（安装、预检、真实生成）

进入 GitHub 仓库 **Actions → Wan2.2 ONE SENTENCE -> 5s VIDEO (Runpod GPU, approval) → Run workflow**。

- **one_sentence**：留空生成仓库已定稿的《白雪公主》S01；也可以填一句自己的5秒分镜要求。
- **approve_gpu_billing**：明确勾选同意本次单镜 GPU 推理费用，否则工作流只能拒绝执行。
- 点击 **Run workflow**；前置 CPU 单元测试成功后，GPU job 需要已上线并带 `runpod-wan22` 标签的 Runpod 自托管 runner。
- 若配置了 Required reviewers，GitHub 会出现 **Review deployments** 提示；同意后才开始正式 GPU job。

实际三个步骤顺序在 `runpod_wan/run_sequence.sh` 固定：

```
1/3 WAN_DOWNLOAD=1 bash runpod_wan/bootstrap.sh
2/3 python -m runpod_wan.smoke --seconds 5 --dry-run
3/3 python -m runpod_wan.smoke --seconds 5 --confirm-gpu-spend
```

由于输出包含随机化 GitHub run ID，同一片段不会无意覆盖前一版。

生成的**真实视频文件在你私有的 Runpod 持久目录**：

```text
/workspace/oneflow-output/snow-white-S01-<run_id>-<attempt>.mp4
/workspace/oneflow-output/snow-white-S01-<run_id>-<attempt>.audit.json
```

技术审核 JSON 会上传 GitHub Actions Artifact，但**MP4 不会从私有 Runpod 存储自动上传到公开 GitHub 仓库**。你可以通过 Runpod Pod 的文件管理、安全复制方式取回视频，再执行视觉终审。任何未生成 MP4、ffprobe 失败、CUDA 缺失都使 GPU job 失败。

## 尚未完成的“一句话完整成片”范围

目前这个 GPU 工作流专为**一条5秒单镜头视频**设计，Wan2.2 TI2V-5B 输出主要是无声画面。当前**未真正打通**从 GitHub OneFlow 每个镜头自动分发到 Runpod、跨镜人物一致性重绘、自动配乐/音效、60秒合片以及多平台 OAuth 发布。先完成 S01 真实视频成功验收后，再复用稳定接口扩展剩余11镜头。

## 不要被排队状态误导

- `queued` 或 `waiting`：通常是 GPU runner 离线、或审核人尚未批准，不表示模型正在推理。
- `DRY_RUN`：只检查命令与模型文件结构，不是视频。
- `success` + `GPU_RENDERED_REVIEW_REQUIRED`：表示真实 MP4 已生成并通过技术核查，仍需人工检查质量、版权和运动逻辑。
- `failure`：查看具体 step 日志，不能以生成分镜或 CI tests 成功代替实机出片。

如未注册 Runpod runner，就不要点击付费生成；先按上面第一部分完成注册。
