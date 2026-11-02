# Qianfan CLI / 千帆 CLI 安装与授权

官方指南：https://aipe-dragonboat.cdn.bcebos.com/qianfan-cli/docs/guide.md

2026-11-02：已通过只读 GitHub Actions 从官方 CDN 抓取并核对本文对应的安装命令；未执行远程指南内容。

## 适用范围

这是新版 Node.js Qianfan CLI，不是旧版 Python SDK。

环境要求：Node.js >= 16。当前公开发行说明支持 Windows 和 macOS (x64/arm64)。建议在能够长期使用的 Windows/macOS 电脑或云主机上完成授权。

GitHub Actions Windows Runner 是**临时环境**，每次作业结束即销毁，包括其安装文件、Skills 和登录状态。通过 GitHub CI 的安装验证，不能等同于 CLI 已安装在用户 Android 手机、个人电脑、ChatGPT 会话环境或长期服务器。

## 官方安装命令（Windows PowerShell / macOS 终端）

    npm config set registry https://registry.npmjs.org/
    npm i @baiducloud/qianfan-cli@latest -g
    qianfan --version

之后在**同一持久设备**完成账户登录：

    qianfan auth login

用户本人在系统浏览器完成授权后：

    qianfan auth status
    qianfan +connect --dry-run
    qianfan +connect
    qianfan +connect list

若在非交互环境，先检查预演结果，再以：

    qianfan +connect --yes

确认执行。不要在公开仓库、Issue、PR、Actions 日志或聊天中输入访问令牌、私人授权码、真实 API Key 或 OAuth 回调令牌。

CLI 的 Skills 安装到它能发现的本地 Agent 目录。没有 Claude Code / Comate 等受支持 Agent 时，可能只安装到本机的 Qianfan Skills 目录，而没有接入相应第三方 Agent。

## 免费只读核查

    qianfan models list --format json
    qianfan doctor

部分命令会要求登录或存在套餐。未经单独确认费用，不运行可能收费的文本推理，例如 qianfan +chat。

## GitHub 5588a 的可重复安装验证

本 PR 提供 .github/workflows/qianfan-cli-install-smoke.yml：

- 在 Windows Runner 使用 Node.js 22；
- 执行 npm 全局安装并检查版本和帮助；
- 以 qianfan auth status 检查登录状态，但不启动公开日志 OAuth 流程；
- 安全预演 qianfan +connect --dry-run；
- 在临时 Runner 上执行 qianfan +connect --yes，并检查 SKILL.md 实际安装数量；
- **不使用任何 API Key、不调用收费模型**。

并提供只读指南下载检查 .github/workflows/qianfan-cli-guide-inspect.yml。

必须强调：GitHub 安装属于每次运行可重复的云端 CI 安装，**不是持久部署**。

## 与 OneFlow 文生图、图生视频关系

新版 CLI 用于模型发现、文本聊天、套餐/用量管理、健康诊断和 Agent Skills。不能仅凭 CLI 安装就确认文生图 o1-base / 图生视频 VQ 模型的权限或解决以前真实图片 POST 的报错。现有 oneflow/qianfan_media.py 独立调用百度多模态 API，权限/额度及请求参数仍需单独验证。

## 安全注意

- 不要公开复制密钥、OAuth token、用户登录状态文件或带私有信息的图片视频。
- 本仓库是 PUBLIC，所有 Actions 日志都可能公开。
- 以前配置的 GitHub Secret QIANFAN_API_KEY 不代表浏览器 OAuth 已完成。
- 若需要持续自动化，必须有用户授权的持久 Windows/macOS 机器或适配的平台；临时 GitHub Actions 不能储存登录会话。

参考：https://www.npmjs.com/package/@baiducloud/qianfan-cli
