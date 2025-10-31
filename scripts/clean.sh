#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"

echo "Cleaning caches, build artifacts, logs..."

rm -rf "$ROOT_DIR/frontend/node_modules" \
       "$ROOT_DIR/frontend/.vite" \
       "$ROOT_DIR/frontend/.cache" \
       "$ROOT_DIR/frontend/dist" \
       "$ROOT_DIR/backend/.venv" || true

find "$ROOT_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} +
find "$ROOT_DIR" -name "*.pyc" -type f -delete
find "$ROOT_DIR" -name ".pytest_cache" -type d -prune -exec rm -rf {} +
find "$ROOT_DIR" -name ".mypy_cache" -type d -prune -exec rm -rf {} +
find "$ROOT_DIR" -name ".ruff_cache" -type d -prune -exec rm -rf {} +
find "$ROOT_DIR" -name ".DS_Store" -type f -delete
find "$ROOT_DIR" -name "*.log" -type f -delete
find "$ROOT_DIR" -name "*.out" -type f -delete
find "$ROOT_DIR" -name "*.tmp" -type f -delete

echo "Done. To restore frontend deps: (cd frontend && npm ci)"

