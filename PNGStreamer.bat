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
if not exist "%ROOT%images" (
  mkdir "%ROOT%images" >nul 2>nul
)
if not exist "%ROOT%app\storage" (
  mkdir "%ROOT%app\storage" >nul 2>nul
)
call :ensure_python
if errorlevel 1 (
  pause
  exit /b 1
)

if not exist "%VENV%\Scripts\python.exe" (
  call %PY_CMD% -m venv "%VENV%"
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

:ensure_python
set "PY_CMD="
call :check_python_cmd python
if not errorlevel 1 exit /b 0
call :check_python_cmd py -3.13
if not errorlevel 1 exit /b 0
call :install_python
if errorlevel 1 exit /b 1
call :check_python_cmd py -3.13
if not errorlevel 1 exit /b 0
call :check_python_cmd python
if not errorlevel 1 exit /b 0
echo Python 3.13+ is required but was not detected after installation.
exit /b 1

:check_python_cmd
set "PY_CMD=%*"
call %PY_CMD% -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,13) else 1)" >nul 2>nul
if errorlevel 1 (
  set "PY_CMD="
  exit /b 1
)
exit /b 0

:install_python
echo Python 3.13+ is required. Attempting to install via winget...
where winget >nul 2>nul
if errorlevel 1 (
  echo Winget not found. Please install Python 3.13 manually.
  exit /b 1
)
winget install -e --id Python.Python.3.13 -h --accept-source-agreements --accept-package-agreements
if errorlevel 1 (
  echo Python installation failed.
  exit /b 1
)
exit /b 0
