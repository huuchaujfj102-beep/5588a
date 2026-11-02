# OneFlow MuseSteamer 上线前验收与明日授权清单（2026-11-03）

> 本文记录 **代码现状**，不把模拟测试等同于外部平台真实跑通。仓库为 public，**禁止提交患者、私密图片、个人令牌或未授权素材**。Actions 生成结果可能对他人可见。建议真正商业化前迁移至私有仓库和受限存储。

## 本次接入的固定链路

```
一句话提示词
  ├─ 首帧模式 A：免费额度内 Cloudflare FLUX 单次生图（需手动确认 Free + 凭据）
  ├─ 首帧模式 B：之前成功的 OneFlow 生图 Actions 任务编号
  └─ 首帧模式 C：用户批准公开的直接 HTTPS 图片 URL
      ↓（仅选择一种来源）
MuseSteamer-Air-I2V /video/generations（5 秒、显式 confirm_paid=true、只创建一次）
      ↓
task_id → GET 只查询 → succeeded → 24h 期限内及时下载视频
      ↓
FFmpeg 规格统一 + 原创合成引擎音效 + 动态「造镜者」水印
      ↓
现有 5588a 技术 QC + 版权/视觉/物理逻辑人工复核
      ↓
人工签名审核 + 仅使用已申请权限的抖音 OAuth
      ↓
抖音私人/公开投稿（单次，检查视频状态，平台审核结果需另行验证）
```

