#!/usr/bin/env bash
set -euo pipefail

ZIP="${1:-loki-refactored-readme-compaction-cache.zip}"
TARGET="${2:-.}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

unzip -q "$ZIP" -d "$TMP"

SOURCE="$(find "$TMP" -mindepth 1 -maxdepth 1 -type d | head -n 1)"

if [ -z "$SOURCE" ]; then
    SOURCE="$TMP"
fi

rsync -av --delete \
    --exclude='.git/' \
    --exclude='.venv/' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='node_modules/' \
    --exclude='.DS_Store' \
    "$SOURCE/" "$TARGET/"

echo
echo "Loki tree synchronized and stale files removed."
