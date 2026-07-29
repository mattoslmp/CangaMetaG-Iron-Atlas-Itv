@echo off
setlocal
cd /d "%~dp0"
python scripts\check_app_runtime.py
if errorlevel 1 (
  echo.
  echo Runtime validation failed. See the message above.
  pause
  exit /b 1
)
python -m streamlit run app.py
endlocal
