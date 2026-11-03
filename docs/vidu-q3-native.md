# Vidu Q3 Pro pilot — 10s / 15s native video

Status: **code staged for CI and review; NO paid Vidu generation has been performed as part of this change**.

Official endpoints:
- Text-to-video: `POST https://api.vidu.com/ent/v2/text2video`
- Image-to-video: `POST https://api.vidu.com/ent/v2/img2video`
- Poll completed creations: `GET https://api.vidu.com/ent/v2/tasks/{id}/creations`
- Auth: `Authorization: Token <VIDU_API_KEY>`
- Model: `viduq3-pro` (native 10 or 15 seconds in pilot, 720p by default).

Official documentation:
https://platform.vidu.com/docs/api-reference/video-models/vidu-q3/text-to-video
https://platform.vidu.com/docs/api-reference/video-models/vidu-q3/image-to-video

## Secret

Save the **bare key value**, never the Key ID and never a `Token ` prefix, as
`VIDU_API_KEY` in GitHub repo Settings > Secrets and variables > Actions.
Never expose the secret in a screenshot, commit, workflow input, issue, or log.
The repository is currently public: prompts and generated artifacts must be
fictional/public and properly licensed; do not upload medical data or private photos.

## Trigger after PR approval and merge

GitHub Actions > **Vidu Q3 Pro 10s 15s opt-in pilot** > Run workflow.
This workflow must first be merged into the default branch to appear as
a standard manual workflow trigger.

For a text-only pilot:
- `operation=generate`, `mode=text2video`
- `brief`: your original supercar concept and motion
- `seconds=10` (test first); `resolution=720p`
- `source_image_run_id` blank
- `confirm_paid=true` **only after reviewing Vidu account credits and agreeing to one billable task**.

To reuse the same approved supercar image:
- `mode=img2video`
- `source_image_run_id=41660915365` only while its OVH artifact still exists (currently expires 2026-11-10 15:10 UTC)
- This checks the source run belongs to this repo, was a successful manual run
  on main, and has one original non-expired OVH image artifact. No public image
  link is needed.
- If you accidentally leave the mode on `text2video` with a valid image run ID, the workflow now **automatically selects** `img2video` rather than failing. With no image ID it remains text-to-video. The effective mode is logged before any charge.
- Preserve the car description in the motion prompt. Results still require
  human review for consistency.

For 15s change `seconds=15` and authorize separately. Standard Q3-Pro 720p is 20 credits/second; 15s costs about **300 credits (~US$1.50)** at official published rates. The workflow first checks Vidu's read-only credits endpoint and blocks the billable POST if the reported balance is insufficient or cannot be established. Do not launch
10s and 15s blindly in parallel. Each is independently billable.

## Recovery and safety

Every paid submission records a status JSON **before** making a POST, then
writes Vidu `task_id` as soon as it is acknowledged. A transport timeout or
missing response is **acceptance unknown**: never use Re-run jobs, nor retry
the POST until you have reconciled tasks and billing in the Vidu console.
A successful POST followed by GET/download failure can be resumed without a
new generation charge: choose `operation=resume`, enter its existing
`resume_task_id`, leave `confirm_paid=false`, and keep the same video
duration for audit.

On completion, the workflow uploads `source.mp4`, `final-draft.mp4`
(1080×1920 with softly drifting 造镜者 watermark) and
`vidu-status.json` for manual quality review. Native audio is expected.
No social-media publishing is performed. Signed Vidu result URLs are not
saved in public artifacts, and provider downloads should occur promptly
because result URLs expire.

The adapter supports offline tests and billing-gated execution only. Green
offline CI does NOT prove that the model account is enabled or that a real
video has been created.
