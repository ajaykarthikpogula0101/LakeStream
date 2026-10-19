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

## Blockers / needs

- Deep's approved URL list (the pages above were ad-hoc tests, not client targets).
- anyIP trial details for the L4 direct-vs-proxy comparison.
- Decision: keep invisible_playwright or switch to Camoufox (two-line change either way).
- Both API keys were shared over chat; rotate them after the assignment.
