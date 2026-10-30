# Remotion 视频合成（5588a）

这是独立的 React/Remotion 渲染模块，当前只验证 3 秒 9:16 视频合成，**不代表**角色一致性、唇形或版权审核通过。

## 本地运行

Node.js 22：

```bash
cd remotion
npm install
npm run studio
npm run compositions
npm run render
```

## GitHub 验证

PR / push 触发 `Remotion render smoke test`，输出视频与 ffprobe 元数据保存为 Actions artifact。渲染成功后如需按原有审核机制复核，可将生成的视频下载到受控环境并执行：

```bash
python -m film_audit.audit --video remotion/out/audit-demo.mp4 --srt examples/sample.srt --assets examples/assets.csv
```

不应将素材本身或凭据提交到仓库。GitHub Actions 的 smoke test 仅对静态测试片运行，不传递任何私有素材。
