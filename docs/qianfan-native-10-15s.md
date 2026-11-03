# 百度千帆原生 10/15 秒图生视频（2026-11-03）

## 核实模型时长
2026-10-22 更新的千帆多模态 V 系列 API 文档：VQ2-Turbo/Pro 原生 1-10 秒；VQ3-Turbo/Pro 和 VQ4 原生 1-16 秒。接口：`POST /beta/video/generations/qianfan-video`。MuseSteamer Air 是独立接口，已验证5秒，但不可将其当成15秒模型。

官方资料：https://cloud.baidu.com/doc/qianfan-multimodal/s/fmn5nsoey

## 已开发
- `oneflow.qianfan_i2v` 在同一条任务中支持 5、10、15 秒，保留 `--confirm-paid`、`task_id` 存档、无盲目重发；15秒优先 VQ3-Turbo。
- Core 默认会把长视频拆分成多个5秒分镜，本模块新增单模型原生长视频模式，一次任务仅一镜头，防止只生成第一镜头却声称完整15秒。
- GitHub Actions 增加秒数与模型选项，目标竖屏 9:16，原始比例仍取决于首帧及模型返回值。若原始生成仍为1:1，不能称为原生竖屏。
- 新增无网络单元测试，覆盖10/15秒及模型限制。

## 真实验收条件
当前尚未向百度提交新的收费请求。真实测试要求：可用模型权限、价格/账单确认、用户手动勾选一次付费授权；完成后检查 MP4 时长、分辨率、车轮运动、车身一致性、音轨、审核报告。10秒与15秒的官方计费可能不同，不能沿用MuseSteamer的5秒 ¥1标价。

## 两平台发布
- 抖音：已有官方上传/创建适配，但须获批 `video.create.bind`、账号 OAuth、人工审核和平台成功回执。官方：https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/video-create
- 视频号：截至本次检索，尚未核实对普通第三方开发者开放的通用“视频号短视频发布”官方 API。腾讯云 `WeChatMiniProgramPublish` 是发布到**微信小程序**，不能拿来冒充视频号发布。应先使用官方许可的手动交接，或获取真实的官方服务商/API文档与授权再实现；不接入未经证实的微信个人号控制/抓包 API。

本版本仅升级百度原生长时视频开发与离线测试，不会自动发布、不会生成第二次收费请求。
