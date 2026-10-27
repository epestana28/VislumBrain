# Instalador do VislumBrain para Windows (PowerShell 5.1 ou superior). Tudo fica dentro da pasta do
# projecto, exceto as caches do pip e do Hugging Face. Não precisa de administrador nem de Docker.
#
#   irm https://raw.githubusercontent.com/epestana28/VislumBrain/main/install.ps1 | iex
#
# Para instalar sem a demonstração no fim, define antes: $env:VISLUMBRAIN_NO_DEMO = "1"
# Variáveis: VISLUMBRAIN_PYTHON (que python usar), VISLUMBRAIN_ZIP (de onde descarregar o projecto).
#
# Faz: descarrega o projecto (se ainda não estiver nele), cria o .venv, instala as dependências e
# corre a demonstração. O Qdrant usa o modo local, que não precisa de Docker.

# Tudo dentro de uma função chamada na última linha: se o download parar a meio, o PowerShell
# não executa um script truncado.
function Install-VislumBrain {
    $ErrorActionPreference = "Stop"
    $zipUrl = if ($env:VISLUMBRAIN_ZIP) { $env:VISLUMBRAIN_ZIP } else { "https://github.com/epestana28/VislumBrain/archive/refs/heads/main.zip" }
    $onWindows = ($env:OS -eq "Windows_NT")
    $env:PYTHONUTF8 = "1"
    $env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
    try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12 } catch { }

    function Say($m)  { Write-Host ""; Write-Host "==> $m" -ForegroundColor Cyan }
    function Warn($m) { Write-Host "aviso: $m" -ForegroundColor Yellow }
    function Stop-Install($m) { Write-Host "erro: $m" -ForegroundColor Red; throw $m }

    # Procura um Python 3.11 ou superior. O lançador "py" é o que o instalador oficial do Python traz.
    $candidates = @()
    if ($env:VISLUMBRAIN_PYTHON) { $candidates += , @($env:VISLUMBRAIN_PYTHON) }
    $candidates += , @("py", "-3.13"), @("py", "-3.12"), @("py", "-3.11"), @("python3"), @("python")
    $py = $null
    foreach ($c in $candidates) {
        try {
            $exe = $c[0]; $extra = @($c | Select-Object -Skip 1)
            if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
            & $exe @extra -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) { $py = $c; break }
        } catch { }
    }
    if (-not $py) {
        Stop-Install ("preciso de Python 3.11 ou superior e não encontrei. Instala-o com: winget install Python.Python.3.12  " +
                      "(ou em https://www.python.org/downloads/, a marcar 'Add python.exe to PATH'). Depois abre um PowerShell novo e corre isto outra vez.")
    }
    $pyExe = $py[0]; $pyArgs = @($py | Select-Object -Skip 1)

    if ((Test-Path "pyproject.toml") -and (Select-String -Path "pyproject.toml" -Pattern 'name = "vislumbrain"' -Quiet)) {
        Say "A usar a pasta actual"
    } else {
        if (-not (Test-Path "VislumBrain")) {
            Say "A descarregar o projecto"
            $zip = Join-Path ([IO.Path]::GetTempPath()) "vislumbrain-main.zip"
            Invoke-WebRequest -Uri $zipUrl -OutFile $zip -UseBasicParsing
            Expand-Archive -Path $zip -DestinationPath "." -Force
            Remove-Item $zip -ErrorAction SilentlyContinue
            $unz = Get-ChildItem -Directory -Filter "VislumBrain-*" | Select-Object -First 1
            if (-not $unz) { Stop-Install "não encontrei a pasta do projecto depois de descompactar." }
            Rename-Item -Path $unz.FullName -NewName "VislumBrain"
        }
        Set-Location "VislumBrain"
        if (-not ((Test-Path "pyproject.toml") -and (Select-String -Path "pyproject.toml" -Pattern 'name = "vislumbrain"' -Quiet))) {
            Stop-Install "a pasta VislumBrain já existia e não é este projecto. Muda-lhe o nome ou apaga-a e corre outra vez."
        }
    }

    Say "A criar o ambiente isolado (.venv)"
    & $pyExe @pyArgs -m venv .venv
    if ($LASTEXITCODE -ne 0) { Stop-Install "não consegui criar o venv." }
    $venvPy = if ($onWindows) { ".venv\Scripts\python.exe" } else { ".venv/bin/python" }
    & $venvPy -m pip install --quiet --upgrade pip

    Say "A instalar o PyTorch (versão para CPU) e o resto. Pode demorar uns minutos"
    & $venvPy -m pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu
    if ($LASTEXITCODE -ne 0) {
        Warn "não consegui a versão para CPU. A usar o torch normal, que é muito maior (vários GB)."
        & $venvPy -m pip install --quiet torch
        if ($LASTEXITCODE -ne 0) { Stop-Install "não consegui instalar o PyTorch." }
    }
    & $venvPy -m pip install --quiet -e .
    if ($LASTEXITCODE -ne 0) { Stop-Install "não consegui instalar o projecto." }

    Say "Qdrant"
    Write-Host "O projecto usa o Qdrant em modo local, que não precisa de Docker (sem HNSW: serve para tudo menos para o benchmark)."

    $launcher = if ($onWindows) { ".\vislumbrain.cmd" } else { "./vislumbrain" }
    if ($env:VISLUMBRAIN_NO_DEMO -ne "1") {
        Say "Demonstração: descarrega os modelos (GPT-2 small e o embedder) e corre o pipeline completo"
        & $launcher run --tag base
        if ($LASTEXITCODE -ne 0) { Stop-Install "a demonstração falhou. Lê a mensagem acima." }
        Say "Experimenta o painel no browser (Ctrl+C para parar)"
        Write-Host ".\vislumbrain.cmd serve --tag base"
        Write-Host "Depois abre http://127.0.0.1:8765 no browser."
    } else {
        Say "Instalado. Primeiro prepara a demonstração: .\vislumbrain.cmd run --tag base. Depois abre o painel: .\vislumbrain.cmd serve --tag base"
    }
    Say "Pronto. Lê o README.md para o resto. Verificar o Selo: .\vislumbrain.cmd verify --tag base"
}

Install-VislumBrain
