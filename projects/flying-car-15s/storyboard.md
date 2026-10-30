# 星空飞行跑车｜15秒电影级短片制作包

## 原始参考
用户上传的白色/黑色未来跑车，荒漠星空夜景。必须使用原图作为唯一外观真值；不能变更轮圈、车头、车尾、比例、车灯、尾翼。视频使用16:9、1920x1080、30fps、450帧。

## 时间线（6个关键帧）
|关键帧|时间|动作|镜头|声音|
|---|---|---|---|---|
|KF01|0-2.0s|剪刀门缓缓完全关闭并自动锁止|低机位中近景缓推|机械闭合、电子锁滴声|
|KF02|2.0-3.5s|车门接缝细节和门锁蓝光闪烁|100mm微距、极浅景深|卡扣咔哒、低频电流|
|KF03|3.5-6.0s|汽车平稳起步，四轮正常旋转，扬起沙尘|低机位前侧跟拍|轮胎碾压碎石、电机加速|
|KF04|6.0-9.0s|四轮毂机关展开，四股喷流垂直向下点火|轮毂与车底交替特写|机械液压、喷流轰鸣|
|KF05|9.0-12.5s|四股喷流协同，整车保持水平升高2米并向前加速|从车底仰拍到宽景|沙尘冲击波、低频推进|
|KF06|12.5-15.0s|汽车缩小飞向峡谷远方，尾部红光留在星海里|后方大远景慢拉|喷流渐远、音乐收束|

## 全局强约束
- 车门仅在KF01关闭，之后所有镜头始终关闭，不可再次打开。
- 任何时候始终仅四个轮子；喷流从每个轮毂下方独立发出，严格朝地面，不能从车顶、车灯或尾翼喷出。
- 车身不得变成飞机或增加机翼；飞行时保持原车轮廓，靠四轮推进升空。
- 夜晚荒漠、真实星空、地面砂石、红色尾灯与原图一致；不要白天、城市或多人出现。
- 写实摄影、真实运动模糊、物理合理沙尘涡流、冷蓝月光加暖红尾灯；禁止塑料CG质感。
- 镜头切换保持方向、左右位置、车辆比例、轮毂结构和光影方向连续。
- 不要LOGO、字幕、水印、额外人物、额外轮子、车轮融化、车体变形、镜头穿帮。
- 输出先逐镜头图片一致性审核，再分别图生视频，最后Remotion/FFmpeg合成与ffprobe检测；不可把关键帧生成成功误报为视频完成。

## 分镜图生成任务
以下 Runway 任务已提交，实际图像完成情况以 Runway 返回为准：
- KF01 自动锁门中景: 52600a46-bd9f-47bb-9835-730383862180
- KF02 门锁特写: 5ce2e7ab-08ab-4f03-ae8c-24aaf7a1461d
- KF03 起步: b8e757f8-be3c-4df5-b2b9-6a1654a2221c
- KF04 四轮喷气: c8369cf6-13a3-49c4-a9b7-5353b5c09f30
- KF05 升空: 875f3d02-2e46-4a58-9a05-4be25238cbfc
- KF06 飞远: 51fb11e2-7b5d-42b5-b452-073fe846ccfc

## 逐镜头图生视频总提示词
Exact same car as uploaded reference, original design strictly preserved, 16:9 cinematic photoreal film. Scene evolves: both scissor doors fully close and automatically lock, an extreme macro shot of latch confirms closure; vehicle smoothly accelerates on the desert floor; four original wheel assemblies independently deploy blue-white downward ion jets; vehicle rises level into the air, atmospheric dust waves and physically coherent lighting; camera tracks behind as it flies toward distant desert canyons under a star-filled night sky. Smooth slow camera moves, crisp material details, high-budget cinematic lighting and sound design. Negative: changing car design, extra wheels, open doors after lock, additional wings, extra jet engines, floating without thrust, daytime, city, text, logos, watermark.
