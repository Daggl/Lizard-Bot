$paths = @(
  'C:\Program Files\GitHub CLI\bin\gh.exe',
  'C:\Program Files\GitHub CLI\gh.exe',
  "$env:USERPROFILE\AppData\Local\Programs\GitHub CLI\gh.exe",
  "$env:USERPROFILE\AppData\Local\GitHubCLI\gh.exe"
)
foreach ($p in $paths) {
  if (Test-Path $p) {
    Write-Output "FOUND: $p"
    & $p --version
    exit 0
  }
}
Write-Output "NOT FOUND"
exit 2
