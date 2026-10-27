@echo off
rem Atalho para o Windows: vislumbrain COMANDO. Usa o venv do projecto, sem ser preciso activa-lo.
rem No PowerShell escreve .\vislumbrain.cmd COMANDO (com o .cmd, senao o PowerShell pode escolher o script de bash).
rem Na consola antiga (cmd) escreve vislumbrain COMANDO.
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"
set "PYTHONUTF8=1"
set "HF_HUB_DISABLE_SYMLINKS_WARNING=1"
"%~dp0.venv\Scripts\python.exe" -m vislumbrain %*
