# OneFlow Commercial V3.0 — 国内/海外13个平台统一策略与发布调度（2026-11-01）

**执行状态：已实现平台策略目录、账号配额、分平台本地时间排期、发布审查门禁、授权发布网关交接、离线测试；尚未配置任何社交账号OAuth/官方应用审核/真实视频输入和成交数据，不得将离线生成的排期称为已自动发布或变现。**

## 市场定位与经营模型

**主业**：AI商业视频定制、产品广告短片、商业客户年度服务。**内容流量入口**：原创未来超跑、工业科技视觉、建筑概念。**第二收入**：有版权的AI影视工作流模板/教学、企业培训和自动化部署。**第三收入**：海外赞助、符合资格的广告与数字产品。流量必须以真实询盘/回款作为最终指标。

全球主流与中国平台分两层，不鼓励机器批量注册或群发：
- 第0层（0-30天）**9个真实、独立定位账号/8个平台**：抖音2、小红书1、视频号1、快手1、B站1、YouTube1、TikTok1、Instagram1。
- 第1层（30-90天达标再扩）**16账号/12个平台**：抖音3、小红书2、视频号1、快手1、B站1、头条1、YouTube2、TikTok1、Instagram1、Facebook1、Pinterest1、LinkedIn1。微博仅作为观察和运营数据源，不立即单开。不能因为“全平台”就盲目注册无定位账号。

## 各平台经营清单

| 平台 | 首发账号→扩张 | 主要内容 | 冷启动与发布频次 | 内容变现 | API可行性 |
|---|---:|---|---|---|---|
| 抖音 | 2→3 | 15-35s超跑剧情式奇观；20-45s工业产品广告；AI幕后 | 7天4-6条原创观察，稳定每号3条/周；看3秒/完播/询盘 | 企业视频、商单、合规商品内容 | OAuth + video.create.bind申请 + 每次明确投稿 |
| 微信视频号 | 1→1 | 30-120s企业客户案例、可信制作过程、微信圈层传播 | 每周3条案例，跟公众号/企业微信合规承接 | 企业视频月费、信任转化 | 普通视频公开发布API未核实；官方视频号助手定时，须人工确认 |
| 小红书 | 1→2 | 搜索型AI商业广告前后对比；4:5可收藏多图教程；2分钟深度 | 每周3条作品+1-2条流程笔记，先研究搜索/收藏/咨询 | 付费定制、模板、符合条件的蒲公英合作 | write_notes仍为规划中，走官方创作后台人工发布 |
| 快手 | 1→1 | 工业/汽配/中国制造真实故事；科技产品解决方案 | 每周3条；强调真实工艺和专业回应 | B2B线索、品牌合作 | user_video_publish申请，发起/上传/异步发布后核验 |
| B站 | 1→1 | 4-10分钟制作拆解+20-90s反差预告 | 每周1长+2短，建系列并标明素材和成本 | 品牌、课程、专业服务 | 官方开放平台有投稿/查询，需要开发者及授权 |
| 头条 | 0→1 | AI产品测评深度、科技知识/图文 | 第61天以后每周2篇改编 | 专业服务、符合资格的收益 | 申请toutiao.video.create及用户授权 |
| YouTube | 1→2 | Shorts 视觉钩子+5-12分钟制作幕后英文深度 | 每周3 Shorts+双周1长，长视频服务商业信任 | 品牌、海外定制、YPP合资格分成 | 视频上传OAuth; 私密视频status.publishAt可定时 |
| TikTok | 1→1 | 15-40s超跑科技钩子+原创制作解释；奖励项目需符合长度和资格 | 每周4条，测试英文前三秒及真实交互 | 合作、定制、合格地区创作者计划 | Direct Post审核/用户授权，否则private |
| Instagram | 1→1 | Reels质感短片+轮播镜头/材质展示 | 每周3 Reels+1轮播 | 品牌合作、商业咨询 | Meta专业账户/授权、容器发布及状态核验 |
| Facebook Reels | 0→1 | 汽车/制造/建筑视觉二次剪辑 | 第2个月后每周3条 | B2B合作 | Meta Page权限与审核后API |
| Pinterest | 0→1 | 工业/空间设计参考图、视频Pin | 第3个月每周3-4 Pin，关键词/收藏/点击 | 设计服务、作品授权 | OAuth pins:write; Trial内容可能仅自己可见 |
| LinkedIn | 0→1 | 工业品牌营销前后对比、30-90s B2B案例 | 第2个月起每周2条，产品采购/品牌决策层 | 国际企业定制、年度内容服务 | Posts+Videos API, 公司管理员及OAuth |
| 微博 | 0→0 | 汽车/设计/AI视觉时事，先作为热点监听 | 不开新号，验证流量价值再申请 | 品牌合作 | 官方weibo-cli需实名开发者、OAuth和额度 |

