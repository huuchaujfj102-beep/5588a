# 《八仙过海·沧海证道》纯AI智能体电影脚本生成与成片验收规则 V4.0

> **人物出图最新强制规范（2026-11-07）**：统一执行 [按景别选图、每次参考图总量≤2张、模式路由、五层资产生产、七字段提示词与三道审片门禁](baxian-character-shot-reference-selection-v1.md)。每次生成必须经过SELF_CHECK（脸/发型/服装/道具/手指/光温/画幅/水印十项）→MASTER_COMPARE（与黄金样张及法宝锚图并排）→DOWNSTREAM（I2V首帧和剪辑前后镜连续性）；缺真实源图、证据或审核时必须PENDING/BLOCKED，不能用文字承诺代替真实视觉审核。

适用：电影文学剧本、AI剧情大纲、分场剧本、分镜脚本、文生图/图生视频镜头提示、声音设计、后期合成、母版交付、P0/P1验收。  
版本：2026-11-07。制作范式：**纯AI智能体生成影片；无真人实拍、现场收音、ADR、摄影机采集环节**。状态：**制作规则已制定，尚不表示现有片源或成片达标。**  
适用优先级：此规则的技术/叙事验收要求与角色法宝锁定规则并行；人物身份、六视图、道具形制、唯一归属以已有批准母图及 `film_audit/assets/baxian_group_enforcement_policy_v3.json` 和各角色最新版锁定为准，不因追求新镜头而重设计。

## I. 四项必达标准（用户批准的基准）

| 类别 | 必须纳入剧本/分镜及制作流程的标准 | 检查阶段 | 失败处理 |
|---|---|---|---|
| 影像 | AI原生图片/视频生成→已批准首帧I2V→剪辑合成→调色与母版输出；目标**≥4K交付分辨率、24fps**，优先支持10bit成片编码；可验证色彩管理流程（如ACES），交付Rec.709/DCI-P3；逐镜保留原生参数及放大/插帧记录 | G00/G05设目标；G06/G07核验真实AI输出；G08母版验收 | 不得把上采样、转码或补帧冒充模型原生4K、10bit和24fps |
| 声音 | AI人物配音/TTS或AI声音合成＋逐句口型同步＋AI拟音、环境音、配乐与分轨混音；48kHz/24bit制作工程目标，立体声或5.1成片；不同发行版本按−23 LUFS/−14 LUFS预设并实测 | G00对白与AI配音计划；G05口型标记；G07生成及混音；G08同步/响度实测 | 角色音色漂移、对白不同步、声音分轨缺失或响度不符禁止正式交付 |
| 叙事 | 完整三幕或**等效结构**；核心主角/主角群有明确**欲望 → 阻力 → 选择 → 代价 → 不可逆改变**；每个主要场次推动因果，不允许仅以漂亮镜头堆砌剧情 | G00大纲及分场；G05分镜；G07剪辑剧本；G08最终观片 | 结构不成立、冲突无升级、代价无后果、主要镜头没有戏剧功能时退回改稿 |
| 完成度 | **全片无已知穿帮、无音画不同步、无重复镜头凑时长**；具备**片头、片尾、演职员表**，版权/素材出处有据可查 | G07逐段、G08母版全片复看 | 任意P0未清零或缺片头片尾/演职员表，正式版不放行 |

**AI技术口径说明**：本项目**没有实拍采集流程**。摄像机RAW/Log/4:2:2采集不适用；4K、10bit、24fps是交付目标而非自动具备的AI原生能力。镜头记录`source_type=AI_GENERATED|AI_EDITED|COMPOSITE|AI_AUDIO`、真实生成分辨率/位深/帧率、上采样/补帧方法与调色交付记录，不得虚称原生规格。

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
  native_bit_depth: null
  output_target_bit_depth: 10
  native_frame_rate: null
  upscale_or_interpolation_method: null
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
  dialogue_generation_plan: "AI_VOICE|NO_DIALOGUE"
  voice_id: null
  voice_model_version: null
  lip_sync_method: null
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

不可编造AI模型原生输出参数。无法从文件元数据确认的字段用 `null`/`PENDING`，不得替代为目标值。每个神仙另引用批准的六视图与对应道具母图，并遵守非生成式锁层规则。

## IV. 影像/声音生产与成片检查

- **AI影像生成/合成检查**：用ffprobe等检查实际画幅、帧率、像素格式、位深、色彩标签和编码；留存AI生成任务ID、原始素材SHA、放大/插帧/调色链路和实际输出；10bit交付编码不等于AI原生10bit。
- **镜头一致性**：八仙脸部/发型/衣袍/道具/骑乘/六视图、镜头轴线、接地、双手双足、眼神线、法宝持握/拔剑归鞘、风浪方向、雨雪/光照持续一致。
- **AI对白与声效**：按角色锁定AI音色ID及模型版本，逐句生成AI对白、同步口型、检查气息和停顿；独立合成AI拟音、环境声、配乐与分轨。无对白镜头填`NO_DIALOGUE`，禁止单一重复配音填满全片。
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

**本次只更新规则与脚本要求，未实际验证任何全片母版的4K/10bit、色彩管理、48kHz/24bit、LUFS或演职员表；相关状态保持 PENDING。**
