// Text to video with Seedance 2.5 on Revana: quote (the server's, or the live price list), confirm, generate, download.
//   REVANA_API_KEY=... node text-to-video.mjs "a paper boat drifting down a rainy street" [--yes]
import { quote, confirm, create, wait, download } from "./revana.mjs";

const prompt = process.argv.slice(2).find((a) => !a.startsWith("--")) ?? "a paper boat drifting down a rainy street at night, close up, reflections";
const model = "seedance-2.5";
const input = { prompt, resolution: "720p", duration: 5, aspect_ratio: "16:9", audio: true };

const q = await quote(model, input);
console.log(`${model}, ${input.duration}s ${input.resolution}: $${q.usd} (priced by the ${q.by}${q.each ? `, $${q.each}/s, ${q.setting}` : ""})`);
if (!(await confirm(`Spend up to $${q.usd}?`))) process.exit(0);

// max_cost_usd caps the charge at the agreed quote; a dearer backup route is skipped rather than billed.
const gen = await create(model, input, q.usd);
console.log(`submitted ${gen.id} (quoted $${gen.quoted_usd})`);
const done = await wait(gen.id, { everyMs: 10_000 });
await download(done.id, "text-to-video.mp4");
console.log(`saved text-to-video.mp4, cost $${done.cost_usd}`);