> 以上内容方向、起号节奏、账号数和发送时间都是**待验证的运营假设**，不是平台保证的起号公式。所有真实账号必须实名合规、定位独立；不要采用模拟浏览器绕过、批量购买账号、搬运改写侵权、虚假播放、刷评论、自动群发陌生人私信等手段。

## 头部内容与细分赛道观察

- **国内高质感/科技故事**：影视飓风（制作过程和品牌合作）、老师好我叫何同学（工程/科技创意结构）、行业工业/智能硬件展示类。参考“作品—过程—产品价值—商业入口”，不要复制对标视频。
- **海外汽车奇观**：Supercar Blondie等汽车媒体重视稀缺视觉和概念技术；我们的账号做**原创未来工业设计与拍摄幕后**，明确标明概念与AI制作，避免虚构汽车真实性能。
- **B站**：2026上半年公司披露AI知识观看同比增长17%，5分钟以上内容观看同比增长20%，汽车/电子数码和AI广告主投入增长。因此应把完整制作复盘和可执行教程作为主干，而非纯短片搬运。
- **小红书**：2026 LINK创作者商业化报告强调内容吸引力/需求激发/转化/经营；中长视频也在增长。高价值关键词、可收藏的案例拆解、真实定制交付比纯炫技更适合获客。
- **快手**：2026三农生态报告显示真实生产、农技/产业生活具有持续观看；我们的选择是**工业实操/产品痛点**，而非空洞AI宇宙奇观。
- **TikTok**：官方TikTok Next 2026推崇真实性、好奇心、情绪投资回报。短片必须加原创解释、互动与证明，不只套同一个模板。
- **Instagram**：2026第三方研究显示Reels更有利于发现、轮播更容易被收藏；用两种内容服务不同运营目标。
- **YouTube**：平台对重复、模板化、批量生产且缺乏独特价值的内容设置变现限制，自动生成≠自动获得分成。

验证头部：每个方向每周抽取10名**真实公开可查**创作者，记录30天作品数、观看/收藏/互动、评论需求、链接与商单证据；无法核实收入一律记为“未知”，禁止虚构“百万播放=盈利”。

## 一句话商业流水线：各层契约

```
输入1句话/目标平台/真实产品档案/预算/授权
  → 竞品研究草稿 + 选题评分 (联网/数据权限不足时注明)
  → 标准化商业视频策划: 价值主张/钩子/分镜/声音/营销事实核查
  → 参考图/品牌锁定 → 生图 → 图生视频逐镜(可靠模型, 已确认商用授权)
  → FFmpeg/Remotion后期 → 每平台版本: 9:16/16:9/4:5字幕封面音效
  → AI内容标识/版权/宣传真实性/质量审核 → 人工审核真实成片及SHA256锁定
  → 平台账号账户映射/OAuth/独立应用审批/每条用户明确同意
  → 本地时间排期 → 允许API的官方网关提交 → 轮询状态
  → 禁止官方API的平台: 导出发布包+人工在官方后台定时
  → 真实发布回执/平台分析/客户CRM/订单/回款/现金成本
  → 更新未来选题与经营模型
```

### 代码和命令（不调用生成模型、不发布视频）

```bash
python -m unittest discover -s tests -p 'test_commercial_v3.py' -v
python -m oneflow.commercial_v3 \
  --brief "给中国智能硬件产品做面向全球的高端AI商业广告，用原创未来超跑风格展示设计和技术" \
  --stage launch \
  --start 2026-11-02T09:00:00+08:00 \
  --out private-inputs/commercial-v3-plan
```

