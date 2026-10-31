# OneFlow V1: 一句话启动 → 开源模型生产 → 审核 → 授权发布 → 数据回收

> 实际状态（2026-11-01）：**代码和离线分镜入口已添加，真实媒体生成、平台 OAuth/发布及数据 API 尚未实机端到端验证。** 这是安全门禁优先的可扩展生产框架，而不是已开通的社交平台代发服务。

## 统一工作流

```
一句话 brief
  ├── Ollama/Qwen 等本地开源文本模型 (可选) → 分镜、音效指令
  └── 离线确定性分镜草稿 (默认，不冒充大模型内容)
       ↓ Shot manifest + stable IDs + draft storyboard
ComfyUI 图像模型 (SDXL/其他合适许可的权重；按用户 API 图)
       ↓ per-shot 参考帧
ComfyUI 图生视频模型 (Wan2.2 I2V；按用户 API 图)
       ↓ per-shot 视频
ComfyUI 音效模型 (已自建的 AudioGen/相关图；按用户 API 图)
       ↓ per-shot 音效
FFmpeg 逐镜统一格式、视频拼接、音轨合成
       ↓ final-draft.mp4
5588a film_audit 技术检查 / 素材记录 + 人工视觉/物理/音效/版权审核
       ↓ 命名审核人核准，SHA-256 锁定已审文件
授权发布服务适配器 (各平台 OAuth 和 API 另行部署/获批)
       ↓ 记录真实发布 ID/链接，仅凭已核实回执标记 published
授权平台数据 API → 播放、互动、ROI 跟踪
```

### 复用和开源工具边界

- **5588a** 既有 `film_audit/` 原样复用：视频技术参数、素材台账。其余视觉/物理/版权仍需人工检查，`REVIEW_REQUIRED` 不能自动变为 `PASS`。
- **OpenMontage** 已可独立安装验证；**Remotion** 有单独测试合成工程。OneFlow V1 的稳定自动合成使用 FFmpeg，不把「OpenMontage 安装测试」说成「已接入产线」。后续可以开发 Remotion/OpenMontage 时间线导出。
- **Ollama/Qwen、SDXL、Wan2.2、AudioGen 等是候选模型**，并非一键安装全部权重。真实执行时需自行部署开源模型、满足显存、模型许可/商用条款和专属 ComfyUI API graph。不能保证“所有开源模型”在同一机器同时运行。
- **低配电脑**：建议在可信云 GPU / Runpod 自建可鉴权 ComfyUI 和 Ollama，由用户控制的工作机（云服务器或自托管 runner）运行 OneFlow，保存媒体到私有持久存储。GitHub Actions 的公开托管 runner 默认只跑离线策划与测试，不承载 GPU 视频生成。

## 零费用启动（一句话生成任务与镜头卡）

GitHub 仓库 Actions → **One-sentence film pipeline (safe launch)** → Run workflow，输入一句话和时长。在 Artifacts 下载分镜清单。此阶段 **不会生成 MP4**，不会调用付费 API，也不会自动发布。

在 Python 3.11+ 环境：

```bash
python -m oneflow run \
  --prompt "生成35秒喷气超跑短片：启动、加速、悬崖腾空、喷蓝焰飞远；只有轰鸣和喷气音效，不要旁白" \
  --seconds 35 --ratio 9:16 \
  --platform douyin --platform youtube \
  --out private-inputs/oneflow-jobs
```

输出 `manifest.json`、`storyboard.md`。输出命令打印 `job` 目录供下一步使用。默认 `heuristic` 仅切分剧情草稿；若需真实 LLM 创意分镜，配置 Ollama 并在 config 中设置 `story.kind=ollama`。

## 真实生成（须授权开源模型、GPU、FFmpeg）

1. 安装 FFmpeg/FFprobe，Python 3.11+。
2. 在你的私有算力上安装 Ollama（可选），以及可运行图像、视频、音效生成模型的 ComfyUI。导出每个 ComfyUI **API 格式** JSON 图（不是 UI 可视化工作流 JSON）；确认真实能输出 images/videos/audio 文件。
3. `cp oneflow/config.example.json private-inputs/oneflow-config.json`，并将经过本地测试的 API 图放 `private-inputs/workflows/`。调整每个 stage 的 `patches` 中节点 ID、输入名及 seed/时长输入。示例中的节点编号只用于说明，**不能直接视为有效工作流**。
4. 使用 `OLLAMA_URL`、`COMFYUI_URL` 和（仅当服务要求时）`COMFYUI_TOKEN` 环境变量。远程推理地址必须是 HTTPS；本地可用 http://localhost。
5. 真正调用模型的一句话命令：

