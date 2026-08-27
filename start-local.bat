@echo off
set NICO_PROFILE=local
set NICO_DEFAULT_PROVIDER=ollama
set OLLAMA_BASE_URL=http://127.0.0.1:11434
if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=qwen2.5:3b
python -m nico.local_launcher %*
