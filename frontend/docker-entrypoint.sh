#!/bin/sh
set -eu

ENV_JS_PATH="/app/public/env.js"
API_URL="${NEXT_PUBLIC_API_URL:-}"
API_URL_ESCAPED=$(printf '%s' "$API_URL" | sed 's/\\/\\\\/g; s/"/\\"/g')

cat > "$ENV_JS_PATH" <<EOF
window.__ENV__ = window.__ENV__ || {};
window.__ENV__.NEXT_PUBLIC_API_URL = "${API_URL_ESCAPED}";
EOF

exec "$@"
