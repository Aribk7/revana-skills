// GET /api/revana/generations/{id}: a generation's status. Poll every few seconds until "succeeded" or "failed".

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^gen_[A-Za-z0-9]+$/.test(id)) return Response.json({ error: "bad id" }, { status: 400 });
  const res = await fetch(`https://api.revana.si/v1/generations/${id}`, {
    headers: { authorization: `Bearer ${process.env.REVANA_API_KEY}` },
    cache: "no-store",
  });
  const g = await res.json();
  if (!res.ok) return Response.json(g, { status: res.status });
  // Hand the browser only what it needs; the file comes through ./content.
  return Response.json({ id: g.id, status: g.status, cost_usd: g.cost_usd, error: g.error, output: g.output && { ...g.output, urls: undefined } });
}
