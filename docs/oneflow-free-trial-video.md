# OneFlow V2.3 · free/trial video-provider gate (Nodaro)

**State as of 2026-11-01: adapter + offline contract checks prepared in a review branch; no Nodaro account or API token has been connected, and no video-generation calls have been made. This does NOT mean 14 seconds are rendered.**

## Why Nodaro first

Official source: https://nodaro.ai/docs/get-started/free-credits

A new Nodaro Cloud account normally starts with a one-time **1,500 credit grant**. Before making any purchase, eligible video engines permit **up to 4 seconds per clip, at the minimum resolution**, with a provider watermark. In particular, the documented default Seedance 2 Fast path uses **480p**. No trial account or credit balance is assumed for this user. The model's current quote must be verified from the account, not guessed.

Official API docs:
- https://nodaro.ai/docs/developers/api/nodes
- https://nodaro.ai/docs/developers/api/credits
- https://nodaro.ai/docs/developers/api/jobs
- https://nodaro.ai/docs/developers/api/uploads
- https://nodaro.ai/docs/developers/api/authentication

The connected ChatGPT Plugin Directory did not expose a Nodaro plugin in the current search. Nodaro's optional MCP integration has its own OAuth flow at https://mcp.nodaro.ai/mcp; **it is not installed or connected just because this adapter is present**.

## Specific job: 1000023067.mp4 continuation

The attached source film was analyzed separately: **13.75 seconds, 24fps, 4:3**. Obtain and manually inspect the **true final image** of the source clip, keeping its original aspect and frame. Keep that reference media private; never commit the media or credentials to this public repository.

The storyboard allocates four segments **4+4+4+2 = 14 seconds**:
1. Emerald bio-neural power-up, exact front three-quarter angle (4s).
2. Physically plausible wet-stone tire launch (4s).
3. Same identity, lakeside chase, restrained jade photon trail (4s).
4. Elevated three-quarter sunset departure (2s).

The previous clip and any new material may only be joined after visually confirming that the first frame of the generated scene matches the actual source end frame and the car, wheels, road geometry, reflections and lighting have not changed. Require human quality review; do not upload anything automatically to social platforms.

## Offline dry run – costs 0 credits

```bash
python -m unittest discover -s tests -p test_nodaro_trial.py -v
python -m oneflow.nodaro_trial > nodaro-14s-plan.json
```

GitHub Actions workflow: `.github/workflows/oneflow-free-trial-video.yml`. It creates a **PLAN-NOT-RENDERED** artifact, not a video. It never uses secrets or starts a chargeable API task.

## Optional authenticated 4-clip generation (NOT yet verified live)

1. Register or sign in to Nodaro and check actual granted credits and licensing conditions.
2. Create a personal API token through Nodaro Settings → API Tokens; add it to your protected environment as `NODARO_API_KEY`. Do **not** paste it in chat or commit it.
3. Read the current model and **exact 4s and 2s 480p cost identifiers** from your account's model/credit pricing API; the adapter intentionally does not guess pricing keys.
4. Store the real final frame of the preceding film as `last_frame.jpg` outside the repository.
5. With explicit confirmed credit ceiling and live credentials, run on an authorized machine with FFmpeg:

```bash
python -m oneflow.nodaro_trial --live \
  --start-frame /private/media/last_frame.jpg \
  --output /private/output/emerald_car_14s \
  --confirm-free-credits --credit-cap YOUR_APPROVED_CREDIT_MAX \
  --price-key-4 YOUR_VERIFIED_4_SECOND_PRICE_ID \
  --price-key-2 YOUR_VERIFIED_2_SECOND_PRICE_ID
```

The script checks all four predicted clip costs against the entered hard maximum and verified account balance before submitting *any* job. Each completed segment's end frame is uploaded as the next start frame. Output `roughcut_14s.mp4` is a **silent**, **480p-origin**, visually **unapproved** rough cut upscaled to a 4:3 delivery raster at 24fps; do not call it native 2K or a commercially licensed release. Need to add **original, licensed sound design** and the floating `造镜者` watermark in a separate local finishing pass after QA.

If a quote is missing, a model requires longer than 4 seconds, credits are insufficient, or an upload/model job fails, the adapter stops and does not silently switch to a paid lane. For a public repository, do not upload source files or generated films to GitHub Actions artifacts; keep all actual production files in access-controlled storage.

## Other discovered candidates (not connected)

- **Hugging Face ZeroGPU:** free daily GPU usage but Space-specific queue, model, output and license restrictions: https://huggingface.co/docs/hub/en/spaces-zerogpu
- **PixVerse Basic:** official initial 60 credits + 30 daily, 540p; web/app credits do not imply open API privileges: https://app.pixverse.ai/subscribe
- **Magic Hour:** API free/trial credit offer requires separate real-time check before enabling.
- **Runway:** connected free workspace has no usable video-generation models at the time of this review, despite an image-workspace credit balance.
- **Higgsfield:** connected free workspace had 10 credits, and a quoted full 14-second low-cost job required 14; not run.
- **HeyGen:** uploaded continuity frame accepted, but generating 14 seconds returned HTTP 402 free videos exhausted.

No model is marked *connected* merely because it is listed. Production will require: approved source, authorized API token, verified quota, safe retry policy, media continuity tests, rights review, optional human approval, and explicit release authorization.


## Magic Hour: candidate for one whole 14-second clip (not connected)

Official price/account references:
- https://magichour.ai/pricing — signup grant 400 credits; eligible free accounts may claim 100 daily credits up to seven times.
- https://magichour.ai/api/image-to-video — official Python `magic_hour` image-to-video SDK.
- https://magichour.ai/products/image-to-video — free generations are personal, non-commercial only.

A basic estimate of 24 credits/sec would imply ~336 credits for a 14s trial. This is **not a confirmed account/model quote**: length and model restrictions apply. The live adapter therefore requires an explicit account quote and never assumes the 400 credits exist for this user.

The optional SDK adapter is `oneflow/magic_hour_trial.py`. Offline:
```bash
python -m oneflow.magic_hour_trial > magic-hour-14s-plan.json
```
After account-specific authentication/price check, and **only with user approval**:
```bash
pip install magic_hour
# Set MAGIC_HOUR_API_KEY in a protected environment, NOT repository code.
python -m oneflow.magic_hour_trial --live \
  --source-frame /private/media/last_frame.jpg \
  --output /private/output/magic-hour-trial \
  --quoted-credits YOUR_CONFIRMED_CREDITS \
  --credit-cap YOUR_MAX_ALLOWED_CREDITS \
  --confirm-trial-credits
```
Optional `--model` must be an exact image-to-video model ID verified in the signed-in account. The provider response and clip are **not** declared visually or commercially approved. API integration has not been live-tested and should not be merged until a real small test confirms the endpoint, SDK and cost policy. Magic Hour's public MCP endpoint is `https://mcp.magichour.ai/`; it is not connected in this conversation.
