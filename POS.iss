[Setup]
AppName=POS
AppVersion=3.0
AppPublisher=AA Graphics
AppId={{6E9F8C12-5A3B-4D7E-9F1C-2B8D4E6F0A3C}}
DefaultDirName={localappdata}\POS
DefaultGroupName=POS
UninstallDisplayIcon={app}\POS.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=installer
OutputBaseFilename=POS
SetupIconFile=icon.ico
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "dist\POS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\POS"; Filename: "{app}\POS.exe"
Name: "{autodesktop}\POS"; Filename: "{app}\POS.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce

[Run]
Filename: "{app}\POS.exe"; Description: "Launch POS"; Flags: nowait postinstall skipifsilent

[Code]

const
  InstallerPassword = 'AA-Graphics125-pos12software76!@';

var
  PasswordPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  PasswordPage := CreateInputQueryPage(
    wpWelcome,
    'Password Required',
    'Please enter the installation password:',
    'Enter password below:'
  );

  PasswordPage.Add('Password:', True);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = PasswordPage.ID then
  begin
    if PasswordPage.Values[0] <> InstallerPassword then
    begin
      MsgBox('Invalid password!', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
