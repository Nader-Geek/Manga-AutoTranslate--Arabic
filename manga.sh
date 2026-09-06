#!/usr/bin/env bash
# ============================================
#   Manga Translator - Linux/macOS launcher
# ============================================
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[X] python3 not found. Install: sudo apt install python3 python3-pip python3-tk"
    exit 1
fi

deps() {
    echo "[i] Checking dependencies (first run may take a while)..."
    python3 -c "import gradio" 2>/dev/null || python3 -m pip install -q gradio
    python3 -c "import cv2" 2>/dev/null || python3 -m pip install -q opencv-python pillow numpy
}

web_bg() {
    
    if ! command -v tmux >/dev/null 2>&1; then
        echo "[X] tmux نصب نیست: sudo apt install tmux  (یا گزینهٔ 2 = foreground)"
        return
    fi
    if tmux has-session -t manga 2>/dev/null; then
        echo "[i] سرور از قبل در tmux اجراست — لینک: tmux attach -t manga"
        return
    fi
    deps
    tmux new-session -d -s manga "python3 manga_app.py --web"
    echo "[✓] سرور در پس‌زمینه (tmux session: manga) اجرا شد."
    echo "    لینک:  http://<ip>:7860"
    echo "    مشاهدهٔ لاگ:  tmux attach -t manga   (خروج: Ctrl+B بعد D)"
    echo "    توقف سرور:   tmux kill-session -t manga"
}

while true; do
    clear
    echo ""
    echo "  ============================================"
    echo "     Manga Translator"
    echo "  ============================================"
    echo ""
    echo "    [1] App    - desktop window"
    echo "    [2] Web    - browser interface (terminal stays open)"
    echo "    [3] Web BG - server in tmux (survives terminal close)"
    echo "    [4] CLI    - asks for input in terminal"
    echo "    [5] Exit"
    echo ""
    read -rp "  Choose [1/2/3/4/5]: " choice
    case "$choice" in
        1)
            if ! python3 -c "import tkinter" 2>/dev/null; then
                echo "[X] tkinter not available - install python3-tk. Use option 2 or 3."
                read -rp "Enter to continue..."
                continue
            fi
            deps
            python3 manga_app.py --desktop
            read -rp "Enter to continue..."
            ;;
        2)
            deps
            echo "[i] Web UI on http://127.0.0.1:7860 — auto-restart on crash (Ctrl+C x2 to stop)"
            while true; do
                python3 -u manga_app.py --web
                echo "[!] Server exited — restart in 3s (Ctrl+C to stop fully)"
                sleep 3
            done
            ;;
        3)
            web_bg
            sleep 3
            ;;
        4)
            deps
            python3 manga_app.py --cli
            read -rp "Enter to continue..."
            ;;
        5) exit 0 ;;
    esac
done
