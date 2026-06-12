#define AppName "StrideLab"
#define AppVersion "0.1.0.0"
#define AppPublisher "University of Roehampton"
#define AppID "{{A85D67B2-C1A2-4EBD-BEA0-7D4ADB2A5CE9}}"

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
DisableDirPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon";

[Files]
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