# L1 results: 2026-10-19

Everything below ran live from a Windows 11 laptop (Python 3.12.10), direct
connection, no proxy. Raw records are in `data/visual_probe/<timestamp>/`
on that machine (gitignored). Keys were never written to any record.

## Compatibility matrix

| Component | What was tested | Result | Numbers |
|---|---|---|---|
| Browser: invisible_playwright 0.40.0 (invisible_core 50.48.0, patched Firefox 151) | headless launch, navigate, viewport + full-page PNG, HTML | works | launch 6–7.5 s, example.com load 1.4 s, first launch +52 MB GeoIP download |
| Browser: bot detection (bot.sannysoft.com, seed 42) | fingerprint scanner suite | all tests green; WebDriver "missing (passed)"; only the Chrome-object check is red, expected on any Firefox | status 200 |
| Vision: google/gemini-2.5-flash-lite via OpenRouter | screenshot → JSON observations | works | 5–9 s, 586–984 tokens, $0.0001–0.00025 per page |
| Vision: google/gemini-2.5-flash via OpenRouter | same | works, slightly richer topics | 7 s, 849 tokens, $0.0010 per page |
| Vision: deepseek/deepseek-chat via OpenRouter | image smoke test | **rejected**: HTTP 404 `No endpoints found that support image input` | – |
| Jev: api.typesafe.ai/v1/systemone (jev-1.13.0), text state | observations → one bounded action | works | 1.2 s, 963 in / 49 out tokens |
| Jev: same endpoint, screenshot inside state | image input | **rejected**: HTTP 400 `max_tokens_exceeded` (556 KB request) | – |
| Java controller | not run | the endpoint is plain HTTPS + JSON, so any Java HTTP client could call it; no JVM needed on the Python path | – |

## Page benchmark (logged out, direct IP)

| URL | HTTP | Outcome | Notes |
|---|---|---|---|
| example.com | 200 | ok | control |
| bot.sannysoft.com | 200 | ok | detection suite passed |
| linkedin.com/company/microsoft | 200 | ok | page fully rendered behind a sign-in pop-up; vision read name, industry, HQ, 29.3M followers, 10,001+ employees, specialties, affiliated pages |
| linkedin.com/in/satyanadella | 999 → authwall | login_wall | "Sign Up \| LinkedIn", stopped |
| linkedin.com/in/williamhgates | 999 → authwall | login_wall | stopped |
| github.com/Champ-Deep | 200 | ok | non-LinkedIn control |

Reached 4 / blocked 2 / failed 0. Company pages are reachable logged out;
individual profile pages are not from this IP without a session, and the
rules say stop there.

## Jev decision on the Microsoft page

Input: Gemini observations (company_page, overlay present, no posts visible).
Choice `CLICK_ACTIVITY` 0.36, `SCROLL` 0.35, `STOP` 0.29, `BACK` 0.00;
confidence 0.15. Low confidence is appropriate: the overlay hides part of
the page. The action set is bounded to open/click/scroll/back/stop.

## Fixes made during the run

- First vision attempt on the Microsoft page looped on the "About" text until
  the token cap and returned truncated JSON. Prompt now caps bio at 300
  chars, posts at 5, topics at 10, whole answer under 400 words.
- LinkedIn's sign-in form embeds a reCAPTCHA script on every public page,
  which LakeStream's `captcha_detector` matches. The probe now treats
  CAPTCHA markers as a block only alongside a challenge title, a block
  status or a tiny page.

## L2: screenshot-guided loop (same day, direct IP, logged out)

| URL | Outcome | Steps | Time | Model calls | Vision cost | Jev input tokens |
|---|---|---|---|---|---|---|
| linkedin.com/company/microsoft | reached posts | SCROLL, SCROLL, goal | 42 s | 5 | $0.0012 | 2.9k |
| linkedin.com/company/google | reached posts | SCROLL, SCROLL, goal | 50 s | 5 | $0.0006 | 2.9k |
| linkedin.com/company/amazon | reached posts | SCROLL (after re-ask), goal | 35 s | 4 | $0.0006 | 2.9k |
| linkedin.com/company/apple | end of page, no posts section on the public page | SCROLL ×4 | 46 s | 8 | $0.0007 | 5.7k |
| linkedin.com/in/satyanadella | stopped at landing: 999 → authwall | 0 | 13 s | 0 | $0 | 0 |

Journeys that reach posts cost about $0.001 in vision plus ~3k Jev input
tokens and take 35–50 s, most of it model latency (vision 4–15 s per step,
Jev 0.7–1.2 s). Evidence per step: before/after PNG, observations, Jev
probabilities. Example: Microsoft step 3 shows the "Updates" card with a
post from 3 days ago under the sign-in overlay.

Observed and fixed during L2:
- The vision model called LinkedIn's sign-in pop-up a "wall" even when the
  page behind it was readable, which pushed Jev to STOP on the first step
  (Amazon: STOP 0.76). The prompt now separates `login_or_access_wall`
  (content replaced) from `signin_popup_present` (overlay on content), Jev
  gets a facts header, and a STOP that contradicts the facts is re-asked once
  with the reason. Amazon then went STOP 0.65 → SCROLL 0.77 and found a post.
- Public company pages expose no Posts/Activity link logged out, so
  `CLICK_ACTIVITY` was never offered; posts are reached by scrolling to the
  "Updates" section. Apple's public page has no such section.
- Individual profile URLs never get past the landing check (authwall), so the
  loop makes no model calls there.

## Blockers / needs

- Deep's approved URL list (the pages above were ad-hoc tests, not client targets).
- anyIP trial details for the L4 direct-vs-proxy comparison.
- Decision: keep invisible_playwright or switch to Camoufox (two-line change either way).
- Both API keys were shared over chat; rotate them after the assignment.
