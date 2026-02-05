@echo off
setlocal
set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "REQ=%ROOT%app\requirements.txt"
set "HASH_FILE=%VENV%\requirements.sha256"

if /i "%~1"=="--run" goto run

set "SHOW_CONSOLE=1"
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "try { $p = '%ROOT%app\storage\settings.json'; if (Test-Path $p) { $s = (Get-Content $p -Raw | ConvertFrom-Json); if ($s.settings.'show-console') { '1' } else { '0' } } else { '1' } } catch { '1' }"`) do set "SHOW_CONSOLE=%%A"

if "%SHOW_CONSOLE%"=="1" (
  "%~f0" --run
) else (
  powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c \"\"%~f0\" --run\"' -WorkingDirectory '%ROOT%'"
)
exit /b

:run
pushd "%ROOT%"
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3.10+ and try again.
  pause
  exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
  python -m venv "%VENV%"
)

set "NEED_INSTALL=1"
if exist "%HASH_FILE%" (
  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '%REQ%').Hash"`) do set "REQ_HASH=%%H"
  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "Get-Content '%HASH_FILE%' -Raw"`) do set "OLD_HASH=%%H"
  if /i "%REQ_HASH%"=="%OLD_HASH%" set "NEED_INSTALL=0"
)

if "%NEED_INSTALL%"=="1" (
  "%VENV%\Scripts\python.exe" -m pip install --upgrade pip
  "%VENV%\Scripts\python.exe" -m pip install -r "%REQ%"
  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "(Get-FileHash -Algorithm SHA256 '%REQ%').Hash"`) do set "REQ_HASH=%%H"
  >"%HASH_FILE%" echo %REQ_HASH%
)

"%VENV%\Scripts\python.exe" main.py
popd
exit /b