官方模型文档：
- [MuseSteamer Air 创建任务](https://cloud.baidu.com/doc/qianfan-api/s/Amg0lgcx4)
- [MuseSteamer Air 查询任务](https://cloud.baidu.com/doc/qianfan-api/s/Bmg0ma4hf)
- [千帆模型服务价格](https://cloud.baidu.com/doc/qianfan/s/wmh4sv6ya)
- [抖音官方上传 API](https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/upload-video)
- [抖音官方创建 API](https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/video-create)

## 代码/验证完成状态

| 项目 | 状态 | 验收证据/限制 |
|---|---|---|
| 一句话分镜与任务初始化 | 可用、离线验证 | oneflow.yml；不能算 AI 全自动成片 |
| Cloudflare / OVH / HF / fal 生图适配 | 存在、离线模拟测试 | 实际可用额度、凭据、图像质量未验证 |
| 一句话 Cloudflare → MuseSteamer | **新增代码，需真人授权试运行** | qianfan-i2v-oneflow.yml；同一次 Actions 使用私有临时首帧 |
| 已有生图工件 → MuseSteamer | **新增代码，需真运行验证** | 检查来源 workflow_dispatch/main、单个图像工件及 PNG |
| MuseSteamer Air 接口 | **官方参数已对齐；自动测试通过** | model=musesteamer-air-i2v；独立 /video/generations；succeeded 状态 |
| MuseSteamer 5 秒费用 | 标价 ¥1/次 | 最终账单与适用计费方式以千帆控制台为准；不是金额硬上限 |
| 防重复模型调用 | 已加 | 明确单次勾选；POST 前持久化本次任务记录；不自动重试不确定结果 |
| MP4 合成、音乐外的合成引擎音效、漂浮水印、技术审核 | 本地 FFmpeg 测试通过 | 非真实赛车音效；高级视觉/物理逻辑需人工检查 |
| 抖音上传/创建 API 适配 | 代码及模拟测试 | video.create.bind 需要开发者应用权限、抖音用户 OAuth |
| 审核后从视频工件直达抖音 | **新增手动 Actions** | 默认为 self-visible；每次要审核确认、OAuth；防重复投稿 marker |
| 平台发布后状态确认与数据回流 | 未完成真实验证 | 创建 API 返回 item_id ≠ 内容已经公开 |
| 15/30/60 秒连续多镜头一致性 | 未达到生产级 | 当前 MuseSteamer pilot 每次仅 5 秒；片段间物理一致性需新方案 |
| 小红书/快手/视频号/YouTube/TikTok 等自动发布 | 未打通 | 现仅部分编辑资料包，不代表具备授权发布 API |
| 自动爆款研究、流量跟踪、变现闭环 | 仍未实现完整自动化 | 需要数据来源、平台权限、策略试验与合规复核 |

## 操作入口（只有主动勾选才可能扣费）

1. [图生视频 Actions](../.github/workflows/qianfan-i2v-oneflow.yml) → **Run workflow**；选择 `main`、`model=musesteamer-air-i2v`。
2. 想用一句话从零生图：`generate_cloudflare_first_frame=true`、`confirm_cloudflare_workers_free=true`，将图片 URL 和上次生图 run ID 留空。
3. 若已有素材：设置 `source_image_run_id`（来自 `main` 上手动成功的 [生图 Actions](../.github/workflows/oneflow-generate-image.yml)）；也可以只填 `public_first_frame_url`。**三种来源必须且只能选择一项**。
4. 确认付款边界和提示词并勾选 `confirm_paid=true`；一次只创建 **一条 5 秒视频**。此时不进行抖音发布。
5. 下载和观看完成后 Actions 的 `qianfan-i2v-public-test-output`（默认保留一天）；人工逐镜复核动作、车身一致性、版权、音乐与水印。
6. 抖音 [人工审核后发布 Actions](../.github/workflows/oneflow-douyin-reviewed-publish.yml) ：设置 `source_video_run_id`、`reviewer`，勾选 `visual_attested`、`rights_attested`、`consent_upload`；默认为 **private**。如需公开，必须单独选 `public` 且勾选 `confirm_public`。

## 明天需要用户自己操作的授权/验收

- **百度千帆**：已由用户报告开通按量计费。已有 `QIANFAN_API_KEY` 仅据先前对话报告已设；仓库不能通过读取 Secrets API 确认。需要一次显式 `confirm_paid` 的真实 5 秒调用才能证明权限和模型输出。
- **Cloudflare**：想一步从零生图时需要 `CLOUDFLARE_ACCOUNT_ID`、`CLOUDFLARE_API_TOKEN`，并确认仍属于 Workers Free；不能用这段声明替代实际配额检查。
- **抖音**：开发者平台必须批准 `video.create.bind`，抖音账户完成 OAuth，授权后将短期有效的 `DOUYIN_ACCESS_TOKEN` 和 `DOUYIN_OPEN_ID` 存入 GitHub Secrets。Token 过期需刷新/重新授权。
- **发布质检**：每个成片仍须真实人工观看后勾选视觉、声音、版权等证明。检查 GitHub environment `douyin-reviewed-post` 可选配置 required reviewers。
- **运营平台**：多平台（含海外）需要各自独立的合规开放平台能力、OAuth、限额及审核策略；当前不可以当作已经全部授权。

## 失败处理

- **绝不盲目重试**已经发过的 POST 任务：如果网络中断但不知道 task_id，先查千帆计费/任务列表，避免重复扣费。
- **如果只处于 processing**：保存包含 task_id 的原始工件，以既有任务 ID 进行只读恢复，不能重新提交。
- MuseSteamer 官方返回的结果 URL 仅有效 **24 小时**，完整视频内容最多保留 **30 天**；要及时下载转存。
- 抖音手动发布前会创建 `oneflow-douyin-source-<run-id>` Issue 作为不可自动重试的标记。**失败也不自动重试**：先人工在抖音核实是否已发布，再决定后续处理。

## 关于“星火计划”

截至本次检查，已连接 GitHub 可见仓库为 `5588a`（影视流水线）和 `8588a`（医生项目）。没有找到以“星火计划”为名称的明确仓库或需求清单；因此本报告**只验证 5588a**，不把用户另一个“火星计划/MARS PROJECT”错误认作“星火计划”。若“星火计划”是单独项目，需要其仓库/资料定位后才能作独立验收。
