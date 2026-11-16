#!/usr/bin/env bash
# Underkeep PT-BR — instalador para Steam Deck / Linux (modo Desktop).
#
# Sem argumentos: abre a interface gráfica (kdialog ou zenity).
# Com argumentos: modo terminal. Exemplos:
#   ./Instalador-Underkeep-PTBR.sh --terminal     instalação interativa no terminal
#   ./Instalador-Underkeep-PTBR.sh --verificar    só verifica (não altera nada)
#   ./Instalador-Underkeep-PTBR.sh --status
#   ./Instalador-Underkeep-PTBR.sh --desinstalar
#
# Este script só localiza o Python do sistema e chama o instalador (app/underkeep_ptbr.py).
# Não usa sudo, não instala pacotes e não grava fora de Documents/Underkeep/mods/base do prefixo do jogo.
set -u

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
TITLE="Underkeep PT-BR"

avisar() {
    printf 'ERRO: %s\n' "$1" >&2
    if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        if command -v kdialog >/dev/null 2>&1; then
            kdialog --title "$TITLE" --error "$1"
        elif command -v zenity >/dev/null 2>&1; then
            zenity --error --title "$TITLE" --text "$1"
        fi
    fi
}

if [ ! -f "$DIR/app/underkeep_ptbr.py" ] || [ ! -f "$DIR/dados/pt-BR/project.json" ]; then
    avisar "Arquivos do instalador não encontrados. Extraia o ZIP inteiro e execute o script de dentro da pasta extraída."
    exit 1
fi

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    avisar "Python 3.11 ou mais novo não foi encontrado. O SteamOS atual já inclui o Python; veja o LEIA-ME.txt."
    exit 1
fi

exec "$PY" -I -B "$DIR/app/underkeep_ptbr.py" "$@"
