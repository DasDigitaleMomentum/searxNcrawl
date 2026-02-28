#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

URL_FILE="${REGRESSION_URL_FILE:-scripts/regression-urls.txt}"
DELAY="${REGRESSION_DELAY:-2.5}"
WAIT_UNTIL="${REGRESSION_WAIT_UNTIL:-networkidle}"
AGGRESSIVE_SPA="${REGRESSION_AGGRESSIVE_SPA:-false}"

if [ ! -f "$URL_FILE" ]; then
  echo "Regression URL file not found: $URL_FILE"
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
if [ -x ".venv/bin/python" ] && [ "${PYTHON_BIN}" = "python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

TOTAL=0
FAILED=0

echo "Running regression crawl suite"
echo "URL file: $URL_FILE"
echo "Delay: ${DELAY}s | Wait until: $WAIT_UNTIL | Aggressive SPA: $AGGRESSIVE_SPA"
echo ""

while IFS= read -r raw_line || [ -n "$raw_line" ]; do
  url="$(printf '%s' "$raw_line" | sed 's/#.*$//' | xargs)"
  if [ -z "$url" ]; then
    continue
  fi

  TOTAL=$((TOTAL + 1))
  out_file="$TMP_DIR/out-${TOTAL}.json"
  err_file="$TMP_DIR/err-${TOTAL}.log"

  cmd=("$PYTHON_BIN" -m crawler.cli crawl "$url" --json --delay "$DELAY" --wait-until "$WAIT_UNTIL")
  if [ "$AGGRESSIVE_SPA" = "true" ]; then
    cmd+=(--aggressive-spa)
  fi

  echo "[$TOTAL] $url"
  if "${cmd[@]}" >"$out_file" 2>"$err_file"; then
    status="$("$PYTHON_BIN" - "$out_file" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)
print(data.get("status", "failed"))
PY
)"
    if [ "$status" = "success" ]; then
      echo "  OK"
    else
      FAILED=$((FAILED + 1))
      echo "  FAIL (status=${status})"
      head -n 20 "$out_file"
    fi
  else
    FAILED=$((FAILED + 1))
    echo "  FAIL (crawl command error)"
    head -n 20 "$err_file"
  fi
done <"$URL_FILE"

echo ""
echo "Completed regression crawl suite: ${TOTAL} total, ${FAILED} failed"
if [ "$FAILED" -gt 0 ]; then
  exit 1
fi
