#!/usr/bin/env bash
# Boots the Python gxwf-web server against a cloned E2E fixture workspace and
# runs the TypeScript Playwright suite from the configured TS worktree against
# it. Requires the TS worktree to support GXWF_E2E_EXTERNAL_URL (harness skip).
set -euo pipefail

GXWF_TS_WORKTREE="${GXWF_TS_WORKTREE:-/Users/jxc755/projects/worktrees/galaxy-tool-util/branch/styling}"
GXWF_UI_DIST="${GXWF_UI_DIST:-$GXWF_TS_WORKTREE/packages/gxwf-ui/dist}"
SEED_DIR="${GXWF_E2E_SEED_DIR:-$GXWF_TS_WORKTREE/packages/gxwf-e2e/fixtures/workspace-seed}"

if [[ ! -d "$GXWF_UI_DIST" ]]; then
  echo "[run-e2e] gxwf-ui dist not found at $GXWF_UI_DIST — run 'make build-ui' first" >&2
  exit 1
fi
if [[ ! -d "$SEED_DIR" ]]; then
  echo "[run-e2e] E2E seed fixture not found at $SEED_DIR" >&2
  exit 1
fi

# Stage a clean copy of the seed workspace so write-back tests don't mutate the
# pristine fixture.
WORKSPACE="$(mktemp -d -t gxwf-e2e-XXXXXX)"
cp -R "$SEED_DIR"/ "$WORKSPACE"/
trap 'rm -rf "$WORKSPACE"' EXIT

# Pick a random free port. Unfortunately `python -m gxwf_web --port 0` isn't a
# thing (uvicorn prints the bound port after `listen`), so we just pick via a
# transient socket and hope for the best.
PORT="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
BASE_URL="http://127.0.0.1:${PORT}"

uv run gxwf-web --ui-dir "$GXWF_UI_DIST" --host 127.0.0.1 --port "$PORT" "$WORKSPACE" &
SERVER_PID=$!
trap 'kill "$SERVER_PID" >/dev/null 2>&1 || true; rm -rf "$WORKSPACE"' EXIT

# Wait for server readiness.
for _ in $(seq 1 60); do
  if curl -sSf "$BASE_URL/workflows" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

export GXWF_E2E_EXTERNAL_URL="$BASE_URL"
export GXWF_E2E_EXTERNAL_WORKSPACE="$WORKSPACE"
export GXWF_E2E_EXTERNAL_SEED="$SEED_DIR"
export GXWF_E2E_SKIP_UI_BUILD=1

cd "$GXWF_TS_WORKTREE"
pnpm --filter @galaxy-tool-util/gxwf-e2e test "$@"
