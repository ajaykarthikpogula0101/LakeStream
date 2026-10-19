"""Visual-scraping probe, step L4: direct access vs ONE sticky proxy session.

Fetches the same permitted URLs twice with probe_browser: once direct, once
through the proxy named by VISUAL_PROBE_PROXY_SERVER (+ _USERNAME/_PASSWORD).
Same fixed seed and the same slow, sequential rate in both runs. Writes a
comparison table with elapsed time, HTML bytes, outcome and, when
--cost-per-gb is given, an estimated proxy cost per successful page.

Rules: one session, no IP rotation, a blocked page stays blocked. If the
proxy is not configured the proxy column is recorded as "not_configured"
and only the direct run happens. Credentials never reach the output.

Usage (repo root, inside .venv):
    python scripts/visual_probe/proxy_compare.py URL URL [--cost-per-gb 3.0] [--region us]

Exit codes: 0 comparison written, 2 proxy not configured (direct run only), 1 error.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import probe_browser  # noqa: E402


async def one(url: str, out_dir: Path, seed: int, proxy: dict | None, timezone: str) -> dict:
    rec = await probe_browser.run(url, out_dir, seed=seed, headless=True, timezone=timezone,
                                  locale="auto", proxy=proxy, timeout_ms=60_000)
    return {
        "outcome": rec.get("outcome"),
        "status": rec.get("status"),
        "elapsed_ms": rec["timings_ms"].get("total"),
        "goto_ms": rec["timings_ms"].get("goto"),
        "html_bytes": rec.get("html_bytes"),
        "error": rec.get("error"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("urls", nargs="+")
    ap.add_argument("--out", default=str(REPO_ROOT / "data" / "visual_probe"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--region", default=None, help="label only, e.g. us / eu / in")
    ap.add_argument("--cost-per-gb", type=float, default=None,
                    help="provider price per GB, to estimate cost per successful page")
    ap.add_argument("--pause-s", type=float, default=5.0, help="pause between fetches")
    args = ap.parse_args()

    proxy = probe_browser._proxy_from_env()
    out_root = Path(args.out) / datetime.now().strftime("l4_%Y%m%d_%H%M%S")
    out_root.mkdir(parents=True, exist_ok=True)
    meta = {
        "provider_host": urlparse(proxy["server"]).hostname if proxy else None,
        "proxy_scheme": urlparse(proxy["server"]).scheme if proxy else None,
        "proxy_configured": bool(proxy),
        "region": args.region,
        "session_policy": "one sticky session, no rotation" if proxy else None,
        "seed": args.seed,
        "started_at": datetime.now().isoformat(),
    }

    rows = []
    for url in args.urls:
        row = {"url": url}
        print(f"=== {url} (direct)", flush=True)
        d = asyncio.run(one(url, out_root / "direct", args.seed, None, ""))
        row.update({f"direct_{k}": v for k, v in d.items()})
        asyncio.run(asyncio.sleep(args.pause_s))
        if proxy:
            print(f"=== {url} (proxy)", flush=True)
            p = asyncio.run(one(url, out_root / "proxy", args.seed, proxy, ""))
            row.update({f"proxy_{k}": v for k, v in p.items()})
            if args.cost_per_gb and p.get("html_bytes") and p.get("outcome") == "ok":
                # HTML only; images/scripts also count on a real bill, so this is a floor.
                row["proxy_cost_floor_usd"] = round(p["html_bytes"] / 1e9 * args.cost_per_gb, 6)
            asyncio.run(asyncio.sleep(args.pause_s))
        else:
            row["proxy_outcome"] = "not_configured"
        rows.append(row)
        print(json.dumps(row), flush=True)

    fields = sorted({k for r in rows for k in r}, key=lambda k: (k != "url", k))
    with (out_root / "comparison.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    (out_root / "comparison.json").write_text(
        json.dumps({"meta": meta, "rows": rows}, indent=2), encoding="utf-8"
    )
    print("\nmeta:", json.dumps(meta), "| out:", out_root)
    return 0 if proxy else 2


if __name__ == "__main__":
    sys.exit(main())