产物是 `commercial-v3-queue.json` 和 `commercial-v3-operations.md`。**这只是已分类的运营排期，不是AI视频或平台已发结果。** `--stage expand` 用于扩张16账号模拟计划。各平台候选发布时间按中国北京时间或美西时区记录；应在真实数据到来后优化，非最佳发布时间承诺。

### 经验证成片后：私有设备上的定时发布交接

```bash
python -m oneflow.commercial_v3 \
  --brief "展示真实品牌授权的智能产品，拍摄原创商业短片" \
  --source-video /private/media/approved.mp4 \
  --source-sha256 VERIFIED_SHA256 \
  --reviewer "Actual reviewer" --rights-attested \
  --out /private/commercial-v3-approved
```

需要在每个目标平台**应用审核、OAuth及用户对这条视频的明确投稿许可**完成后，由可信私有账户系统生成单条 `per_post_consent` 注册清单，标记精确账号、最终排期、有效批准编号、官方授权状态。外部系统必须二次校验，不得把单纯JSON自报当成有效OAuth。

```bash
export ONEFLOW_PUBLISHER_GATEWAY=https://your-controlled-official-api-gateway.example
export ONEFLOW_PUBLISHER_HOSTNAME=your-controlled-official-api-gateway.example
export ONEFLOW_PUBLISHER_TOKEN="only in private credential store"
# First list eligible due-time items (zero outbound requests)
python -m oneflow.commercial_dispatch \
  --queue /private/commercial-v3-approved/commercial-v3-queue.json \
  --consent-registry /private/approvals/consents.json \
  --out /private/commercial-dispatch-preview.json
# In a trusted PRIVATE scheduler that has verified OAuth and persistent media storage:
python -m oneflow.commercial_dispatch \
  --queue /private/commercial-v3-approved/commercial-v3-queue.json \
  --consent-registry /private/approvals/consents.json \
  --out /private/commercial-dispatch-result.json --live --release-consent
```

Gateway contract `POST /publish`: JSON `platform, account_key, approved_asset_sha256, media_source, scheduled_at, consent_ref, title, ai_content_label, idempotency_key`; the gateway MUST resolve approved media by hash from its OWN private store, verify OAuth and per-post user consent, invoke official vendor API, poll asynchronous status and return `{"status":"published","id":"...","url":"..."}` or `{"status":"pending","id":"..."}`. **Current GitHub 5588a does not have this live, platform-connected gateway or media store.** Pending is never successful publication. Do not run in public PR Actions, and do not upload personal accounts/large media/token to a public repository.

Manual routes for 小红书 and 视频号: generate title/封面/视频/标识说明/建议发布时间; operator imports into the official web/app scheduler, confirms publication, then manually registers URL/ID. Never automate with scraped private endpoints, cookies or stealth browser scripts.

## 预算、时间和90天效果假设

- **第1–7天**：选择三个品牌栏目，注册9个真实合规平台账号（不需要买9套设备），建立内容身份/产品档案和首次12组分镜。
- **第8–30天**：原创制作12–20条主视频，再在适合的平台改编成约50–90条**经过逐平台修改**的发布成品；每平台按实际精力调整频率。与60家匹配的智能制造、3C、设计企业进行合规商业洽谈；不发机器群私信。
- **第31–60天**：把有效的品牌案例变成标准报价，目标1–3个付费试片；平台API按申请进展接入，不为增长而强行绕过权限。
- **第61–90天**：若客户成本和质量达标，将布局扩到16账号，目标累计2–6个付费试片、0–2个长期付费客户。失败时维持9个或缩减至高效渠道。

**现金预算（不含员工工资和办公场地）**：30天¥7,000–15,000，60天累计¥15,000–30,000，90天累计¥25,000–50,000。涵盖AI合规商用额度、视频/音效软件、云存储、语言本地化、少量投流、客户打样与返工预备金；实际价格以逐任务模型报价和账户账单为准。若总可用预算仅¥20,000–30,000，应优先保留约5个高效运营账号，其他账号先注册但不承诺频繁更新。除非订单增长，不新增专职人员和付费云GPU。

