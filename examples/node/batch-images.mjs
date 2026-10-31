// Several pictures at once: quote the whole batch, confirm once, run them in parallel, save each.
//   REVANA_API_KEY=... node batch-images.mjs [--model gpt-image-2] [--yes]
import { quote, confirm, create, wait, download } from "./revana.mjs";

const i = process.argv.indexOf("--model");
const model = i > 0 ? process.argv[i + 1] : "nano-banana-pro";
const prompts = [
  "a ceramic coffee mug on a walnut desk, morning light, product photo",
  "the same mug on a picnic blanket in a park, product photo",
  "the same mug held in two hands by a window in the rain, product photo",
];
const base = { resolution: "2K", aspect_ratio: "1:1" };

const q = await quote(model, { ...base, prompt: prompts[0] }); // every picture has the same settings, so the same price
const total = Math.round(q.usd * prompts.length * 100) / 100;
console.log(`${prompts.length} x ${model} (${q.setting}): $${q.usd} each, $${total} in all`);
if (!(await confirm(`Spend up to $${total}?`))) process.exit(0);

const results = await Promise.allSettled(
  prompts.map(async (prompt, n) => {
    const gen = await create(model, { ...base, prompt }, q.usd); // its own Idempotency-Key, reused on resends
    const done = await wait(gen.id, { everyMs: 3000, log: false });
    const file = await download(done.id, `batch-${n + 1}.png`);
    return `${file} ($${done.cost_usd})`;
  }),
);
for (const r of results) console.log(r.status === "fulfilled" ? `saved ${r.value}` : `failed: ${r.reason.message}`);
