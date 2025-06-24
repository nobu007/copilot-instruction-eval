@echo off
setlocal

for /f "tokens=1,* delims==" %%a in ('findstr "AGENT_V1_API_KEY" .env') do (
    set "GEMINI_API_KEY=%%b"
)

if not defined GEMINI_API_KEY (
    echo ERROR: AGENT_V1_API_KEY not found in .env file.
    exit /b 1
)

curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=%GEMINI_API_KEY%" ^
  -H "Content-Type: application/json" ^
  -d "{\"contents\":[{\"parts\":[{\"text\":\"Explain how AI works in a few words\"}]}]}"

echo.
endlocal
