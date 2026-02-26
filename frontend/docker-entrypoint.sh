#!/bin/sh
set -eu

ENV_JS_PATH="/app/public/env.js"
API_URL="${NEXT_PUBLIC_API_URL:-}"

# Escape the API_URL for safe JSON output (handle quotes, backslashes, newlines)
API_URL_ESCAPED=$(printf '%s' "$API_URL" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/$/\\n/' | tr -d '\n')

# Use quoted heredoc to prevent shell expansion of $ and backticks
cat > "$ENV_JS_PATH" <<'EOF'
window.__ENV__ = window.__ENV__ || {};
window.__ENV__.NEXT_PUBLIC_API_URL = 
EOF

# Append the escaped API_URL as a JSON string
printf '"%s"' "$API_URL_ESCAPED" >> "$ENV_JS_PATH"
echo ';' >> "$ENV_JS_PATH"

exec "$@"
