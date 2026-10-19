# Visual scraping probe (checklist L1)

Three small scripts that test whether "screenshot → vision model → action
decision" works with the tools we actually have. Each one writes a JSON
record that is the evidence; nothing here touches LakeStream's job queue,
database or default scraping path. Measured results for 2026-10-19 are in
[RESULTS.md](RESULTS.md).

| Step | Script | Proves | Needs |
|---|---|---|---|
| 1 | `probe_browser.py` | the stealth browser loads a page and we get a screenshot + block/login-wall verdict | nothing (browser is cached locally) |
| 2 | `probe_vision.py` | a vision model turns that screenshot into structured observations | `OPENROUTER_API_KEY` |
| 3 | `probe_jev.py` | Jev picks one bounded action from the observations | `TYPESAFE_API_KEY` |

## Browser choice

The brief says Camoufox. This probe uses **invisible_playwright**
(`pip install invisible-playwright`), a patched Firefox with the same
Playwright API, because it drops into the existing Playwright fetcher with a
two-line change. Swapping back to Camoufox is the same two lines.

First launch downloads a 52 MB GeoIP database (used to keep timezone and
locale consistent with the exit IP). On a slow link this takes several
minutes and looks like a hang; let it finish once.

## Jev

Jev is TypeSafe's decision model, reached at
`https://api.typesafe.ai/v1/systemone` (the endpoint `jev-ultrafast` uses).
It is not a chat model: the request carries a page *state* (url, title,
text, elements, recent actions) and *questions* of type `choice`; the reply
is one choice per question with probabilities and a confidence. The schema
has no image field, so the loop is: screenshot → vision model → observations
→ Jev → action. Sending a screenshot inside the state is rejected with
HTTP 400 `max_tokens_exceeded` (recorded in RESULTS.md).

## Run

```powershell
.venv\Scripts\activate
python scripts/visual_probe/probe_browser.py https://example.com
python scripts/visual_probe/probe_vision.py data/visual_probe/<run>/example_com.viewport.png
python scripts/visual_probe/probe_jev.py --observations data/visual_probe/<run>/vision_record.google_gemini-2.5-flash-lite.json
```

Outputs land in `data/visual_probe/<timestamp>/` (gitignored). Keys are read
from the environment or the repo `.env` (gitignored). Records never contain
keys or proxy credentials.

## Rules baked in

- A login wall, real challenge page or 403/429/503/999 is recorded as
  `login_wall` / `captcha` / `blocked` and the run ends. No retry, no
  cookies, no IP cycling.
- A reCAPTCHA script on an otherwise rendered page (LinkedIn's sign-in form
  has one on every public page) is noted as a signal, not treated as a block.
- Only URLs on Deep's approved list go through step 1.
- Missing API access is recorded as `blocked` / `not_configured`, not as a
  model failure.
