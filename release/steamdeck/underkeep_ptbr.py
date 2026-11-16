"""Ponto de entrada do pacote Steam Deck/Linux (chamado por ``Instalador-Underkeep-PTBR.sh``).

Roda com ``python3 -I -B``: ambiente isolado (sem PYTHONPATH, site do usuário ou diretório atual)
e sem gravar caches ``__pycache__`` na pasta extraída.
"""
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent

if sys.version_info < (3, 11):
    sys.exit("ERRO: o instalador precisa do Python 3.11 ou mais novo (encontrado: %d.%d)." % sys.version_info[:2])

sys.path.insert(0, str(APP))

from ukloc import gui  # noqa: E402

if __name__ == "__main__":
    sys.exit(gui.main(l10n_root=APP.parent / "dados" / "pt-BR", entry_script=Path(__file__).resolve()))
