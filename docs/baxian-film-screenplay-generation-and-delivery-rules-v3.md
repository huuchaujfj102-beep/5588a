# 《八仙过海·沧海证道》电影脚本生成、拍摄规格与成片验收强制规则 V3.0

适用：电影文学剧本、AI剧情大纲、分场剧本、分镜脚本、文生图/图生视频镜头提示、声音设计、后期合成、母版交付、P0/P1验收。  
版本：2026-11-07。状态：**制作规则已制定，尚不表示现有片源或成片达标。**  
适用优先级：此规则的技术/叙事验收要求与角色法宝锁定规则并行；人物身份、六视图、道具形制、唯一归属以已有批准母图及 `film_audit/assets/baxian_group_enforcement_policy_v3.json` 和各角色最新版锁定为准，不因追求新镜头而重设计。

## I. 四项必达标准（用户批准的基准）

| 类别 | 必须纳入剧本/分镜及制作流程的标准 | 检查阶段 | 失败处理 |
|---|---|---|---|
| 影像 | **采集母版目标 ≥4K、10bit、4:2:2 Log 或 RAW、24fps**；**ACES** 管理调色流程；交付 **Rec.709 或 DCI-P3** 并注明版本和转换链 | G00/G05明确规格；G06/G07检查源文件及调色流程；G08验收母版元数据 | 未达规定采集或母版规格的素材不得假称合格，记录源头能力限制；只能作为预演或经项目单独批准的非母版素材 |
| 声音 | **48kHz/24bit** 制作；交付 **5.1或立体声**；响度目标按发行版区分 **−23 LUFS（广电目标）／−14 LUFS（流媒体目标）**；对白按场分配现场同期声/ADR，不能整片只靠一条同期录音 | G00对白与声音场次表；G05分镜同步点；G07实际录音、混音；G08响度、峰值、声画同步报告 | 缺声轨、单条对白硬铺全片、采样精度/响度偏差、嘴形不同步，阻断正式交付 |
| 叙事 | 完整三幕或**等效结构**；核心主角/主角群有明确**欲望 → 阻力 → 选择 → 代价 → 不可逆改变**；每个主要场次推动因果，不允许仅以漂亮镜头堆砌剧情 | G00大纲及分场；G05分镜；G07剪辑剧本；G08最终观片 | 结构不成立、冲突无升级、代价无后果、主要镜头没有戏剧功能时退回改稿 |
| 完成度 | **全片无已知穿帮、无音画不同步、无重复镜头凑时长**；具备**片头、片尾、演职员表**，版权/素材出处有据可查 | G07逐段、G08母版全片复看 | 任意P0未清零或缺片头片尾/演职员表，正式版不放行 |

**技术口径说明**：传统片场的“采集”规格适用于真实摄影母片。AI文生图/I2V生成素材若未提供可验证的原生10bit、4:2:2 Log/RAW采集证明，不得因为转换、升频或上采样而声称它是原生符合采集规格的摄影素材。必须在镜头表填写 `source_type=REAL_CAPTURE|AI_GENERATED|ARCHIVE|COMPOSITE`、原生分辨率/位深、输出转换与验证状态。对AI素材，应尽量按项目技术母版规格合成、调色，并**明确区分原生生成参数和交付编码参数**。

**声学口径说明**：−23 LUFS和−14 LUFS是此项目选择的两种目标发行预设，而非所有国家/平台一律适用的强制法定数值；实际投递仍以目标平台/播出方具体响度、True Peak、短时响度、声道布局和音频封装规范为准。24fps为主时间线目标；项目有意采用变帧率或特殊帧率时须写明换算及用户批准，不得偷偷混用。

## II. 剧本生成前：必须先建立的叙事模型

1. **核心欲望**：八仙众仙既已成仙，影片不是再获仙籍，而是救回受困渔民与阿宁，阻止黑潮、还玄溟旧案真相。记录八人各自的选择，不把他们写成同一性格。
2. **阻力阶梯**：人间救援困境 → 海上妖潮与法术互克 → 群仙分离/错解真相 → 内在执念考验 → 归墟抉择；每幕阻力必须使前一方案失效。
3. **代价与改变**：明确“为了救众生必须放弃什么”，例如错过制敌机会、承担守阵责任、接受宽恕并不等于免责。代价须在后续剧情留下实质后果。
4. **三幕映射**：现有五幕文本用等效映射：第一幕(0–20分钟)建立欲望、导火索、越过第一转折；第二幕(20–96分钟)包含对抗、重大中点、失败/黑暗时刻、第二转折；第三幕(96–108分钟)结果与回报。**具体分钟比例暂为编剧规划，不应仅凭五幕名称就宣称三幕节奏已经验证。** 按真实剪辑时长重新测量结构占比。
5. **每场戏最小字段**：`scene_id`、时间/地点、主视角、人物欲望、阻力来源、策略、动作、代价、情绪变化、法宝状态、场景/声音变化、该场的戏剧功能、进入/退出条件、下一场因果桥。
6. **删减规则**：无人物选择、无因果增量、无法建立人物关系或意境必要性的纯漂亮段落必须给出保留理由，不能以重复镜头凑时长。

## III. 文学剧本、分镜和镜头脚本模板（必填）

每个镜头必须写明：

