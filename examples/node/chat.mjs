// Chat completions on the same Revana key: the OpenAI-compatible endpoint, 90+ language models.
// Any OpenAI SDK works too: new OpenAI({ baseURL: "https://api.revana.si/v1", apiKey: process.env.REVANA_API_KEY })
//   REVANA_API_KEY=... node chat.mjs "Write a 10-word hook for a water bottle ad"
import { api } from "./revana.mjs";

const prompt = process.argv[2] ?? "Write a 10-word hook for a water bottle ad.";
const res = await api("POST", "/v1/chat/completions", {
  body: { model: "claude-haiku-5-5", messages: [{ role: "user", content: prompt }], max_tokens: 200 },
});
console.log(res.choices[0].message.content);
console.log(`cost $${res.usage?.cost_usd}`);
