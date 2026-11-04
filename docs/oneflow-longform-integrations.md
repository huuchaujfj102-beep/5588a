# 星火3.0｜全球长片插件接入 V0.1（代码已提交，运行须另行授权）
> 2026-11-04 · 独立Draft PR · 尚未合并main；未执行付费生成、自动发布或下载大型模型权重。

## 当前实际接入状态
| 组件 | 实施结果 | 余项 |
|---|---|---|
| Story2Video式章节规划 | 新增oneflow/longform.py，SQLite Episode→Scene→Shot；420秒7场约50镜，1200秒4章16场约144镜，镜头ID稳定 | 未复制上游许可证不明的源代码；后续Postgres迁移与真人剧情素材库 |
| Shotstack | 官方Edit API JSON导出及带预算和幂等锁的POST适配 | 独立Shotstack密钥、正式授权、云端实测、最终文件回存 |
| JSON2Video | v2 Movie JSON导出、POST接入、保存project ID和禁止重复收费请求 | 独立JSON2Video密钥、账户限额与真实账单确认 |
| SVI | 上游官方Shell脚本的受控CLI描述 | GPU/已审源码/权重/输入映射与云端运行 |
| LongCat-Video | 上游torchrun命令的受控CLI描述 | GPU/13.6B权重/输出回填 |
| Rhubarb | 中文音频 phonetic recognizer 和JSON mouth cues输出命令 | 安装官方Binary并实测中文口型 |
| 资产数据库 | SQLite episode/scene/shot/asset/model_jobs/render_jobs | 云对象存储、权限隔离、账本与Webhook |
| 旧OneFlow 10秒流程 | 未修改core.py、老工作流、发布门禁 | 保持现有测试 |

## 一、离线生成7分钟分镜数据库（零模型费用）
在Python3.11+，5588a根目录执行：

    python -m oneflow.longform plan \
      --title '雨夜借灯' \
      --brief '原创国风悬疑故事，人物一致，雨夜驿站，先声音后动画，七分钟' \
      --seconds 420 --ratio '16:9' \
      --db private-inputs/longform.sqlite \
      --out private-inputs/episode-plan.json

输出7场约50镜的离线占位分镜。不是AI写好的完整剧本，也不产出MP4。先批准故事与角色圣经。

## 二、素材与权属绑定
每个镜头需要可证明使用权的HTTPS媒体源。本工具只验证URL语法；并不会主动从互联网下载素材，也不能验证版权证明本身。

    python -m oneflow.longform bind \
      --db private-inputs/longform.sqlite \
      --shot-id EP-实际ID-C01-S01-H001 --kind image \
      --url https://approved.example.com/scene01.png \
      --rights-ref CONTRACT-001

只有全部镜头绑定后才允许输出正式云渲染请求体。部署端还必须阻断DNS重绑定/私网地址，不给云端供应商提供内网资源。

## 三、离线生成第三方API的正式请求JSON

    python -m oneflow.longform export \
      --db private-inputs/longform.sqlite \
      --episode-id EP-实际ID --provider shotstack \
      --out private-inputs/shotstack-request.json

    python -m oneflow.longform export \
      --db private-inputs/longform.sqlite \
      --episode-id EP-实际ID --provider json2video \
      --out private-inputs/json2video-request.json

Shotstack采用timeline.tracks.clips；JSON2Video采用scenes.elements。合成总时长严格等于420秒，离线生成JSON不扣费。

## 四、真正提交到云端（可能计费，严格需授权）
分别在可信私有环境设置SHOTSTACK_API_KEY或JSON2VIDEO_API_KEY，**不要粘贴公开仓库、GitHub Actions输入或聊天**。

    python -m oneflow.longform_renderer \
      --db private-inputs/longform.sqlite \
      --episode-id EP-实际ID \
      --provider json2video \
      --quote-rmb 2 --budget-cap-rmb 20 --confirm-paid

这里的quote-rmb必须由真人按账户实时报价填写，不能视为服务商自动限额。无密钥、无确认、不满足预算、素材未经登记、已提交过同一任务会拒绝。
- Shotstack POST目标固定为 https://api.shotstack.io/edit/stage/render，Stage可能水印或收费，以真实计划为准。
- JSON2Video POST目标为 https://api.json2video.com/v2/movies，返回project ID；结果状态尚未自动轮询。
- 本地幂等锁防止重复提交。网络请求出现不确定结果时不得盲目再次POST。
- 成功先记录SUBMITTED_NOT_PUBLISHED。新增了**只读任务状态查询**，仅在供应商返回done时记录RENDERED_AWAITING_QA，绝不自动标记发布：

    python -m oneflow.longform_status \
      --db private-inputs/longform.sqlite \
      --job-id 本地job_id

尚未实现云端成片自动下载、回调验签及发布。即使供应商状态done，也必须取回文件并由5588a人工审查后才可放行。

## 五、SVI、LongCat、Rhubarb本地插件预检
下面只建立计划命令，缺少上游源码/权重/程序时明确阻断：

    python -m oneflow.longform_plugins --provider svi \
      --repo-dir private-inputs/upstream/Stable-Video-Infinity

    python -m oneflow.longform_plugins --provider longcat \
      --repo-dir private-inputs/upstream/LongCat-Video \
      --checkpoint-dir private-inputs/models/LongCat-Video

    python -m oneflow.longform_plugins --provider rhubarb \
      --audio private-inputs/audio/actor.wav \
      --output private-inputs/audio/actor-mouth.json

真正运行本地程序需要人工加入 --execute --license-checked --confirm-gpu-cost 并具备设备/授权/可用脚本。这里未自动clone任何第三方源码，也未下载权重、启用收费GPU。SVI脚本初始使用官方demo配置，尚不接受用户自定义镜头映射。

## 六、7分钟生产线未完成的工作
1. 人工审定完整原创剧本、角色与场景资产库，不把离线占位分镜冒充创作完成。
2. 为48–50镜补充真实媒体素材，并建立版权凭证。
3. 做Rhubarb中文口型20秒试片和真实成本测量。
4. SVI或LongCat选择一个进行30秒云GPU小样，测试连续性、真实消耗和权重许可。
5. 完整生成90秒混合动画后，先通过5588a逐镜视觉/声音/权属审核，再做420秒长片。
6. 真正接通云端回执查询、下载回存、全片质检、人工审批与官方发布授权。
7. 本PR仍保留Draft；未通过CI/人工验收和实机测试前不合并main。

## 资料
- Shotstack官方API：https://shotstack.io/docs/api/
- JSON2Video v2 API：https://json2video.com/docs/v2/reference/api-endpoints/movies-create
- SVI：https://github.com/vita-epfl/Stable-Video-Infinity
- LongCat：https://github.com/meituan-longcat/LongCat-Video
- Rhubarb：https://github.com/DanielSWolf/rhubarb-lip-sync/blob/master/README.adoc
- Story2Video：https://github.com/approximatelylinear/story2video

本仓库是公开的。API密钥、客户未公开素材、授权合同、生产SQLite数据库与私有媒体不得提交至仓库或CI artifacts。