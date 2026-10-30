// Animate a local picture: upload it (free), then use it as the first frame of a Seedance 2.5 clip.
//   REVANA_API_KEY=... node image-to-video.mjs photo.png "the camera slowly pushes in, steam rises" [--yes]
import { quote, confirm, create, wait, download, upload } from "./revana.mjs";

const [file, prompt = "the camera slowly pushes in, gentle natural motion"] = process.argv.slice(2).filter((a) => !a.startsWith("--"));
if (!file) {
  console.error("usage: node image-to-video.mjs <image.png|jpg|webp> [prompt] [--yes]");
  process.exit(1);
}

const model = "seedance-2.5";
const input = { prompt, resolution: "720p", duration: 5, aspect_ratio: "adaptive" };
input.image_url = await upload(file); // uploads are free; the link is public for 14 days
console.log(`uploaded ${file}`);

const q = await quote(model, input);
console.log(`${model}, ${input.duration}s ${input.resolution} from ${file}: $${q.usd}`);
if (!(await confirm(`Spend up to $${q.usd}?`))) process.exit(0);

const gen = await create(model, input, q.usd);
console.log(`submitted ${gen.id}`);
const done = await wait(gen.id, { everyMs: 10_000 });
await download(done.id, "image-to-video.mp4");
console.log(`saved image-to-video.mp4, cost $${done.cost_usd}`);