```yaml
project: 八仙过海·沧海证道
scene_id: Sxx
shot_id: Sxx-yy
act: ACT_1|ACT_2|ACT_3
story_goal: ""
character_desire: ""
obstacle: ""
choice_and_cost: ""
cause_from_previous: ""
effect_on_next: ""
source_type: AI_GENERATED
reference_assets:
  characters: [approved_hero_and_multiview_ids]
  props: [approved_prop_reference_ids]
  reference_hashes: []
camera:
  aspect_ratio: "16:9"
  native_resolution: null
  target_resolution: ">=3840x2160"
  target_fps: 24
  capture_bit_depth: null
  target_bit_depth: 10
  capture_chroma: null
  target_chroma: "4:2:2"
  capture_profile: null
  target_color_pipeline: ACES
  delivery_color_space: Rec.709
  lens_mm: null
  camera_move: ""
  axis_and_screen_direction: ""
character_blocking: []
prop_owner_and_state: []
key_action_start_end: ""
physics_and_contact: ""
light_wind_water_direction: ""
sound:
  dialogue: []
  dialogue_source_plan: "SYNC|ADR|BOTH|NO_DIALOGUE"
  foley_and_ambience: []
  music_cues: []
  lip_sync_markers: []
  project_sample_rate_hz: 48000
  project_bit_depth: 24
  delivery_channels: "STEREO|5.1"
  delivery_loudness_profile: "BROADCAST_-23_LUFS|STREAMING_-14_LUFS"
editing:
  intended_duration_s: null
  transition_to_next: ""
  no_repeated_filler: true
qc:
  preflight: PENDING
  identity_props: PENDING
  narrative: PENDING
  sound_sync: PENDING
  color_pipeline: PENDING
  final_user_approval: PENDING
```

不可编造实际采集参数。无法从文件元数据确认的字段用 `null`/`PENDING`，不得替代为目标值。每个神仙另引用批准的六视图与对应道具母图，并遵守非生成式锁层规则。

## IV. 影像/声音生产与成片检查

- **影像采集/合成检查**：用 ffprobe 或同等媒体分析检查实际画幅、帧率、像素格式、位深、色彩标记、编码；对RAW/Log及ACES的 IDT/工作色彩空间/ODT/输出版本保留链路记录。真实10bit 4:2:2不能由8bit素材转码伪造。
- **镜头一致性**：八仙脸部/发型/衣袍/道具/骑乘/六视图、镜头轴线、接地、双手双足、眼神线、法宝持握/拔剑归鞘、风浪方向、雨雪/光照持续一致。
- **对白声音**：逐场写人物对白、录音来源、ADR需求、口型/气息停顿、声画同步点；先编辑对白，再加现场环境/拟音/音乐，独立stem可追溯。无对白镜头写 `NO_DIALOGUE`，不要强行配音凑戏。
- **混音及响度**：留存48kHz/24bit制作工程与导出规格，立体声/5.1分别混音；交付前实际量测综合响度（LUFS）、True Peak、声道映射、相位、对白可懂度和同步偏差。不同发行版分别提交，不能混淆两个响度目标。
- **剪辑与重复**：重复镜头必须有明确叙事目的（回忆、信息再解释、对照等）及版本记录；若仅为补足时长，按P0整改。
- **片头片尾**：片头项目/作品名合法准确；片尾包含角色及制作职务、实际参与者与工具/服务必要鸣谢、音乐/素材授权与版权声明，不得虚构真人或制作资历。
- **终审**：字幕/片头/片尾/演职员表、无穿帮、无重复凑时长、全部声音对白同步、发行编码和色彩无误、交付包/报告完整。P0>0不能定版。

## V. 四层门禁（脚本→素材→剪辑→交付）

- `SCRIPT_GATE`：结构/角色欲望/阻力/代价/场次戏剧功能/对白计划/镜头技术目标缺一则 `BLOCKED`。此门禁目前为**人工审核规范**，未实现自动脚本语义评分器。
- `ASSET_GATE`：严格使用 `film_audit/baxian_group_gate.py` 对批准原图、层和遮罩执行源文件/哈希/人物法宝归属检查；不能把文字提示词称为真正视觉锁定。
- `EDIT_GATE`：镜头时序、声画同步、音轨采样率、混音版本、重复段落、身份连续性由媒体检查加人工逐镜审核共同验收。
- `MASTER_GATE`：校验母版参数与颜色输出、响度报告、视觉质量/片头片尾/演职员表、用户最终批准。**任何生产流程自动通过都不能代替用户签核。**

## VI. 严重问题分类（新增）

- **P0**：核心叙事动机和代价缺失致使剧情不成立；角色/法宝乱变；严重肢体与空间穿帮；对话声画明显不同步；使用重复镜头凑片长；片头/片尾/演职员表缺失；技术母版未达到合同约定仍伪报合格。
- **P1**：待确定发行版细分参数；独立声道声像偏移；局部调色风格不一致；次要环境/拟音衔接瑕疵；脚本戏剧功能薄弱。
- **P2**：可修的小颗粒、场景装饰、微小字幕排版与局部混音修饰。P2也应在最终交付前按约定关闭。

## VII. 与现有文件的关系

- 文学剧本：`docs/baxian-canghaizhengdao-screenplay-v1.md`
- 影视生产总控：`docs/baxian-feature-production-masterplan-v2.md`
- 人物与法宝：`film_audit/baxian_character_rules.json`
- 六视图/道具/合体硬门禁：`docs/baxian-group-asset-enforcement-v3.md`
- 制作流程：`docs/baxian-cg-continuity-v1.md`

**本次只更新规则与脚本要求，未实际验证任何全片母版的4K/10bit、ACES、48kHz/24bit、LUFS或演职员表；相关状态保持 PENDING。**
