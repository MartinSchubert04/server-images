# Exporta los volúmenes de Docker Desktop a .tar.gz, para importarlos en Linux con import-volumes.sh.
# Antes, parar los contenedores que los usan.
#
#   .\linux\export-volumes.ps1                      # los volúmenes de siempre
#   .\linux\export-volumes.ps1 -Extra job-autoapply_ollama
param(
    [string]$Out = 'C:\migracion\volumes',
    [string[]]$Extra = @()
)

# Whisper, Piper, los modelos de ollama y las cachés no van: se vuelven a bajar o a generar
$vols = @(
    'home-assistant_homeassistant_data',
    'home-assistant_esphome_data',
    'n8n_n8n_data',
    'waha_waha_sessions',
    'kopia_kopia_config',
    'job-autoapply_auth'
) + $Extra

New-Item -ItemType Directory -Force $Out | Out-Null

$enUso = docker ps --format '{{.Names}}' | ForEach-Object {
    docker inspect $_ --format '{{range .Mounts}}{{.Name}} {{end}}'
}
foreach ($v in $vols) {
    if ($enUso -match [regex]::Escape($v)) {
        Write-Warning "$v lo está usando un contenedor prendido: la copia puede quedar inconsistente"
    }
    docker run --rm -v "${v}:/v:ro" -v "${Out}:/out" alpine tar czf "/out/$v.tar.gz" -C /v .
    if ($LASTEXITCODE -ne 0) { Write-Error "Falló $v"; exit 1 }
    "{0}: {1:N0} MB" -f $v, ((Get-Item "$Out\$v.tar.gz").Length / 1MB)
}
