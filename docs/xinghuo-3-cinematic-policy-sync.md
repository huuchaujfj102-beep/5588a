# 星火计划 3.0｜电影级文生图 + 图生视频规则同步（2026-11-05）

## 规则来源与绑定
- 文生图正向（唯一母版）：[`cinematic-positive-global-prompt.md`](cinematic-positive-global-prompt.md)
- 文生图负面（分层 / 仅按后端能力发送）：[`cinematic-negative-suppression-prompt.md`](cinematic-negative-suppression-prompt.md)
- 图生视频时序与审片：[`cinematic-i2v-temporal-sop.md`](cinematic-i2v-temporal-sop.md)
- 既有总览 / 资产卡：[`cinematic-image-rules-v2.md`](cinematic-image-rules-v2.md)

## 星火 OneFlow 调用链
市场/选题 → 一句话 brief → 创意/故事板 → `shot_id`/角色与场景资产卡 → **正向生图规则自动前置**、负面生图规则作为独立计划字段 → 文生图 → 静态首帧质量审核和人为批准（`PASS_HUMAN`，含 SHA256）→ **七模块导演提示词自动前置时序约束** → I2V 生成 → 光影/角色/拓扑/运动抽检 → 合成+音效+造镜者品牌水印（按项目要求） → 七道质量审核 → SHA 锁定+版权/平台人工终审 → 官方授权发布 → 真实数据回流与变现核算。

### 代码对应关系
1. `oneflow/image_generation.py`：现有 GitHub 一句话/分镜生图入口已将 `GLOBAL_PREFIX` 加到正向提示词；独立 negative 目前只存计划与记录，当前 HF 代码未发送单独 negative 参数。
2. `oneflow/director.py`：七模块影片提示词由 `apply_temporal_rules` 加时序前置规则；在 `oneflow/core.py` 中为 OneFlow 任务的 `visual_prompt` 所用。
3. `oneflow/core.py`：每个新任务的 `shots[]` 另外存档 `image_prompt` / `image_negative_prompt` / `video_negative_prompt` / `source_image_review_status: REVIEW_REQUIRED`，并写入 `production_policy` 版本引用。**这些字段仅为生产计划审计信息；已有 ComfyUI 通用生产入口是否发送这些参数，必须逐个模型适配验证。**
4. `oneflow/cinematic_i2v_rules.py` 的 `source_frame_gate`：提供 `PASS_HUMAN` 准入校验函数，但尚未连接到所有真实生成适配器的强制入口。不得凭状态字段冒称首帧审核完成。
5. `oneflow/visual_review.py`：现有 VLM 只抽首尾两帧，不能认定全面通过时序闪烁/动作/版权审核；真正审核必须看片且人工签核。

### 不破坏既有能力
- 不改 Vidu/Qianfan/Wan 等实际提供商调用 URL、密钥、计费、分辨率和时长；不触发任何付费模型调用。
- 已经跑通的 **10 秒镜头**保留原有独立调用路径；长篇 **7 分钟/20 分钟**采用分镜/分场/分章组装，不因为新增质量词自动宣称支持一次长生成。
- 为成本可控保留显式付费确认、真实版权许可、模型可用性和官方平台授权检查。
- 影视画质/8K/ACES/180°快门等为有条件的目标；只有实际引擎支持且可测量时才算执行。

## 生产审核门禁（目标状态）
|阶段|必需输入|目标 PASS 条件|当前事实|
|---|---|---|---|
|T2I prompt|创意 + 锁定角色/场景|引用正/负规则版本|正向已接入两种生图入口；负面需按后端适配|
|静态首帧|真实图文件 + hash|人工图像审核通过|任务默认 REVIEW_REQUIRED，尚未统一强制拦截所有生产提供商|
|I2V prompt|已批准底图 + 七模块动作|时序正向前置 + 负面按后端能力|导演文本已接入，后端 Negative 支持待确认|
|时序质检|真实视频/镜头表|无重大帧间跳变/审片员签核|需要人工审片；自动抽帧仅咨询|
|发布|已审核 MP4 + 资产授权|授权平台回执|不得把草稿/规划当发布成功|

## 后续验收用例
- 静态人像：眨眼、发丝轻动，检查面孔/衣服/光源稳定。
- 宏大角色：黄金圣衣、武器、特效保持几何一致，禁增减部件。
- 高速超跑：轮位/喷口数量及位置锁定，先尾喷蓝焰再熄灭轮喷并飞远；不得重新从地上起飞。
- 镜头连续：室内门窗/招牌朝向、空间基准、手持道具和动作时间线一致。
- 各用例对比：完整规则 / 轻量规则 / 仅参考图，记录可用率、失败项、费用与每镜重试次数。

**合并门禁**：测试通过、人工审阅 PR、验证真实模型适配后才合并 main；不得以规则入库代替真实运行验证。
