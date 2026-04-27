## Script para clonar repositorios de GitHub
## Uso: .\clone_repos.ps1
## Lee las URLs desde repos.txt y clona cada repo en la carpeta .\repos\

$reposFile = Join-Path $PSScriptRoot "repos.txt"
$reposDir = Join-Path $PSScriptRoot "repos"

# Crear carpeta de repos si no existe
if (-not (Test-Path $reposDir)) {
    New-Item -ItemType Directory -Path $reposDir | Out-Null
    Write-Host "Carpeta 'repos' creada." -ForegroundColor Green
}

# Leer URLs del archivo
$urls = Get-Content $reposFile | Where-Object { 
    $_.Trim() -ne "" -and -not $_.StartsWith("#") 
}

if ($urls.Count -eq 0) {
    Write-Host "No se encontraron URLs en repos.txt. Agrega las URLs y vuelve a ejecutar." -ForegroundColor Yellow
    exit
}

Write-Host "Se encontraron $($urls.Count) repositorios para clonar." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$success = 0
$failed = 0

foreach ($url in $urls) {
    $url = $url.Trim()
    
    # Extraer nombre del repo de la URL
    $repoName = ($url -split "/")[-1] -replace "\.git$", ""
    $targetPath = Join-Path $reposDir $repoName
    
    if (Test-Path $targetPath) {
        Write-Host "[$repoName] Ya existe, saltando..." -ForegroundColor Yellow
        $success++
        continue
    }
    
    Write-Host "[$repoName] Clonando..." -ForegroundColor White -NoNewline
    
    try {
        git clone --depth 1 $url $targetPath 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host " OK" -ForegroundColor Green
            $success++
        } else {
            Write-Host " ERROR" -ForegroundColor Red
            $failed++
        }
    } catch {
        Write-Host " ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    }
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Completado: $success exitosos, $failed fallidos de $($urls.Count) total." -ForegroundColor Cyan
