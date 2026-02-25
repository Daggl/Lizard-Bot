$me = $PID
$procs = Get-Process -Name powershell -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne $me }
if ($procs) {
    foreach ($p in $procs) {
        Write-Output ("STOPPING: {0} Path:{1}" -f $p.Id, $p.Path)
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    }
} else {
    Write-Output "NO_POWERSHELLS"
}
