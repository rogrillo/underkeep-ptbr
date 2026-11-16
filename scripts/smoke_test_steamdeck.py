#!/usr/bin/env python3
"""Teste de fumaça do pacote Steam Deck/Linux, FORA do workspace.

Extrai o ZIP num diretório temporário do sistema e roda ``app/underkeep_ptbr.py`` com ``python -I -B``
(como faz ``Instalador-Underkeep-PTBR.sh``) contra a instalação real do jogo (SOMENTE leitura) e uma pasta
Documentos SINTÉTICA, com espaço e acento no caminho. Nunca usa a pasta Documentos real.

Verifica: SHA-256 e estrutura do ZIP (caminhos POSIX, permissões, LF), versão, verificação sem efeitos,
instalação, status, instalação duplicada recusada, desinstalação, desinstalação repetida, ausência de
``__pycache__`` na pasta extraída e hashes do jogo inalterados. Com ``--comparar``, confere que o pack
instalado é idêntico (hash a hash) a um pack instalado por outro meio, por exemplo o instalador Windows.

Não testa a interface gráfica nem o Proton: isso exige o Steam Deck (ver docs/STEAM_DECK.md).

Uso: ``python scripts/smoke_test_steamdeck.py dist/Underkeep-PTBR-v<versão>-SteamDeck.zip
[--jogo PASTA] [--comparar PASTA_MODS_BASE]``
"""
from __future__ import annotations

import argparse
import locale
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ukloc import shadow, steam  # noqa: E402

LAUNCHER = "Instalador-Underkeep-PTBR.sh"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip", type=Path)
    parser.add_argument("--jogo", type=Path, help="pasta do jogo (padrão: detectar na Steam)")
    parser.add_argument("--comparar", type=Path, help="mods/base instalado por outro meio, para comparar hashes")
    parser.add_argument("--manter", action="store_true", help="não apaga o diretório temporário")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    zip_path = args.zip.resolve()
    games = [args.jogo] if args.jogo else steam.find_game_dirs()
    if not games:
        print("ERRO: jogo não encontrado; use --jogo")
        return 1
    game = games[0]
    root = Path(tempfile.mkdtemp(prefix="ukptbr_deck_smoke_"))
    if PROJECT_ROOT in root.parents:
        print("ERRO: o teste precisa rodar fora do workspace")
        return 1
    results: list[bool] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append(ok)
        print(f"[{'OK' if ok else 'FALHA'}] {name}" + (f" — {detail[-600:]}" if detail and not ok else ""))

    try:
        print(f"Diretório de teste: {root}\nJogo (somente leitura): {game}")
        game_before = shadow.hash_tree(game)
        expected_sha = zip_path.with_name(zip_path.name + ".sha256").read_text(encoding="ascii").split()[0]
        check("SHA-256 confere com o arquivo .sha256", shadow.file_sha256(zip_path) == expected_sha)
        with zipfile.ZipFile(zip_path) as zf:
            infos = zf.infolist()
            posix = all("\\" not in i.orig_filename and i.create_system == 3 for i in infos)
            launcher = next(i for i in infos if i.filename.endswith("/" + LAUNCHER))
            check("ZIP com caminhos POSIX e permissões Unix", posix)
            check("launcher com permissão 755 e LF",
                  stat.S_IMODE(launcher.external_attr >> 16) == 0o755 and b"\r" not in zf.read(launcher))
            zf.extractall(root / "extraido")
        package = next((root / "extraido").iterdir())
        entry = package / "app" / "underkeep_ptbr.py"
        docs = root / "Documentos do jogador ç"
        (docs / "Underkeep").mkdir(parents=True)
        (docs / "Underkeep" / "game_config.txt").write_text("config sintética", encoding="utf-8")
        env = {k: v for k, v in os.environ.items()
               if k.upper() in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "HOME", "LANG"}}
        # ``-I`` ignora PYTHONIOENCODING: a saída vem na codificação do sistema (UTF-8 no SteamOS)
        encoding = locale.getpreferredencoding(False)

        def run(*extra: str) -> tuple[int, str]:
            proc = subprocess.run([sys.executable, "-I", "-B", str(entry), *extra], capture_output=True,
                                  text=True, encoding=encoding, errors="replace", env=env, cwd=root,
                                  stdin=subprocess.DEVNULL, timeout=900, check=False)
            return proc.returncode, proc.stdout + proc.stderr

        d = ["--jogo", str(game), "--documentos", str(docs)]
        code, out = run("--version")
        check("pacote extraído roda com python -I -B (--version)", code == 0 and "beta" in out, out)
        code, out = run("--verificar", *d)
        check("verificação compatível e sem alterações",
              code == 0 and "Jogo compatível" in out and not (docs / "Underkeep" / "mods").exists(), out)
        code, out = run("--sim", *d)
        target = docs / "Underkeep" / "mods" / "base"
        check("geração do pack-sombra e instalação", code == 0 and (target / shadow.MANIFEST_NAME).is_file(), out)
        code, out = run("--status", *d)
        check("status reconhece a instalação", code == 0 and "instalada (" in out, out)
        code, out = run("--sim", *d)
        check("instalação duplicada recusada", code == 2 and "já está instalada" in out, out)
        if args.comparar:
            same = shadow.hash_tree(target) == shadow.hash_tree(args.comparar)
            check(f"pack idêntico ao de {args.comparar}", same)
        code, out = run("--desinstalar", "--sim", *d)
        check("desinstalação", code == 0 and not target.exists(), out)
        code, out = run("--desinstalar", "--sim", *d)
        check("desinstalação repetida não faz nada", code == 2 and "nada instalado" in out, out)
        check("configuração do jogo preservada",
              (docs / "Underkeep" / "game_config.txt").read_text(encoding="utf-8") == "config sintética")
        check("sem __pycache__ na pasta extraída", not list(package.rglob("__pycache__")))
        check("instalação original do jogo preservada (hashes)", shadow.hash_tree(game) == game_before)
    finally:
        if not args.manter:
            shutil.rmtree(root, ignore_errors=True)
    print(f"\n{sum(results)}/{len(results)} verificações OK")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
