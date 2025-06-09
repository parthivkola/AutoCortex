@echo off
echo Starting Ollama...
start "" /MIN ollama serve
timeout /t 3 >nul

echo Pulling Mistral (if not already present)...
ollama pull mistral

echo Starting AutoCortex...
venv\Scripts\python chat.py
pause
