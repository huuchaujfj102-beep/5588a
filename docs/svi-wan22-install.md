# Stable Video Infinity 2.0 / Wan 2.2 安装说明（星火3.0）

2026-11-04。**这是SVI优先安装的独立草稿PR**：不改变5588a原先10秒模型、Wan2.2 TI2V-5B和main。源码安装与GPU部署必须严格区分。

## 官方版本
- SVI代码：https://github.com/vita-epfl/Stable-Video-Infinity ，使用 svi_wan22 分支。
- 固定提交：bab066229ea530a09587bed52c41ed6089bd509f。安装脚本校验分支版本、Git远端、MIT代码许可证及推理入口；上游更改后绝不自动跟随。
- 官方Python3.10、PyTorch 2.7.1、torchvision0.22.1、torchaudio2.7.1、CUDA12.8、flash-attn2.8.0.post2；需可信NVIDIA GPU和nvcc。SVI Wan2.2底座是Wan-AI/Wan2.2-I2V-A14B，不等于原TI2V-5B。
- 安装LoRA两份：SVI_Wan2.2-I2V-A14B_high_noise_lora_v2.0.safetensors 和 SVI_Wan2.2-I2V-A14B_low_noise_lora_v2.0.safetensors。
- README不保证24GB显存足够运行A14B。较高显存机型（如A100 80GB）可作为首测选择，仍须实际验收。
- SVI仓库MIT仅是源码许可证；LoRA权重、Wan底座、底图、输出商用范围分别审核。

## 一、源码级安装：GitHub Actions CPU自动验证
CI工作流：.github/workflows/svi-wan22-install.yml
- Python3.10 + bash安全测试
- Git克隆官方固定SHA，独立临时安装目录
- 编辑安装源代码（pip --no-deps --no-build-isolation -e），不安装torch大模型依赖
- 核查Python包元数据 diffsynth==2.0.0
- 此安装只存在于**临时GitHub CPU runner**；即使CI success也不意味着用户Runpod Pod已安装。

## 二、真实Runpod Pod安装（必须具备GPU授权）
在你已经启动并允许计费的私有Runpod Pod中，准备git、Python3.10、CUDA驱动/编译器、足够磁盘。

拉取此PR代码：
    git clone --branch feat/svi-wan22-install-20261104 https://github.com/huuchaujfj102-beep/5588a.git /workspace/5588a-svi-install
    cd /workspace/5588a-svi-install

第一步，安装、锁定SVI官方源码：
    bash runpod_svi/install.sh source

第二步，安装独立GPU Python环境（**只有你明确允许GPU计费后**）：
    SVI_APPROVE_GPU_BILLING=1 bash runpod_svi/install.sh runtime

第三步，下载基础A14B权重及两份SVI LoRA（很大，只在许可与费用均审核后）：
    SVI_APPROVE_GPU_BILLING=1 SVI_APPROVE_DOWNLOAD=1 SVI_MODEL_LICENSE_CHECKED=1 bash runpod_svi/install.sh weights

第四步，只读核验：
    python runpod_svi/preflight.py

目录分离：SVI源码/workspace/Stable-Video-Infinity-svi_wan22，独立venv/workspace/venvs/svi-wan22；不覆盖原Wan2.2目录。权重下载前至少180GiB可用存储。GPU Pod开机可能持续计费，安装后自行停机/查看账单；安装脚本不创建或停止Pod。

## 三、GitHub手工GPU入口
如果此独立PR经过CI和审核并合并到main，Actions会提供 Stable Video Infinity Wan2.2 source install and GPU opt-in 的手工启动项。必须勾选approve_gpu_billing；下载模型还需install_weights及model_licenses_checked。该job使用你原Wan2.2工作流的self-hosted runpod-wan22标签，以及runpod-paid-gpu Environment。须亲自在GitHub Settings > Environments配置Required reviewers，否则仅声明environment并不能产生人工审批界面。
任何时候都不要在公开仓库、日志、工作流输入或聊天粘贴HF_TOKEN或Runpod密钥。HF_TOKEN如需使用，放在可信的机密存储中。

## 四、验证目标和完成定义
1. 源码验证：CI在Python3.10环境安装upstream editable，并核验metadata和commit；**这一阶段没有模型权重和视频生成**。
2. GPU环境：Pod中torch.cuda.is_available()为真，flash-attn安装成功，pyproject依赖能用。
3. 模型：官方Wan2.2 I2V-A14B与高低LoRA存在、实际许可审核完成。
4. 真实样片：以原创国风角色参考帧，使用官方inference_svi_2.0.py先做2个81帧片段（15fps，合计约10秒）与30秒镜头试验，人工检查人设、视频长度、连续性及GPU费用。
5. 长片：经测试后，SVI仅负责故事关键长动态镜，分场剧情、配音、口型和7分钟总合成仍交给5588a长片调度系统。

目前PR未自动调用GPU或下载权重，未生成10秒/7分钟MP4。用户授权前不部署付费模型。源码安装失败需查看Actions日志，不允许凭文件存在宣称成功。
