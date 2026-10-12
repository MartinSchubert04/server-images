# Copies the Kopia repository to a second location (pendrive, other disk, NAS share).
# To move the copy somewhere else, change $Dest. The repository is self-contained:
# any copy of this folder plus KOPIA_PASSWORD from .env is enough to restore.
$Source = 'C:\Backups\kopia'
$Dest   = 'D:\kopia-backups'
$Log    = Join-Path $PSScriptRoot 'mirror.log'

function Write-Log($msg) {
    "{0}  {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg | Add-Content -Path $Log
}

if (-not (Test-Path (Split-Path $Dest -Qualifier))) {
    Write-Log "ERROR destino no disponible: $Dest"
    exit 1
}

robocopy $Source $Dest /MIR /R:2 /W:5 /NP /NFL /NDL /NJH /NJS | Out-Null
$code = $LASTEXITCODE

# Robocopy: 0-7 are success variants, 8+ means something failed to copy
if ($code -ge 8) {
    Write-Log "ERROR robocopy codigo $code"
    exit 1
}

$mb = [math]::Round(((Get-ChildItem $Dest -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 0)
Write-Log "OK copia en $Dest ($mb MB, robocopy $code)"
exit 0
