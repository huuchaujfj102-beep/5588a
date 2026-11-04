# 星火3.0｜全球可API/数据库接入的AI长视频工具深度研究（2026-11-04）
> **专项研究 v1.0**｜覆盖全球商业API、GitHub开源长视频模型、分镜编排/自动合成、口型与数据库连接；专门面向7分钟国风故事、后续20分钟长篇。**此次不复查用户已安装插件、不执行部署和付费请求。**本报告作为PR#52草稿内容，尚未合并main。

## 研究边界与口径
- “能做7/20分钟”分为A原生/延长生成连续片段、B短镜头生成后经时间线组成长片、C配音/脚本/图库整合输出长片、D仅编排/合成。不能把B/C/D宣称为模型一次生成420/1200秒。
- “能数据库接入”需有REST API、SDK、本地CLI/HTTP、Webhook或项目导出格式，能记录scene/shot/task、素材URI、render URL、计费、授权和审核结果。
- “已核实”意为官方文档/GitHub存在；**不是**已经取得用户账户授权、在5588a实测成功或已确认商业合规。
- 开源代码许可证、模型权重许可证、供应商API条款、素材/音频版权**分开核查**。全球可访问、可商用有地区/收入/模型版本限制。
- 先低成本90秒样片→420秒7分钟→章级1200秒20分钟；不能只凭star或宣传demo判为量产合格。

## 一、优先级清单：5种类型、17个候选
| # | 工具/官方项目 | 类型 | API/数据接口 | 长片能力的真实含义 | 商用/风险判断 | 星火结论 |
|---|---|---|---|---|---|---|
| 1 | Stable Video Infinity (vita-epfl/Stable-Video-Infinity) | 连续视频模型/LoRA | GitHub推理脚本、ComfyUI工作流、可用适配器 | 官方展示8分钟动画、14分钟视频；并非一键稳定叙事 | 代码MIT，底座Wan权重和示例素材另审；高GPU成本 | **优先深测**：7分钟持续运动研究 |
| 2 | LongCat-Video（meituan-longcat/LongCat-Video） | 多分钟T2V/I2V/续帧 | CLI Python推理及视频延长脚本，可封REST | README明确声称分钟级长视频，720p 30fps | 仓库MIT，下载权重及输出授权另核；13.6B模型重 | **优先深测**：长镜头与角色延长 |
| 3 | FramePack（lllyasviel/FramePack） | 低显存分段长视频 | Python本地程序/需自行包API | 官方1分钟示例，6GB起；长时速度慢 | 代码Apache2；注意官方仅GitHub、假站钓鱼 | **保留研究**：单镜持续动作与低VRAM |
| 4 | SkyReels-V2（SkyworkAI/SkyReels-V2） | Diffusion Forcing续视频 | Python推理/本地REST包装 | 官方30/60秒参数示例，所谓无限延长不等于无漂移 | Skywork模型社区许可非MIT、需逐条审 | **中优先**：场景内延长 |
| 5 | SkyReels-V3（SkyworkAI/SkyReels-V3） | 多角色参考、音频驱动、V2V | 官方仓库+apifree.ai API入口 | 强项参考人物/音频/续视频，非420秒完整剧情 | Skywork社区许可，商业条件另核 | **优先小样**：角色与对白 |
| 6 | LTX-2.x（Lightricks/LTX-2） | 同步音视频I2V/多关键帧 | Python模型推理、社区托管API | **短镜头**，不是原生7分钟 | LTX-2.x Community License，年营收≥US$10m商业许可条件；核对权重版本 | **辅助**：剧情动态镜头 |
| 7 | HunyuanVideo-1.5（Tencent-Hunyuan/HunyuanVideo-1.5） | 高效T/I2V | Python脚本、可自部署API | 逐镜头生成后拼长片 | Tencent专有社区许可**排除EU/UK/韩国**等，跨国发行与输出条款有风险 | **暂缓跨国商业版** |
| 8 | Story2Video（approximatelylinear/story2video） | 章节/场景导演编排 | **SQLite/JSON**、CLI/Web UI；MiniMax/fal/Venice/Wan接口 | Story→Chapters→Scenes→短片→FFmpeg，非单次420秒 | 小项目，未见明确仓库许可证/商业许可；代码与稳定性审查 | **第一优先开源研究** |
| 9 | Script2Video（reaink/script2video） | 脚本→镜头→合成 | 浏览器会话IndexedDB；多模型API | 自动剪多个短镜成为长片，可导出SRT | 浏览器本地缓存不等于生产数据库，需后端改造 | **可借鉴分镜界面** |
| 10 | StoryMind（LinHao-city/StoryMind） | AI导演＋多服务生产 | CLI/多模型服务、结构化视频流程 | 根据分镜合片，示例多为几十秒至2分钟 | AGPL-3.0；如网络服务改造可能触发开源义务 | **评估代码不直接复制** |
| 11 | MoneyPrinterTurbo（harry0703/MoneyPrinterTurbo） | 主题→字幕配音素材合成 | WebUI/API/CLI；多云模型与发布适配 | 长篇旁白/素材拼片可借鉴，不是长连续AI动画 | MIT代码，但图库/LLM/声音/发布按提供商审 | **可借鉴任务接口** |
| 12 | Fliki（developer.fliki.ai） | 原稿/URL→配音视频 | **正式REST API**、生成任务查询 | Standard最长15分钟，Premium最长30分钟；更偏讲述/素材视频 | 商业权由订阅和素材条款约束；不主打原创动态国风剧 | **低代码备选** |
| 13 | JSON2Video（json2video.com） | 完整云端长片时间线 | REST API+Webhook+SDK；JSON scenes | 官方付费最长30分钟；可将多镜/配音/字幕组成420/1200秒 | 成片渲染服务，不产生所有原创动态镜 | **首选云合成候选** |
| 14 | Shotstack（shotstack.io） | JSON时间线云渲染 | REST API+素材托管+Webhook/Make/n8n | 任意多素材时长合成，付费按输出分钟；上限以账户验收 | AI镜头生成另计费，不能误认为每分钟价包括AI镜头 | **首选云合成候选** |
| 15 | Creatomate（creatomate.com） | 模板/RenderScript自动渲染 | REST API+Webhook、模板管理 | 适合分层绘本、品牌化片头字幕、批量长视频模板 | 渲染文件最多托管30天，务必自动回存；额度按分辨率/帧率 | **首选2D模板合成候选** |
| 16 | Rhubarb Lip Sync（DanielSWolf/rhubarb-lip-sync） | 2D嘴型时间轴 | CLI，JSON/TSV/XML输出 | 7分钟语言对白可生成mouth cues后与2D角色合成 | MIT；默认PocketSphinx仅识别英语，中文需phonetic模式且误差需复核 | **低成本新增核心组件** |
| 17 | fal.ai | 多模型云代理 | REST API/SDK/任务队列/结果URL | 调用不同短视频模型，再交长片合成服务 | 按具体模型/分辨率计费；并非长片时间线本身 | **动态镜头替代/比价层** |

