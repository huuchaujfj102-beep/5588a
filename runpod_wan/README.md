# Runpod → Wan2.2 TI2V-5B：安全单镜部署入口

**状态：GitHub 侧的安装脚本、T2V/I2V 单镜测试命令与离线单元测试。并没有在你的 Runpod 账户创建 Pod、支付费用、下载权重或完成 GPU 实机测试。** 当前 ChatGPT 连接仅可操作 GitHub，无法读取、创建或控制你的 Runpod GPU Pod。

## 选择这条路线的原因

Wan2.2 官方 TI2V-5B 支持 **T2V 文生视频 + I2V 图生视频**；官方示例使用至少 **24GB VRAM**（如 RTX 4090）、`--offload_model True --convert_model_dtype --t5_cpu`，生成 `704×1280` 竖屏 24fps。所需 PyTorch/驱动和模型以官方仓库当前依赖为准：

- 官方 Wan: https://github.com/Wan-Video/Wan2.2
- Runpod Pod: https://docs.runpod.io/pods
- Runpod CLI 管理: https://docs.runpod.io/runpodctl/reference/runpodctl-remove-pods

此路径先使用 **Wan 官方 Python generate.py**，不猜测 ComfyUI 节点 ID。未来验证好 ComfyUI API-format graph 才接入 OneFlow 的生产 `--live` 多模型路由。

## 1. 在 Runpod 账号中创建 GPU Pod（需要本人账户权限和收费）

Runpod 控制台 **Pods → Deploy**，选择有足够空闲显存的 GPU（先选 **RTX 4090 24GB** 或更高）和当前兼容 CUDA 的 PyTorch 模板。建议把 `/workspace` 配在足够容量的持久空间中（**130GB 或以上是保守初步建议，不是保证值**）；注意模型/依赖下载、显存/系统内存与账单。优先用单 GPU + 单镜头试跑，并配置 Runpod 的自动停止或自定监控，避免闲置扣费。可用 GPU 型号、价格、存储价格和地域库存以 Runpod 控制台实时显示为准。

安全要求：**不要公开无鉴权的 ComfyUI、Jupyter 或 SSH 端口**；不要向聊天、GitHub Issues、公开仓库提交 RUNPOD_API_KEY。此前在任何聊天或公开日志出现过的密钥应先在 Runpod 控制台撤销并重新创建。GPU 测试结束确认停止计算资源；网络持久卷/磁盘可能继续计费。

## 2. 在已经启动的 Runpod Pod 终端安装源码和权重

这些命令**必须在 Pod 终端运行**。普通 GitHub Actions 没有 GPU，不执行安装或推理。

```bash
cd /workspace
git clone https://github.com/huuchaujfj102-beep/5588a.git oneflow-5588a
cd /workspace/oneflow-5588a

# 第一次准备：下载并固定 Wan2.2 官方源码，再安装环境及 TI2V-5B 权重
WAN_DOWNLOAD=1 bash runpod_wan/bootstrap.sh
```

此脚本将 Wan 源码固定在经核对的官方提交 `1ea34ff48f87168174e12956e200b1d908b1c5ff`，并将权重下载到 `/workspace/models/Wan2.2-TI2V-5B`。依赖不匹配、磁盘不足或缺少 CUDA 时会报错，不能宣称成功；`WAN_DOWNLOAD=1` 会传输大量模型文件（可能产生存储/网络费用）。

## 3. **零 GPU 推理费用**的命令预检

```bash
python -m runpod_wan.smoke \
  --prompt-file runpod_wan/sample_snow_white_S01.txt \
  --output /workspace/oneflow-output/snow-white-S01.mp4 \
  --seconds 5 --dry-run
```

预检只验证代码、权重目录、提示词和命令构建，返回 `DRY_RUN`，不会生成媒体。

## 4. 真正生成 S01 约五秒文生视频

只有在已确认账号费用和素材后，才执行：

```bash
python -m runpod_wan.smoke \
  --prompt-file runpod_wan/sample_snow_white_S01.txt \
  --output /workspace/oneflow-output/snow-white-S01.mp4 \
  --seconds 5 --seed 128839 --confirm-gpu-spend
```

脚本在开始推理前核实 GPU 显存，并检查输出 FFprobe 参数与时长；最终输出 MP4 及同目录 JSON 审核记录。**Wan 生成的是视频画面，不会自动得到完整对白、配乐与音效**。

如果已经有审查合格的固定角色首帧，可追加 `--image /workspace/approved/S01.png --approved-image` 切换图生视频。未经批准的首帧不可通过该命令进入正式项目制作。

## 5. OneFlow 接力（仍需完成）

当 S01 实机合格后，下一步才应：
1. 在 Runpod 内部署受控本地推理 API 或导出经过测试的 ComfyUI API-format graph，验证完整视频输出后接入 OneFlow `video` 提供商；
2. 接入固定参考图资产库，维护白雪公主、王后、七位矮人的身份锁定，逐镜生成；5B 没有让每个角色完美一致的保证；
3. 接入商用可用的声音生成/音轨合成，执行 `film_audit` + 人工视觉审核 + 返修；
4. 只有完成这些才能声明“一句话 → 真实视频 → 审核”在 Runpod 云端打通。

本模块没有对 Runpod 的商业 API 发出请求，也没有在 GitHub Actions 上启动付费 GPU。审核合格、用户决定后才能发布成片。
