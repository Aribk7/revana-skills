// Animate a local picture: upload it (free), then use it as the first frame of a Seedance 2.5 clip.
//   REVANA_API_KEY=... node image-to-video.mjs photo.png "the camera slowly pushes in, steam rises" [--max-cost 1.50] [--yes]
import { quote, confirm, create, wait, download, upload, maxCostArg } from "./revana.mjs";

const args = process.argv.slice(2).filter((a, i, all) => !a.startsWith("--") && all[i - 1] !== "--max-cost");
const [file, prompt = "the camera slowly pushes in, gentle natural motion"] = args;
if (!file) {
  console.error("usage: node image-to-video.mjs <image.png|jpg|webp> [prompt] [--max-cost <usd>] [--yes]");
  process.exit(1);
}

const model = "seedance-2.5";
const input = { prompt, resolution: "720p", duration: 5, aspect_ratio: "adaptive" };
input.image_url = await upload(file); // uploads are free; the link is public for 14 days
console.log(`uploaded ${file}`);

const q = await quote(model, input);
const cap = maxCostArg() ?? q.usd;
console.log(`${model}, ${input.duration}s ${input.resolution} from ${file}: $${q.usd} (priced by the ${q.by})`);
if (q.floor && !maxCostArg()) {
  console.log("note: listed price. With a start image Seedance 2.5 costs more; if the API refuses the cap (free), pass --max-cost <usd>.");
}
if (!(await confirm(`Spend up to $${cap}?`))) process.exit(0);

const gen = await create(model, input, cap);
console.log(`submitted ${gen.id} (quoted $${gen.quoted_usd})`);
const done = await wait(gen.id, { everyMs: 10_000 });
await download(done.id, "image-to-video.mp4");
console.log(`saved image-to-video.mp4, cost $${done.cost_usd}`);
