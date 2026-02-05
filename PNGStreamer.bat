@echo off
setlocal EnableExtensions

set "REPO_OWNER=ENCIDI"
set "REPO_NAME=PNG-Streamer"
set "DEFAULT_INSTALL=%LOCALAPPDATA%\PNGStreamer"

if /i "%~1"=="--run" goto run
if /i "%~1"=="--update" goto update

echo PNG Streamer installer
echo.
echo Install path (Enter for default):
echo %DEFAULT_INSTALL%
set /p INSTALL_DIR=>
if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%DEFAULT_INSTALL%"
set "INSTALL_DIR=%INSTALL_DIR:"=%"

if not exist "%INSTALL_DIR%" (
  mkdir "%INSTALL_DIR%" 2>nul
  if errorlevel 1 (
    echo.
    echo Cannot create folder: %INSTALL_DIR%
    echo If this path requires admin rights, run this .bat as Administrator.
    pause
    exit /b 1
  )
)

set "TEST_FILE=%INSTALL_DIR%\._write_test"
> "%TEST_FILE%" (echo test) 2>nul
if errorlevel 1 (
  echo.
  echo Cannot write to: %INSTALL_DIR%
  echo If this path requires admin rights, run this .bat as Administrator.
  pause
  exit /b 1
)
del "%TEST_FILE%" >nul 2>nul

call :download_repo
if errorlevel 1 exit /b 1

robocopy "%SRC_DIR%" "%INSTALL_DIR%" /E /NFL /NDL /NJH /NJS /NC /NS >nul

set "INSTALL_BAT=%INSTALL_DIR%\PNGStreamer.bat"
if not exist "%INSTALL_BAT%" (
  copy "%~f0" "%INSTALL_BAT%" >nul
)

if defined INSTALL_SHA (
  >"%INSTALL_DIR%\.installed_sha" echo %INSTALL_SHA%
)

echo.
echo Shortcut location:
echo 1) In installation folder (default)
echo 2) Desktop
echo 3) Start Menu
set /p SHORTCUT_CHOICE=>
if "%SHORTCUT_CHOICE%"=="" set "SHORTCUT_CHOICE=1"

set "SHORTCUT_DIR=%INSTALL_DIR%"
if "%SHORTCUT_CHOICE%"=="2" set "SHORTCUT_DIR=%USERPROFILE%\Desktop"
if "%SHORTCUT_CHOICE%"=="3" set "SHORTCUT_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

powershell -NoProfile -Command ^
  "$shell=New-Object -ComObject WScript.Shell;" ^
  "$lnk=Join-Path '%SHORTCUT_DIR%' 'PNG Streamer.lnk';" ^
  "$s=$shell.CreateShortcut($lnk);" ^
  "$s.TargetPath='%INSTALL_BAT%';" ^
  "$s.WorkingDirectory='%INSTALL_DIR%';" ^
  "$s.IconLocation=Join-Path '%INSTALL_DIR%' 'app\\ui\\PNGStreamer.ico';" ^
  "$s.Save();"

rd /s /q "%TMP_ROOT%" >nul 2>nul

echo.
echo Installed to: %INSTALL_DIR%
echo.
echo Starting PNG Streamer...
call "%INSTALL_BAT%" --run
exit /b

:run
set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "REQ=%ROOT%app\requirements.txt"
set "HASH_FILE=%VENV%\requirements.sha256"
set "SHA_FILE=%ROOT%\.installed_sha"

set "SHOW_CONSOLE=1"
for /f "usebackq delims=" %%A in (`powershell -NoProfile -Command "try { $p = '%ROOT%app\storage\settings.json'; if (Test-Path $p) { $s = (Get-Content $p -Raw | ConvertFrom-Json); if ($s.settings.'show-console') { '1' } else { '0' } } else { '1' } } catch { '1' }"`) do set "SHOW_CONSOLE=%%A"

if "%SHOW_CONSOLE%"=="0" (
  powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -WindowStyle Hidden -FilePath 'cmd.exe' -ArgumentList '/c \"\"%~f0\" --run\"' -WorkingDirectory '%ROOT%'"
  exit /b
)

