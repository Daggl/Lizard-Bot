[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [int]$KeepTrackedBackups = 5
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repoRoot

$removedFiles = 0
$removedDirs = 0

function Remove-FileSafe {
    param([string]$Path)
    if (Test-Path -LiteralPath $Path) {
        if ($PSCmdlet.ShouldProcess($Path, 'Remove file')) {
            Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
            $script:removedFiles++
        }
    }
}

# 1) Remove __pycache__ folders outside .venv
$cacheDirs = Get-ChildItem -Recurse -Directory -Force | Where-Object {
    $_.Name -eq '__pycache__' -and $_.FullName -notlike "*$([IO.Path]::DirectorySeparatorChar).venv$([IO.Path]::DirectorySeparatorChar)*"
}

foreach ($dir in $cacheDirs) {
    if ($PSCmdlet.ShouldProcess($dir.FullName, 'Remove directory')) {
        Remove-Item -LiteralPath $dir.FullName -Recurse -Force -ErrorAction SilentlyContinue
        $removedDirs++
    }
}

# 2) Remove UI trace leftovers
Remove-FileSafe -Path (Join-Path $repoRoot 'data/logs/tmp_ui_trace_tail.txt')
Remove-FileSafe -Path (Join-Path $repoRoot 'data/logs/ui_run_trace.log')

# 3) Prune tracked.log backups (keep latest N)
$trackedPattern = Join-Path $repoRoot 'data/logs/tracked.log.bak.*'
$trackedBackups = Get-ChildItem -Path $trackedPattern -File -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending

$toDelete = $trackedBackups | Select-Object -Skip ([Math]::Max(0, $KeepTrackedBackups))
foreach ($file in $toDelete) {
    if ($PSCmdlet.ShouldProcess($file.FullName, 'Remove old tracked backup')) {
        Remove-Item -LiteralPath $file.FullName -Force -ErrorAction SilentlyContinue
        $removedFiles++
    }
}

Write-Output ("cleanup_runtime complete: removedDirs={0}, removedFiles={1}" -f $removedDirs, $removedFiles)
