; Inno Setup script for the per-user Windows installer.
; Build after PyInstaller (dist\PNGStreamer must exist):
;   iscc /DAppVersion=3.0.0 packaging\windows\PNGStreamer.iss
; Updates run this installer silently into the same folder; the data\ folder
; next to the program is never touched by install, update or uninstall
; (the user is asked before it is deleted on uninstall).

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
#define AppName "PNG Streamer"
#define AppExe "PNGStreamer.exe"
#define Root "..\.."

[Setup]
AppId={{726FE429-2BC9-48E9-B6A5-373EAFEB1127}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=ENCIDI
AppPublisherURL=https://github.com/ENCIDI/PNG-Streamer
AppSupportURL=https://github.com/ENCIDI/PNG-Streamer/issues
AppUpdatesURL=https://github.com/ENCIDI/PNG-Streamer/releases
VersionInfoVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\PNGStreamer
DisableDirPage=auto
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
UsePreviousTasks=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
AppMutex=PNGStreamerMutex
CloseApplications=yes
SetupIconFile={#Root}\app\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile={#Root}\LICENSE
OutputDir={#Root}\dist
OutputBaseFilename=PNGStreamer-Setup-{#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"

[CustomMessages]
en.StartMenuIcon=Create a Start menu shortcut
ru.StartMenuIcon=Создать ярлык в меню «Пуск»
en.DeleteData=Also delete your profiles and images (the data folder)?
ru.DeleteData=Удалить также ваши профили и картинки (папку data)?

[Tasks]
Name: "startmenuicon"; Description: "{cm:StartMenuIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; Drop libraries of the previous version so nothing stale is left behind.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "{#Root}\dist\PNGStreamer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: startmenuicon
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; Autostart entry written by the app itself; removed on uninstall.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "PNGStreamer"; Flags: uninsdeletevalue dontcreatekey

[Run]
; Not skipped in silent mode: after an automatic update the app starts again.
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{app}\data');
    if DirExists(DataDir) and not UninstallSilent() then
      if MsgBox(CustomMessage('DeleteData'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
