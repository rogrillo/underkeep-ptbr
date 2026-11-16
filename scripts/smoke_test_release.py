#!/usr/bin/env python3
"""Teste de fumaça do pacote de release, FORA do workspace e sem ambiente virtual.

Extrai o ZIP num diretório temporário do sistema e roda os executáveis com um ambiente mínimo
(sem Python no PATH), contra a instalação real do jogo (SOMENTE leitura) e pastas Documentos
SINTÉTICAS. A pasta Documentos real nunca é usada. Ao final, confere que a instalação do jogo
ficou byte a byte igual.

Cenários: SHA-256 do ZIP, versão, detecção automática, seleção manual (prompt), jogo incompatível,
pasta inexistente, Documentos sem pasta do jogo, conflito com mods/base desconhecido, outro mod
preservado, instalação real, instalação duplicada, status, desinstalação adulterada recusada,
desinstalação, desinstalação repetida.

Uso: ``python scripts/smoke_test_release.py dist/Underkeep-PTBR-v<versão>-Windows.zip [--jogo PASTA]``
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ukloc import shadow, steam  # noqa: E402

INSTALL = "Instalar-Underkeep-PTBR.exe"
UNINSTALL = "Desinstalar-Underkeep-PTBR.exe"


class Smoke:
    def __init__(self, package: Path, root: Path) -> None:
        self.package = package
        self.root = root
        self.results: list[tuple[str, bool, str]] = []
        system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
        self.env = {"SYSTEMROOT": system_root, "WINDIR": system_root, "PATH": str(Path(system_root) / "System32"),
                    "TEMP": str(root / "tmp"), "TMP": str(root / "tmp")}

    def run(self, exe: str, *args: str, stdin: str = "") -> tuple[int, str]:
        proc = subprocess.run([str(self.package / exe), *args], input=stdin.encode("utf-8"), env=self.env,
                              cwd=self.root, capture_output=True, timeout=900, check=False)
        output = (proc.stdout + proc.stderr).decode("cp1252", errors="replace")
        return proc.returncode, output

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append((name, ok, detail))
        print(f"[{'OK' if ok else 'FALHA'}] {name}" + (f" — {detail}" if detail and not ok else ""))


def file_sha256(path: Path) -> str:
    return shadow.file_sha256(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("zip", type=Path)
    parser.add_argument("--jogo", type=Path, help="pasta do jogo (padrão: detectar na Steam)")
    parser.add_argument("--manter", action="store_true", help="não apaga o diretório temporário")
    args = parser.parse_args(argv)
    zip_path = args.zip.resolve()
    games = [args.jogo] if args.jogo else steam.find_game_dirs()
    if not games:
        print("ERRO: jogo não encontrado; use --jogo")
        return 1
    game = games[0]
    root = Path(tempfile.mkdtemp(prefix="ukptbr_smoke_"))
    if PROJECT_ROOT in root.parents:
        print("ERRO: o teste precisa rodar fora do workspace")
        return 1
    try:
        print(f"Diretório de teste: {root}\nJogo (somente leitura): {game}")
        game_before = shadow.hash_tree(game)
        (root / "tmp").mkdir()
        smoke = Smoke(root / "pacote" / zip_path.stem, root)
        sums = zip_path.with_name(zip_path.name + ".sha256")
        smoke.check("SHA-256 confere com o arquivo .sha256",
                    sums.is_file() and sums.read_text(encoding="ascii").split()[0] == file_sha256(zip_path))
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(root / "pacote")
        docs = root / "docs"
        (docs / "Underkeep" / "mods" / "meu_mod").mkdir(parents=True)
        (docs / "Underkeep" / "mods" / "meu_mod" / "x.txt").write_text("terceiro", encoding="utf-8")
        (docs / "Underkeep" / "save_sintetico").write_bytes(b"save")
        conflict = root / "docs_conflito"
        (conflict / "Underkeep" / "mods" / "base").mkdir(parents=True)
        (conflict / "Underkeep" / "mods" / "base" / "outro.txt").write_text("outro mod", encoding="utf-8")
        (root / "docs_semjogo").mkdir()
        fake = root / "jogo_falso"
        (fake / "base").mkdir(parents=True)
        (fake / "underkeep.exe").write_bytes(b"MZ build falsa")
        d = ["--documentos", str(docs)]
        has_python = shutil.which("python", path=smoke.env["PATH"]) or shutil.which("py", path=smoke.env["PATH"])
        smoke.check("ambiente de teste sem Python no PATH", not has_python)

        code, out = smoke.run(INSTALL, "--version")
        smoke.check("executável roda sem ambiente virtual (--version)", code == 0 and "beta" in out, out)
        code, out = smoke.run(INSTALL, "--verificar", "--sim", *d)
        smoke.check("detecção automática + verificação de hashes", code == 0 and "Jogo compatível" in out, out)
        code, out = smoke.run(INSTALL, "--verificar", *d, stdin=str(game / "underkeep.exe") + "\n")
        smoke.check("seleção manual da pasta (prompt)", code == 0 and "Jogo compatível" in out, out)
        code, out = smoke.run(INSTALL, "--sim", "--jogo", str(fake), *d)
        smoke.check("bloqueio de versão incompatível", code == 2 and "não suportada" in out, out)
        code, out = smoke.run(INSTALL, "--sim", "--jogo", str(root / "nao_existe"), *d)
        smoke.check("bloqueio de pasta inexistente", code == 2 and "não encontrado" in out, out)
        code, out = smoke.run(INSTALL, "--sim", "--documentos", str(root / "docs_semjogo"))
        smoke.check("bloqueio sem Documentos/Underkeep", code == 2 and "abra o Underkeep" in out, out)
        code, out = smoke.run(INSTALL, "--sim", "--documentos", str(conflict))
        smoke.check("conflito com mods/base desconhecido", code == 2 and "outro mod" in out
                    and (conflict / "Underkeep/mods/base/outro.txt").read_text(encoding="utf-8") == "outro mod", out)
        code, out = smoke.run(INSTALL, "--sim", *d)
        target = docs / "Underkeep" / "mods" / "base"
        manifest_ok = False
        if target.is_dir():
            manifest = shadow.read_manifest(target)
            manifest_ok = not shadow._verify_mod_dir(target, manifest)  # noqa: SLF001
        smoke.check("geração do pack-sombra e instalação", code == 0 and "Pronto!" in out and manifest_ok, out)
        smoke.check("aviso de outro mod", "meu_mod" in out, out)
        smoke.check("temporários removidos", not any((root / "tmp").iterdir()))
        code, out = smoke.run(INSTALL, "--sim", *d)
        smoke.check("instalação duplicada recusada", code == 2 and "já está instalada" in out, out)
        code, out = smoke.run(INSTALL, "--status", *d)
        smoke.check("status", code == 0 and "instalada" in out, out)
        tampered = root / "docs_adulterado"
        shutil.copytree(docs, tampered)
        victim = next((tampered / "Underkeep/mods/base/base").glob("text_text_game_*.rfile"))
        victim.write_bytes(victim.read_bytes() + b"\0")
        code, out = smoke.run(UNINSTALL, "--sim", "--documentos", str(tampered))
        smoke.check("desinstalação de pasta adulterada recusada", code == 2 and victim.exists(), out)
        code, out = smoke.run(UNINSTALL, "--sim", *d)
        smoke.check("desinstalação", code == 0 and not target.exists()
                    and (docs / "Underkeep/mods/meu_mod/x.txt").is_file()
                    and (docs / "Underkeep/save_sintetico").read_bytes() == b"save", out)
        code, out = smoke.run(UNINSTALL, "--sim", *d)
        smoke.check("desinstalação repetida não faz nada", code == 2 and "nada instalado" in out, out)
        smoke.check("instalação original do jogo preservada (hashes)", shadow.hash_tree(game) == game_before)
    finally:
        if not args.manter:
            shutil.rmtree(root, ignore_errors=True)
    failed = [name for name, ok, _ in smoke.results if not ok]
    print(f"\n{len(smoke.results) - len(failed)}/{len(smoke.results)} verificações OK")
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