call :check_update
if "%UPDATE_AVAILABLE%"=="1" (
  echo.
  echo Update available. Install now? (Y/N)
  set /p UPDATE_CONFIRM=>
  if /i "%UPDATE_CONFIRM%"=="Y" (
    call "%~f0" --update
  )
)

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

:update
set "ROOT=%~dp0"
set "INSTALL_DIR=%ROOT%"
call :download_repo
if errorlevel 1 exit /b 1
robocopy "%SRC_DIR%" "%INSTALL_DIR%" /E /NFL /NDL /NJH /NJS /NC /NS >nul
if defined INSTALL_SHA (
  >"%INSTALL_DIR%\.installed_sha" echo %INSTALL_SHA%
)
exit /b

:check_update
set "UPDATE_AVAILABLE=0"
set "UPDATE_BRANCH="
set "LATEST_SHA="
set "LOCAL_SHA="
if exist "%SHA_FILE%" (
  for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "Get-Content '%SHA_FILE%' -Raw"`) do set "LOCAL_SHA=%%H"
)
for /f "usebackq delims=" %%A in (`
  powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$owner='%REPO_OWNER%'; $repo='%REPO_NAME%';" ^
  "$branches=@('main','master');" ^
  "$out='';" ^
  "foreach($b in $branches){ try { $url='https://api.github.com/repos/'+$owner+'/'+$repo+'/commits/'+$b; $resp=Invoke-WebRequest -Uri $url -UseBasicParsing -Headers @{ 'User-Agent'='PNGStreamer' }; $json=$resp.Content | ConvertFrom-Json; if($json.sha){ $out=$b+'|'+$json.sha; break } } catch {} }" ^
  "Write-Output $out"
`) do set "CHECK_RESULT=%%A"

for /f "tokens=1,2 delims=|" %%B in ("%CHECK_RESULT%") do (
  set "UPDATE_BRANCH=%%B"
  set "LATEST_SHA=%%C"
)

if not "%LATEST_SHA%"=="" if /i not "%LATEST_SHA%"=="%LOCAL_SHA%" (
  set "UPDATE_AVAILABLE=1"
)
exit /b

:download_repo
set "TMP_ROOT=%TEMP%\pngstreamer_install_%RANDOM%%RANDOM%"
set "TMP_EXTRACT=%TMP_ROOT%\extract"
set "TMP_ZIP=%TMP_ROOT%\repo.zip"
set "SRC_DIR="
set "INSTALL_SHA="
mkdir "%TMP_ROOT%" >nul 2>nul

for /f "usebackq delims=" %%A in (`
  powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$owner='%REPO_OWNER%'; $repo='%REPO_NAME%';" ^
  "$zip='%TMP_ZIP%'; $extract='%TMP_EXTRACT%';" ^
  "$branches=@('main','master'); $branch=''; $sha='';" ^
  "foreach($b in $branches){ try { $url='https://github.com/'+$owner+'/'+$repo+'/archive/refs/heads/'+$b+'.zip'; Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing; $branch=$b; break } catch {} }" ^
  "if([string]::IsNullOrWhiteSpace($branch)){ exit 2 }" ^
  "try { $api='https://api.github.com/repos/'+$owner+'/'+$repo+'/commits/'+$branch; $resp=Invoke-WebRequest -Uri $api -UseBasicParsing -Headers @{ 'User-Agent'='PNGStreamer' }; $json=$resp.Content | ConvertFrom-Json; $sha=$json.sha } catch {}" ^
  "if(Test-Path $extract){ Remove-Item $extract -Recurse -Force }" ^
  "Expand-Archive -Path $zip -DestinationPath $extract;" ^
  "$src=Join-Path $extract ($repo+'-'+$branch);" ^
  "Write-Output ($src + '|' + $sha)"
`) do set "DOWNLOAD_RESULT=%%A"

for /f "tokens=1,2 delims=|" %%B in ("%DOWNLOAD_RESULT%") do (
  set "SRC_DIR=%%B"
  set "INSTALL_SHA=%%C"
)

if "%SRC_DIR%"=="" (
  echo.
  echo Failed to download from GitHub.
  pause
  exit /b 1
)

rd /s /q "%TMP_ROOT%" >nul 2>nul
exit /b
