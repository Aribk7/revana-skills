"""The same text-to-video flow with the official package: pip install revana

  REVANA_API_KEY=... python3 sdk_example.py [--yes]
"""
import sys

from revana import Revana

from revana_rest import confirm

client = Revana()  # reads REVANA_API_KEY

model = next(m for m in client.models.list() if m["id"] == "veo-3.1-fast")  # live list, no key needed
seconds = 8
usd = round(model["price"]["usd"]["720p+audio"] * seconds, 2)
print(f"{model['name']}, {seconds}s 720p with sound: ${usd}")
if not confirm(f"Spend up to ${usd}?"):
    sys.exit(0)

video = client.generate(
    model="veo-3.1-fast",
    input={"prompt": "a hummingbird drinking from a red flower, slow motion, macro", "duration": seconds, "resolution": "720p", "audio": True},
    max_cost_usd=usd,
)
with open("sdk.mp4", "wb") as f:
    f.write(client.generations.download(video["id"]))
print(f"saved sdk.mp4, cost ${video['cost_usd']}")
