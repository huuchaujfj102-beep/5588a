# 《八仙·大显神通》R6｜20章逐章制作与验收规则 V1.0

生效日期：2026-11-22。适用20章40段全片。规则写入不代表实际生成或验收。

## 逐章强制流水线

1. 剧本核对：逐章核对R6完整剧本、前章结尾与后章开头、人物动机、对白、动作因果、情绪和地理轴线。不得把已有图片串联视作剧情完整。

2. 分镜规划：按动作意图而非固定秒数拆镜；逐镜确定时长、景别、首中尾帧、动作节拍、声音桥和跨章接点。镜头数不等于新增图片数。

3. 原始资产审计：打开实际已批准PNG，核验SHA256、原生像素、人物五官服饰、法器道具、场景地形、机位、风雨潮向和时序。原图只读，不覆盖。

4. 逐镜缺口：每镜标记REUSE_ORIGINAL、CROP_SAME_SOURCE、I2V_ONLY、NEW_KEYFRAME_REQUIRED或HOLD_REFERENCE；说明新增图承担的独立叙事信息，避免重复生图。

5. 参考图真实绑定：新图生成时必须实际输入批准母图像素，保存文件ID、SHA、模型请求与输入证据。文字提示‘参考母图’不算绑定；无证据标记BLOCKED_REFERENCE_UNBOUND。

6. 静帧逐张生成与验收：按小批次逐张核对A-L（身份人数、剧情顺序、道具归属、接触承重、视线轴线、光影环境、质感、时序物理、画幅像素、原生参数、参考绑定、邻镜连续性）。失败图隔离整改，用户明确‘过’只记录导演静帧认可，不替代技术通过。

7. 图生视频：技术和导演静帧双通过后，按动作完整性、首尾帧、口音声线、口型、声画同步、风雨潮向、物理与声桥生成；实际视频逐段审查。未生成不得标VIDEO_PASS。

8. 整章验收：检查叙事完整、片长节奏、角色弧光、道具连续、场景地理、声音、动态接缝和下一章起点；阻断项清零、视频实际通过、导演确认后才可CHAPTER_LOCKED。

9. 下一章准入：第N章未CHAPTER_LOCKED不得宣称第N+1章正式制作完成；可提前盘点跨章母图与衔接但不可跳过验收。继承地点、天气、潮位、浪向、人物站位衣装伤势和道具状态。

10. 可追溯归档：每章独立保存剧本版本、镜头表、图片哈希、真实参考输入日志、生成参数、技术审核、导演审批、成片与跨章接点；GitHub工作分支，原图不覆盖。

## 状态门禁

SCRIPT_CHECKED → SHOT_LEDGER_READY → ASSETS_AUDITED → GAP_LIST_LOCKED → REFERENCE_BOUND → STILLS_TECH_PASS → STILLS_DIRECTOR_APPROVED → I2V_RENDERED → VIDEO_QC_PASS → CHAPTER_LOCKED → NEXT_CHAPTER。任一项失败退回整改，不越级。

## 必填台账字段

chapter_id, scene_id, shot_id, story_beat, dialogue, voice_accent, timing_seconds, source_file_id, source_sha256, character_master, prop_master, scene_master, reference_actually_sent, model_request_id, output_sha256, native_resolution, frame_role, action_phase, previous_end, next_start, review_A_L, technical_status, director_status, i2v_status, chapter_gate。未知填UNKNOWN。

## 第一章现状

第一章49镜为制作规划，不是49张新图已生成。原始批准5张，同源裁切2张获导演认可；N16原海堤不一致暂缓。5项缺口执行包V2属于准备材料，尚未完成实际参考绑定与全部新帧。第一章未CHAPTER_LOCKED，不得宣称整章连续成片已通过。

## 全片质量红线

不为凑100分钟机械拉长镜头，不为凑约1320张预算重复生图。严格锁定八仙身份法器、四王与龙族、沧汐守海印、阿宁小满与唯一铜灯。9:16目标分辨率和模型实际原生像素分别记录。