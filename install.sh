#!/usr/bin/env bash
# Instalador do VislumBrain. Tudo fica dentro da pasta do projecto, exceto as caches do pip e do
# Hugging Face em ~/.cache. Sem sudo e sem tocar no sistema.
#
#   curl -fsSL https://raw.githubusercontent.com/epestana28/VislumBrain/main/install.sh | bash
#
# Prefere ler antes de correr:
#   wget -O install.sh https://raw.githubusercontent.com/epestana28/VislumBrain/main/install.sh
#   less install.sh && bash install.sh
#
# Opções (com curl: ... | bash -s -- --no-demo):
#   --no-demo   instala, mas não corre a demonstração no fim
#
# Variáveis: PYTHON (que python usar), VISLUMBRAIN_REPO (de onde clonar).
#
# Faz: clona o projecto (se ainda não estiver nele), cria .venv, instala as dependências,
# arranca o Qdrant em Docker se existir (senão usa o modo local) e corre a demonstração.

# Tudo dentro de main, chamada na última linha: se o download parar a meio, o bash não executa
# um script truncado.
main() {
  set -euo pipefail

  local REPO_URL="${VISLUMBRAIN_REPO:-https://github.com/epestana28/VislumBrain.git}"
  local DEMO=1 a PY="" c
  for a in "$@"; do
    case "$a" in
      --no-demo) DEMO=0 ;;
      -h|--help) echo "uso: install.sh [--no-demo]"; return 0 ;;
      *) echo "opção desconhecida: $a" >&2; return 2 ;;
    esac
  done

  say()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
  warn() { printf '\033[33maviso: %s\033[0m\n' "$*" >&2; }
  fail() { printf '\033[31merro: %s\033[0m\n' "$*" >&2; exit 1; }

  [ "$(id -u)" -ne 0 ] || fail "não corras isto como root. Nada aqui precisa de privilégios."

  # Procura um Python 3.11 ou superior. Em RHEL, Rocky e Alma o python3 pode ser o 3.9.
  for c in "${PYTHON:-}" python3.13 python3.12 python3.11 python3; do
    [ -n "$c" ] && command -v "$c" >/dev/null || continue
    if "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then PY="$c"; break; fi
  done
  [ -n "$PY" ] || fail "preciso de Python 3.11 ou superior e não encontrei (tentei python3.13, 3.12, 3.11 e python3). Podes indicar um com PYTHON=/caminho/python3.12."

  if [ -f pyproject.toml ] && grep -q 'name = "vislumbrain"' pyproject.toml; then
    say "A usar a pasta actual"
  else
    command -v git >/dev/null || fail "falta o git para clonar o projecto."
    if [ ! -d VislumBrain ]; then
      say "A clonar o projecto"
      git clone --depth 1 "$REPO_URL" VislumBrain
    fi
    cd VislumBrain
    grep -q 'name = "vislumbrain"' pyproject.toml 2>/dev/null \
      || fail "a pasta VislumBrain/ já existia e não é este projecto. Muda-lhe o nome ou apaga-a e corre outra vez."
  fi

  say "A criar o ambiente isolado (.venv)"
  "$PY" -m venv .venv || fail "não consegui criar o venv. Em Debian e Ubuntu instala o pacote python3-venv."
  .venv/bin/python -m pip install --quiet --upgrade pip

  say "A instalar o PyTorch (versão para CPU) e o resto. Pode demorar uns minutos"
  if ! .venv/bin/python -m pip install --quiet torch --index-url https://download.pytorch.org/whl/cpu; then
    warn "não consegui a versão para CPU. A usar o torch normal, que é muito maior (vários GB)."
    .venv/bin/python -m pip install --quiet torch
  fi
  .venv/bin/python -m pip install --quiet -e .
  chmod +x vislumbrain

  say "Qdrant"
  if command -v docker >/dev/null && docker info >/dev/null 2>&1; then
    mkdir -p qdrant_storage  # criada por ti, para o Docker não a criar como root
    export VB_UID="$(id -u)" VB_GID="$(id -g)"  # o Qdrant corre como tu e a pasta qdrant_storage é tua
    docker compose up -d 2>/dev/null || docker-compose up -d \
      || warn "o Docker não arrancou o Qdrant. O projecto usa o modo local, que funciona na mesma."
  else
    echo "Sem Docker: o projecto usa o Qdrant em modo local (sem HNSW). Serve para tudo menos para o benchmark."
  fi

  if [ "$DEMO" -eq 1 ]; then
    say "Demonstração: descarrega os modelos (GPT-2 small e o embedder) e corre o pipeline completo"
    ./vislumbrain run --tag base
    say "Experimenta o painel no browser (Ctrl+C para parar)"
    echo './vislumbrain serve --tag base'
    echo 'Depois abre http://127.0.0.1:8765 no browser.'
    echo 'Ou vê no terminal: ./vislumbrain live --tag base --text "The bank near the river opened a new account."'
  else
    say "Instalado. Primeiro prepara a demonstração: ./vislumbrain run --tag base. Depois abre o painel: ./vislumbrain serve --tag base"
  fi

  say "Pronto. Lê o README.md para o resto. Verificar o Selo: ./vislumbrain verify --tag base"
}

main "$@"
