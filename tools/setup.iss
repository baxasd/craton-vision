#define AppName "CratonVision"
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
OutputBaseFilename=CratonVision
SetupIconFile=app.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "openfolder"; Description: "Open install folder after setup"; Flags: checked

[Files]
; Source is relative to the .iss file (one level up to project root, then into dist)
Source: "..\dist\CratonVision\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName} - Calibrator"; Filename: "{app}\calibrator.exe"
Name: "{group}\{#AppName} - Recorder"; Filename: "{app}\recorder.exe"
Name: "{group}\{#AppName} - Viewer"; Filename: "{app}\viewer.exe"

Name: "{autodesktop}\Calibrator"; Filename: "{app}\calibrator.exe"; Tasks: desktopicon
Name: "{autodesktop}\Capture"; Filename: "{app}\recorder.exe"; Tasks: desktopicon
Name: "{autodesktop}\Viewer"; Filename: "{app}\viewer.exe"; Tasks: desktopicon

[Run]
Filename: "{cmd}"; Parameters: "/C explorer ""{app}"""; Tasks: openfolder; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"