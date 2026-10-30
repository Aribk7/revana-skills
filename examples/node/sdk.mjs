// The same text-to-video flow with the official SDK: npm i revana
//   REVANA_API_KEY=... node sdk.mjs [--yes]
import { writeFile } from "node:fs/promises";
import { Revana } from "revana";
import { confirm } from "./revana.mjs";

const revana = new Revana(); // reads REVANA_API_KEY

const model = await revana.models.get("veo-3.1-fast"); // live list, no key needed
const seconds = 8;
const perSecond = model.price.usd["720p+audio"];
const usd = Math.round(perSecond * seconds * 100) / 100;
console.log(`${model.name}, ${seconds}s 720p with sound: $${usd}`);
if (!(await confirm(`Spend up to $${usd}?`))) process.exit(0);

const video = await revana.generate({
  model: "veo-3.1-fast",
  input: { prompt: "a hummingbird drinking from a red flower, slow motion, macro", duration: seconds, resolution: "720p", audio: true },
  max_cost_usd: usd,
});
await writeFile("sdk.mp4", new Uint8Array(await revana.generations.download(video.id)));
console.log(`saved sdk.mp4, cost $${video.cost_usd}`);
