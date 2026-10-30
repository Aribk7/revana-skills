// Revana as tools for the Vercel AI SDK (v6+): the model can price a video for free, and makes one only after
// the user approves (needsApproval), capped at the quoted price.
//
//   import { streamText } from "ai";
//   import { revanaTools } from "./revana-tools";
//   const result = streamText({ model, tools: revanaTools, prompt: "Make a 5 s video of a paper boat in the rain" });
//
// Needs REVANA_API_KEY on the server. npm i ai zod
import { tool } from "ai";
import { z } from "zod";

const API = "https://api.revana.si";

async function revana(path: string, init: RequestInit = {}) {
  const res = await fetch(API + path, {
    ...init,
    headers: { authorization: `Bearer ${process.env.REVANA_API_KEY}`, "content-type": "application/json", ...init.headers },
  });
  const body = await res.json();
  if (!res.ok) throw new Error(`${res.status} ${body.error?.code}: ${body.error?.message}`);
  return body;
}

const videoInput = z.object({
  model: z.string().describe("A Revana video model id, e.g. seedance-2.5, veo-3.1-fast, kling-3.0, wan-3.0"),
  prompt: z.string(),
  duration: z.number().int().describe("Seconds; must be one the model lists"),
  resolution: z.string().describe("e.g. 480p, 720p, 1080p; must be one the model lists"),
  aspect_ratio: z.string().optional().describe("e.g. 16:9, 9:16, 1:1"),
  audio: z.boolean().optional(),
  image_url: z.string().url().optional().describe("Public https link to the first frame"),
});

async function price(input: z.infer<typeof videoInput>) {
  const { data } = await (await fetch(`${API}/v1/models`)).json();
  const m = data.find((x: { id: string }) => x.id === input.model);
  if (!m) throw new Error(`Unknown model ${input.model}; see GET ${API}/v1/models`);
  const usd = m.price.usd;
  const each = typeof usd === "number" ? usd : (input.audio ? usd[`${input.resolution}+audio`] : undefined) ?? usd[input.resolution];
  if (each === undefined) throw new Error(`${input.model} has no ${input.resolution} price: ${JSON.stringify(usd)}`);
  return Math.ceil(each * input.duration * 100) / 100;
}

export const revanaTools = {
  listVideoModels: tool({
    description: "List Revana video models with their options and live price per second. Free.",
    inputSchema: z.object({}),
    execute: async () => {
      const { data } = await (await fetch(`${API}/v1/models`)).json();
      return data
        .filter((m: { kind: string }) => m.kind === "video")
        .map((m: { id: string; options: unknown; price: unknown }) => ({ id: m.id, options: m.options, price: m.price }));
    },
  }),

  quoteVideo: tool({
    description: "Price a video before making it. Free. Tell the user the price and ask before generateVideo.",
    inputSchema: videoInput,
    execute: async (input) => ({ usd: await price(input) }),
  }),

  generateVideo: tool({
    description: "Make a video on Revana. Costs money: quote it first and pass max_cost_usd at the agreed price.",
    inputSchema: videoInput.extend({ max_cost_usd: z.number().positive().describe("The price the user agreed to") }),
    needsApproval: true, // the user approves every spend in the UI
    execute: async ({ model, max_cost_usd, ...input }) => {
      const gen = await revana("/v1/generations", {
        method: "POST",
        headers: { "idempotency-key": crypto.randomUUID() },
        body: JSON.stringify({ model, input, max_cost_usd }),
      });
      return { id: gen.id, status: gen.status, quoted_usd: gen.quoted_usd };
    },
  }),

  getVideo: tool({
    description: "Check a Revana generation. When status is succeeded, output.urls has the file links.",
    inputSchema: z.object({ id: z.string() }),
    execute: async ({ id }) => {
      const g = await revana(`/v1/generations/${encodeURIComponent(id)}`);
      return { status: g.status, cost_usd: g.cost_usd, urls: g.output?.urls, error: g.error };
    },
  }),
};
