; PDF Studio — Inno Setup Installer Script
; Produces: PDFStudio_Setup_v1.0_Windows.exe
; Build with Inno Setup 6+: iscc PDFStudio_Installer.iss

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=PDF Studio
AppVersion=1.0
AppVerName=PDF Studio 1.0
AppPublisher=Vercher Technologies
AppPublisherURL=https://github.com/jvercher71/PDF-Studio
AppSupportURL=https://github.com/jvercher71/PDF-Studio/issues
AppUpdatesURL=https://github.com/jvercher71/PDF-Studio/releases

; Install to user profile — no admin rights required
DefaultDirName={localappdata}\PDFStudio
DefaultGroupName=PDF Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Output
OutputDir=Output
OutputBaseFilename=PDFStudio_Setup_v1.0_Windows
SetupIconFile=assets\pdfstudio.ico
UninstallDisplayIcon={app}\PDFStudio.exe

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
Name: "assocpdf";      Description: "Associate .pdf files with PDF Studio"; GroupDescription: "File associations:"; Flags: unchecked

[Files]
; PyInstaller output — copy entire dist\PDFStudio\ folder
Source: "dist\PDFStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PDF Studio";              Filename: "{app}\PDFStudio.exe"
Name: "{group}\Uninstall PDF Studio";   Filename: "{uninstallexe}"
Name: "{userdesktop}\PDF Studio";       Filename: "{app}\PDFStudio.exe"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\PDF Studio"; Filename: "{app}\PDFStudio.exe"; Tasks: quicklaunch

[Registry]
; File association for .pdf
Root: HKCU; Subkey: "Software\Classes\.pdf";                          ValueType: string; ValueName: ""; ValueData: "PDFStudio.Document"; Flags: uninsdeletevalue; Tasks: assocpdf
Root: HKCU; Subkey: "Software\Classes\PDFStudio.Document";            ValueType: string; ValueName: ""; ValueData: "PDF Document"; Flags: uninsdeletekey; Tasks: assocpdf
Root: HKCU; Subkey: "Software\Classes\PDFStudio.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\PDFStudio.exe,0"; Tasks: assocpdf
Root: HKCU; Subkey: "Software\Classes\PDFStudio.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\PDFStudio.exe"" ""%1"""; Tasks: assocpdf

; Add to "Open With" for PDF
Root: HKCU; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "PDFStudio.Document"; ValueData: ""; Flags: uninsdeletevalue; Tasks: assocpdf

[Run]
Filename: "{app}\PDFStudio.exe"; Description: "Launch PDF Studio"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\PDFStudio\logs"
Type: filesandordirs; Name: "{localappdata}\PDFStudio\cache"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;
