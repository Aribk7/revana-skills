"""Animate a local picture: upload it (free), then use it as the first frame of a Seedance 2.5 clip.

  REVANA_API_KEY=... python3 image_to_video.py photo.png "the camera slowly pushes in" [--max-cost=1.50] [--yes]
"""
import sys

from revana_rest import confirm, create, download, max_cost_arg, quote, upload, wait

args = [a for a in sys.argv[1:] if not a.startswith("--")]
if not args:
    sys.exit("usage: python3 image_to_video.py <image.png|jpg|webp> [prompt] [--max-cost=<usd>] [--yes]")
path = args[0]
prompt = args[1] if len(args) > 1 else "the camera slowly pushes in, gentle natural motion"

model = "seedance-2.5"
inp = {"prompt": prompt, "resolution": "720p", "duration": 5, "aspect_ratio": "adaptive"}
inp["image_url"] = upload(path)  # uploads are free; the link is public for 14 days
print(f"uploaded {path}")

q = quote(model, inp)
cap = max_cost_arg() or q["usd"]
print(f"{model}, {inp['duration']}s {inp['resolution']} from {path}: ${q['usd']} (priced by the {q['by']})")
if q.get("floor") and not max_cost_arg():
    print("note: listed price. With a start image Seedance 2.5 costs more; if the API refuses the cap (free), pass --max-cost=<usd>.")
if not confirm(f"Spend up to ${cap}?"):
    sys.exit(0)

gen = create(model, inp, cap)
print(f"submitted {gen['id']} (quoted ${gen['quoted_usd']})")
done = wait(gen["id"], every_s=10)
download(done["id"], "image_to_video.mp4")
print(f"saved image_to_video.mp4, cost ${done['cost_usd']}")
