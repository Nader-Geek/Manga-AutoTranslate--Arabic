@echo off
rem ============================================================
rem  Manga-AutoTranslate - Arabic, 100%% local (Ollama) - Windows
rem  Usage:  run_local_ar.bat                   (interactive app)
rem          run_local_ar.bat INPUT OUTPUT.pdf  (direct CLI)
rem ============================================================
setlocal
cd /d "%~dp0"

if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=qwen2.5:7b-instruct
set MANGA_TARGET_LANG=ar
if "%MANGA_AR_DIALECT%"=="" set MANGA_AR_DIALECT=msa
if "%OLLAMA_CONTEXT_LENGTH%"=="" set OLLAMA_CONTEXT_LENGTH=8192
set PYTHONUTF8=1

where ollama >nul 2>&1
if errorlevel 1 (
    echo [X] Ollama is not installed. Download: https://ollama.com/download
    exit /b 1
)

curl -fs http://localhost:11434/api/tags >nul 2>&1
if errorlevel 1 (
    echo [i] Starting ollama server...
    start "" /b ollama serve
    timeout /t 5 /nobreak >nul
)

ollama list | findstr /b /c:"%OLLAMA_MODEL%" >nul 2>&1
if errorlevel 1 (
    echo [i] Pulling model %OLLAMA_MODEL% ^(one time^)...
    ollama pull %OLLAMA_MODEL%
)

set DEVICE=--cpu
if "%USE_GPU%"=="1" set DEVICE=--gpu

if "%~2"=="" (
    python manga_app.py
) else (
    python manga.py -i "%~1" -o "%~2" --font fonts\Vazirmatn-Bold.ttf --provider ollama --model %OLLAMA_MODEL% --target-lang ar --ar-dialect %MANGA_AR_DIALECT% --bubbles-per-request 4 --batch-workers 1 --workers 1 %DEVICE%
)
endlocal
