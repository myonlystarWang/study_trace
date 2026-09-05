import os
import pathlib

profile_path = pathlib.Path(os.environ["USERPROFILE"]) / "Documents/WindowsPowerShell/Microsoft.PowerShell_profile.ps1"
profile_path.parent.mkdir(parents=True, exist_ok=True)

content = r"""# fnm & uv environment auto-activation
$fnmBin = "C:\Users\ww\AppData\Local\Microsoft\WinGet\Packages\Schniz.fnm_Microsoft.Winget.Source_8wekyb3d8bbwe"
if (Test-Path $fnmBin) {
    $env:PATH = "$fnmBin;$env:PATH"
}
$uvBin = "C:\Users\ww\.local\bin"
if (Test-Path $uvBin) {
    $env:PATH = "$uvBin;$env:PATH"
}
try {
    fnm env --use-on-cd | Out-String | Invoke-Expression
} catch {}
"""

profile_path.write_text(content, encoding="utf-8")
print(f"PowerShell profile written to: {profile_path}")
print("Verified content:")
print(profile_path.read_text(encoding="utf-8"))
