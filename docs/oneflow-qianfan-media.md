# Qianfan image → image-to-video integration (2026-11)

## Status

This PR provides a standalone provider task client and **mock-only tests**.
A one-sentence-to-video OneFlow renderer adapter is **not yet enabled**:
the current OneFlow media providers still expect a locally verified rendered file.
No paid API request has been made during this PR.

Official API references:
- [Create image](https://cloud.baidu.com/doc/qianfan-multimodal/s/8mmt3c9jr)
- [Query image](https://cloud.baidu.com/doc/qianfan-multimodal/s/gmmt3c9im)
- [Create VQ image-to-video](https://cloud.baidu.com/doc/qianfan-multimodal/s/fmn5nsoey)
- [Query VQ video](https://cloud.baidu.com/doc/qianfan-multimodal/s/1mn5nsohk)

Note: The October 2026 VQ API response format differs from the image API:
image POST returns data.task_id and data.task_status; video POST returns
top-level task_id and status. Video GET returns status and creations[].url.

## Safety / expected costs

The repository is **PUBLIC**. Never use private prompts, private pictures,
confidential work, hospital/patient information or personal content in GitHub
Actions inputs and artifacts. Never print or commit QIANFAN_API_KEY.

Submissions are blocked unless allow_paid=True. Successful GET /v2/models
**does not** demonstrate that image or video model access is enabled.

- Image: o1-base or v3o, n=1, 1k or 2k, 16:9/9:16/1:1.
- Video: VQ2-Turbo/Pro, VQ3-Turbo/Pro, VQ4, explicit first-frame public HTTPS URL,
  5 seconds at 720p for the first controlled test; no auto-selected music or
  prompt recommendation. Model pricing and available credits must be checked
  before proceeding. A task can incur charges even if it fails later.
- No automatic retry/submission when waiting. GET polling has attempt limits.
- Downloading images or videos, continuity audit, final MP4 synthesis and
  publishing require additional safe connector work, not yet represented as done.

## Zero-cost offline verification

Run:
  python -m unittest discover -s tests -p 'test_qianfan_media.py' -v

After merging to main, the GitHub Actions tab will also show:
  Qianfan image and video manual test (explicit billing opt-in)

With defaults operation=dry-run and confirm_paid=false, it runs **only
offline tests** and cannot submit a model request.

## Future *optional* one-image and one-video tests

Do not run a paid operation unless the account's model entitlement, price,
credits and public-test content are understood and approved.

1. In GitHub Actions, choose image-1k and check confirm_paid. This creates
   exactly one public synthetic supercar image task using o1-base.
2. The job checks its status with bounded GET polling, places public sample
   metadata/returned image URL into a one-day artifact. It does not automatically
   create a video or download any media.
3. Inspect image proportions, body, wheels and headlight geometry. Retrieve the
   result image URL while still valid and, only if public, reuse it as the video
   input URL.
4. Choose video-5s, paste the PUBLIC image URL, and check confirm_paid. This
   submits exactly one VQ2-Turbo request (5 seconds, 720p), then polls.
5. Check the generated public test video for actual forward movement, consistent
   model/body features, no jump cut back to starting position and physics.
6. Only after both tests pass: add image/video result fetching into a private
   storage area, audit and FFmpeg/watermark integration, preserving all human
   review gates before any publication.

No video generation should run automatically after an image job because this
would create an accidental second charge.
