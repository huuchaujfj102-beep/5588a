# OneFlow Commercial V3.1 — 已登录网页调研 → 可审计视频制作 → 授权排期

> 2026-11-02：本模块基于用户上传的桌面照片需求建立。照片显示小红书网页调研已在**另一个已登录的浏览器会话**中进行；出现人机/滑块验证步骤。照片本身不是全链路完成证据，且我们无权从图片导出登录状态。

## 目标与本次实测边界

一句话 → 全平台调研指令 → 真实公开帖子链接/计数/结构证据 → 运营选题 → 影视分镜 → 商业生产与审核 → 分平台包装 → 按授权定点发布 → 官方数据+询盘+订单+回款分析。

当前本PR可以**直接运行**：研究任务生成、人工授权浏览器证据JSON导入/格式审查、至少5帖/3创作者的近45天样本门禁、内容结构归纳、原创创意交接、OneFlow离线分镜、9账号/16账号排期、待发布门禁和CI单测。当前**不能冒充已实现**：登录态网页自动执行、验证码跨越、视频推理、真实平台发布、真实ROI。后者需分别提供已授权浏览器控制通道、商业AI模型API、真实媒体存储、审核人、官方出版API和CRM。

## 先在小红书走通“调研→创意”闭环

推荐账号方向：AI商业大片实验室。先研究“AI产品广告”、“商业创意短片”、“三维/AI广告前后对比”、“AI影视工作流”。截图中的“北京周末活动”仅是浏览器操作示范，不用作本项目的对标样本。

运行无需密钥的准备命令（生成待办，而**非爬取**）：

```bash
python -m oneflow.commercial_campaign \
 --brief "调研小红书最近45天AI产品广告与高端影视制作热门账号，做一条30秒原创商业广告短片" \
 --platform xiaohongshu --seconds 30 --stage launch \
 --start 2026-11-02T09:00:00+08:00 \
 --out private-inputs/v3.1-xhs
```

输出 `research/browser-research-tasks.json`（浏览器调研任务单）、`research/xiaohongshu-evidence-report.json`（最初为空、状态SAMPLE_INSUFFICIENT）、`schedules/commercial-v3-queue.json`、`campaign-manifest.json`。一切真实数据仍为待录入。

### 已登录浏览器操作标准（用于Work云端浏览器/授权的研究人员）

1. **用户本人在官方网页完成登录**。若出现滑块/验证码，由用户手动验证；不可绕过、冒用Cookies或自动解验证码。不要保存密码、cookies、手机号、私信/通讯录等隐私信息到GitHub或第三方。
2. 研究人员在平台公开搜索结果中选择**至少3个独立创作者、5条45天内公开视频**，建议目标5个创作者12条公开作品；不得未经授权批量抓取或访问隐藏接口。
3. 每条记录：公开的帖子URL、创作者展示名（不是实名隐私）、发帖时间、调研时间、封面/开场钩子、内容结构、视频类型、可见点赞/收藏/评论/观看计数、可见商单/商品/联系入口与证据URL。不可见的数据留空，**不得估算、补零或猜收益**。
4. 对标目标：3秒钩子、视觉特色、留存设计、评论问题、搜索关键词、商业联系入口，全部保留原始公开URL；对原创、广告、AI标注及商业使用权作独立审查。
5. **创作者内容只能用于结构研究，不能下载重发或复制镜头/素材**；明确区分观察到的商业入口与真实收入。
6. 小样至少5条/3创作者后，人类研究负责人复核来源、时间、关键事实并签核。AI随后才可将其推进原创分镜。

### 本地JSON结构（虚构字段示意，URL必须替换为真实浏览器研究所得链接）

```json
{
  "xiaohongshu": [
    {
      "url": "https://www.xiaohongshu.com/explore/REPLACE_WITH_REAL_POST",
      "creator": "公开作者展示昵称",
      "title": "可见标题",
      "published_at": "2026-10-28T10:00:00+08:00",
      "captured_at": "2026-11-02T09:30:00+08:00",
      "format": "short_video",
      "hook": "前三秒产品变形前后对比",
      "structure": "问题-产品亮点-过程-成片",
      "metrics": {"likes": 120, "comments": 8, "saves": 18},
      "lead_signal": "business_contact",
      "lead_evidence_url": null
    }
  ]
}
```

