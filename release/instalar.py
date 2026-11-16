"""Ponto de entrada do instalador empacotado (PyInstaller)."""
import sys

from ukloc.installer import main

if __name__ == "__main__":
    sys.exit(main(prog="Instalar-Underkeep-PTBR"))
