// POST /api/revana/generations: start a Revana generation from your Next.js app (App Router).
// The key stays on the server (REVANA_API_KEY). Your users never see it, and this route caps what one
// request may spend, so a stranger calling it cannot drain your balance.
//
// Body: { "model": "seedance-2.5", "input": { "prompt": "...", "duration": 5, "resolution": "720p" } }
// Answers the generation (202) with its quote; poll GET /api/revana/generations/{id}.

const API = "https://api.revana.si";
const ALLOWED = new Set(["seedance-2.5", "veo-3.1-fast", "kling-3.0", "wan-3.0", "nano-banana-pro", "gpt-image-2"]);
const MAX_USD = Number(process.env.REVANA_MAX_COST_USD ?? 2); // the most one request may cost

type Price = { unit: string; usd: number | Record<string, number> };

/** Price one generation from the live list (cached for 5 minutes). Returns null if a value isn't priced. */
async function quote(model: string, input: Record<string, unknown>): Promise<number | null> {
  const res = await fetch(`${API}/v1/models`, { next: { revalidate: 300 } });
  const { data } = (await res.json()) as { data: { id: string; price: Price }[] };
  const price = data.find((m) => m.id === model)?.price;
  if (!price) return null;
  const res_ = String(input.resolution ?? "");
  const each =
    typeof price.usd === "number"
      ? price.usd
      : (input.audio ? price.usd[`${res_}+audio`] : undefined) ?? price.usd[res_];
  if (each === undefined) return null;
  const seconds = price.unit === "per_second" ? Number(input.duration ?? 5) : 1;
  return Math.ceil(each * seconds * 100) / 100;
}

export async function POST(req: Request) {
  // Put your own auth here (session check, rate limit) before spending anything.
  const { model, input } = (await req.json()) as { model: string; input: Record<string, unknown> };
  if (!ALLOWED.has(model)) return Response.json({ error: "model not allowed" }, { status: 400 });

  const usd = await quote(model, input);
  if (usd === null) return Response.json({ error: "set a resolution the model offers" }, { status: 400 });
  if (usd > MAX_USD) return Response.json({ error: `costs $${usd}, over the $${MAX_USD} limit` }, { status: 402 });

  const res = await fetch(`${API}/v1/generations`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${process.env.REVANA_API_KEY}`,
      "content-type": "application/json",
      "idempotency-key": req.headers.get("idempotency-key") ?? crypto.randomUUID(),
    },
    body: JSON.stringify({ model, input, max_cost_usd: usd }),
  });
  return Response.json(await res.json(), { status: res.status });
}