以上数据和数字仅示例，不能作为真实市场研究结论或入库。统一导入前至少5条且3名创作者、均为45天以内记录。谨慎处理URL（不得包含token/cookie/session），公开可验证HTTPS URL的域名必须匹配平台。

导入：把研究结果保存在**私有工作机**上（不要commit到公开GitHub）：

```bash
python -m oneflow.commercial_campaign \
 --brief "面向3C智能硬件制作原创30秒电影级产品大片，抓住真实客户购买痛点" \
 --platform xiaohongshu --seconds 30 \
 --evidence /private/observations/xhs-public-posts.json \
 --approve-research --research-editor "已核实链接的实际审核人" \
 --out /private/campaigns/xhs-001
```

输出真实 `production-plans/film-*/manifest.json` 和 `storyboard.md`（脚本，不是MP4），同时保留 `evidence-report.json` 与对应平台排期。若样本不足则只输出研究缺口，不能编造头部账号数据。

## 后续视频生产和发布（已有V3.0接口；尚未全量接通）

1. 根据研究审核后的原创分镜准备真实产品授权图、事实参数，锁定人物/车辆/场景。
2. 使用 OneFlow 已有 `run --live`，仅在实际具备**许可确认、可用GPU/模型API图、明确预算**的生产机器上逐镜生成；相机、道具和物理连续性进行人工审核。
3. FFmpeg/Remotion剪辑，生成9:16、16:9、4:5、不同语言的合格版本；品牌LOGO/AI合成标识遵循各平台规则。
4. 将真实视频路径与SHA256送入 `oneflow.commercial_v3`，由实际审核人核准版权、广告真实性、内容结构和画质。
5. 官方API支持且已获批准的账号由可信**私有调度服务**在批准时间调用 `oneflow.commercial_dispatch`；后台负责官方OAuth、素材读取、实际上传、异步状态轮询、发布ID/URL核验以及去重。不能仅由GitHub的一句计划就推断已发布。
6. 小红书/视频号普通账号：优先生成发布包+官方创作者工具的人工确认排期；待有正式发布API再进入无人值守公开发布。不会私自调用非公开接口或伪装浏览器绕过验证。
7. API数据、官方后台截图及合法客户CRM导出 → 实际曝光/观看、有效询盘、成交金额、退款、模型推理费用和净利润。没有数据的字段应当为NULL。

## 上线验收顺序

- **A 调研真数据**：用户网页登录、完成验证；小红书5帖/3创作者真实URL经复核导入并形成可执行选题（现阶段代码/测试支持，但尚无实际调研数据入库）。
- **B 视频真成片**：1条30秒多镜商业短片真实生成、查看失败次数与总成本、审核通过；无商用许可的免费额度只能用于测试。
- **C 一个账号真发布**：YouTube OAuth+视频上传与定点发布（或经审批的抖音API）得到真实公开URL与状态。
- **D 多平台扩张**：按账号合法授权，逐个新增渠道并记录有效发布回执；对不可API发布的渠道保持人工辅助。
- **E 商业闭环**：真实客户询盘/报价/回款/成本/续费数据导入，至少一个可审计真实订单，才谈“开始变现”。

## 官方发布边界（2026-11）

- 小红书授权scope官方文档：`write_notes`仍标注“规划中，特定场景额外审核”；网页登录成功 ≠ API自动发布资格。https://openaccount.xiaohongshu.com/docs/scope
- 抖音开放平台创建视频需申请对应`video.create.bind`并由用户授权；发布需用户感知且存在内容审核。https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/video-create
- TikTok官方Direct Post需`video.publish`、用户明确同意与应用审核，未审核客户端只可私密发布。https://developers.tiktok.com/docs/en/content-posting-api-reference-direct-post
- 中国生成合成内容需合规标识；平台适用规则、账号身份、跨境数据和商业合同需另行确认。
