#!/usr/bin/env bash
# ============================================================
#  Manga-AutoTranslate  -  Arabic, 100% local (Ollama)
#  Usage:  ./run_local_ar.sh                  (interactive app)
#          ./run_local_ar.sh INPUT OUTPUT.pdf (direct CLI)
#  Env:    OLLAMA_MODEL   (default qwen2.5:7b-instruct)
#          MANGA_AR_DIALECT=egyptian|msa  (default msa)
#          USE_GPU=1 to force --gpu, otherwise --cpu
# ============================================================
set -e
cd "$(dirname "$0")"

MODEL="${OLLAMA_MODEL:-qwen2.5:7b-instruct}"
export MANGA_TARGET_LANG=ar
export MANGA_AR_DIALECT="${MANGA_AR_DIALECT:-msa}"
# default Ollama context is small; the prompt + 6 bubbles need more
export OLLAMA_CONTEXT_LENGTH="${OLLAMA_CONTEXT_LENGTH:-8192}"

if ! command -v ollama >/dev/null 2>&1; then
    echo "[X] Ollama is not installed. Install it from https://ollama.com/download"
    echo "    Linux:  curl -fsSL https://ollama.com/install.sh | sh"
    exit 1
fi

if ! curl -fs http://localhost:11434/api/tags >/dev/null 2>&1; then
    echo "[i] Starting ollama server..."
    (ollama serve >/tmp/ollama.log 2>&1 &)
    for _ in $(seq 1 30); do
        curl -fs http://localhost:11434/api/tags >/dev/null 2>&1 && break
        sleep 1
    done
fi

if ! ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$MODEL"; then
    echo "[i] Pulling model $MODEL (one time)..."
    ollama pull "$MODEL"
fi

if [ "${USE_GPU:-0}" = "1" ]; then DEVICE="--gpu"; else DEVICE="--cpu"; fi

if [ $# -ge 2 ]; then
    exec python3 manga.py -i "$1" -o "$2" \
        --font fonts/Vazirmatn-Bold.ttf \
        --provider ollama --model "$MODEL" \
        --target-lang ar --ar-dialect "$MANGA_AR_DIALECT" \
        --bubbles-per-request 4 --batch-workers 1 --workers 1 \
        $DEVICE
else
    exec python3 manga_app.py
fi
