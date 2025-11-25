#!/bin/bash
#!/usr/bin/env bash
set -euo pipefail

# Build output directory (do not modify source files in-place)
OUT_DIR="build"
SOURCE_DIR="website"
mkdir -p "$OUT_DIR"

# Generate config.js into build directory from environment variables at build time
cat > "$OUT_DIR/config.js" << EOF
// Contact form configuration - Generated at build time
window.APP_CONFIG = {
    WEB3FORMS_ACCESS_KEY: '${WEB3FORMS_ACCESS_KEY:-YOUR_KEY_HERE}'
};
EOF

echo "✅ Generated $OUT_DIR/config.js with Web3Forms key"

# Copy static site into build directory and inject DEMO_KEY into the copy if provided
cp "$SOURCE_DIR"/*.html "$OUT_DIR/"

if [ -n "${DEMO_KEY:-}" ]; then
    echo "🔐 Injecting DEMO_KEY into $OUT_DIR/index.html"
    if command -v python3 >/dev/null 2>&1; then
        python3 scripts/inject_demo_key.py "$DEMO_KEY" "$OUT_DIR/index.html"
    else
        echo "python3 not found; skipping DEMO_KEY injection"
    fi
else
    echo "No DEMO_KEY provided; leaving $OUT_DIR/index.html unchanged"
fi

echo "✅ Build complete. Output in $OUT_DIR/"
