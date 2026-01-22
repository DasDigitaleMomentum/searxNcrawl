#!/usr/bin/env sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f ".env" ]; then
  echo "Missing .env. Copy .env.example to .env and set SEARXNG_URL (and MCP_PORT if needed)."
  exit 1
fi

MCP_PORT="$(grep -E '^MCP_PORT=' .env | tail -n1 | cut -d= -f2 || true)"
if [ -z "${MCP_PORT}" ]; then
  MCP_PORT=9555
fi

BASE_URL="http://localhost:${MCP_PORT}/mcp"

echo "Starting Docker Compose..."
docker compose up --build -d

cleanup() {
  echo "Stopping Docker Compose..."
  docker compose down
}
trap cleanup EXIT INT TERM

echo "Initializing MCP session..."
INIT_RESPONSE_HEADERS="$(mktemp)"
INIT_RESPONSE_BODY="$(mktemp)"

curl -sS -D "$INIT_RESPONSE_HEADERS" -o "$INIT_RESPONSE_BODY" \
  -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-realworld","version":"1.0"}}}'

SESSION_ID="$(awk 'BEGIN{IGNORECASE=1} /^mcp-session-id:/ {print $2}' "$INIT_RESPONSE_HEADERS" | tr -d '\r')"

if [ -z "$SESSION_ID" ]; then
  echo "Failed to obtain MCP session id."
  cat "$INIT_RESPONSE_BODY"
  exit 1
fi

echo "Session ID: $SESSION_ID"

call_tool() {
  NAME="$1"
  PAYLOAD="$2"
  echo "Calling tool: $NAME"
  curl -sS \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d "$PAYLOAD" | head -n 5
  echo ""
}

call_tool "crawl" '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"crawl","arguments":{"urls":["https://example.com"]}}}'
call_tool "crawl_site" '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"crawl_site","arguments":{"url":"https://example.com","max_depth":1,"max_pages":2}}}'
call_tool "search" '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search","arguments":{"query":"python asyncio tutorial","max_results":3}}}'

echo "Done."
