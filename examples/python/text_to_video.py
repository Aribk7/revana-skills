"""Text to video with Seedance 2.5 on Revana: quote (the server's, or the live price list), confirm, generate, download.

  REVANA_API_KEY=... python3 text_to_video.py "a paper boat drifting down a rainy street" [--yes]
"""
import sys

from revana_rest import confirm, create, download, quote, wait

args = [a for a in sys.argv[1:] if not a.startswith("--")]
prompt = args[0] if args else "a paper boat drifting down a rainy street at night, close up, reflections"
model = "seedance-2.5"
inp = {"prompt": prompt, "resolution": "720p", "duration": 5, "aspect_ratio": "16:9", "audio": True}

q = quote(model, inp)
print(f"{model}, {inp['duration']}s {inp['resolution']}: ${q['usd']} (priced by the {q['by']})")
if not confirm(f"Spend up to ${q['usd']}?"):
    sys.exit(0)

# max_cost_usd caps the charge at the agreed quote; a dearer backup route is skipped rather than billed.
gen = create(model, inp, q["usd"])
print(f"submitted {gen['id']} (quoted ${gen['quoted_usd']})")
done = wait(gen["id"], every_s=10)
download(done["id"], "text_to_video.mp4")
print(f"saved text_to_video.mp4, cost ${done['cost_usd']}")
