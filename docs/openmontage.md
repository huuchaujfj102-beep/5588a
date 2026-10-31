# OpenMontage 接入 5588a：云端视频生产工作台

上游项目：[calesthio/OpenMontage](https://github.com/calesthio/OpenMontage)（AGPL-3.0）。
本仓库不复制或修改上游源码，仅通过固定提交 `195eab24478dc9363326aec437aefc3701635ddf` 在独立目录安装。
这样不会覆盖既有影视审核流程（`film_audit/`、`remotion/`），也避免意外把上游许可证和第三方依赖混入本仓库。

## 在 GitHub 云端安装并验证（不依赖本地电脑）

在仓库 **Actions → OpenMontage cloud install and verify → Run workflow** 运行。默认只安装免费基础依赖并执行 preflight 和 demo 清单验证，不会调用付费生成模型。
如选择 `render_demo=true`，额外尝试零 API 密钥的 Remotion 示例渲染。查看 Actions 的成功/失败结果，不要把安装完成误认为已经生成视频。

GitHub Actions 使用临时运行器，每次执行重新安装；不会产生永久在线的视频工作站。
GitHub Actions 的运行分钟数及网络下载可能受账户额度约束。

## 长期可用的云端工作环境：Codespaces

在仓库 **Code → Codespaces → Create codespace on main**。
新增的 `.devcontainer/devcontainer.json` 会自动安装 Python、Node、FFmpeg 和固定版本的 OpenMontage 到 `.local/openmontage`。
在 Codespaces 终端运行：

```bash
cd .local/openmontage
make preflight
make demo-list
# 运行无需付费密钥的示例渲染（会占用云端 CPU/时间）
make demo
```

要实际自动生成新作品，需要在 Codespaces 内使用能读取和运行仓库代码的 AI 编程助手，例如 Codex、Claude Code 等，并按上游 `AGENT_GUIDE.md` 的流程发出制作任务。
也可以把同样的安装脚本部署在自己的 Runpod 虚拟机中。云端图生视频模型仍需单独的 API 授权/额度；安装 OpenMontage 本身不会自动激活 Runway、可灵或其他供应商的付费额度。

## 与现有审核体系配合

OpenMontage：脚本/分镜/素材/剪辑/合成 → 导出视频与音轨。
5588a：用原有审核命令执行字幕、素材台账、视频技术参数等初步检查；口型、物理连续性、版权与角色一致性仍保留人工/模型复核，不会因安装 OpenMontage 自动变成已通过。

示例：`python -m film_audit.audit --video video.mp4 --srt subtitles.srt --assets assets.csv`。

## 安全与版本管理

- 上游源码保存在 `.local/`（被 `.gitignore` 排除）；不要提交视频、隐私素材、个人肖像库或 .env/API 密钥。
- CI 安装不注入任何 Runpod、视频平台或其他密钥，GitHub token 不以持久凭据存入 checkout。
- 使用固定 Git commit，升级前需复查更改和依赖。只想升级时，显式设置 `OPENMONTAGE_REF` 并重跑安装脚本；不要盲目跟踪最新主分支。
- OpenMontage 的 AGPL-3.0 授权、第三方素材使用规则及模型费用必须分别遵守。
