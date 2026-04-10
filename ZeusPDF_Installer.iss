; Zeus PDF — Inno Setup Installer Script
; Produces: ZeusPDF_Setup_v1.0_Windows.exe
; Build with Inno Setup 6+: iscc ZeusPDF_Installer.iss

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=Zeus PDF
AppVersion=1.0
AppVerName=Zeus PDF 1.0
AppPublisher=Vercher Technologies
AppPublisherURL=https://github.com/jvercher71/PDF-Studio
AppSupportURL=https://github.com/jvercher71/PDF-Studio/issues
AppUpdatesURL=https://github.com/jvercher71/PDF-Studio/releases

; Install to user profile — no admin rights required
DefaultDirName={localappdata}\ZeusPDF
DefaultGroupName=Zeus PDF
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Output
OutputDir=Output
OutputBaseFilename=ZeusPDF_Setup_v1.0_Windows
SetupIconFile=assets\zeuspdf.ico
UninstallDisplayIcon={app}\ZeusPDF.exe

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Wizard
WizardStyle=modern
WizardSizePercent=120
DisableWelcomePage=no
DisableDirPage=no
DisableReadyPage=no

; Misc
AllowNoIcons=yes
ChangesAssociations=yes
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "Create a &desktop shortcut";    GroupDescription: "Additional icons:"; Flags: unchecked
Name: "quicklaunch";   Description: "Create a &Quick Launch shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked; OnlyBelowVersion: 6.1
Name: "assocpdf";      Description: "Associate .pdf files with Zeus PDF"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
; PyInstaller output — copy entire dist\ZeusPDF\ folder
Source: "dist\ZeusPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Zeus PDF";              Filename: "{app}\ZeusPDF.exe"
Name: "{group}\Uninstall Zeus PDF";   Filename: "{uninstallexe}"
Name: "{userdesktop}\Zeus PDF";       Filename: "{app}\ZeusPDF.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Zeus PDF"; Filename: "{app}\ZeusPDF.exe"; Tasks: quicklaunch

[Registry]
; File association for .pdf
Root: HKCU; Subkey: "Software\Classes\.pdf";                          ValueType: string; ValueName: ""; ValueData: "ZeusPDF.Document"; Flags: uninsdeletevalue; Tasks: assocpdf
Root: HKCU; Subkey: "Software\Classes\ZeusPDF.Document";            ValueType: string; ValueName: ""; ValueData: "PDF Document"; Flags: uninsdeletekey; Tasks: assocpdf
Root: HKCU; Subkey: "Software\Classes\ZeusPDF.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\ZeusPDF.exe,0"; Tasks: assocpdf
Root: HKCU; Subkey: "Software\Classes\ZeusPDF.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\ZeusPDF.exe"" ""%1"""; Tasks: assocpdf

; Add to "Open With" for PDF
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "ZeusPDF.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assocpdf

[Run]
Filename: "{app}\ZeusPDF.exe"; Description: "Launch Zeus PDF"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\ZeusPDF\logs"
Type: filesandordirs; Name: "{localappdata}\ZeusPDF\cache"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
