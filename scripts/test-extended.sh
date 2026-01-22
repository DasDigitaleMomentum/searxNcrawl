#!/usr/bin/env sh
# Extended real-world tests for searxNcrawl MCP server
# Tests all tools including new features like remove_links and Unicode handling
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
PASSED=0
FAILED=0

echo "=========================================="
echo "searxNcrawl Extended Test Suite"
echo "=========================================="
echo ""

echo "Starting Docker Compose..."
docker compose up --build -d

# Wait for server to be ready
echo "Waiting for MCP server to start..."
sleep 5

cleanup() {
  echo ""
  echo "=========================================="
  echo "Test Results: $PASSED passed, $FAILED failed"
  echo "=========================================="
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
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-extended","version":"1.0"}}}'

SESSION_ID="$(awk 'BEGIN{IGNORECASE=1} /^mcp-session-id:/ {print $2}' "$INIT_RESPONSE_HEADERS" | tr -d '\r')"

if [ -z "$SESSION_ID" ]; then
  echo "❌ FAILED: Could not obtain MCP session id."
  cat "$INIT_RESPONSE_BODY"
  exit 1
fi

echo "✓ Session ID: $SESSION_ID"
echo ""

call_tool() {
  NAME="$1"
  PAYLOAD="$2"
  EXPECT_PATTERN="${3:-}"
  
  echo "Testing: $NAME"
  RESPONSE=$(curl -sS \
    -X POST "$BASE_URL" \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -H "Mcp-Session-Id: $SESSION_ID" \
    -d "$PAYLOAD")
  
  # Check for error in response
  if echo "$RESPONSE" | grep -q '"error"'; then
    echo "  ❌ FAILED: Error in response"
    echo "$RESPONSE" | head -c 200
    echo ""
    FAILED=$((FAILED + 1))
  fi
  
  # Check for expected pattern if provided
  if [ -n "$EXPECT_PATTERN" ]; then
    if echo "$RESPONSE" | grep -q "$EXPECT_PATTERN"; then
      echo "  ✓ PASSED: Found expected pattern"
      PASSED=$((PASSED + 1))
    else
      echo "  ❌ FAILED: Expected pattern not found: $EXPECT_PATTERN"
      echo "$RESPONSE" | head -c 200
      echo ""
      FAILED=$((FAILED + 1))
    fi
  else
    echo "  ✓ PASSED: Response received"
    PASSED=$((PASSED + 1))
  fi
  echo ""
}

echo "=========================================="
echo "1. Basic Crawl Tests"
echo "=========================================="

call_tool "crawl - single page" \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"crawl","arguments":{"urls":["https://example.com"]}}}' \
  "Example Domain"

call_tool "crawl - JSON output" \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"crawl","arguments":{"urls":["https://example.com"],"output_format":"json"}}}' \
  "crawled_at"

echo "=========================================="
echo "2. remove_links Feature Tests"
echo "=========================================="

call_tool "crawl - with remove_links=true" \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"crawl","arguments":{"urls":["https://example.com"],"remove_links":true}}}'

echo "=========================================="
echo "3. Site Crawl Tests"
echo "=========================================="

call_tool "crawl_site - basic" \
  '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"crawl_site","arguments":{"url":"https://example.com","max_depth":1,"max_pages":1}}}' \
  "Example Domain"

call_tool "crawl_site - with remove_links" \
  '{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"crawl_site","arguments":{"url":"https://example.com","max_depth":1,"max_pages":1,"remove_links":true}}}'

echo "=========================================="
echo "4. Search Tests"
echo "=========================================="

call_tool "search - basic" \
  '{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"search","arguments":{"query":"python programming","max_results":3}}}' \
  "results"

call_tool "search - German query (Unicode test)" \
  '{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"search","arguments":{"query":"Köln Wetter","language":"de","max_results":3}}}' \
  "results"

echo "=========================================="
echo "5. MCP Schema Tests"
echo "=========================================="

# Test tools/list to verify no output_schema wrapper
echo "Testing: tools/list (schema validation)"
TOOLS_RESPONSE=$(curl -sS \
  -X POST "$BASE_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SESSION_ID" \
  -d '{"jsonrpc":"2.0","id":9,"method":"tools/list","params":{}}')

if echo "$TOOLS_RESPONSE" | grep -q "x-fastmcp-wrap-result"; then
  echo "  ❌ FAILED: Found x-fastmcp-wrap-result in schema (should be removed)"
  FAILED=$((FAILED + 1))
else
  echo "  ✓ PASSED: No output_schema wrapper found"
  PASSED=$((PASSED + 1))
fi

# Check for remove_links parameter in schema
if echo "$TOOLS_RESPONSE" | grep -q "remove_links"; then
  echo "  ✓ PASSED: remove_links parameter present in schema"
  PASSED=$((PASSED + 1))
else
  echo "  ❌ FAILED: remove_links parameter not found in schema"
  FAILED=$((FAILED + 1))
fi

echo ""
echo "=========================================="
echo "All tests completed!"
echo "=========================================="
