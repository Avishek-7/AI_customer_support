#!/bin/sh
set -eu

ENV_JS_PATH="/app/public/env.js"
API_URL="${NEXT_PUBLIC_API_URL:-}"
API_URL_ESCAPED=$(printf '%s\n' "$API_URL" | jq -R -s -c .)

cat > "$ENV_JS_PATH" <<EOF
window.__ENV__ = window.__ENV__ || {};
window.__ENV__.NEXT_PUBLIC_API_URL = $API_URL_ESCAPED;
EOF

exec "$@"
