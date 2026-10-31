#!/usr/bin/env python3
"""Rank Revana models by price for one job, from the live list at GET /v1/models (no key needed).

  python3 cheapest.py --kind video --seconds 5 --resolution 720p
  python3 cheapest.py --kind video --family veo --seconds 8 --audio
  python3 cheapest.py --kind image --task image_to_image --resolution 2K
  python3 cheapest.py --kind text --top 5

Prices change; this always reads the live list. Standard-list prices: an account on another price book may
see a different quoted_usd on the generation itself.
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

MODELS_URL = "https://api.revana.si/v1/models"


def load_models():
    req = urllib.request.Request(MODELS_URL, headers={"User-Agent": "revana-skills/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["data"]
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" not in str(e):
            raise
        # python.org builds on macOS ship without CA certificates; the list is public, so curl will do.
        out = subprocess.run(["curl", "-sf", MODELS_URL], capture_output=True, check=True).stdout
        return json.loads(out)["data"]


def duration_ok(model, seconds):
    d = model.get("options", {}).get("durations")
    if seconds is None or d is None:
        return True
    if isinstance(d, dict):
        return d.get("min", 0) <= seconds <= d.get("max", 10**9)
    return seconds in d


def unit_price(model, resolution, audio):
    """(usd, price key) for one second / image / job, or None if the model can't do it."""
    usd = model.get("price", {}).get("usd")
    if isinstance(usd, (int, float)):
        listed = model.get("options", {}).get("resolutions")
        if resolution and listed and resolution not in listed:
            return None
        return float(usd), "flat"
    if not isinstance(usd, dict) or not usd:
        return None
    if resolution:
        keys = [f"{resolution}+audio", resolution] if audio else [resolution]
        for k in keys:
            if k in usd:
                return float(usd[k]), k
        return None
    # No resolution asked: the cheapest plain setting (with sound, if asked and priced separately).
    plain = {k: v for k, v in usd.items() if "+" not in k}
    if audio:
        with_audio = {k: v for k, v in usd.items() if k.endswith("+audio")}
        plain = with_audio or plain
    if not plain:
        return None
    k = min(plain, key=lambda k: plain[k])
    return float(plain[k]), k


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--kind", choices=["video", "image", "audio", "text"], required=True)
    p.add_argument("--task", help="e.g. text_to_video, image_to_video, image_to_image")
    p.add_argument("--family", help="substring of the model id or name, e.g. veo, kling, seedance, flux")
    p.add_argument("--resolution", help="e.g. 720p, 1080p, 1K, 2K")
    p.add_argument("--seconds", type=float, help="video length (video models)")
    p.add_argument("--audio", action="store_true", help="the video needs sound")
    p.add_argument("--top", type=int, default=10)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    rows = []
    for m in load_models():
        if m.get("kind") != a.kind:
            continue
        if a.task and a.task not in m.get("tasks", []):
            continue
        if a.family and a.family.lower() not in (m["id"] + " " + m.get("name", "")).lower():
            continue
        price = m.get("price", {})
        if a.kind == "text":
            total = float(price.get("input", 0)) + float(price.get("output", 0))
            rows.append({"id": m["id"], "usd": total, "detail": f"in ${price.get('input')}/M, out ${price.get('output')}/M tokens"})
            continue
        if a.audio and not m.get("options", {}).get("audio"):
            continue
        if not duration_ok(m, a.seconds):
            continue
        up = unit_price(m, a.resolution, a.audio)
        if up is None:
            continue
        usd, key = up
        unit = price.get("unit", "")
        if unit == "per_second":
            secs = a.seconds or 5
            rows.append({"id": m["id"], "usd": round(usd * secs, 4), "detail": f"${usd}/s x {secs:g}s ({key})"})
        else:
            rows.append({"id": m["id"], "usd": usd, "detail": f"${usd} {unit.replace('_', ' ')} ({key})"})

    rows.sort(key=lambda r: (r["usd"], r["id"]))
    rows = rows[: a.top]
    if a.json:
        json.dump(rows, sys.stdout, indent=2)
        print()
        return
    if not rows:
        print("No model matches. Loosen --resolution, --seconds or --task.")
        return
    label = "in+out $/M" if a.kind == "text" else "job price"
    print(f"{'model':32} {label:>11}  detail")
    for r in rows:
        print(f"{r['id']:32} {('$%.4g' % r['usd']):>11}  {r['detail']}")
    if a.task == "image_to_video":
        print("\nWith a start image some models (Seedance 2.5 among them) charge more than the listed price: these are"
              "\nthe least each costs. POST /v1/generations/quote (with a key) prices the exact request.")


if __name__ == "__main__":
    main()
