"""Ponto de entrada do desinstalador empacotado (PyInstaller)."""
import sys

from ukloc.installer import main

if __name__ == "__main__":
    sys.exit(main(["--desinstalar", *sys.argv[1:]], prog="Desinstalar-Underkeep-PTBR"))
