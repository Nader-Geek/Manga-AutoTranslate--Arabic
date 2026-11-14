#!/usr/bin/env bash
# Pull the latest upstream fork changes (amirwolf512k/Manga-AutoTranslate) into this branch,
# then re-run the checks. On conflict it stops so you can resolve (usually only in
# manga_sections/95_run.py and 99_cli.py, where our --export-typer / blank-page patches live).
set -euo pipefail
cd "$(dirname "$0")/.."
git remote get-url fork >/dev/null 2>&1 || git remote add fork https://github.com/amirwolf512k/Manga-AutoTranslate.git
git fetch fork
git merge --no-edit fork/main || { echo "CONFLICT: resolve, then rerun the checks below"; exit 1; }
python3 scripts/build_manga.py --check
for t in tests/test_bot_*.py; do python3 "$t"; done
echo "synced OK — review 'git log' then push"
