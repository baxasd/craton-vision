#define AppName "StrideLab"
#define AppVersion "0.1.0"
#define AppPublisher "University of Roehampton"
#define AppID "{{C32CEE2E-E574-44DA-AC6C-4E6B1206EB03}}"

[Setup]
AppId={#AppID}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={userdocs}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\installer
OutputBaseFilename=StrideLab
SetupIconFile=..\vision.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "openfolder"; Description: "Open install folder after setup"; Flags: checked

[Files]
; Source is relative to the .iss file (two levels up to project root, then into dist/StrideLab — the COLLECT name in build.spec)
Source: "..\..\dist\StrideLab\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName} - Calibrator"; Filename: "{app}\calibrator.exe"
Name: "{group}\{#AppName} - Recorder"; Filename: "{app}\recorder.exe"
Name: "{group}\{#AppName} - Viewer"; Filename: "{app}\viewer.exe"
Name: "{group}\{#AppName} - Workbench"; Filename: "{app}\workbench.exe"

Name: "{autodesktop}\Calibrator"; Filename: "{app}\calibrator.exe"; Tasks: desktopicon
Name: "{autodesktop}\Capture"; Filename: "{app}\recorder.exe"; Tasks: desktopicon
Name: "{autodesktop}\Viewer"; Filename: "{app}\viewer.exe"; Tasks: desktopicon
Name: "{autodesktop}\Workbench"; Filename: "{app}\workbench.exe"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C explorer ""{app}"""; Tasks: openfolder; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"