**关键结果不可保证：**
- Day30: 9账号运营测试、20个有版权原创视频母片以内、至少建立3种内容角度的数据，目标3–10个有效商业询盘；
- Day60: 1–3个付费样片的挑战性目标；
- Day90: 2–6个付费样片，争取0–2个续费客户。
实际播放、粉丝、变现收入必须从官方后台/真实合同回收，以上均为管理目标而非预测。

## 100万元年利润的现实商业条件

只靠短视频播放分成风险极高。示例成熟月度经营情景：
- 15家企业月包×¥15,000 = ¥225,000
- 7个项目×¥16,000 = ¥112,000
- 150份合规工作流产品×¥299 = ¥44,850
- 总收入¥381,850/月。若交付、销售、平台、税前经营开支约¥263,970/月，经营利润约¥117,880/月，等速年化约¥141万。**这不是第一年利润预测**，且不包括税务差异、到账波动和续约风险。

## 安全合规硬门槛（必要）

1. 中国2025-09-01起AI生成合成内容标识法规；2026-05-12网信办推进短视频分类必选标注，含AI、营销、虚构。
2. 中国2026-09-01起《互联网信息内容多渠道分发服务管理规定》，如作为MCN/多渠道分发服务机构开展业务，须评估经营主体登记、平台协议、真实账号主体与内容责任。
3. 短片含品牌“造镜者”水印时，需另为抖音等平台准备符合法规与审核的版本，品牌水印不能替代法定AI标识。
4. 不做版权搬运、虚假广告、夸大产品性能、后台群发、代操作第三方未经授权账户、未获同意自动投稿。
5. 知名大号参考内容结构，不使用未经许可的他人原片素材；免费试用AI产物未获商业许可不得用于客户成片。
6. YouTube等平台对高度重复、模板化、缺乏原创价值的批量AI内容可能限制变现。要增加原创观点、真实实验和显著剪辑差异。
7. 外国平台经营、纳税、收款与目标地区资格须以真实身份和官方授权为前提。

## 代表性原始资料（更新至2026-11-01）

- 抖音创作者大会: https://www3.xinhuanet.com/tech/20260924/59ed2c0f6db34f8e8e305daefeac1a89/c.html
- 抖音发布: https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/video-create
- 小红书Scope: https://openaccount.xiaohongshu.com/docs/scope
- 小红书LINK: https://news.inewsweek.cn/observe/2026-09-20/32222.shtml
- 快手API: https://open.kuaishou.com/platformDocs/openAbility/contentManagement/createAVideo
- 快手三农2026: https://www.ithome.com/1/018/145.htm
- 视频号普通视频公开API可用性评估: https://lovstudio.ai/blog/wechat-channels-upload-automation
- B站Open API: https://open.bilibili.com/doc
- B站2026财报: https://www.sec.gov/Archives/edgar/data/1723690/000119312526400258/d163378dex991.pdf
- YouTube Data API: https://developers.google.com/youtube/data/reference/rest/v3/videos/insert
- YouTube盈利政策: https://support.google.com/youtube/answer/1311392
- TikTok direct post: https://developers.tiktok.com/docs/en/content-posting-api-get-started
- TikTok Next 2026: https://newsroom.tiktok.com/introducing-tiktok-next-2026-our-trend-forecast-for-marketers-for-the-year-ahead-sg
- Meta Instagram publishing: https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api
- Instagram 2026 research: https://metricool.com/press-release-instagram-study-2026/
- Pinterest Video Pins: https://developer.pinterest.com/docs/work-with-organic-content-and-users/create-boards-and-pins/
- LinkedIn Posts: https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api?view=li-lms-2026-06
- 微博官方CLI: https://open.weibo.com/cli/quickstart
- 中国AI标识办法: https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm
- 短视频必选标注: https://www.cac.gov.cn/2026-05/12/c_1780328273038196.htm
- 多渠道分发服务管理: https://www.cac.gov.cn/2026-05/29/c_1781795864412597.htm