> 额外研究：mifi/editly为MIT的Node.js+FFmpeg可编程剪辑框架，可做Shotstack/JSON2Video的本地fallback；非新AI生视频模型。Supabase/Postgres与n8n属于控制面和数据库，而不是生视频模型。

## 二、开源“原生长视频”最值得深入的4项
**SVI（最贴近长片研究）**
- 官方展示8分钟动画和14分钟视频；有Wan2.1主分支与Wan2.2分支、SVI2.0 Pro工作流；声称长距离稳定性依赖LoRA和生成配置。
- 风险：20分钟剧情需要跨场景/角色统一、故事语义控制；长度demo并不证明一口气7分钟不崩，也不证明可商用。
- 试验：先相同角色30秒（4次5–10秒）→60秒→90秒；记录脸/服装漂移、背景一致、开始结束帧、GPU小时及权重授权。

**LongCat-Video（第二首选）**
- README提供T2V、I2V、Continuation、long-video、Avatar 1.5（May 2026）脚本；有明确分钟级目标与720p 30fps。
- 风险：13.6B高算力、官方性能声明不等于自有云GPU性能；叙事分镜跨景物镜头仍需要独立导演层。

**FramePack（第三）**
- 官方6GB显存可运行13B/1分钟示例，但4090单帧约1.5–2.5秒推理，60秒×30fps≈45–75分钟渲染（不含读取、初始化、返工）。
- 按此简单线性外推420秒≈5.25–8.75GPU小时只是时间量级估算，跨镜头连贯/修片会更久；低显存≠低云账单。

**SkyReels-V2/V3**
- V2 Diffusion Forcing延长理论上无限，仓库例子包括60秒；V3更适合多人参考、声音控制和图生视频。
- 先用V3做人设一致的对话镜，用V2单场景延长；模型社区许可优先法务核查，不把它作为可自由复制的MIT模型。

