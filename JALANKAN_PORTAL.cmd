@echo off
setlocal
cd /d "%~dp0"
if not exist ".cache\venv\Scripts\python.exe" (
  python -m venv .cache\venv
  if errorlevel 1 goto failed
)
".cache\venv\Scripts\python.exe" -c "import fastapi, uvicorn, pwdlib, pydantic_settings" >nul 2>&1
if errorlevel 1 (
  ".cache\venv\Scripts\python.exe" -m pip install --require-hashes -r app\requirements\web.lock
  if errorlevel 1 goto failed
)
if not exist "app\web\dist\index.html" (
  pushd app\web
  call npm ci
  if errorlevel 1 goto build_failed
  call npm run build
  if errorlevel 1 goto build_failed
  popd
)
echo Portal: http://127.0.0.1:8000
echo Buka alamat portal di atas untuk melanjutkan.
echo Tutup server dengan Ctrl+C. Database sensus hanya dibaca.
".cache\venv\Scripts\python.exe" -B app\scripts\run_portal.py
goto end
:build_failed
popd
:failed
echo Portal belum dapat dijalankan. Periksa Python 3.11+, Node 22.20+, dan hasil perintah di atas.
pause
:end
endlocal
