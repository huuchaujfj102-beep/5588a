# OneFlow Commercial V3.1 · LibTV 图生视频服务适配

**验证状态（2026-11-02）:** 调研完成，适配器/测试编写中。尚未连接用户的LibTV身份或任何授权密钥，未调用远程模型、不消耗积分、未生成成片。该模块属于 `feature/oneflow-commercial-v3-20261101` 开发分支的 PR #19，需通过CI、授权真实小样和商业版权验证后才可合并主分支。

## 两种不同的接入路径

**A. 官方 Codex 插件 (OAuth/MCP，适合交互式导演)**

官方 LibTV Marketplace: https://github.com/liblib-ai/marketplace 。插件 `libtv` 使用生产端点 `https://mcp.liblib.tv/mcp`，OAuth登录是 Codex 插件服务负责，**不会自动赋予本聊天/本仓库 GitHub Actions 的授权**。在用户自己的 Codex 环境中：

```bash
codex plugin marketplace add https://github.com/liblib-ai/marketplace.git --ref main
codex plugin add libtv@libtv
```

安装后创建新 Codex 任务，完成由服务方弹出的登录授权。只有用户所在 Codex 客户端完成OAuth后，才能调用 MCP 工具。不能把 `mcp.liblib.tv` 误当成无需认证的普通 REST URL。

**B. Agent-IM 会话 OpenAPI (Access Key，适合 OneFlow 私有执行环境)**

供参考的 Agent-IM Skill: https://github.com/libtv-labs/libtv-skills 。公开的接口定义：

- `POST https://im.liblib.tv/openapi/upload` (multipart media + accessKey)
- `POST https://im.liblib.tv/openapi/session` (消息与可选 sessionId)
- `GET https://im.liblib.tv/openapi/session/{sessionId}?afterSeq=N` (查询媒体结果)
- 图片/视频结果默认在 `https://libtv-res.liblib.art` 资源域。

**注意:** 两种认证不能直接互换。Agent-IM 的 `LIBTV_ACCESS_KEY` 是否对你的 LibTV 账户开通，需要在服务提供方确认，不能用普通账户登录密码、Cookie或Codex OAuth凭据冒充它。

## 为何适合当前 OneFlow

已有生产链有 `oneflow/commercial_campaign.py` 进行“一句话→真实竞品证据→原创视频分镜”交接；接着把分镜与锁定参考图交由 LibTV 会话型Agent 生成视频或继续编辑，再将实际视频MP4和SHA256交给 FFmpeg/Remotion、5588a审核和 V3.1 平台发布网关。

优势：创意任务可直接给 LibTV 智能导演处理，多模型编排及视频续写，适合概念超跑、商业产品广告、未来建筑。风险：多模型可能由服务端自动选择，镜头/时长与尺寸未必受 Agent-IM API 严格控制，仍必须检查实际视频、授权许可和积分账单。**不能仅凭一次 session 发送成功宣称生成14秒、2K或已可商业使用。**

## 当前可立即运行的零费用验收

在检出的开发分支中：

```bash
python -m unittest discover -s tests -p 'test_libtv_adapter.py' -v

python -m oneflow.libtv_adapter \
 --brief "用已授权的原创未来银白翡翠超跑首帧生成14秒真实加速片段，保持车型一致，湖畔日落，最后缓慢收束" \
 --reference /private/video/last_frame.jpg \
 --out private-inputs/libtv-offline
```

输出 `private-inputs/libtv-offline/libtv-job.json`，明确 `OFFLINE_PLAN_NOT_GENERATED`。此命令不需要 LibTV Token、不上传、不扣积分。

## 经过账户授权与费用确认后的单次提交 (仅限受控私有运行环境)

1. 从 LibTV 官方/服务端取得可用于 Agent-IM 的授权 `LIBTV_ACCESS_KEY`，放入受控 Secrets；不能提交到公开GitHub、打印在日志或发聊天消息。
2. 在 LibTV 账户内确认你要使用的模型、具体一次请求消耗的积分及商用许可证；**当前没有已验证的报价API**，本适配器不会伪称能在提交前自动核实余额/扣费；人工确认后才可以放开一次提交。
3. 本地私有系统中保存真实首帧（原用户素材不要推到公开GitHub）。
4. 只为明确批准的一个任务执行：

```bash
export LIBTV_ACCESS_KEY='YOUR_TOKEN_IN_PRIVATE_ENV' # illustrative; use secure secret store
python -m oneflow.libtv_adapter \
  --brief "根据参考图生成后14秒高质感商业级延续镜头，原始车身结构和建筑位置严格不变" \
  --reference /private/media/last_frame.jpg \
  --out /private/jobs/emerald-14s \
  --live-submit --approve-single-request --confirmed-cost-and-rights
```

执行一次上传 + 单次生成会话请求；返回真实 `session_id` 和 `project_url` 后，**不重试**任何因网络超时无法确认的提交，先查账户是否产生任务和扣费。若需要续写，同样一次显式授权，以已存在的 `--session-id` 调用。

查询、下载：

```bash
python -m oneflow.libtv_adapter --check --session-id REAL_SESSION_ID --out /private/jobs/emerald-14s

python -m oneflow.libtv_adapter \
  --download-url https://libtv-res.liblib.art/REAL_VIDEO.mp4 \
  --download-to /private/jobs/emerald-14s/shot01.mp4 \
  --out /private/jobs/emerald-14s
```

下载文件仍需 ffprobe、视觉物理一致性和使用权审核；有自己的媒体授权记录后才会进入商用发布队列。

## 防止误解的硬限制

- GitHub仓库 `5588a` 为公开仓库。任何开发分支/CI均不可把 `LIBTV_ACCESS_KEY`、媒体文件、私人账号内容或客户资料提交公开代码。
- 默认CI不设置 `LIBTV_ACCESS_KEY`、不调用真实LibTV服务，也不触发消耗积分的“测试”。
- 官方Codex插件暂不等同于ChatGPT Plugin Directory安装；当前会话搜索不到名为LibTV的可直接调用插件。Code/Adapter可以放进 OneFlow，但真实授权要在用户自己的服务/客户端完成。
- LibTV 官网当前活动可能展示“0积分畅用”，但有会员/套餐/模型限制，**不视作Agent-IM API的免费商用权利**。不能自动使用付费模型作为失败回退。
- 用户已确定的7模块镜头和原图锁定约束必须作为输入，生成结果人工逐镜审查，不合格返修要再次明确授权与费用。
- LibTV只负责视频生产和编辑；抖音、小红书、视频号、YouTube等账号OAuth、发布权限与收益回流依然由独立发布适配器处理。
