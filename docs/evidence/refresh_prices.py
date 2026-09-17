#!/usr/bin/env python3
"""
D6 EVIDENCE · are the prices in config.py still the vendor's prices?

    python3 docs/evidence/refresh_prices.py              # check the table
    python3 docs/evidence/refresh_prices.py MODEL_SLUG   # look one up

Reads openrouter.ai/api/v1/models, which is public and needs no key, and
compares every entry in config.PRICES against it. Exits non-zero if any
has moved.

The scaffold shipped a single hardcoded pair with the comment "RE-CHECK
THEM: quoting a price you did not verify is the kind of thing D6 is
marked on." This is that re-check, as a command rather than a good
intention - and it is also how a teammate adds their own model, since a
model missing from the table gets costed at a deliberately silly
placeholder rather than silently at somebody else's rate.

No key, no cost, one HTTP GET.
"""
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "A2_scaffold"))

import config      # noqa: E402

RULE = "=" * 72
ENDPOINT = "https://openrouter.ai/api/v1/models"
TOLERANCE = 0.0005      # per million tokens; below this is rounding


def fetch():
    req = urllib.request.Request(ENDPOINT, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)["data"]
    out = {}
    for m in data:
        p = m.get("pricing") or {}
        try:
            out[m["id"]] = (float(p.get("prompt") or 0) * 1e6,
                            float(p.get("completion") or 0) * 1e6)
        except (TypeError, ValueError):
            continue
    return out


def lookup(live, slug):
    if slug in live:
        pin, pout = live[slug]
        print("\n  %s\n    in  US$%.3f / M\n    out US$%.3f / M\n"
              % (slug, pin, pout))
        print("  Add to PRICES in config.py:")
        print('      "%s": (%.3f, %.3f),\n' % (slug, pin, pout))
        return 0
    print("\n  %r is not on OpenRouter.\n" % slug)
    near = sorted(s for s in live if slug.split("/")[0] in s)[:12]
    if near:
        print("  Same vendor:")
        for s in near:
            print("      %s" % s)
    print()
    return 1


def main():
    if len(sys.argv) > 1:
        return lookup(fetch(), sys.argv[1])

    live = fetch()
    print()
    print(RULE)
    print("  config.PRICES against openrouter.ai, US$ per million tokens")
    print(RULE)
    print("  %-44s %8s %8s" % ("model", "in", "out"))
    print("  " + "-" * 62)

    drift, missing = [], []
    for slug, (pin, pout) in sorted(config.PRICES.items()):
        if slug not in live:
            print("  %-44s %8s %8s   GONE FROM OPENROUTER" % (slug, "-", "-"))
            missing.append(slug)
            continue
        lin, lout = live[slug]
        moved = (abs(lin - pin) > TOLERANCE or abs(lout - pout) > TOLERANCE)
        print("  %-44s %8.3f %8.3f   %s"
              % (slug, pin, pout,
                 "MOVED -> %.3f / %.3f" % (lin, lout) if moved else "ok"))
        if moved:
            drift.append((slug, (lin, lout)))

    print()
    if config.MODEL not in config.PRICES:
        print("  config.MODEL is %r and is NOT in the table." % config.MODEL)
        print("  Look it up:  python3 %s %s"
              % (os.path.relpath(__file__, REPO), config.MODEL))
        print()

    if drift:
        print(RULE)
        print("  %d price(s) moved. Paste into config.PRICES:" % len(drift))
        for slug, (lin, lout) in drift:
            print('      "%s": (%.3f, %.3f),' % (slug, lin, lout))
        print(RULE)
        print()
        return 1
    if missing:
        print("  %d model(s) no longer listed - whoever runs them should"
              % len(missing))
        print("  pick a replacement before the battery.")
        print()
        return 1

    print(RULE)
    print("  Every price on file still matches the vendor.")
    print("  config.MODEL = %r costs US$%.3f in / US$%.3f out per M."
          % (config.MODEL, config.PRICE_IN, config.PRICE_OUT))
    print(RULE)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
