# R6 第一章 C01-N06 / C01-N16｜连贯性镜头复核 V2（2026-11-22）

审核对象：前镜 F01-02（SHA 9bb8e8d39f865d89c9e26bb0303b6b2e9905798da4f2ac177f5171cbffa7d4a7）、后镜 F01-03（SHA fd17c5b4dfee8c8dc7a7bc1602e26a07f61fdcd4f2ab77d438d393b604dbfc2d）与 F01-04（SHA ac6f718fabf3daa7e394e9fd1c362970adf1f2ca00b27555137fc94be8d099df）。这些原始PNG已经从第一章ZIP提取并校验SHA。**本文件不代表新图已生成。**

## 用户批准的边界
2026-11-22用户对C01-N05局部原图参考及专业提示词回复“过”。登记为**N05参考裁切与提示词审核通过**，不得登记为N05新图通过或图生视频通过，因为尚未实际生成。

## C01-N06｜母子对白同轴反应｜修改为两个动作相位，不强制生成反打新图
原有“阿宁肩后看小满”的设想容易要求人物互换位置、失去阿宁握柱动作，且不利于真实原图锁定。以F01-02为摄影基准，不跨180度轴线，优先一张图生视频通过**连续同机位动作**完成对白：母亲仍在小满后上方，一手搭孩子肩部，另一手抓画面右侧门廊木柱；小满仍在画面中下方、木桌前护唯一一盏高脚莲纹铜灯。原场景为**半开放临海木屋门廊**，画面外侧可见风雨与浪，严禁写作“封闭室内”“木门缝透光”。

动作节拍建议（只是剪辑/表演设计，不是模型已生成）：母亲看向灯与孩子（0.7–1.0s）→小满目光微抬问话（1.7–2.4s）→母亲眼神下落安抚（1.0–1.6s）；每个节拍以实际音频长度微调，不能硬按固定秒数截断。保留F01-02人物原脸、发髻、服装、手势、湿发与光照，镜头微推不切反轴。

### 供实际图生视频的正向提示词
真实批准原图F01-02作为首帧及人物、道具、场景图像输入；古装真人电影，9:16，风雨临海半开放门廊，同一摄影轴线，同一两人空间站位。阿宁始终位于小满后上方，一只手轻搭小满肩，另一只手持续握住画面右侧竖木柱；小满在湿木桌前双手护住唯一高脚莲纹铜灯的火焰，不触碰火芯、不拿起灯。先由小满微抬目光向阿宁发问，再由阿宁以低头眼神与轻柔表情回应，动作微小、连续、自然；嘴唇动作与最终锁版中文对白音轨同步，音频未确认前禁止强制口型。暖色火光照亮面部、双手和莲纹铜灯，冷青灰风雨与外部海浪连续，灯焰随同一风向轻微侧伏，木柱和木桌位置固定，湿发、布料、皮肤和水体真实。摄影机沿原光轴轻微推进，保持人物、道具拓扑和真实物理接触。

### 专项负面
mother moves in front of child, mother leaves post, missing hand on shoulder, hand changes gripping post, child turns 180 degrees, child lifts lamp, duplicate lamp, different lamp pattern, enclosed indoor room, door-gap light, swapped faces, age drift, costume drift, hand interpenetration, extra fingers, broken lips, lip-sync ahead of audio, axis reversal, camera teleport, scene rebuilding, floating flame, unnatural CGI skin, text, watermark.

### 对白冲突门禁
R5三句：阿宁“手别碰火。挡住风就好。” 小满“灯灭了，他们找得到家吗？” 阿宁“先让它亮着。”
R6曾写阿宁“小满，护住灯。娘去把门顶住。”，该句若配合现有原图会暗示阿宁离开小满身后，存在连续性风险。**临时执行以R5三句为参考，不可声称对白已最终锁版**；先制作无口型表演版本，待对白版本确认后再对口型。

### 处置
N06作为独立新静帧：HOLD；优先从F01-02真实首帧生成同轴连续表演，减少人物漂移。生成接口必须验证真实图像文件传入，且后续逐帧质检通过。

## C01-N16｜越堤前一拍｜独立新帧候选
**镜头意图：**从海底封印破裂转到陆上海浪冲击，建立水体运动的方向和物理因果，不能把石门黑流直接剪成岸边另一股方向不明的浪。

### 正向
以真实批准F01-04海堤原图为必要图像参考，以F01-C01/C02真实海岸与缆绳原图为辅助环境参考。电影级9:16竖构图，沿F01-04相同的防波堤轴线、近远关系和风暴光线，保留既有木桩排列、石堤高度、右后方建筑和岸线轮廓。捕捉浪峰将触及堤顶、尚未完全越堤的物理前相位；水流从原F01-04浪来方向向堤面推进，泡沫、碎浪与雨幕连续。海堤、建筑、船只位置与原图完全一致，真实冷青灰海水与风雨摄影，禁止提前毁坏村庄、改变潮向或增加建筑。

### 负面
different seawall, different posts, new lighthouse, shifted village, reversed wave direction, wave already overtopping, repaired stonework, duplicate pier, impossible water physics, disconnected foam, background morph, wrong lens perspective, glossy CGI water, cartoon, oversharpened, watermarks, text.

### 处置
N16保留为候选。生成前必须验证模型接收真实F01-04与海岸参考图；生成后按A–L逐项审查并请用户“过”，不得自动入库。

## 审核状态
- N05：原图局部与提示词 USER_PASS；新图 NOT_GENERATED。
- N06：改为同轴图生视频优先；静帧生成 HOLD。
- N16：PROMPT_REVISED / IMAGE_REFERENCE_SUBMISSION_NOT_VERIFIED / NOT_GENERATED。
- 本轮新图：0；本轮新视频：0；已批准原图：保持不变。
