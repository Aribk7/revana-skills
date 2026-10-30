// GET /api/revana/generations/{id}/content: send the browser to the finished file.
// Revana answers a redirect to a short-lived file link; pass that on, so the key never leaves the server.

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^gen_[A-Za-z0-9]+$/.test(id)) return Response.json({ error: "bad id" }, { status: 400 });
  const res = await fetch(`https://api.revana.si/v1/generations/${id}/content`, {
    headers: { authorization: `Bearer ${process.env.REVANA_API_KEY}` },
    redirect: "manual",
    cache: "no-store",
  });
  const location = res.headers.get("location");
  if (location) return Response.redirect(location, 302);
  return new Response(res.body, { status: res.status, headers: { "content-type": res.headers.get("content-type") ?? "application/octet-stream" } });
}
