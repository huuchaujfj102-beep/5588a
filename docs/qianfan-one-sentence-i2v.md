# Qianfan one-sentence -> first-frame video -> OneFlow audit -> approved release

## Actual state (2026-11-02)

- Qianfan official V-series image-to-video API request, task status GET,
  resumable task ID, safe download, FFmpeg assembly, optional original
  synthetic engine sound, moving "造镜者" watermark, film audit and publication
  package are implemented in the pilot.
- Offline mock tests and synthetic FFmpeg media tests do not generate real AI
  video or prove the account has media billing enabled.
- Public GitHub Actions production inputs are visible to others. **Use only
  publicly approved fictional prompts and reference images**. For your own
  confidential racing imagery, use the local image file mode in a trusted,
  private persistent runtime, not public GitHub Actions.
- No platform OAuth publisher adapter is active. Existing OneFlow refuses to
  publish before both signed human review and official publisher connection.

### Real-money approval and price (official model list 2026-10-14)

For ONE five-second image-to-video VQ2-Turbo clip, 720p, audio=false,
the public VQ2 price table is 1.25 CNY, excluding transaction-specific
promotions and charges. For VQ3-Turbo at 720p the table shows 0.375 CNY/s,
roughly 1.875 CNY for five seconds with model audio. **Check the actual
balance and rights to use that model before opting in.** The user's earlier
Qianfan console displayed that "模型服务按量后付费尚未开通";
image/video API generation may be blocked until they activate an authorized
payment method. API Key and CLI login are different, and a successful GET
/v2/models is not proof of video generation entitlement.

https://cloud.baidu.com/doc/qianfan-multimodal/s/nmo74mg17
https://cloud.baidu.com/doc/qianfan-multimodal/s/fmn5nsoey
https://cloud.baidu.com/doc/qianfan-multimodal/s/1mn5nsohk

## Workflow in private/local environment

Requires Python 3.11+, FFmpeg and FFprobe, Noto CJK fonts (unless using
--no-watermark), the QIANFAN_API_KEY environment variable, and an existing
reference JPG/PNG/WEBP file for the locked supercar.

1. FREE plan (does not call Qianfan):

    python -m oneflow.qianfan_i2v run \
      --brief "银灰色超跑点火启动，轮胎转动，瞬间疾驰，绝不改变原车外观" \
      --first-frame-file /private/assets/approved-car.png \
      --seconds 5 --ratio 16:9 --model VQ2-Turbo \
      --platform douyin

2. When billing is enabled, prices verified and the user explicitly approves
   exactly one paid generation task, run WITH --confirm-paid. This is a
   **new job**; it does not submit a job created by planning above:

    python -m oneflow.qianfan_i2v run \
      --brief "银灰色超跑点火启动，轮胎转动，瞬间疾驰，绝不改变原车外观" \
      --first-frame-file /private/assets/approved-car.png \
      --seconds 5 --ratio 16:9 --model VQ2-Turbo \
      --sound synthetic --platform douyin \
      --confirm-paid

3. If it prints VIDEO_PENDING / fails after task acceptance, copy the
   existing job path and run **resume** (GET only, no additional POST):

    python -m oneflow.qianfan_i2v resume --job /private/oneflow-jobs/film-xxxx

   A failed or uncertain POST has no confirmed task_id and must NEVER be
   automatically retried or charged again. Inspect Qianfan console first.

4. After successful download, get:
   - final-draft.mp4: normalized video with gently drifting 造镜者 overlay.
   - qc.json: technical audit, not visual or copyright approval.
   - manifest.json: model provenance, job status, task ID.
   - release-package/douyin.json: draft metadata, **not published**.
   - Original synthesized engine audio is explicitly tagged as synthetic;
     no false claim of real engine recordings is made.

5. Personally view the video and confirm vehicle geometry, true FORWARD
   acceleration, frame continuity, no new wheels or redesign, sound and
   licenses. Only after approval:

    python -m oneflow approve --job /private/oneflow-jobs/film-xxxx \
       --reviewer "制片人" --visual-attested --rights-attested

6. **Real Douyin release** needs an approved Douyin developer application,
   video.create.bind scope and account OAuth token (or another permitted
   publisher). OneFlow currently supports an independent trusted publisher
   bridge, not direct Douyin OAuth or clickless posting. Once this separate
   publisher service is actually connected, publication can be requested with
   explicit consent:

    python -m oneflow publish --job /private/oneflow-jobs/film-xxxx \
       --platform douyin --config /private/oneflow-config.json --consent

   Without PUBLISHER_URL/PUBLISHER_TOKEN and necessary real platform
   privileges, this deliberately fails closed; it must never report
   "published" or invent a platform video ID.

   Douyin official developer docs:
   https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/video-management/douyin/create-video/video-create

## In GitHub Actions from Android

After merging this PR, navigate to Actions > "Qianfan One-Sentence I2V ->
MP4 -> Audit (opt-in)".

- By default, confirm_paid=false. Running workflow builds just a 5-second
  PLAN and executes mock media tests. **No Baidu generation request**.
- To generate one REAL 5-second clip, enter only a publicly approved car
  first-frame URL accessible without login, use one public brief, choose
  VQ2-Turbo, and explicitly check confirm_paid after verifying model price
  and billing. Repo is PUBLIC: generated output artifact is public-facing,
  retained for one day. No private input or sensitive media allowed.
- Video may need more time than the Action job. The task ID is stored BEFORE
  polling; use the existing ID to resume if pending. Do not click Run again
  with a paid selection to "retry", or that creates a second charged task.

## Correct limits of this MVP

- One **single 3-5s shot** only. No guaranteed 13/30/35s cinematic consistency.
  The next step can stitch reviewed shots with the same locked asset, but
  that will require multiple charged model requests and individual QC.
- 720p VQ model output is normalized to the OneFlow 1080p target by
  FFmpeg scaling; this is **not true native 1080p**.
- VQ2-Turbo model audio=false is followed by ORIGINAL synthetic engine
  swell. For model-generated original audio choose VQ3-Turbo + embedded
  mode, subject to actual account entitlement and cost. No narration.
- Physical movement prompts reduce but do not eliminate the risk of the car
  standing still, drifting identity, teleportation or physics errors.
  Human review remains mandatory before posting.
- The API Key can authenticate to Qianfan without an interactive CLI OAuth
  login. The optional Qianfan CLI OAuth on a persistent host is separate.

## How to extend

1. First verify one public 5-second reference frame and actual paid response.
2. Build private first-frame asset storage, persistent task history and
   downloadable media retention, not GitHub public artifacts.
3. Connect a real authorized platform publisher (Douyin or YouTube), then
   integrate approval release, publishing and metrics.
4. Extend to 13s / multiple shots, each with reused approved reference and
   visual identity/physics audit. Require separate user spending limits.
