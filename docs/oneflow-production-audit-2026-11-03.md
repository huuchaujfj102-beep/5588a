# OneFlow / Qianfan / MuseSteamer production audit — 2026-11-03

## Scope and evidence

Repository: `huuchaujfj102-beep/5588a`. Audit performed on the live 5s, 10s and stitched 35s generation paths, asynchronous task receipt and GET polling, GitHub Actions gates, public reference images, FFmpeg normalization, and human-reviewed distribution. Primary incidents:

- Run `41581721684`: Cloudflare Workers AI `HTTP 400` / `8007` before any Baidu paid video call.
- Run `41583766804`: first 5s MuseSteamer POST timed out; task acceptance unknown, `task_id=null`; six further POSTs correctly blocked. Billing must be reconciled.
- Run `41588168677`: a controlled 5s MuseSteamer POST again timed out at 45s; task acceptance unknown, `task_id=null`. No MP4.
- Run `41584411340` (#6): offline tests were green but live job skipped, misleading if interpreted as end-to-end success.
- VQ3-Turbo 10s path returned HTTP 401 on real POST; invalid task GET returning 400 is *not* proof of generation rights.

## Fixes implemented and tested

| Severity | Issue | New behavior | Test limitation |
| --- | --- | --- | --- |
| P0 | 45-second fixed async POST timeout | 180s ACK timeout for billable POST; 30s read-only GET. No automatic POST retry; ambiguous acceptance remains blocked | Mocked HTTP timings, not a successful provider acknowledgement |
| P0 | Lack of public frame content verification | Bounded 9 MB, GET-only and no redirects; checks HTTPS, response content-type and JPG/PNG/WebP signatures before the first billable POST | Does not certify image semantics, rights, or accessibility from Baidu servers |
| P1 | GitHub success when user did not approve real generation | Explicit dispatch gate fails if paid consent or valid source selection missing | PR-only CI deliberately skips any live paid step |
| P1 | API Key accidental Bearer prefix / whitespace | Reject locally before network | Fake-key unit tests; no account secrets in CI |
| P1 | Unbounded provider JSON | Response limit 1 MiB, safe generic errors, allowlisted provider error IDs | Does not prove upstream provider response schema stability |
| P1 | Cloudflare 8007 blocked all filming | Earlier change allowed approved public first frame without Cloudflare | Public image must be verified and rights-cleared |
| P1 | No real video processing CI | Prior work added FFmpeg CPU portrait encoding and real end-frame extraction smoke | Seven full live clips still not verified |

PR #46 contains the latest corrections and tests. The 35s and single-shot Actions and general baseline checks passed their unbilled CI after the final change.

## NOT production-certified — blocking work

1. **Unknown Baidu acceptance and charges.** The two MuseSteamer POST timeouts have no `task_id`. There is no reliable, documented lookup-by-request id or idempotency key established in this repository. The account owner or Baidu support must reconcile the precise request time against server-side job and billing records before any new video POST.
2. **No live 35s video.** Seven-shot sequencing was mocked in tests. No uninterrupted 7 x 5s model run, no real car-consistency verification, no proven 35.00s 9:16 MP4 from the provider, and no platform publish.
3. **VQ3 10s model entitlement.** Genuine POST got HTTP 401; the free GET 400 probe is insufficient evidence of video-generation rights.
4. **Cloudflare FLUX.** Live request got HTTP 400 / 8007. Exact provider-side meaning not confirmed; cannot infer plan/balance from this alone.
5. **Persistence beyond ephemeral GitHub runner.** Attempt markers and partial clips are uploaded as artifacts at job exit, but an abrupt runner termination may happen before upload. Production multi-shot use needs durable checkpointing after each segment before unattended 7-task operation.
6. **Reference image / license and rights.** Public photographs are not equivalent to rights-cleared fictional concept-car source material. Legal approval, author attribution and licensing review required.
7. **Quality and publication gates.** Automated duration/codec/presence checks do NOT ensure mechanical physics, motion continuity, correct car identity, true engine realism, editorial quality, music rights, or social-platform compliance. Approved Douyin OAuth, upload/create and publish status must be verified separately; no auto-publishing of unreviewed content.
8. **Public repository exposure.** All workflow inputs, logs and uploaded artifacts may be exposed. Never include private photos, patient data, tokens, secret URLs or proprietary unreleased materials. Consider migrating sensitive jobs/artifacts to a private repository under a deliberate access-control plan.

## Mandatory staged signoff protocol

1. Billing and job reconciliation for both timed-out POSTs, including server-side task acceptance and any charge.
2. Account-side confirmation of the required Qianfan endpoint permissions and balance; GET probes do not replace POST entitlement.
3. A single **explicitly authorized** paid 5-second model task; record a valid task ID, successful GET status, actual MP4 playable and 5s audited metadata. **Do not retry on timeout.**
4. Separate 5s tail-bridge test from first segment into second; two clips must pass identity/motion and ownership review.
5. Only after verified 2-part test, deliberately authorize up to 7 x 5s tasks, with an appropriate spending cap and durable checkpoints.
6. Confirm 35s actual video duration/quality and sign off manually before approved platform upload. No promise of virality or guaranteed audience.

## Rules for future changes

- Do not bypass a failed CI gate.
- Do not merge untested billing-side behavior to main.
- No background work, paid generation, automatic reruns, or platform publication without explicit authorized execution.
- All provider failures must leave a safe and accurate audit trail, never leak tokens or raw private response bodies.
- Treat a green **offline-validation** job as a test result, not a generation result.
