# Revana MCP server

Remote MCP at **`https://revana.si/api/mcp`** (streamable HTTP). Your agent can list models, get a free quote,
make a video on your prepaid credits once you say yes, restage clips (Nemesis), upload files and fetch download
links. Most apps sign you in with OAuth: approve the connection on revana.si and the app gets its own key, which
you can revoke from the dashboard.

| App | Add it |
|---|---|
| Claude Code | `claude mcp add --transport http revana https://revana.si/api/mcp`, then `/mcp` to sign in |
| Codex CLI | `codex mcp add revana --url https://revana.si/api/mcp` then `codex mcp login revana` |
| VS Code | `code --add-mcp '{"name":"revana","type":"http","url":"https://revana.si/api/mcp"}'` |
| Cursor | copy [`cursor.mcp.json`](cursor.mcp.json) to `.cursor/mcp.json` (or `~/.cursor/mcp.json`) |
| Claude.ai / Desktop | Settings, Connectors, Add custom connector, paste the URL |
| ChatGPT | Settings, Apps & Connectors, Advanced: Developer mode on; Create, paste the URL, OAuth |

With an API key instead of OAuth (any client that takes a URL and headers), see
[`mcp-with-key.json`](mcp-with-key.json). Claude Code expands `${REVANA_API_KEY}` from the environment; Cursor
writes it `${env:REVANA_API_KEY}`. Keep the key out of files you commit.

Tools: `list_models`, `get_quote`, `generate_video`, `get_video`, `get_video_link`, `quote_nemesis`,
`make_nemesis`, `upload_file`, `get_balance`. The server asks the agent to quote first and pass a price cap.
Details: https://revana.si/mcp