```bash
python -m oneflow run \
  --prompt "制作35秒电影级喷气跑车短片，启动、急加速、腾空，尾部蓝色喷焰，只有轰鸣、喷气和环境声" \
  --seconds 35 --ratio 9:16 \
  --platform douyin --platform youtube \
  --config private-inputs/oneflow-config.json \
  --out private-inputs/oneflow-jobs \
  --live
```

生成任务的 `status` 只有在实际完成生成、合成及技术审查后才会变为 `AWAITING_HUMAN_REVIEW`；提供商调用缺失或失败时会报错，不能把提示词和空视频当成成功。为防超额费用，默认不重复重试同一提供商；如已生成的镜头文件存在，重复 `produce` 会跳过该阶段。清单默认最多 12 镜。

### 人工终审与发行

查看 `final-draft.mp4` 和 `qc.json`，重点逐镜确认：人物/车辆一致、运动物理、因果顺序、声画同步、原创素材与音乐许可、平台内容政策。准确记录审核人；只有本人真正检查后执行：

```bash
python -m oneflow approve \
  --job private-inputs/oneflow-jobs/film-xxxxxxxxxxxx \
  --reviewer "制片人" --visual-attested --rights-attested
```

审核会把视频文件 SHA-256 锁住；修改了 MP4 后，发布被拒绝，必须重新审核。

### 真正平台发布：必须另接官方授权适配器

**目前没有自动接通抖音、小红书、快手、B站、YouTube、TikTok 的账号 OAuth**。不同平台 API 有产品审核、范围、开放条件、视频规格限制；网页登陆、手机 App 连接不等于开放发布 API 授权。

OneFlow 已提供通用 `publisher` 插件协议。你必须先搭建并合法授权独立平台网关，配置：

```bash
export PUBLISHER_URL="https://your-trusted-publisher.example"
export PUBLISHER_TOKEN="YOUR_TOKEN_FROM_SECURE_STORE"
python -m oneflow publish --job ... --platform youtube \
  --config private-inputs/oneflow-config.json --consent
python -m oneflow metrics --job ... --config private-inputs/oneflow-config.json
```

发布器协议：

- `POST /publish`，Bearer token + multipart `metadata` (JSON) 和 `video` (MP4)。metadata 提供 job_id、platform、title、description、sha256、idempotency_key。服务必须验证用户授权和平台 API，避免重复发布。成功返回 `{"status":"published","id":"真实平台ID","url":"真实平台视频URL"}`；异步排队可返回 `{"status":"pending","id":"平台任务ID"}`。若仅上传中、授权不足或审核失败，不得伪报 published。
- `GET /metrics?platform=...&id=...`，Bearer token，成功返回 `{"status":"ok","data":{"views":..., "likes":...}}`，字段根据实际 API。平台没有数据权限时不得臆造数据。
- 用户必须明确在一条任务选择目标平台，每个平台发布时再次给予 `--consent`；未经审核或未经授权一律拒绝。当前单次发布不代表多平台批量已通。

## 安全、私密和已知限制

- 永不把模特参考资产、未公开剧本、视频、令牌或医疗患者素材上传到公开 5588a；输出默认在 `private-inputs/`（Git ignored）。
- API 调用可能有算力或模型成本；不默认调用云模型。输入可能含版权保护内容，先做改编和授权审查，不自动克隆未获许可的视频。
- ComfyUI 需要可用的特定 API 图及节点映射；当前只支持单一输出图片/视频/音效中的第一个匹配文件，无法智能判断最优帧或视觉连续性。
- 真人效果、机械结构、镜头一致性、噪声或音效真实性无法由 ffprobe 保证。须人工终审。
- 大视频上传目前只支持单个小于 500MB 的文件；生产用平台适配器可升级分块上传、任务队列、重试和异步状态回调。
- 若公网主机没有可鉴权 HTTPS 代理，不能直接将未加密的 ComfyUI HTTP API 暴露互联网。

## 阶段完成定义

| 阶段 | 验收 |
|---|---|
| A 一句话解析 | Actions 与本地测试通过，输出带稳定镜头 ID 的分镜，默认零模型调用 |
| B 实时生成 | 每镜真实图片/视频/音频文件；完整 MP4；实际模型、成本和许可证记录 |
| C 审核放行 | FFprobe+现有审查，人工视觉/版权双签核，锁住视频哈希 |
| D 平台发布 | 每个平台 OAuth 通过，真实平台 ID 和 URL 返回；失败回执不冒充成功 |
| E 数据回流 | 官方授权 API 返回实际数据，记录采集时刻并复盘 |

阶段 A 完成后需要在自托管云环境继续配置 B—E。**不得把只有框架或 smoke test 的结果声明为全链路生产就绪。**
