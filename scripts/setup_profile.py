import os
import pathlib

profile_path = pathlib.Path(os.environ["USERPROFILE"]) / "Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1"
profile_path.parent.mkdir(parents=True, exist_ok=True)

content = r"""# Direct prepend Node 22 & uv to PATH (overriding Machine PATH Node 14)
$node22 = "$env:APPDATA\fnm\node-versions\v22.23.2\installation"
if (Test-Path $node22) {
    $env:PATH = "$node22;$env:PATH"
}

$uvBin = "C:\Users\ww\.local\bin"
if (Test-Path $uvBin) {
    $env:PATH = "$uvBin;$env:PATH"
}

$fnmBin = "C:\Users\ww\AppData\Local\Microsoft\WinGet\Packages\Schniz.fnm_Microsoft.Winget.Source_8wekyb3d8bbwe"
if (Test-Path $fnmBin) {
    $env:PATH = "$fnmBin;$env:PATH"
}
"""

profile_path.write_text(content, encoding="utf-8")
print(f"PowerShell profile written to: {profile_path}")
print("Verified content:")
print(profile_path.read_text(encoding="utf-8"))
