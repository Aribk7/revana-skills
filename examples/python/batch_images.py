"""Several pictures at once: quote the whole batch, confirm once, run them in parallel, save each.

  REVANA_API_KEY=... python3 batch_images.py [--model=gpt-image-2] [--yes]
"""
import sys
from concurrent.futures import ThreadPoolExecutor

from revana_rest import confirm, create, download, quote, wait

model = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--model=")), "nano-banana-pro")
prompts = [
    "a ceramic coffee mug on a walnut desk, morning light, product photo",
    "the same mug on a picnic blanket in a park, product photo",
    "the same mug held in two hands by a window in the rain, product photo",
]
base = {"resolution": "2K", "aspect_ratio": "1:1"}

q = quote(model, {**base, "prompt": prompts[0]})  # every picture has the same settings, so the same price
total = round(q["usd"] * len(prompts), 2)
print(f"{len(prompts)} x {model} ({q['setting']}): ${q['usd']} each, ${total} in all")
if not confirm(f"Spend up to ${total}?"):
    sys.exit(0)


def one(n_prompt):
    n, prompt = n_prompt
    gen = create(model, {**base, "prompt": prompt}, q["usd"])  # its own Idempotency-Key, reused on resends
    done = wait(gen["id"], every_s=3, log=False)
    return f"{download(done['id'], f'batch-{n + 1}.png')} (${done['cost_usd']})"


with ThreadPoolExecutor(max_workers=len(prompts)) as pool:
    futures = [pool.submit(one, p) for p in enumerate(prompts)]
    for f in futures:
        try:
            print("saved", f.result())
        except Exception as e:  # one failed picture should not hide the others
            print("failed:", e)