## 三、能“真正组装7分钟”的商业API：预算可核算
| 组件 | 当前公开价/套餐 | 7分钟只计合成的示例 | 业务角色 |
|---|---|---|---|
| Shotstack | 按量US$10/50分钟，月订阅US$39/250分钟等 | 按量7×US$0.20≈US$1.40 | 云端JSON多轨合成，API/素材/异步任务 |
| JSON2Video | US$49.95预付120分钟；专业版US$49.95/月200分钟 | 预付折合7×US$0.41625≈US$2.91；订阅折合约US$1.75 | 付费30分钟上限，完整JSON场景API |
| Creatomate | 720p 25fps约14 credits/分钟；金额取决订阅 | 7分钟约98积分，需核账户单价 | 分层2D/模板、字幕动画和API自动导出 |
| Fliki | Standard最长15分钟，Premium最长30分钟 | API额度/套餐计费，未核到可直接换算单集的可靠数字 | 自动旁白图文/素材视频的低代码备选 |
| fal.ai H3 Turbo | 官方价约US$0.025/**模型生成秒** | 假设105秒动态画面×1.6生成≈US$4.20，**仅I2V模型** | 用于关键动画镜头而非全片渲染 |

**重要**：上述云合成7分钟报价不包括每段生图、视频片段、TTS、音乐商用许可、素材下载、人工、失败重做与存储。Shotstack/Creatomate/JSON2Video的render和AI generation必须分别记账。部分平台免费方案有水印或禁止商用，不能直接用免费测试输出接商单。
- JSON2Video官方定价页和Docs存在一个套餐说明差异：定价页Hobby说最长30min、Docs中的旧表将Professional标为10min且Startup30min；**以实际账户plan limit及预检API为准，不把跨页冲突当成已验证规格**。
- Shotstack付费按输出视频分钟，不是“镜头生成秒”；套餐一律以实际创建前的账户计划和账单为准。

## 四、适配数据库的端到端架构（新研究重点）
**推荐技术栈：Supabase/Postgres + 私有S3对象存储 + GitHub/OneFlow调度 + Story2Video场景模型 + 新增关键帧/口型模块 + Shotstack或JSON2Video云合成（或原有FFmpeg/Remotion本地回退）**。

数据对象（不保存公开秘密令牌）：
- projects：项目ID、商业预算、资产许可证、视频规格、客户隐私级别。
- episodes：总目标420/1200秒、剧情版本、全片状态、目标平台。
- scenes：集数ID、场景序号/场次剧情/预估时长/角色/地点/语言/声音轨。
- shots：稳定镜头ID、场景ID、目标秒数、镜头提示词七模块、首尾参考帧URI、角色版本、运动控制。
- assets：文件UUID、SHA256、真实S3 URI、来源授权、商用合同、文件类型、作废/有效状态。
- generations：backend、version、provider_task_id、seed、输入资产、状态、生成秒数、原始计费、重试原因。
- audio_cues：语句文本、speaker_id、wav URI、SRT时码、口型数据URI。
- renders：renderer、render_job_id、回调签名、成片URI、编码参数、持续时间。
- qc_reports：镜/场/整片状态、自动证据、人工审核人、禁止自动放行项。
- publications：平台、审批、AI标识、真实发布回执、指标采集时刻。
- cost_ledger：币种、单价版本、实际账单、供应商任务ID、项目支出、退款。

数据触发：
（1）写入scene/shot→（2）n8n或私有worker监听任务、要求budget_approved→（3）调用模型/CLI，存入S3→（4）API/webhook回调→（5）对任务ID验签+幂等，写回数据库→（6）按场合片→（7）5588a七关＋人工视觉/版权审核→（8）逐平台授权发布→（9）真实数据与回款回填。
对Supabase启用RLS、Service Role不交给前端；GitHub公开仓库不得存客户视频、API token、素材版权证明或私密角色库。S3对象桶按客户/项目隔离；不接收不可信外部URL作为任意服务器下载对象，避免SSRF。

## 五、首条7分钟国风故事试验三方案
**A：最低复杂度（优先）**：Story2Video(场景/SQLite借鉴但不直接依赖其稳定性)＋角色生图＋Rhubarb中文phonetic口型＋2D分层动画＋Shotstack/JSON2Video 420秒合片。75%约315秒由分层动画承担，25%约105秒高光镜交付fal或已授权短镜模型。
**B：电影感增强**：A+SVI/LongCat做30–60秒连续动作关键段，每个GPU推理任务独立成本封顶；3分钟以上不要靠一个模型从头生成。
**C：简易全自动解说/旁白**：Fliki API从原始文本一键生成长语音和匹配素材，再由OneFlow二次剪辑。适合讲历史/文化知识，不适合角色互动多、剧情复杂的国风动画。

初步预算（人民币，**不是实机账单**）：
- 原创剧本/角色资产/分层动画API或云工具：¥80–220；
- 105秒动态镜头+返修：¥50–350（供参考，视外币汇率、模型及1.6次尝试变化）；
- TTS/音效、必要音乐版权：¥50–180；
- 云合成/存储/转码：¥15–90；
- **现金¥195–840/集**；人工30–70小时×¥50/h = ¥1500–3500；全成本约¥1695–4340。故首条预算审批上限为现金¥900，第一轮90秒样片现金上限¥200。
- 先全自动测试场景分解和数据库写回，之后只做90秒片；通过画面一致、配音口型、实际计费与版权审计，才放行剩余330秒。不得从商业宣传推定利润。

## 六、评分与决策（星火年营收100万规划配套）
评分口径：国风7分钟适配40%、API数据库20%、商用许可15%、成本/算力15%、工程成熟度10%；人工判断，不是客观性能跑分。
| 候选 | 适配分/100（分析估计） | 优先动作 |
|---|---:|---|
| Story2Video 架构 + GitHub技术改造 | 86 | 优先拆架构、写Scene JSON与数据库表，不未经审计复制代码 |
| Shotstack云合成 | 84 | API sandbox 7分钟空镜/图片+字幕合成测试 |
| JSON2Video云合成 | 83 | 核对免费/付费最长时长及2026账户计划；7分钟测试 |
| Creatomate | 81 | 2D分层模板原型，渲染一次7分钟样本 |
| Rhubarb | 80 | 中文30秒phonetic口型误差实测 |
| Stable Video Infinity | 78 | 云GPU 30秒→60秒→90秒视觉漂移评测 |
| LongCat-Video | 75 | 权重许可/显存预估；短片续帧试验 |
| fal.ai | 73 | 统一I2V任务适配、明细计费、错误重试 |
| FramePack | 64 | 仅用于单镜长动作，不用于整集生产 |
| Fliki | 61 | 解说/知识栏目备用，国风多人剧非主力 |
| HunyuanVideo-1.5 | 45 | 跨国地区许可风险，暂缓 |

## 七、两周接入调研验收计划（建议，不是完成状态）
D1–2：审许可证、真正限时/计费方式；制作场景数据模型、测试素材授权台账。
D3–4：Story2Video数据库导出与本项目Scene JSON对照；检查是否有投毒、不安全模型调用/密钥泄露。
D5–6：Rhubarb中文口型小样、7分钟静态图层动画基础版。
D7–8：以Shotstack或JSON2Video sandbox 合并7分钟合成测试，不调用昂贵模型。
D9–10：SVI/LongCat任选一个30秒云GPU小样，记录真实GPU用量、连续性与成本；不达标即停止。
D11–12：混合90秒试片，生成真实素材hash、权属台账、字幕/对白、QA报告和实际成本。
D13–14：结论复盘，决定是否开发420秒production分章队列。**未获授权不执行外部写入、开户或付费调用。**

## 八、资料来源（官方，2026-11-04查阅）
1. https://github.com/vita-epfl/Stable-Video-Infinity
2. https://github.com/meituan-longcat/LongCat-Video
3. https://github.com/lllyasviel/FramePack
4. https://github.com/SkyworkAI/SkyReels-V2
5. https://github.com/SkyworkAI/SkyReels-V3
6. https://github.com/Lightricks/LTX-2
7. https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
8. https://github.com/approximatelylinear/story2video
9. https://github.com/reaink/script2video
10. https://github.com/LinHao-city/StoryMind
11. https://github.com/harry0703/MoneyPrinterTurbo
12. https://github.com/DanielSWolf/rhubarb-lip-sync
13. https://shotstack.io/docs/api/ ；https://shotstack.io/pricing/
14. https://json2video.com/docs/v2/reference/credits/plans ；https://json2video.com/pricing/
15. https://creatomate.com/docs/api/reference/introduction ；https://creatomate.com/pricing
16. https://developer.fliki.ai/ ；https://fliki.ai/pricing
17. https://fal.ai/pricing
18. https://supabase.com/docs/guides/api ；https://supabase.com/docs/guides/database/webhooks

## 审计备注
- 开源项目研究使用只读GitHub连接核对仓库README/License；未部署，也未宣称当前免费GPU可用。
- SVI仓库MIT仅说明该仓库代码许可，必须核查其底座权重及引入的LoRA素材条款。
- LTX-2.x有年收入≥US$10m的商用协议条件；腾讯HunyuanVideo模型社区许可有明确地区限制，不能把所有开源项目直接作为全球分发商业授权。
- UI/AI演示片可能包含有版权的动画人物，例如官方demo本身不可照搬。
- 三家云合成计费与上限在官方网站可能随时调整，账户预检和真实账单优先。
- 此报告**仅是研究与方案扩展，不代表“用户新插件已装好”**。