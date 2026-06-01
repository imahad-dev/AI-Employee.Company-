param(
  [ValidateSet("start", "test", "build", "docker-build", "docker-up", "docker-down")]
  [string]$Command = "start"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Run-BackendTests {
  Push-Location $Root
  python -m unittest discover -s backend\tests
  python -m compileall -q backend\app
  Pop-Location
}

function Run-FrontendBuild {
  Push-Location (Join-Path $Root "frontend")
  npm run build
  Pop-Location
}

switch ($Command) {
  "test" {
    Run-BackendTests
  }
  "build" {
    Run-BackendTests
    Run-FrontendBuild
  }
  "docker-build" {
    Push-Location $Root
    docker compose build
    Pop-Location
  }
  "docker-up" {
    Push-Location $Root
    docker compose up --build
    Pop-Location
  }
  "docker-down" {
    Push-Location $Root
    docker compose down
    Pop-Location
  }
  default {
    Push-Location $Root
    Start-Process -FilePath python -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8000","--reload" -WorkingDirectory (Join-Path $Root "backend")
    Start-Process -FilePath npm.cmd -ArgumentList "run","dev","--","-p","3000" -WorkingDirectory (Join-Path $Root "frontend")
    Pop-Location
    Write-Host "Backend:  http://127.0.0.1:8000"
    Write-Host "Frontend: http://127.0.0.1:3000"
  }
}
