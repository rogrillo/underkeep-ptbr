"""Localização da instalação Steam do Underkeep (somente leitura).

Fontes consultadas, nesta ordem, sem nunca escrever nelas:

1. ``SteamPath`` / ``InstallPath`` no Registro do Windows (apenas leitura via ``winreg``);
2. caminhos padrão da Steam (Windows e Linux/SteamOS);
3. ``steamapps/libraryfolders.vdf`` de cada raiz, para bibliotecas em outros discos;
4. ``steamapps/appmanifest_2411200.acf`` de cada biblioteca, que traz ``installdir`` e ``buildid``;
5. no Linux/Steam Deck, ``steamapps/compatdata/2411200/pfx/drive_c/users/steamuser/Documents`` — a pasta
   Documentos que o jogo enxerga dentro do prefixo Proton.

Caminhos equivalentes (links simbólicos como ``~/.steam/steam`` → ``~/.local/share/Steam``) são
reconhecidos pelo caminho real, para não aparecerem como instalações diferentes.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Iterable

APP_ID = "2411200"
GAME_EXE = "underkeep.exe"
DEFAULT_INSTALLDIR = "Underkeep"
# Pasta Documentos do usuário Wine nos prefixos Proton (versões antigas usavam "My Documents").
PROTON_DOCUMENTS = (("pfx", "drive_c", "users", "steamuser", "Documents"),
                    ("pfx", "drive_c", "users", "steamuser", "My Documents"))

_VDF_PAIR = re.compile(r'"((?:[^"\\]|\\.)*)"\s+"((?:[^"\\]|\\.)*)"')


def _unescape(value: str) -> str:
    return value.replace("\\\\", "\\").replace('\\"', '"')


def vdf_pairs(text: str) -> list[tuple[str, str]]:
    """Pares ``"chave" "valor"`` de um arquivo VDF/ACF (estrutura aninhada ignorada)."""
    return [(_unescape(k), _unescape(v)) for k, v in _VDF_PAIR.findall(text)]


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def registry_steam_roots() -> list[Path]:
    """Raízes da Steam registradas no Windows (leitura do Registro; nada é gravado)."""
    if sys.platform != "win32":
        return []
    import winreg

    found: list[Path] = []
    keys = [(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")]
    for hive, sub, name in keys:
        try:
            with winreg.OpenKey(hive, sub, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, name)
        except OSError:
            continue
        if isinstance(value, str) and value.strip():
            found.append(Path(value))
    return found


def default_steam_roots() -> list[Path]:
    roots: list[Path] = []
    if sys.platform == "win32":
        for env in ("ProgramFiles(x86)", "ProgramFiles"):
            base = os.environ.get(env)
            if base:
                roots.append(Path(base) / "Steam")
    else:
        home = Path.home()
        roots += [home / ".local" / "share" / "Steam", home / ".steam" / "steam", home / ".steam" / "root",
                  home / ".steam" / "debian-installation",
                  home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"]
    return roots


def library_folders(steam_root: Path) -> list[Path]:
    """Bibliotecas declaradas em ``libraryfolders.vdf`` (inclui a própria raiz)."""
    libraries = [steam_root]
    for vdf in (steam_root / "steamapps" / "libraryfolders.vdf", steam_root / "config" / "libraryfolders.vdf"):
        text = _read_text(vdf)
        if text is None:
            continue
        libraries += [Path(value) for key, value in vdf_pairs(text) if key == "path" and value.strip()]
    return libraries


def _dedupe(paths: Iterable[Path]) -> list[Path]:
    """Remove repetições, comparando pelo caminho real (resolve links simbólicos)."""
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        key = os.path.normcase(os.path.realpath(path))
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def game_dir_in_library(library: Path) -> Path | None:
    """Pasta do jogo numa biblioteca, se o manifesto do app ou a pasta padrão existir."""
    steamapps = library / "steamapps"
    installdir = DEFAULT_INSTALLDIR
    text = _read_text(steamapps / f"appmanifest_{APP_ID}.acf")
    if text is not None:
        installdir = dict(vdf_pairs(text)).get("installdir") or DEFAULT_INSTALLDIR
    candidate = steamapps / "common" / installdir
    return candidate if (candidate / GAME_EXE).is_file() else None


def all_libraries(steam_roots: Iterable[Path] | None = None) -> list[Path]:
    """Todas as bibliotecas Steam conhecidas (SSD interno, microSD, outros discos), sem repetição."""
    roots = list(steam_roots) if steam_roots is not None else registry_steam_roots() + default_steam_roots()
    return _dedupe(lib for root in _dedupe(roots) for lib in library_folders(root))


def find_game_dirs(steam_roots: Iterable[Path] | None = None) -> list[Path]:
    """Instalações do Underkeep encontradas (pode ser vazia; nunca levanta por caminho inexistente)."""
    return _dedupe(game for lib in all_libraries(steam_roots) if (game := game_dir_in_library(lib)) is not None)


def library_of_game(game_root: Path) -> Path | None:
    """Biblioteca que contém ``<biblioteca>/steamapps/common/<jogo>``; ``None`` se o layout não for esse."""
    if game_root.parent.name.lower() != "common" or game_root.parent.parent.name.lower() != "steamapps":
        return None
    return game_root.parent.parent.parent


def proton_documents_in_library(library: Path) -> list[Path]:
    """Pastas Documentos do prefixo Proton do Underkeep nessa biblioteca (existentes)."""
    prefix = library / "steamapps" / "compatdata" / APP_ID
    return _dedupe(p for parts in PROTON_DOCUMENTS if (p := prefix.joinpath(*parts)).is_dir())


@dataclass
class ProtonDocuments:
    """Resultado da busca pela pasta Documentos do Proton.

    ``matched`` só é preenchido quando a correspondência com o jogo é inequívoca: o prefixo está na
    mesma biblioteca da instalação do jogo e há uma única pasta candidata ali (ou uma única que já
    contém ``Underkeep``). Os demais casos ficam em ``candidates`` e exigem escolha do jogador.
    """

    matched: Path | None
    candidates: list[Path]


def find_proton_documents(game_root: Path | None, steam_roots: Iterable[Path] | None = None) -> ProtonDocuments:
    own: list[Path] = []
    library = library_of_game(game_root) if game_root is not None else None
    if library is not None:
        own = proton_documents_in_library(library)
    others = [doc for lib in all_libraries(steam_roots) for doc in proton_documents_in_library(lib)]
    candidates = _dedupe(own + others)
    matched: Path | None = None
    with_game_dir = [doc for doc in own if (doc / DEFAULT_INSTALLDIR).is_dir()]
    if len(with_game_dir) == 1:
        matched = with_game_dir[0]
    elif len(own) == 1 and not with_game_dir:
        matched = own[0]
    return ProtonDocuments(matched, candidates)


def game_build(game_root: Path) -> str | None:
    """``buildid`` do manifesto Steam ao lado da pasta do jogo (``steamapps/appmanifest_*.acf``)."""
    text = _read_text(game_root.parent.parent / f"appmanifest_{APP_ID}.acf")
    if text is None:
        return None
    return dict(vdf_pairs(text)).get("buildid")
