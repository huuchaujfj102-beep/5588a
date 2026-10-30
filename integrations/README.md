# Free video adapters (isolated, no GPU or paid API)
This branch does not vendor or execute the full MoneyPrinterTurbo, ComfyUI or Wan 2.2 engines.
- Kinocut 1.16.4: installed in CI with FFmpeg, run `kino doctor --json`.
- MoneyPrinterTurbo MIT: local-service metadata and local-only endpoint validation, no remote requests or runtime deployment.
- ComfyUI GPL-3.0: validate API-format node workflow, prepare JSON to post to /prompt once an explicitly authorized local server is available. No requests sent.
- Wan 2.2 Apache-2.0: model registration only; no weights downloaded, no GPU provisioned.
Safety: loopback only, no secrets, no third-party API calls, no paid services.
15-second CI proof: FFmpeg produces 450 frames / 30fps / 1080x1920 H.264; this is a synthetic video and is **not** a Wan generated or MoneyPrinterTurbo-produced film.
Do not merge until Kinocut installation/doctor, offline tests, and output artifact all pass. Full end-to-end generative acceptance requires separately approved runtime and assets.
