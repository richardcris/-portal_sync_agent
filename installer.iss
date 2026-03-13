; Inno Setup script for VEXPER SISTEMAS Sync Agent
#define MyAppName "VEXPER SISTEMAS - Sync Agent"
#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif
#define MyAppPublisher "VEXPER SISTEMAS"
#define MyAppExeName "VEXPER-SISTEMAS.exe"

[Setup]
AppId={{A44E477E-0B6A-4F80-9EC8-BCC5A52E41CC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\VEXPER SISTEMAS\Sync Agent
DefaultGroupName=VEXPER SISTEMAS
OutputDir=dist
OutputBaseFilename=VEXPER-SISTEMAS-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.example.json"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "logo.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\VEXPER SISTEMAS - Sync Agent"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar VEXPER SISTEMAS - Sync Agent"; Filename: "{uninstallexe}"
Name: "{autodesktop}\VEXPER SISTEMAS - Sync Agent"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar VEXPER SISTEMAS - Sync Agent"; Flags: nowait postinstall skipifsilent
