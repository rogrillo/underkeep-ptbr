#!/usr/bin/env python3
"""Gera os pacotes de release (release candidata; NÃO publica nada).

Pacotes:
* ``Underkeep-PTBR-v<versão>-Windows.zip``: ``Instalar-``/``Desinstalar-Underkeep-PTBR.exe`` gerados com
  PyInstaller (``requirements-build.txt``), ``dados/pt-BR``, LEIA-ME, VERSAO, licenças do projeto e de terceiros;
* ``Underkeep-PTBR-v<versão>-SteamDeck.zip``: ``Instalador-Underkeep-PTBR.sh`` (executável),
  ``app/underkeep_ptbr.py`` + somente os módulos de ``ukloc`` que o instalador importa (código-fonte,
  sem ``__pycache__``), ``dados/pt-BR``, LEIA-ME, VERSAO e licenças do projeto. Usa o Python do SteamOS.

Os dois levam ``licencas/`` com a licença MIT do código, a CC BY-NC-SA 4.0 da tradução e o aviso legal.
A auditoria também confere que a versão do nome do pacote aparece em VERSAO.txt, LEIA-ME.txt e, no Deck,
em ``installer.VERSION``.

Etapas: confere o catálogo versionado; monta cada pacote; compacta de forma determinística em
``dist/<nome>.zip`` (caminhos POSIX ``/``, permissões Unix gravadas: 755 no ``.sh``, 644 no resto) e grava
``<nome>.zip.sha256``; audita o ZIP (extensões/nomes proibidos, caminhos inseguros ou com ``\\``, caches
Python, permissões, fins de linha LF nos scripts, catálogo sem campos estranhos, caminhos e e-mail do
desenvolvedor ausentes, arquivos previstos, tamanho).

Uso: ``python scripts/build_release.py [--plataforma windows|steamdeck|todas] [--skip-exe]``
(``--skip-exe`` reaproveita os .exe já gerados).
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
from hashlib import sha256
from importlib import metadata
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ukloc import l10n  # noqa: E402
from ukloc.installer import VERSION  # noqa: E402

PACKAGE_NAME = f"Underkeep-PTBR-v{VERSION}-Windows"
DECK_PACKAGE_NAME = f"Underkeep-PTBR-v{VERSION}-SteamDeck"
DECK_SOURCES = PROJECT_ROOT / "release" / "steamdeck"
DECK_LAUNCHER = "Instalador-Underkeep-PTBR.sh"
DECK_ENTRY_MODULES = ("ukloc.gui",)  # o fechamento de imports traz installer, shadow, l10n, steam, formats...
BUILD_DIR = PROJECT_ROOT / "build" / "release"
DIST_DIR = PROJECT_ROOT / "dist"
EXES = {"Instalar-Underkeep-PTBR": PROJECT_ROOT / "release" / "instalar.py",
        "Desinstalar-Underkeep-PTBR": PROJECT_ROOT / "release" / "desinstalar.py"}
CATALOG_FILES = ("project.json", "common.json", "game.json", "items.json", "skills.json")
FORBIDDEN_SUFFIXES = (".rfile", ".db", ".level", ".dds", ".wav", ".ogg", ".mp3", ".sav", ".clip", ".gzf",
                      ".gpr", ".dmp", ".pak", ".csv", ".xlsx", ".log", ".md", ".pyc", ".pyo", ".tmp")
LF_ONLY_SUFFIXES = (".sh", ".py")
FORBIDDEN_NAMES = ("underkeep.exe", "game_config.txt", "player_profile", "save_auto", "save_quick")
# Licenças e aviso legal do projeto, presentes nos dois pacotes (destino -> origem na raiz do repositório).
PROJECT_LICENSES = {"licencas/LICENCA-CODIGO-MIT.txt": "LICENSE",
                    "licencas/LICENCA-TRADUCAO-CC-BY-NC-SA-4.0.txt": "LICENSE-TRADUCAO.md",
                    "licencas/AVISO-LEGAL.txt": "AVISO_LEGAL.md"}
ZIP_TIME = (2026, 1, 1, 0, 0, 0)
MAX_ZIP_BYTES = 40 * 1024 * 1024


class ReleaseError(Exception):
    pass


@dataclass
class PackageSpec:
    """O que um pacote deve conter (caminhos relativos à pasta raiz do pacote)."""

    name: str
    expected: set[str]
    allowed_dirs: tuple[str, ...] = ()  # conteúdo livre nessas subpastas (ex.: licenças)
    executables: set[str] = field(default_factory=set)


def windows_spec() -> PackageSpec:
    files = {"Instalar-Underkeep-PTBR.exe", "Desinstalar-Underkeep-PTBR.exe", "LEIA-ME.txt", "VERSAO.txt"}
    files |= {f"dados/pt-BR/{n}" for n in CATALOG_FILES} | set(PROJECT_LICENSES)
    return PackageSpec(PACKAGE_NAME, files, allowed_dirs=("licencas/",))


def deck_spec() -> PackageSpec:
    files = {DECK_LAUNCHER, "LEIA-ME.txt", "VERSAO.txt", "app/underkeep_ptbr.py"}
    files |= {f"dados/pt-BR/{n}" for n in CATALOG_FILES} | set(PROJECT_LICENSES)
    files |= {f"app/{rel}" for rel in module_files(DECK_ENTRY_MODULES)}
    return PackageSpec(DECK_PACKAGE_NAME, files, executables={DECK_LAUNCHER})


def _module_path(module: str) -> Path | None:
    base = PROJECT_ROOT.joinpath(*module.split("."))
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return base.with_suffix(".py") if base.with_suffix(".py").is_file() else None


def module_files(entries: tuple[str, ...]) -> list[str]:
    """Arquivos ``.py`` de ``ukloc`` alcançados pelos imports a partir de ``entries`` (relativos à raiz).

    Inclui os ``__init__.py`` dos pacotes intermediários. Imports fora de ``ukloc`` precisam ser da
    biblioteca padrão; o teste de fumaça do pacote extraído confirma que nada falta.
    """
    seen: set[str] = set()
    pending = list(entries)
    while pending:
        module = pending.pop()
        if module in seen:
            continue
        path = _module_path(module)
        if path is None:
            continue
        seen.add(module)
        parts = module.split(".")
        for n in range(1, len(parts)):
            pending.append(".".join(parts[:n]))
        package = module if path.name == "__init__.py" else ".".join(parts[:-1])
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level:
                anchor = package.split(".")[: len(package.split(".")) - (node.level - 1)]
                target = ".".join(anchor + ([node.module] if node.module else []))
                pending.append(target)
                pending += [f"{target}.{alias.name}" for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "ukloc":
                pending.append(node.module)
                pending += [f"{node.module}.{alias.name}" for alias in node.names]
            elif isinstance(node, ast.Import):
                pending += [alias.name for alias in node.names if alias.name.split(".")[0] == "ukloc"]
    return sorted(_module_path(m).relative_to(PROJECT_ROOT).as_posix() for m in seen)  # type: ignore[union-attr]


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def private_markers() -> list[bytes]:
    """Marcas que não podem aparecer no pacote: pasta do usuário, nome da conta, e-mail do Git."""
    markers = {str(Path.home()), Path.home().name, str(PROJECT_ROOT)}
    try:
        email = subprocess.run(["git", "config", "user.email"], cwd=PROJECT_ROOT, capture_output=True,
                               text=True, check=False).stdout.strip()
    except OSError:
        email = ""
    if email:
        markers.add(email)
    found: list[bytes] = []
    for marker in markers:
        if len(marker) >= 4:
            found += [marker.encode("utf-8"), marker.encode("utf-16-le"),
                      marker.replace("\\", "/").encode("utf-8")]
    return found


def check_catalog() -> None:
    root = PROJECT_ROOT / "l10n" / "pt-BR"
    status = subprocess.run(["git", "status", "--porcelain", "--", "l10n/pt-BR"], cwd=PROJECT_ROOT,
                            capture_output=True, text=True, check=False).stdout.strip()
    if status:
        print(f"AVISO: l10n/pt-BR tem alterações não commitadas:\n{status}")
    for category, catalog in l10n.load_catalogs(root).items():  # valida estrutura e campos permitidos
        pending = [i for i, e in catalog.entries.items() if not e.is_applicable("translated")]
        if pending:
            print(f"AVISO: {category}: {len(pending)} entradas não aplicáveis (pending/needs_review)")


def build_exes() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for name, script in EXES.items():
        cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onefile", "--console",
               "--name", name, "--paths", str(PROJECT_ROOT),
               "--distpath", str(BUILD_DIR / "exe"), "--workpath", str(BUILD_DIR / "work"),
               "--specpath", str(BUILD_DIR / "spec"),
               "--exclude-module", "tkinter", "--exclude-module", "unittest", "--exclude-module", "pytest",
               "--exclude-module", "pydoc", "--exclude-module", "sqlite3",
               str(script)]
        print("PyInstaller:", name)
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise ReleaseError(f"PyInstaller falhou para {name}:\n{result.stderr[-3000:]}")
        out[name] = BUILD_DIR / "exe" / f"{name}.exe"
    return out


def third_party_licenses(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise ReleaseError(f"licença do Python não encontrada em {python_license}")
    shutil.copyfile(python_license, target / "PYTHON-LICENSE.txt")
    dist = metadata.distribution("pyinstaller")
    copied = False
    for file in dist.files or []:
        if file.name.upper().startswith(("COPYING", "LICENSE")):
            shutil.copyfile(Path(dist.locate_file(file)), target / "PYINSTALLER-COPYING.txt")
            copied = True
            break
    if not copied:
        raise ReleaseError("licença do PyInstaller não encontrada")
    (target / "LEIA-ME-LICENCAS.txt").write_text(
        "Os executáveis foram gerados com PyInstaller e incluem o interpretador Python.\r\n"
        "- Python: Python Software Foundation License (PYTHON-LICENSE.txt).\r\n"
        "- PyInstaller: GPL com exceção que permite distribuir executáveis gerados (PYINSTALLER-COPYING.txt).\r\n"
        "Estas licenças não se aplicam ao jogo Underkeep, que pertence à Rake in Grass.\r\n", encoding="utf-8")


def project_licenses(stage: Path, *, windows: bool) -> None:
    """Copia LICENSE, LICENSE-TRADUCAO.md e AVISO_LEGAL.md como ``.txt`` (CRLF+BOM no Windows, LF no Deck)."""
    for dest, source in PROJECT_LICENSES.items():
        text = (PROJECT_ROOT / source).read_text(encoding="utf-8")
        target = stage / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(crlf(text).encode("utf-8-sig") if windows else lf(text).encode("utf-8"))


def crlf(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def assemble(exes: dict[str, Path]) -> Path:
    project = l10n.load_project(PROJECT_ROOT / "l10n" / "pt-BR" / "project.json")
    stage = BUILD_DIR / "stage" / PACKAGE_NAME
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "dados" / "pt-BR").mkdir(parents=True)
    for name, exe in exes.items():
        if not exe.is_file():
            raise ReleaseError(f"executável ausente: {exe} (rode sem --skip-exe)")
        shutil.copyfile(exe, stage / exe.name)
    for name in CATALOG_FILES:
        shutil.copyfile(PROJECT_ROOT / "l10n" / "pt-BR" / name, stage / "dados" / "pt-BR" / name)
    readme = (PROJECT_ROOT / "release" / "LEIA-ME.txt").read_text(encoding="utf-8")
    readme = readme.replace("{VERSION}", VERSION).replace("{BUILD}", str(project.expected_build))
    (stage / "LEIA-ME.txt").write_bytes(crlf(readme).encode("utf-8-sig"))
    version = version_info(["Windows 11 x64: instalação pelo .exe, jogo traduzido e desinstalação (playtest)"],
                           ["Windows 10"])
    (stage / "VERSAO.txt").write_bytes(crlf(
        f"Underkeep PT-BR {VERSION}\nBuild Steam suportada: {project.expected_build}\n\n"
        + json.dumps(version, ensure_ascii=False, indent=2) + "\n").encode("utf-8-sig"))
    third_party_licenses(stage / "licencas")
    project_licenses(stage, windows=True)
    return stage


def lf(text: str) -> str:
    return text.replace("\r\n", "\n")


def version_info(platforms_tested: list[str], platforms_untested: list[str]) -> dict:
    project = l10n.load_project(PROJECT_ROOT / "l10n" / "pt-BR" / "project.json")
    return {"traducao": VERSION, "jogo": "Underkeep (Steam AppID 2411200)",
            "build_steam_suportada": project.expected_build,
            "underkeep_exe_sha256": project.expected_exe_sha256,
            "plataformas_testadas": platforms_tested, "plataformas_nao_testadas": platforms_untested,
            "politica_de_build": "translated (revisão humana em andamento)"}


def assemble_deck() -> Path:
    """Pasta do pacote Steam Deck: só código-fonte do instalador, catálogos e textos (LF, sem BOM)."""
    project = l10n.load_project(PROJECT_ROOT / "l10n" / "pt-BR" / "project.json")
    stage = BUILD_DIR / "stage" / DECK_PACKAGE_NAME
    if stage.exists():
        shutil.rmtree(stage)
    (stage / "dados" / "pt-BR").mkdir(parents=True)
    (stage / "app").mkdir()
    for name in CATALOG_FILES:
        shutil.copyfile(PROJECT_ROOT / "l10n" / "pt-BR" / name, stage / "dados" / "pt-BR" / name)
    for rel in module_files(DECK_ENTRY_MODULES):
        target = stage / "app" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(lf((PROJECT_ROOT / rel).read_text(encoding="utf-8")).encode("utf-8"))
    for name, dest in (("underkeep_ptbr.py", stage / "app" / "underkeep_ptbr.py"),
                       (DECK_LAUNCHER, stage / DECK_LAUNCHER)):
        dest.write_bytes(lf((DECK_SOURCES / name).read_text(encoding="utf-8")).encode("utf-8"))
    readme = (DECK_SOURCES / "LEIA-ME.txt").read_text(encoding="utf-8")
    readme = readme.replace("{VERSION}", VERSION).replace("{BUILD}", str(project.expected_build))
    (stage / "LEIA-ME.txt").write_bytes(lf(readme).encode("utf-8"))
    info = version_info(["Steam Deck / SteamOS, modo Desktop: janela kdialog, instalação, jogo traduzido pelo "
                         "Proton e desinstalação (playtest da beta.2)",
                         "Steam Deck pelo terminal com o Python do SteamOS (playtest da beta.1)"],
                        ["zenity em outros ambientes gráficos", "outras distribuições Linux"])
    (stage / "VERSAO.txt").write_bytes(lf(
        f"Underkeep PT-BR {VERSION} (Steam Deck / Linux)\nBuild Steam suportada: {project.expected_build}\n\n"
        + json.dumps(info, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    project_licenses(stage, windows=False)
    return stage


def make_zip(stage: Path, package_name: str = PACKAGE_NAME, executables: set[str] | None = None) -> Path:
    """ZIP determinístico com caminhos POSIX e permissões Unix (``create_system=3``).

    O ``create_system=3`` é o que faz o Ark/``unzip`` respeitarem as permissões gravadas; sem ele o
    ``.sh`` chegaria ao Linux sem permissão de execução.
    """
    executables = executables or set()
    DIST_DIR.mkdir(exist_ok=True)
    target = DIST_DIR / f"{package_name}.zip"
    tmp = target.with_suffix(".zip.tmp")
    entries = sorted(p for p in stage.rglob("*") if p.is_file() or p.is_dir())
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        root = zipfile.ZipInfo(f"{package_name}/", ZIP_TIME)
        root.create_system = 3
        root.external_attr = (stat.S_IFDIR | 0o755) << 16 | 0x10
        zf.writestr(root, b"")
        for path in entries:
            rel = path.relative_to(stage).as_posix()
            if path.is_dir():
                info = zipfile.ZipInfo(f"{package_name}/{rel}/", ZIP_TIME)
                info.create_system = 3
                info.external_attr = (stat.S_IFDIR | 0o755) << 16 | 0x10
                zf.writestr(info, b"")
                continue
            info = zipfile.ZipInfo(f"{package_name}/{rel}", ZIP_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | (0o755 if rel in executables else 0o644)) << 16
            zf.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    os.replace(tmp, target)
    digest = file_sha256(target)
    target.with_name(target.name + ".sha256").write_text(f"{digest} *{target.name}\n", encoding="ascii",
                                                          newline="\n")
    return target


def pyinstaller_payloads(exe_bytes: bytes) -> list[tuple[str, bytes]]:
    """Conteúdo descomprimido de um .exe do PyInstaller (CArchive + módulos do PYZ)."""
    from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

    out: list[tuple[str, bytes]] = []
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "a.exe"
        exe.write_bytes(exe_bytes)
        archive = CArchiveReader(str(exe))
        for name in archive.toc:
            data = archive.extract(name)
            if not isinstance(data, bytes):
                continue
            out.append((name, data))
            if "PYZ" in name:
                pyz = Path(tmp) / "a.pyz"
                pyz.write_bytes(data)
                reader = ZlibArchiveReader(str(pyz))
                for module in reader.toc:
                    code = reader.extract(module, raw=True)
                    if isinstance(code, bytes):
                        out.append((f"{name}:{module}", code))
    return out


def version_problems(zf: zipfile.ZipFile, spec: PackageSpec, names: set[str]) -> list[str]:
    """A versão do nome do pacote tem de aparecer em VERSAO.txt, LEIA-ME.txt e, no Deck, em ``installer.VERSION``."""
    match = re.fullmatch(r"Underkeep-PTBR-v(?P<v>[0-9][0-9A-Za-z.\-]*?)-(?:Windows|SteamDeck)", spec.name)
    if not match:
        return [f"nome de pacote fora do padrão: {spec.name}"]
    version = match["v"]
    prefix = f"{spec.name}/"
    problems: list[str] = []
    for rel, needle in (("VERSAO.txt", f"Underkeep PT-BR {version}"), ("LEIA-ME.txt", f"UNDERKEEP PT-BR {version}")):
        if prefix + rel in names and needle not in zf.read(prefix + rel).decode("utf-8-sig", "replace"):
            problems.append(f"{rel} não mostra a versão {version}")
    installer = prefix + "app/ukloc/installer.py"
    if installer in names:
        found = re.search(r'^VERSION = "([^"]+)"', zf.read(installer).decode("utf-8"), re.M)
        if not found or found.group(1) != version:
            problems.append(f"installer.VERSION ({found.group(1) if found else '?'}) difere do pacote ({version})")
    return problems


def audit_zip(path: Path, spec: PackageSpec | None = None) -> list[str]:
    spec = spec or windows_spec()
    problems: list[str] = []
    markers = private_markers()
    allowed_fields = set(l10n.ENTRY_FIELDS)
    prefix = f"{spec.name}/"
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        names = [i.filename for i in infos if not i.is_dir()]
        for info in infos:
            name = info.filename
            raw = info.orig_filename  # nome gravado no ZIP (no Windows, ``filename`` já vem com "/")
            if "\\" in raw or raw.startswith("/") or ".." in raw.replace("\\", "/").split("/") or ":" in raw:
                problems.append(f"caminho inseguro ou não POSIX no ZIP: {raw!r}")
            if not name.startswith(prefix):
                problems.append(f"fora da pasta do pacote: {name}")
            if "__pycache__" in name.split("/"):
                problems.append(f"cache Python no pacote: {name}")
            if info.create_system != 3:
                problems.append(f"permissões Unix ausentes (create_system={info.create_system}): {name}")
            if not info.is_dir():
                mode = (info.external_attr >> 16) & 0o777
                want = 0o755 if name[len(prefix):] in spec.executables else 0o644
                if mode != want:
                    problems.append(f"permissão {oct(mode)} em {name} (esperado {oct(want)})")
        for name in names:
            low = name.lower()
            if low.endswith(FORBIDDEN_SUFFIXES) or Path(low).name in FORBIDDEN_NAMES:
                problems.append(f"arquivo proibido no pacote: {name}")
            data = zf.read(name)
            if low.endswith(LF_ONLY_SUFFIXES) and b"\r" in data:
                problems.append(f"fim de linha CRLF em {name} (quebra o script no Linux)")
            blobs = [(name, data)]
            if low.endswith(".exe"):
                blobs += [(f"{name}::{inner}", payload) for inner, payload in pyinstaller_payloads(data)]
            for label, blob in blobs:
                if any(marker in blob for marker in markers):
                    problems.append(f"dado privado/caminho do desenvolvedor em {label}")
            if low.endswith(".json") and "/dados/pt-br/" in low and not low.endswith("project.json"):
                catalog = json.loads(data.decode("utf-8"))
                for entry_id, entry in catalog.get("entries", {}).items():
                    if set(entry) - allowed_fields:
                        problems.append(f"campo inesperado em {name}:{entry_id}")
                        break
        problems += version_problems(zf, spec, set(names))
        expected = {prefix + n for n in spec.expected}
        missing = sorted(expected - set(names))
        if missing:
            problems.append(f"faltando no pacote: {missing}")
        unexpected = sorted(n for n in names if n not in expected
                            and not any(n.startswith(prefix + d) for d in spec.allowed_dirs))
        if unexpected:
            problems.append(f"arquivos não previstos: {unexpected}")
    if path.stat().st_size > MAX_ZIP_BYTES:
        problems.append(f"pacote grande demais: {path.stat().st_size} bytes")
    return problems


def build_windows(skip_exe: bool) -> tuple[Path, PackageSpec]:
    exes = ({n: BUILD_DIR / "exe" / f"{n}.exe" for n in EXES} if skip_exe else build_exes())
    return make_zip(assemble(exes)), windows_spec()


def build_deck() -> tuple[Path, PackageSpec]:
    spec = deck_spec()
    return make_zip(assemble_deck(), DECK_PACKAGE_NAME, spec.executables), spec


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--plataforma", choices=("windows", "steamdeck", "todas"), default="todas")
    parser.add_argument("--skip-exe", action="store_true", help="reaproveita os .exe de build/release/exe")
    args = parser.parse_args(argv)
    failed = False
    try:
        check_catalog()
        built: list[tuple[Path, PackageSpec]] = []
        if args.plataforma in {"windows", "todas"}:
            built.append(build_windows(args.skip_exe))
        if args.plataforma in {"steamdeck", "todas"}:
            built.append(build_deck())
        for zip_path, spec in built:
            problems = audit_zip(zip_path, spec)
            print(f"Pacote: {zip_path} ({zip_path.stat().st_size / 2**20:.2f} MB)")
            print(f"SHA-256: {file_sha256(zip_path)}")
            if problems:
                failed = True
                print("AUDITORIA FALHOU:")
                for problem in problems:
                    print(f"  - {problem}")
            else:
                print("Auditoria do conteúdo: OK (sem arquivos do jogo, sem dados privados, estrutura POSIX)")
    except (ReleaseError, l10n.CatalogError, OSError, ValueError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
