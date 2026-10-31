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
type Quote = { usd: number; by: "server" | "list" } | { error: unknown; status: number };

/**
 * The server's free quote (POST /v1/generations/quote) prices the exact request. API versions from before the
 * 2026-10-31 deploy answer it 404; then the live list prices it.
 */
async function quote(model: string, input: Record<string, unknown>): Promise<Quote> {
  const res = await fetch(`${API}/v1/generations/quote`, {
    method: "POST",
    headers: { authorization: `Bearer ${process.env.REVANA_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({ model, input }),
    cache: "no-store",
  });
  if (res.ok) return { usd: ((await res.json()) as { quoted_usd: number }).quoted_usd, by: "server" };
  if (res.status !== 404) return { error: (await res.json().catch(() => ({}))).error, status: res.status };
  const usd = await listQuote(model, input);
  return usd === null ? { error: "set a resolution the model offers", status: 400 } : { usd, by: "list" };
}

/** Price one generation from the live list (cached for 5 minutes). Returns null if a value isn't priced. */
async function listQuote(model: string, input: Record<string, unknown>): Promise<number | null> {
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
  return Math.ceil(Math.round(each * seconds * 1e6) / 1e4 - 1e-9) / 100; // up to a whole cent, without float noise
}

export async function POST(req: Request) {
  // Put your own auth here (session check, rate limit) before spending anything.
  const { model, input } = (await req.json()) as { model: string; input: Record<string, unknown> };
  if (!ALLOWED.has(model)) return Response.json({ error: "model not allowed" }, { status: 400 });

  const q = await quote(model, input);
  if ("error" in q) return Response.json({ error: q.error }, { status: q.status });
  if (q.usd > MAX_USD) return Response.json({ error: `costs $${q.usd}, over the $${MAX_USD} limit` }, { status: 402 });
  // The list does not show what a start image adds on some models (Seedance 2.5), so a list quote with image_url
  // is capped at this route's limit instead; the server's quote is exact.
  const maxCost = q.by === "list" && input.image_url ? MAX_USD : q.usd;

  // Revana keeps Idempotency-Keys per account (yours), so a key from the browser must be scoped to the signed-in
  // user, or two users who sent the same key would share one generation. The browser makes one key per video and
  // resends it only after a timeout or a 5xx; after a failed generation it makes a new one.
  const userId = "anonymous"; // your session's user id
  const clientKey = req.headers.get("idempotency-key");
  const idempotencyKey = clientKey ? `${userId}:${clientKey}`.slice(0, 200) : crypto.randomUUID();

  const res = await fetch(`${API}/v1/generations`, {
    method: "POST",
    headers: {
      authorization: `Bearer ${process.env.REVANA_API_KEY}`,
      "content-type": "application/json",
      "idempotency-key": idempotencyKey,
    },
    body: JSON.stringify({ model, input, max_cost_usd: maxCost }),
  });
  // Errors pass through with their code and request_id, so a support request can name the exact call.
  return Response.json(await res.json(), { status: res.status });
}
